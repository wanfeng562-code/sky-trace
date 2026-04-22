from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ApiResponse
from app.state import flight_store

router = APIRouter(prefix="/api/v1", tags=["flights"])


@router.get("/flights")
async def list_flights(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    callsign: str | None = Query(default=None, description="Partial callsign filter (case-insensitive)"),
    lat_min: float | None = Query(default=None),
    lat_max: float | None = Query(default=None),
    lon_min: float | None = Query(default=None),
    lon_max: float | None = Query(default=None),
) -> ApiResponse:
    """Return current flight snapshot with optional callsign / bounding-box filters."""

    flights = await flight_store.list_flights(
        callsign=callsign,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
    )
    start = (page - 1) * page_size
    end = start + page_size
    items = flights[start:end]

    return ApiResponse(
        data={
            "total": len(flights),
            "items": [f.model_dump(mode="json") for f in items],
        }
    )


@router.get("/flights/{flight_id}")
async def get_flight_detail(flight_id: str) -> ApiResponse:
    """Return one flight detail object and short track history."""

    detail = await flight_store.get_flight(flight_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="flight not found")
    return ApiResponse(data=detail.model_dump(mode="json"))


@router.get("/flights/{flight_id}/track")
async def get_flight_track(
    flight_id: str,
    since: datetime | None = Query(default=None, description="ISO 8601 UTC start time"),
    until: datetime | None = Query(default=None, description="ISO 8601 UTC end time"),
) -> ApiResponse:
    """Return track points for a flight, optionally bounded by a time range."""

    track = await flight_store.get_track(flight_id, since=since, until=until)
    return ApiResponse(data=[point.model_dump(mode="json") for point in track])
