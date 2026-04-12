from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ApiResponse
from app.state import flight_store

router = APIRouter(prefix="/api/v1", tags=["flights"])


@router.get("/flights")
async def list_flights(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> ApiResponse:
    """Return current flight snapshot.

    TODO: Add filters (callsign, viewport bounds) according to API contract.
    """

    flights = await flight_store.list_flights()
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
async def get_flight_track(flight_id: str) -> ApiResponse:
    """Return only track points for a flight.

    TODO: Add time-range query support for replay mode.
    """

    track = await flight_store.get_track(flight_id)
    return ApiResponse(data=[point.model_dump(mode="json") for point in track])
