from fastapi import APIRouter, Query

from app.models.schemas import ApiResponse
from app.state import flight_store, unified_pipeline

router = APIRouter(prefix="/api/v1/datahub", tags=["datahub"])


@router.get("/status")
async def get_collection_status() -> ApiResponse:
    """Return collector profile and latest refresh status of all data layers."""

    return ApiResponse(data=await unified_pipeline.get_status())


@router.get("/weather/nearest")
async def get_nearest_weather(
    lat: float = Query(description="Latitude of the query point"),
    lon: float = Query(description="Longitude of the query point"),
) -> ApiResponse:
    """Return cached weather + AQI for the hub nearest to the given coordinates.

    No external API call is made – data is served from the in-memory environment
    cache populated every 5 minutes by the backend collector.
    """
    return ApiResponse(data=await unified_pipeline.get_nearest_hub_weather(lat, lon))


@router.get("/weather")
async def get_weather_snapshot() -> ApiResponse:
    """Return cached environment-layer snapshot fetched by backend collector."""

    return ApiResponse(data=await unified_pipeline.get_weather_cache())


@router.get("/air_quality")
async def get_air_quality_snapshot() -> ApiResponse:
    """Return cached air quality snapshot (AQI + 8 pollutants) from OpenWeather."""

    return ApiResponse(data=await unified_pipeline.get_air_quality_cache())


@router.get("/commercial")
async def get_commercial_snapshot() -> ApiResponse:
    """Return cached commercial-layer snapshot fetched by backend collector."""

    return ApiResponse(data=await unified_pipeline.get_commercial_cache())


@router.get("/quota")
async def get_quota() -> ApiResponse:
    """Return today's API call counts and configured budgets for all data sources."""

    return ApiResponse(data=await unified_pipeline.get_quota())


@router.get("/snapshot")
async def get_unified_snapshot(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> ApiResponse:
    """Return one unified payload for frontends to consume from backend only."""

    flights = await flight_store.list_flights()
    start = (page - 1) * page_size
    end = start + page_size
    items = [item.model_dump(mode="json") for item in flights[start:end]]

    return ApiResponse(
        data={
            "status": await unified_pipeline.get_status(),
            "flights": {
                "total": len(flights),
                "items": items,
            },
            "weather": await unified_pipeline.get_weather_cache(),
            "air_quality": await unified_pipeline.get_air_quality_cache(),
            "commercial": await unified_pipeline.get_commercial_cache(),
        }
    )
