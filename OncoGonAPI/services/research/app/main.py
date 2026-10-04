import logging

from fastapi import FastAPI, Request

from .api.routes import router
from .config import get_settings
from .deps import get_repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()

app = FastAPI(
    title="OncoGon Research Service",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url=None,
)
app.include_router(router)


@app.middleware("http")
async def data_mode_header(request: Request, call_next):
    """Labels every response with where its data came from (SIMULATED while on mock data)."""
    response = await call_next(request)
    response.headers["X-Data-Mode"] = get_repository().get_meta().get("data_mode", "RESEARCH")
    return response


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "research", "data_mode": get_repository().get_meta().get("data_mode")}
