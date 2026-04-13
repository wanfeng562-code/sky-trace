from fastapi import APIRouter, Query

from app.models.schemas import ApiResponse
from app.state import flight_store, unified_pipeline

router = APIRouter(prefix="/api/v1/datahub", tags=["datahub"])


@router.get("/status")
async def get_collection_status() -> ApiResponse:
    """Return collector profile and latest refresh status of all data layers."""

    return ApiResponse(data=await unified_pipeline.get_status())


@router.get("/weather")
async def get_weather_snapshot() -> ApiResponse:
    """Return cached environment-layer snapshot fetched by backend collector."""

    return ApiResponse(data=await unified_pipeline.get_weather_cache())


@router.get("/commercial")
async def get_commercial_snapshot() -> ApiResponse:
    """Return cached commercial-layer snapshot fetched by backend collector."""

    return ApiResponse(data=await unified_pipeline.get_commercial_cache())


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
            "commercial": await unified_pipeline.get_commercial_cache(),
        }
    )
