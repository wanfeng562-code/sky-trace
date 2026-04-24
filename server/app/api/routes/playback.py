"""Historical flight playback endpoint.

Snapshots are persisted by the realtime collector every
``playback_snapshot_interval_seconds`` (default 300 s) and retained for
``playback_ttl_hours`` (default 24 h).  This endpoint queries those rows and
returns a sequence of frames suitable for a frontend replay controller.

Example request
---------------
GET /api/v1/playback
    ?start=2026-04-24T06:00:00Z
    &end=2026-04-24T08:00:00Z
    &interval=300

Response shape
--------------
{
  "code": 0,
  "message": "ok",
  "data": {
    "start": "...",
    "end": "...",
    "interval_seconds": 300,
    "total_frames": 24,
    "frames": [
      {
        "ts": "2026-04-24T06:00:12.345678+00:00",
        "flights": [
          {"id": "icao24-3c6547", "lat": 23.39, "lon": 113.30,
           "alt": 35000, "spd": 480, "hdg": 270, "cat": 4, "cs": "CES2345"},
          ...
        ]
      },
      ...
    ]
  }
}
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ApiResponse
from app.services.db import query_playback_frames

router = APIRouter(prefix="/api/v1", tags=["playback"])

_MAX_RANGE_HOURS = 48
_MAX_FRAMES = 2_000  # safety cap to avoid huge payloads


@router.get("/playback")
async def get_playback(
    start: datetime = Query(description="Replay start time (ISO 8601, UTC preferred)"),
    end: datetime = Query(description="Replay end time (ISO 8601, UTC preferred)"),
    interval: int = Query(
        default=300,
        ge=30,
        le=3_600,
        description="Step size in seconds between frames (30–3600)",
    ),
) -> ApiResponse:
    """Return historical flight positions as a sequence of playback frames.

    Frames are sampled from stored snapshots at *interval*-second steps.
    The closest available snapshot is used for each step; consecutive
    duplicates are deduplicated automatically.

    Constraints
    -----------
    - ``end`` must be after ``start``
    - Time range must not exceed 48 hours
    - ``interval`` must be between 30 and 3600 seconds
    - Maximum 2 000 frames returned per request
    """
    # Normalise to UTC-aware datetimes.
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if end <= start:
        raise HTTPException(status_code=422, detail="'end' must be after 'start'")

    range_seconds = (end - start).total_seconds()
    if range_seconds > _MAX_RANGE_HOURS * 3_600:
        raise HTTPException(
            status_code=422,
            detail=f"Time range must not exceed {_MAX_RANGE_HOURS} hours",
        )

    expected_frames = int(range_seconds / interval) + 1
    if expected_frames > _MAX_FRAMES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Request would produce ~{expected_frames} frames "
                f"(limit {_MAX_FRAMES}).  Increase 'interval' or reduce the time range."
            ),
        )

    frames = await query_playback_frames(
        start.isoformat(),
        end.isoformat(),
        interval,
    )

    return ApiResponse(
        data={
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval_seconds": interval,
            "total_frames": len(frames),
            "frames": frames,
        }
    )
