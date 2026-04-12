from fastapi import APIRouter

from app.models.schemas import ApiResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health() -> ApiResponse:
    """Basic health endpoint for Qt and CI checks.

    TODO: Add checks for data source connectivity and persistence availability.
    """

    return ApiResponse(data={"status": "ok"})
