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
from typing import Any

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
    airline_iata      TEXT,
    dep_time          TEXT,
    arr_time          TEXT,
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS airports (
    iata_code TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    city      TEXT,
    country   TEXT,
    lat       REAL NOT NULL,
    lon       REAL NOT NULL,
    is_hub    INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_airports_is_hub ON airports (is_hub);
CREATE INDEX IF NOT EXISTS idx_airports_lat_lon ON airports (lat, lon);

CREATE TABLE IF NOT EXISTS place_names (
    cache_key    TEXT PRIMARY KEY,
    name_zh      TEXT NOT NULL,
    name_en      TEXT,
    source_text  TEXT,
    updated_at   TEXT NOT NULL
);
"""

_SERVER_ROOT = Path(__file__).resolve().parent.parent.parent
_AIRPORTS_SEED_PATH = _SERVER_ROOT / "data" / "airports.seed.json"
_AIRPORTS_IATA_PATH = _SERVER_ROOT / "data" / "airports.iata.json"


async def init_db() -> None:
    """Open the SQLite connection and apply DDL migrations."""
    global _db
    path = Path(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(str(path))
    _db.row_factory = aiosqlite.Row
    await _db.executescript(_DDL)
    # Migration: add columns that may not exist in pre-existing databases
    for alter in [
        "ALTER TABLE flight_details_extra ADD COLUMN airline_iata TEXT",
        "ALTER TABLE flight_details_extra ADD COLUMN dep_time TEXT",
        "ALTER TABLE flight_details_extra ADD COLUMN arr_time TEXT",
        "ALTER TABLE airports ADD COLUMN city TEXT",
        "ALTER TABLE airports ADD COLUMN country TEXT",
        "ALTER TABLE airports ADD COLUMN is_hub INTEGER NOT NULL DEFAULT 1",
    ]:
        try:
            await _db.execute(alter)
        except Exception:
            pass  # Column already exists
    await _migrate_tracks_unique_index()
    await _seed_airports_if_empty()
    await _merge_airports_iata_catalog()
    await _db.commit()
    logger.info("SQLite initialised at %s", path.resolve())


async def _migrate_tracks_unique_index() -> None:
    """Add unique (flight_id, ts) on tracks after deduping legacy duplicate rows."""
    db = get_db()
    async with db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        ("idx_tracks_flight_ts_unique",),
    ) as cursor:
        if await cursor.fetchone():
            return

    try:
        await db.execute(
            "CREATE UNIQUE INDEX idx_tracks_flight_ts_unique ON tracks (flight_id, ts)"
        )
        return
    except Exception:
        pass

    async with db.execute("SELECT COUNT(*) AS cnt FROM tracks") as cursor:
        row = await cursor.fetchone()
        total = int(row["cnt"]) if row else 0

    logger.info(
        "Tracks table has duplicate (flight_id, ts) rows (%d total); "
        "rebuilding table (one-time migration, may take several minutes)…",
        total,
    )
    await db.executescript(
        """
        BEGIN IMMEDIATE;
        CREATE TABLE tracks_dedup (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_id   TEXT    NOT NULL,
            ts          TEXT    NOT NULL,
            lat         REAL    NOT NULL,
            lon         REAL    NOT NULL,
            altitude_ft INTEGER,
            speed_kts   INTEGER
        );
        INSERT INTO tracks_dedup (id, flight_id, ts, lat, lon, altitude_ft, speed_kts)
        SELECT id, flight_id, ts, lat, lon, altitude_ft, speed_kts
        FROM (
            SELECT id, flight_id, ts, lat, lon, altitude_ft, speed_kts,
                   ROW_NUMBER() OVER (PARTITION BY flight_id, ts ORDER BY id) AS rn
            FROM tracks
        )
        WHERE rn = 1;
        DROP TABLE tracks;
        ALTER TABLE tracks_dedup RENAME TO tracks;
        CREATE INDEX IF NOT EXISTS idx_tracks_flight_ts ON tracks (flight_id, ts);
        CREATE UNIQUE INDEX idx_tracks_flight_ts_unique ON tracks (flight_id, ts);
        COMMIT;
        """
    )
    async with db.execute("SELECT COUNT(*) AS cnt FROM tracks") as cursor:
        row = await cursor.fetchone()
        kept = int(row["cnt"]) if row else 0
    logger.info(
        "Tracks deduplication complete: kept %d rows (removed %d duplicates)",
        kept,
        max(0, total - kept),
    )


async def _seed_airports_if_empty() -> None:
    """Load airports from local seed JSON when the airports table is empty."""
    db = get_db()
    async with db.execute("SELECT COUNT(*) AS cnt FROM airports") as cursor:
        row = await cursor.fetchone()
    if row and int(row["cnt"]) > 0:
        return

    if not _AIRPORTS_SEED_PATH.exists():
        logger.warning("Airports seed file not found: %s", _AIRPORTS_SEED_PATH)
        return

    try:
        raw = json.loads(_AIRPORTS_SEED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read airports seed: %s", exc)
        return

    if not isinstance(raw, list):
        logger.warning("Airports seed should be a list: %s", _AIRPORTS_SEED_PATH)
        return

    rows: list[tuple[str, str, str, str, float, float, int]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        iata = str(item.get("iata_code", "")).strip().upper()
        name = str(item.get("name", "")).strip()
        city = str(item.get("city", "")).strip()
        country = str(item.get("country", "")).strip()
        lat = item.get("lat")
        lon = item.get("lon")
        is_hub = 1 if bool(item.get("is_hub", True)) else 0
        if len(iata) != 3 or not name:
            continue
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        rows.append((iata, name, city, country, float(lat), float(lon), is_hub))

    if not rows:
        logger.warning("No valid airport rows found in seed: %s", _AIRPORTS_SEED_PATH)
        return

    await db.executemany(
        """
        INSERT INTO airports (iata_code, name, city, country, lat, lon, is_hub)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    logger.info("Seeded airports table with %d records", len(rows))


async def _merge_airports_iata_catalog() -> None:
    """Upsert global IATA airports from OurAirports-derived JSON (keeps hub seed rows)."""
    if not _AIRPORTS_IATA_PATH.exists():
        logger.info(
            "IATA airport catalog not found (%s); run scripts/build_airports_iata.py",
            _AIRPORTS_IATA_PATH,
        )
        return

    try:
        raw = json.loads(_AIRPORTS_IATA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read IATA airport catalog: %s", exc)
        return

    if not isinstance(raw, list):
        logger.warning("IATA airport catalog should be a list: %s", _AIRPORTS_IATA_PATH)
        return

    db = get_db()
    batch: list[tuple[str, str, str, str, float, float, int]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        iata = str(item.get("iata_code", "")).strip().upper()
        name = str(item.get("name", "")).strip()
        city = str(item.get("city", "")).strip()
        country = str(item.get("country", "")).strip()
        lat = item.get("lat")
        lon = item.get("lon")
        is_hub = 1 if bool(item.get("is_hub", False)) else 0
        if len(iata) != 3 or not name:
            continue
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        batch.append((iata, name, city, country, float(lat), float(lon), is_hub))

    if not batch:
        return

    await db.executemany(
        """
        INSERT INTO airports (iata_code, name, city, country, lat, lon, is_hub)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(iata_code) DO UPDATE SET
            name = CASE WHEN airports.is_hub = 1 THEN airports.name ELSE excluded.name END,
            city = CASE WHEN airports.city IS NULL OR airports.city = '' THEN excluded.city ELSE airports.city END,
            country = CASE WHEN airports.country IS NULL OR airports.country = '' THEN excluded.country ELSE airports.country END,
            lat = excluded.lat,
            lon = excluded.lon,
            is_hub = CASE WHEN airports.is_hub = 1 OR excluded.is_hub = 1 THEN 1 ELSE 0 END
        """,
        batch,
    )
    logger.info("Merged IATA airport catalog (%d rows)", len(batch))


async def upsert_airport_from_route(
    iata: str | None,
    *,
    name: str | None = None,
    city: str | None = None,
    country: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> None:
    """Ensure a route IATA exists in airports when enrichment provides coordinates."""
    code = (iata or "").strip().upper()
    if len(code) != 3:
        return
    try:
        db = get_db()
    except RuntimeError:
        return

    async with db.execute(
        "SELECT 1 FROM airports WHERE iata_code = ?", (code,)
    ) as cursor:
        if await cursor.fetchone():
            return

    if lat is None or lon is None:
        return

    await db.execute(
        """
        INSERT INTO airports (iata_code, name, city, country, lat, lon, is_hub)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(iata_code) DO NOTHING
        """,
        (
            code,
            name or code,
            city or "",
            country or "",
            float(lat),
            float(lon),
        ),
    )
    await db.commit()


async def close_db() -> None:
    """Close the SQLite connection gracefully."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("SQLite connection closed")


def _parse_iso_utc(value: str) -> datetime:
    """Parse ISO-8601 timestamps from SQLite/API into timezone-aware UTC."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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


async def cleanup_old_tracks(max_age_hours: int = 24) -> int:
    """Delete track history older than *max_age_hours*.  Returns number of rows deleted."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    db = get_db()
    cursor = await db.execute("DELETE FROM tracks WHERE ts < ?", (cutoff,))
    await db.commit()
    return cursor.rowcount


async def persist_playback_snapshot(
    ts_iso: str,
    data_json: str,
    *,
    snapshot_ttl_hours: int,
    tracks_ttl_hours: int,
) -> tuple[int, int]:
    """Insert snapshot and purge expired snapshots + tracks in one transaction."""
    now = datetime.now(timezone.utc)
    snap_cutoff = (now - timedelta(hours=snapshot_ttl_hours)).isoformat()
    track_cutoff = (now - timedelta(hours=tracks_ttl_hours)).isoformat()
    db = get_db()
    await db.execute(
        "INSERT INTO flight_snapshots (ts, data) VALUES (?, ?)",
        (ts_iso, data_json),
    )
    snap_cur = await db.execute(
        "DELETE FROM flight_snapshots WHERE ts < ?",
        (snap_cutoff,),
    )
    track_cur = await db.execute(
        "DELETE FROM tracks WHERE ts < ?",
        (track_cutoff,),
    )
    await db.commit()
    return snap_cur.rowcount, track_cur.rowcount


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

    try:
        start_dt = _parse_iso_utc(start_iso)
        end_dt = _parse_iso_utc(end_iso)
    except ValueError as exc:
        logger.warning("Invalid playback range: %s", exc)
        return []

    if end_dt < start_dt:
        return []

    # Pre-parse timestamps once for efficient bisect-based nearest lookup.
    parsed: list[tuple[datetime, str, str]] = []
    for r in rows:
        try:
            parsed.append((_parse_iso_utc(r["ts"]), r["ts"], r["data"]))
        except ValueError:
            logger.warning("Skipping snapshot with invalid ts: %r", r["ts"])

    if not parsed:
        return []

    parsed_dts = [p[0] for p in parsed]

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
            try:
                flights = json.loads(data_str)
            except json.JSONDecodeError:
                logger.warning("Skipping corrupt snapshot at %s", ts_str)
                t += timedelta(seconds=interval_s)
                continue
            if not isinstance(flights, list):
                logger.warning("Skipping snapshot with non-list payload at %s", ts_str)
                t += timedelta(seconds=interval_s)
                continue
            frames.append({"ts": ts_str, "flights": flights})
            last_ts = ts_str
        t += timedelta(seconds=interval_s)

    return frames


async def get_airports_by_iata(codes: list[str]) -> list[dict[str, Any]]:
    """Batch-fetch airport rows by IATA codes."""
    cleaned = []
    seen: set[str] = set()
    for raw in codes:
        code = (raw or "").strip().upper()
        if len(code) != 3 or code in seen:
            continue
        seen.add(code)
        cleaned.append(code)
    if not cleaned:
        return []

    db = get_db()
    placeholders = ",".join("?" for _ in cleaned)
    sql = (
        "SELECT iata_code, name, city, country, lat, lon, is_hub FROM airports "
        f"WHERE iata_code IN ({placeholders})"
    )
    async with db.execute(sql, cleaned) as cursor:
        rows = await cursor.fetchall()
    return [
        {
            "iata_code": row["iata_code"],
            "name": row["name"],
            "city": row["city"] or "",
            "country": row["country"] or "",
            "lat": row["lat"],
            "lon": row["lon"],
            "is_hub": bool(row["is_hub"]),
        }
        for row in rows
    ]


async def get_airport_by_iata(iata: str) -> dict[str, Any] | None:
    """Return one airport row by IATA code, or None."""
    code = (iata or "").strip().upper()
    if len(code) != 3:
        return None
    db = get_db()
    async with db.execute(
        "SELECT iata_code, name, city, country, lat, lon, is_hub FROM airports WHERE iata_code = ?",
        (code,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    return {
        "iata_code": row["iata_code"],
        "name": row["name"],
        "city": row["city"] or "",
        "country": row["country"] or "",
        "lat": row["lat"],
        "lon": row["lon"],
        "is_hub": bool(row["is_hub"]),
    }


async def list_airports(*, is_hub: bool | None = None) -> list[dict[str, Any]]:
    """Return airports from SQLite as dictionaries."""
    db = get_db()
    sql = "SELECT iata_code, name, city, country, lat, lon, is_hub FROM airports"
    params: tuple[Any, ...] = ()
    if is_hub is not None:
        sql += " WHERE is_hub = ?"
        params = (1 if is_hub else 0,)
    sql += " ORDER BY iata_code"

    async with db.execute(sql, params) as cursor:
        rows = await cursor.fetchall()

    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "iata_code": row["iata_code"],
                "name": row["name"],
                "city": row["city"],
                "country": row["country"],
                "lat": row["lat"],
                "lon": row["lon"],
                "is_hub": bool(row["is_hub"]),
            }
        )
    return out


async def get_place_names(keys: list[str]) -> list[dict[str, Any]]:
    """Batch-fetch cached display names by cache_key."""
    cleaned = [k.strip() for k in keys if k and k.strip()]
    if not cleaned:
        return []
    db = get_db()
    placeholders = ",".join("?" for _ in cleaned)
    sql = (
        "SELECT cache_key, name_zh, name_en, source_text, updated_at "
        f"FROM place_names WHERE cache_key IN ({placeholders})"
    )
    async with db.execute(sql, cleaned) as cursor:
        rows = await cursor.fetchall()
    return [
        {
            "cache_key": row["cache_key"],
            "name_zh": row["name_zh"],
            "name_en": row["name_en"],
            "source_text": row["source_text"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


async def upsert_place_names(items: list[dict[str, Any]]) -> int:
    """Insert or update place name rows. Returns number of rows written."""
    if not items:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    db = get_db()
    rows: list[tuple[str, str, str | None, str | None, str]] = []
    for item in items:
        key = str(item.get("cache_key", "")).strip()
        name_zh = str(item.get("name_zh", "")).strip()
        if not key or not name_zh:
            continue
        rows.append(
            (
                key[:180],
                name_zh[:500],
                (str(item["name_en"]).strip()[:500] if item.get("name_en") else None),
                (
                    str(item["source_text"]).strip()[:500]
                    if item.get("source_text")
                    else None
                ),
                now,
            )
        )
    if not rows:
        return 0
    await db.executemany(
        """
        INSERT INTO place_names (cache_key, name_zh, name_en, source_text, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            name_zh = excluded.name_zh,
            name_en = COALESCE(excluded.name_en, place_names.name_en),
            source_text = COALESCE(excluded.source_text, place_names.source_text),
            updated_at = excluded.updated_at
        """,
        rows,
    )
    await db.commit()
    return len(rows)
