"""OncoGon API gateway — the single public entry point. Routes /api/v1/<service>/... to microservices."""

import asyncio
import contextlib
import logging
import re
import uuid
from contextlib import asynccontextmanager

import httpx
import websockets
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from .config import get_settings
from .ratelimit import SlidingWindowLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("oncogon.gateway")
settings = get_settings()

# Service registry: public prefix -> internal base URL and path prefix.
SERVICES = {
    "auth": (settings.auth_service_url, "/auth"),
    "research": (settings.research_service_url, "/research"),
    # Voice backend (oncogon-tts-sst): STT, assistant (LLM + RAG), TTS in the cloned voice, recordings.
    "voice": (settings.voice_service_url, "/api/v1"),
}
# Voice answers (STT → LLM → TTS) take far longer than a JSON lookup; streams send events as they go.
SERVICE_TIMEOUTS = {"voice": settings.voice_timeout_seconds, "research": settings.research_timeout_seconds}
# Not exposed to the app: the voice backend's own user accounts (the platform's auth service is the
# only sign-in) and voice cloning (an admin task that spends ElevenLabs credits).
BLOCKED_PATHS = {"voice": ("auth", "voice-clone")}
# WebSocket routes the app may open (live transcription while recording). Everything else is HTTP only.
WEBSOCKET_PATHS = {"voice": ("stt/live",)}
# Headers passed to a WebSocket upstream: auth and the display time zone, nothing else.
WEBSOCKET_HEADERS = {"authorization", "x-api-key", "x-timezone"}
RATE_LIMITED_PATHS = {"login", "register", "password/forgot", "password/verify", "password/reset"}
HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "te", "upgrade", "proxy-authorization", "host", "content-length"}

limiter = SlidingWindowLimiter(settings.auth_rate_limit_per_minute)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=settings.upstream_timeout_seconds)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="OncoGon API Gateway",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


def is_blocked(service: str, path: str) -> bool:
    segments = [s for s in path.split("/") if s]
    if any(s in {".", ".."} for s in segments):  # no escaping the service prefix
        return True
    return bool(segments) and segments[0] in BLOCKED_PATHS.get(service, ())


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


@app.get("/health", tags=["health"])
async def health(request: Request):
    results: dict[str, str] = {}
    for name, (base, _) in SERVICES.items():
        try:
            r = await request.app.state.http.get(f"{base}/health", timeout=3)
            results[name] = "ok" if r.status_code == 200 else f"error ({r.status_code})"
        except httpx.HTTPError:
            results[name] = "unreachable"
    ok = all(v == "ok" for v in results.values())
    return JSONResponse({"status": "ok" if ok else "degraded", "services": results}, status_code=200 if ok else 503)


@app.api_route("/api/v1/{service}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(service: str, path: str, request: Request):
    target = SERVICES.get(service)
    if target is None or is_blocked(service, path):
        return JSONResponse({"detail": "Not found."}, status_code=404)

    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    ip = client_ip(request)

    if service == "auth" and request.method == "POST" and path.rstrip("/") in RATE_LIMITED_PATHS:
        allowed, retry_after = limiter.allow(f"{ip}:{path}")
        if not allowed:
            return JSONResponse(
                {"detail": "Too many requests. Please wait a moment and try again."},
                status_code=429,
                headers={"Retry-After": str(retry_after), "X-Request-ID": request_id},
            )

    base, prefix = target
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    headers.update({"x-request-id": request_id, "x-forwarded-for": ip})
    http: httpx.AsyncClient = request.app.state.http
    upstream_request = http.build_request(
        request.method,
        f"{base}{prefix}/{path}",
        params=request.query_params,
        content=await request.body(),
        headers=headers,
        timeout=SERVICE_TIMEOUTS.get(service, settings.upstream_timeout_seconds),
    )
    try:
        # Streamed, so Server-Sent Events (voice answers) reach the app as they are produced.
        upstream = await http.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        log.error("Upstream %s failed (%s): %s", service, request_id, exc)
        return JSONResponse(
            {"detail": "Service temporarily unavailable."},
            status_code=503,
            headers={"X-Request-ID": request_id},
        )

    log.info("%s %s -> %s %s [%s]", request.method, request.url.path, service, upstream.status_code, request_id)
    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP | {"content-encoding"}}
    response_headers["X-Request-ID"] = request_id
    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        headers=response_headers,
        background=BackgroundTask(upstream.aclose),
    )


@app.websocket("/api/v1/{service}/{path:path}")
async def proxy_websocket(websocket: WebSocket, service: str, path: str):
    target = SERVICES.get(service)
    if target is None or is_blocked(service, path) or path.strip("/") not in WEBSOCKET_PATHS.get(service, ()):
        await websocket.close(code=1008)
        return

    request_id = websocket.headers.get("x-request-id") or uuid.uuid4().hex
    base, prefix = target
    url = re.sub(r"^http", "ws", base) + f"{prefix}/{path}"
    headers = {k: v for k, v in websocket.headers.items() if k.lower() in WEBSOCKET_HEADERS}
    forwarded = websocket.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (websocket.client.host if websocket.client else "unknown")
    headers.update({"x-request-id": request_id, "x-forwarded-for": ip})
    try:
        upstream = await websockets.connect(url, additional_headers=headers, max_size=2**20, open_timeout=10)
    except websockets.InvalidStatus as exc:
        status = exc.response.status_code
        log.info("WS %s -> %s refused %s [%s]", websocket.url.path, service, status, request_id)
        if status in (401, 403):
            # Accept, then close with 4401: unlike a refused handshake (which looks the same as a
            # network failure), the app can tell the token was rejected and refresh it.
            await websocket.accept()
            await websocket.close(code=4401)
        else:
            await websocket.close(code=1011)
        return
    except (OSError, TimeoutError, websockets.WebSocketException) as exc:
        log.error("Upstream %s websocket failed (%s): %s", service, request_id, type(exc).__name__)
        await websocket.close(code=1011)
        return

    await websocket.accept()
    log.info("WS %s -> %s opened [%s]", websocket.url.path, service, request_id)

    async def client_to_upstream() -> None:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            if message.get("bytes") is not None:
                await upstream.send(message["bytes"])
            elif message.get("text") is not None:
                await upstream.send(message["text"])

    async def upstream_to_client() -> None:
        async for message in upstream:
            if isinstance(message, bytes):
                await websocket.send_bytes(message)
            else:
                await websocket.send_text(message)

    tasks = [asyncio.create_task(client_to_upstream()), asyncio.create_task(upstream_to_client())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
            with contextlib.suppress(BaseException):
                await task
        await upstream.close()
        with contextlib.suppress(Exception):  # already closed by the app
            await websocket.close(code=upstream.close_code or 1000)
        log.info("WS %s -> %s closed %s [%s]", websocket.url.path, service, upstream.close_code, request_id)
