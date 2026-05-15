import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes.api_monitor import router as api_monitor_router
from app.api.routes.data_hub import router as data_hub_router
from app.api.routes.flights import router as flights_router
from app.api.routes.health import router as health_router
from app.api.routes.insights import router as insights_router
from app.api.routes.map_proxy import router as map_proxy_router
from app.api.routes.playback import router as playback_router
from app.api.ws.flights_ws import router as ws_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.db import close_db, init_db
from app.state import unified_pipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    logger.info("starting backend service")
    await init_db()
    await unified_pipeline.start()
    host = settings.app_host if settings.app_host != "0.0.0.0" else "localhost"
    port = settings.app_port
    logger.info("backend ready → http://%s:%d/", host, port)
    logger.info("  主界面     http://%s:%d/debug/flights-dashboard", host, port)
    logger.info("  API 监控   http://%s:%d/debug/api-monitor", host, port)
    logger.info("  API 文档   http://%s:%d/docs", host, port)
    try:
        yield
    finally:
        await unified_pipeline.stop()
        await close_db()
        logger.info("stopping backend service")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/debug/flights-dashboard")


app.include_router(health_router)
app.include_router(insights_router)
app.include_router(api_monitor_router)
app.include_router(map_proxy_router)
app.include_router(flights_router)
app.include_router(data_hub_router)
app.include_router(playback_router)
app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
