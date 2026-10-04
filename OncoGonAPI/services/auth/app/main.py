import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .api.routes import router
from .config import get_settings
from .db import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()

app = FastAPI(
    title="OncoGon Auth Service",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url=None,
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    """Return the first readable message as `detail` (what the app shows) plus the full list."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:])
    msg = str(first.get("msg", "Invalid request.")).removeprefix("Value error, ")
    detail = msg if not field or msg.lower().startswith(field.split(".")[-1]) else f"{field.replace('_', ' ').capitalize()}: {msg}"
    return JSONResponse(status_code=422, content={"detail": detail, "errors": jsonable_encoder(errors)})


@app.get("/health", tags=["health"])
async def health():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "service": "auth", "database": "ok"}
