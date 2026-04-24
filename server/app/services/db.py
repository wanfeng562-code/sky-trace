"""SQLite persistence layer.

Tables
------
flights              Latest position snapshot per flight_id (upserted on each realtime tick).
tracks               Insert-only position history; supports time-range replay queries.
flight_details_extra Commercial-API-enriched metadata keyed by callsign (ICAO format).
flight_snapshots     Periodic full-fleet snapshots for historical playback (TTL-managed).
"""
from __future__ import annotations

import bisect
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from app.core.config import settings

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None

_DDL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS flights (
    flight_id   TEXT PRIMARY KEY,
    callsign    TEXT,
    lat         REAL    NOT NULL,
    lon         REAL    NOT NULL,
    heading     INTEGER,
    speed_kts   INTEGER,
    altitude_ft INTEGER,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tracks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id   TEXT    NOT NULL,
    ts          TEXT    NOT NULL,
    lat         REAL    NOT NULL,
    lon         REAL    NOT NULL,
    altitude_ft INTEGER,
    speed_kts   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tracks_flight_ts ON tracks (flight_id, ts);

CREATE TABLE IF NOT EXISTS flight_snapshots (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts   TEXT    NOT NULL,
    data TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON flight_snapshots (ts);

CREATE TABLE IF NOT EXISTS flight_details_extra (
    callsign          TEXT PRIMARY KEY,
    departure_airport TEXT,
    arrival_airport   TEXT,
    aircraft_type     TEXT,
    status            TEXT,
    source            TEXT,
    updated_at        TEXT NOT NULL
);
"""


async def init_db() -> None:
    """Open the SQLite connection and apply DDL migrations."""
    global _db
    path = Path(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(str(path))
    _db.row_factory = aiosqlite.Row
    await _db.executescript(_DDL)
    await _db.commit()
    logger.info("SQLite initialised at %s", path.resolve())


async def close_db() -> None:
    """Close the SQLite connection gracefully."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("SQLite connection closed")


def get_db() -> aiosqlite.Connection:
    """Return the active database connection.

    Raises RuntimeError if :func:`init_db` has not been called yet.
    """
    if _db is None:
        raise RuntimeError("Database not initialised – call init_db() first")
    return _db


async def save_flight_snapshot(ts_iso: str, data_json: str) -> None:
    """Insert one compact fleet snapshot row for playback."""
    db = get_db()
    await db.execute(
        "INSERT INTO flight_snapshots (ts, data) VALUES (?, ?)",
        (ts_iso, data_json),
    )
    await db.commit()


async def cleanup_old_snapshots(max_age_hours: int = 24) -> int:
    """Delete snapshots older than *max_age_hours*.  Returns number of rows deleted."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    db = get_db()
    cursor = await db.execute("DELETE FROM flight_snapshots WHERE ts < ?", (cutoff,))
    await db.commit()
    return cursor.rowcount


async def query_playback_frames(
    start_iso: str,
    end_iso: str,
    interval_s: int,
) -> list[dict]:
    """Return playback frames sampled at *interval_s* steps between start and end.

    Each frame is ``{"ts": <iso8601>, "flights": [...]}``.  The closest stored
    snapshot is used for each step; consecutive duplicate frames are deduplicated.
    """
    db = get_db()
    async with db.execute(
        "SELECT ts, data FROM flight_snapshots WHERE ts >= ? AND ts <= ? ORDER BY ts",
        (start_iso, end_iso),
    ) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        return []

    # Pre-parse timestamps once for efficient bisect-based nearest lookup.
    parsed: list[tuple[datetime, str, str]] = [
        (datetime.fromisoformat(r["ts"].replace("Z", "+00:00")), r["ts"], r["data"])
        for r in rows
    ]
    parsed_dts = [p[0] for p in parsed]

    start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))

    frames: list[dict] = []
    last_ts: str | None = None
    t = start_dt
    while t <= end_dt:
        idx = bisect.bisect_left(parsed_dts, t)
        if idx >= len(parsed):
            idx = len(parsed) - 1
        elif idx > 0:
            dist_right = abs((parsed_dts[idx] - t).total_seconds())
            dist_left = abs((parsed_dts[idx - 1] - t).total_seconds())
            if dist_left < dist_right:
                idx -= 1
        _, ts_str, data_str = parsed[idx]
        if ts_str != last_ts:
            frames.append({"ts": ts_str, "flights": json.loads(data_str)})
            last_ts = ts_str
        t += timedelta(seconds=interval_s)

    return frames
