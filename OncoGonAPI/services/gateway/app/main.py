"""OncoGon API gateway — the single public entry point. Routes /api/v1/<service>/... to microservices."""

import logging
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .ratelimit import SlidingWindowLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("oncogon.gateway")
settings = get_settings()

# Service registry: public prefix -> internal base URL and path prefix.
SERVICES = {"auth": (settings.auth_service_url, "/auth")}
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
    if target is None:
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
    try:
        upstream = await request.app.state.http.request(
            request.method,
            f"{base}{prefix}/{path}",
            params=request.query_params,
            content=await request.body(),
            headers=headers,
        )
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
    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)
