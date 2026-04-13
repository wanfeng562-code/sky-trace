import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes.flights import router as flights_router
from app.api.routes.health import router as health_router
from app.api.routes.insights import router as insights_router
from app.api.ws.flights_ws import router as ws_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.state import flight_store, mock_collector

logger = logging.getLogger(__name__)
_collector_task: asyncio.Task | None = None


async def _collector_loop() -> None:
    """Background loop to update in-memory flight store.

    TODO: Move this job to scheduler module and support multiple source adapters.
    """

    while True:
        updates = mock_collector.collect()
        await flight_store.apply_updates(updates)
        await asyncio.sleep(settings.fetch_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _collector_task
    configure_logging(settings.log_level)
    logger.info("starting backend service")
    _collector_task = asyncio.create_task(_collector_loop())
    try:
        yield
    finally:
        if _collector_task:
            _collector_task.cancel()
            with suppress(asyncio.CancelledError):
                await _collector_task
        logger.info("stopping backend service")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/debug/flights-dashboard")


app.include_router(health_router)
app.include_router(insights_router)
app.include_router(flights_router)
app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
