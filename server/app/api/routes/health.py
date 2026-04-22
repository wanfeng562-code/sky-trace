from fastapi import APIRouter

from app.models.schemas import ApiResponse
from app.services.db import get_db

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health() -> ApiResponse:
    """Basic health endpoint; also verifies SQLite connectivity."""

    db_ok = False
    try:
        db = get_db()
        async with db.execute("SELECT 1") as cur:
            await cur.fetchone()
        db_ok = True
    except Exception:
        pass

    return ApiResponse(data={"status": "ok", "db": "ok" if db_ok else "unavailable"})
