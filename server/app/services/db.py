"""SQLite persistence layer.

Tables
------
flights              Latest position snapshot per flight_id (upserted on each realtime tick).
tracks               Insert-only position history; supports time-range replay queries.
flight_details_extra Commercial-API-enriched metadata keyed by callsign (ICAO format).
"""
from __future__ import annotations

import logging
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
