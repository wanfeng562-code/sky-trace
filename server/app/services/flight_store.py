from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.models.schemas import FlightBrief, FlightDetail, TrackPoint
from app.services.db import get_db
from app.services.flight_status import resolve_flight_status

logger = logging.getLogger(__name__)

# Primary realtime layer IDs (OpenSky + mock fallback). Replaced each collect tick.
_PRIMARY_REALTIME_PREFIXES = ("mock-", "icao24-")


def _is_primary_realtime_id(flight_id: str) -> bool:
    return flight_id.startswith(_PRIMARY_REALTIME_PREFIXES)


class FlightStore:
    """Flight snapshot + track store backed by in-memory cache and SQLite."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._flights: dict[str, FlightBrief] = {}
        self._tracks: dict[str, list[TrackPoint]] = defaultdict(list)
        # In-memory commercial enrichment cache: callsign → extra fields dict
        self._commercial: dict[str, dict] = {}
        # Throttle SQLite track inserts (memory still keeps last 200 points).
        self._last_track_db_persist: dict[str, datetime] = {}

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    async def apply_realtime_snapshot(self, updates: list[FlightBrief]) -> None:
        """Replace OpenSky/mock fleet snapshot; does not remove FR24 supplemental rows."""
        removed_ids: list[str] = []
        async with self._lock:
            for fid in list(self._flights):
                if _is_primary_realtime_id(fid):
                    del self._flights[fid]
                    removed_ids.append(fid)
                    self._tracks.pop(fid, None)
                    self._last_track_db_persist.pop(fid, None)

            for flight in updates:
                self._upsert_flight_locked(flight)

        await self._persist_realtime_snapshot(updates, removed_ids)

    async def apply_updates(self, updates: list[FlightBrief]) -> None:
        """Upsert supplemental flights (e.g. FR24) without clearing the primary snapshot."""
        async with self._lock:
            for flight in updates:
                self._upsert_flight_locked(flight)

        await self._persist_updates(updates)

    async def apply_fr24_snapshot(self, updates: list[FlightBrief]) -> None:
        """Replace the FR24 supplemental fleet; removes stale fr24-* rows."""
        new_ids = {f.flight_id for f in updates}
        removed_ids: list[str] = []
        async with self._lock:
            for fid in list(self._flights):
                if fid.startswith("fr24-") and fid not in new_ids:
                    del self._flights[fid]
                    removed_ids.append(fid)
                    self._tracks.pop(fid, None)
                    self._last_track_db_persist.pop(fid, None)
            for flight in updates:
                self._upsert_flight_locked(flight)

        await self._persist_fr24_snapshot(updates, removed_ids)

    def _upsert_flight_locked(self, flight: FlightBrief) -> None:
        self._flights[flight.flight_id] = flight

        tp = TrackPoint(
            ts=flight.updated_at,
            lat=flight.lat,
            lon=flight.lon,
            altitude_ft=flight.altitude_ft,
            speed_kts=flight.speed_kts,
        )
        self._tracks[flight.flight_id].append(tp)
        # Keep only a short in-memory window to avoid unbounded growth.
        self._tracks[flight.flight_id] = self._tracks[flight.flight_id][-200:]

    async def _persist_realtime_snapshot(
        self,
        updates: list[FlightBrief],
        removed_ids: list[str],
    ) -> None:
        try:
            db = get_db()
        except RuntimeError:
            return

        try:
            await db.execute(
                "DELETE FROM flights WHERE flight_id LIKE 'mock-%' OR flight_id LIKE 'icao24-%'"
            )
            await db.execute(
                "DELETE FROM tracks WHERE flight_id LIKE 'mock-%' OR flight_id LIKE 'icao24-%'"
            )
            await self._write_flight_rows(db, updates)
            await db.commit()
        except Exception as exc:
            logger.warning("SQLite purge primary realtime flights failed: %s", exc)

        if removed_ids:
            logger.debug(
                "Replaced primary realtime snapshot: removed %d stale flights, wrote %d",
                len(removed_ids),
                len(updates),
            )

    async def _persist_fr24_snapshot(
        self,
        updates: list[FlightBrief],
        removed_ids: list[str],
    ) -> None:
        try:
            db = get_db()
        except RuntimeError:
            return

        if removed_ids:
            try:
                placeholders = ",".join("?" for _ in removed_ids)
                await db.execute(
                    f"DELETE FROM flights WHERE flight_id IN ({placeholders})",
                    removed_ids,
                )
                await db.execute(
                    f"DELETE FROM tracks WHERE flight_id IN ({placeholders})",
                    removed_ids,
                )
                for fid in removed_ids:
                    self._last_track_db_persist.pop(fid, None)
            except Exception as exc:
                logger.warning("SQLite purge stale FR24 flights failed: %s", exc)

        try:
            await self._write_flight_rows(db, updates)
            await db.commit()
        except Exception as exc:
            logger.warning("SQLite persist FR24 snapshot failed: %s", exc)

    async def _write_flight_rows(
        self,
        db: Any,
        updates: list[FlightBrief],
    ) -> None:
        if not updates:
            return
        await db.executemany(
            """
            INSERT INTO flights (flight_id, callsign, lat, lon, heading, speed_kts, altitude_ft, updated_at)
            VALUES (:flight_id, :callsign, :lat, :lon, :heading, :speed_kts, :altitude_ft, :updated_at)
            ON CONFLICT (flight_id) DO UPDATE SET
                callsign    = excluded.callsign,
                lat         = excluded.lat,
                lon         = excluded.lon,
                heading     = excluded.heading,
                speed_kts   = excluded.speed_kts,
                altitude_ft = excluded.altitude_ft,
                updated_at  = excluded.updated_at
            """,
            [
                {
                    "flight_id": f.flight_id,
                    "callsign": f.callsign,
                    "lat": f.lat,
                    "lon": f.lon,
                    "heading": f.heading,
                    "speed_kts": f.speed_kts,
                    "altitude_ft": f.altitude_ft,
                    "updated_at": f.updated_at.isoformat(),
                }
                for f in updates
            ],
        )
        track_rows = [
            {
                "flight_id": f.flight_id,
                "ts": f.updated_at.isoformat(),
                "lat": f.lat,
                "lon": f.lon,
                "altitude_ft": f.altitude_ft,
                "speed_kts": f.speed_kts,
            }
            for f in updates
            if self._should_persist_track_to_db(f)
        ]
        if track_rows:
            await db.executemany(
                """
                INSERT OR IGNORE INTO tracks (flight_id, ts, lat, lon, altitude_ft, speed_kts)
                VALUES (:flight_id, :ts, :lat, :lon, :altitude_ft, :speed_kts)
                """,
                track_rows,
            )

    async def _persist_updates(self, updates: list[FlightBrief]) -> None:
        try:
            db = get_db()
        except RuntimeError:
            return  # DB not ready yet; skip silently

        try:
            await self._write_flight_rows(db, updates)
            await db.commit()
        except Exception as exc:
            logger.warning("SQLite persist failed: %s", exc)

    async def upsert_detail_extra(
        self,
        callsign: str,
        *,
        departure_airport: str | None,
        arrival_airport: str | None,
        aircraft_type: str | None,
        status: str | None,
        source: str,
        airline_iata: str | None = None,
        dep_time: str | None = None,
        arr_time: str | None = None,
    ) -> None:
        """Persist commercial-API-enriched detail fields for a callsign."""
        async with self._lock:
            self._commercial[callsign] = {
                "departure_airport": departure_airport,
                "arrival_airport": arrival_airport,
                "aircraft_type": aircraft_type,
                "status": status,
                "airline_iata": airline_iata,
                "dep_time": dep_time,
                "arr_time": arr_time,
            }

        try:
            db = get_db()
        except RuntimeError:
            return

        now = datetime.now(timezone.utc).isoformat()
        try:
            await db.execute(
                """
                INSERT INTO flight_details_extra
                    (callsign, departure_airport, arrival_airport, aircraft_type, status, source,
                     airline_iata, dep_time, arr_time, updated_at)
                VALUES (:callsign, :dep, :arr, :ac, :status, :source, :airline_iata, :dep_time, :arr_time, :now)
                ON CONFLICT (callsign) DO UPDATE SET
                    departure_airport = excluded.departure_airport,
                    arrival_airport   = excluded.arrival_airport,
                    aircraft_type     = excluded.aircraft_type,
                    status            = excluded.status,
                    source            = excluded.source,
                    airline_iata      = excluded.airline_iata,
                    dep_time          = excluded.dep_time,
                    arr_time          = excluded.arr_time,
                    updated_at        = excluded.updated_at
                """,
                {
                    "callsign": callsign,
                    "dep": departure_airport,
                    "arr": arrival_airport,
                    "ac": aircraft_type,
                    "status": status,
                    "source": source,
                    "airline_iata": airline_iata,
                    "dep_time": dep_time,
                    "arr_time": arr_time,
                    "now": now,
                },
            )
            await db.commit()
        except Exception as exc:
            logger.warning("SQLite upsert_detail_extra failed: %s", exc)

    async def upsert_detail_extra_batch(self, items: list[dict[str, Any]]) -> int:
        """Batch upsert commercial enrichment rows in one transaction."""
        if not items:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        rows: list[dict[str, Any]] = []
        async with self._lock:
            for item in items:
                callsign = str(item.get("callsign", "")).strip()
                if not callsign:
                    continue
                self._commercial[callsign] = {
                    "departure_airport": item.get("departure_airport"),
                    "arrival_airport": item.get("arrival_airport"),
                    "aircraft_type": item.get("aircraft_type"),
                    "status": item.get("status"),
                    "airline_iata": item.get("airline_iata"),
                    "dep_time": item.get("dep_time"),
                    "arr_time": item.get("arr_time"),
                }
                rows.append(
                    {
                        "callsign": callsign,
                        "dep": item.get("departure_airport"),
                        "arr": item.get("arrival_airport"),
                        "ac": item.get("aircraft_type"),
                        "status": item.get("status"),
                        "source": item.get("source") or "unknown",
                        "airline_iata": item.get("airline_iata"),
                        "dep_time": item.get("dep_time"),
                        "arr_time": item.get("arr_time"),
                        "now": now,
                    }
                )

        if not rows:
            return 0

        try:
            db = get_db()
        except RuntimeError:
            return 0

        try:
            await db.executemany(
                """
                INSERT INTO flight_details_extra
                    (callsign, departure_airport, arrival_airport, aircraft_type, status, source,
                     airline_iata, dep_time, arr_time, updated_at)
                VALUES (:callsign, :dep, :arr, :ac, :status, :source, :airline_iata, :dep_time, :arr_time, :now)
                ON CONFLICT (callsign) DO UPDATE SET
                    departure_airport = excluded.departure_airport,
                    arrival_airport   = excluded.arrival_airport,
                    aircraft_type     = excluded.aircraft_type,
                    status            = excluded.status,
                    source            = excluded.source,
                    airline_iata      = excluded.airline_iata,
                    dep_time          = excluded.dep_time,
                    arr_time          = excluded.arr_time,
                    updated_at        = excluded.updated_at
                """,
                rows,
            )
            await db.commit()
            return len(rows)
        except Exception as exc:
            logger.warning("SQLite upsert_detail_extra_batch failed: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    async def list_flights(
        self,
        *,
        callsign: str | None = None,
        lat_min: float | None = None,
        lat_max: float | None = None,
        lon_min: float | None = None,
        lon_max: float | None = None,
    ) -> list[FlightBrief]:
        """Return current snapshot with optional callsign / bounding-box filters."""
        async with self._lock:
            flights = list(self._flights.values())

        if callsign:
            needle = callsign.upper()
            flights = [f for f in flights if f.callsign and needle in f.callsign.upper()]

        # Deduplicate: when both OpenSky (icao24-{hex}) and FR24 (fr24-{hex})
        # entries exist for the same aircraft, keep only the OpenSky entry.
        # FR24-only entries (no matching icao24 in OpenSky) are kept as-is.
        opensky_icao24s = {
            f.flight_id[7:] for f in flights if f.flight_id.startswith("icao24-")
        }
        if opensky_icao24s:
            flights = [
                f for f in flights
                if not (f.flight_id.startswith("fr24-") and f.flight_id[5:] in opensky_icao24s)
            ]

        if lat_min is not None:
            flights = [f for f in flights if f.lat >= lat_min]
        if lat_max is not None:
            flights = [f for f in flights if f.lat <= lat_max]
        if lon_min is not None:
            flights = [f for f in flights if f.lon >= lon_min]
        if lon_max is not None:
            flights = [f for f in flights if f.lon <= lon_max]

        # Enrich with commercial data from in-memory cache
        enriched: list[FlightBrief] = []
        for f in flights:
            cs = f.callsign
            if cs and cs in self._commercial:
                extra = self._commercial[cs]
                f = f.model_copy(update={
                    "departure_airport": extra.get("departure_airport"),
                    "arrival_airport": extra.get("arrival_airport"),
                    "airline_iata": extra.get("airline_iata"),
                })
            enriched.append(f)

        return enriched

    async def get_flight(self, flight_id: str) -> FlightDetail | None:
        async with self._lock:
            flight = self._flights.get(flight_id)
            if not flight:
                return None
            tracks = list(self._tracks.get(flight_id, []))

        # Attempt to enrich from commercial DB row.
        dep = arr = ac_type = flight_status = dep_time = arr_time = airline_iata = None
        if flight.callsign:
            extra = await self._load_detail_extra(flight.callsign)
            if extra:
                dep = extra["departure_airport"]
                arr = extra["arrival_airport"]
                ac_type = extra["aircraft_type"]
                flight_status = extra["status"]
                dep_time = extra.get("dep_time")
                arr_time = extra.get("arr_time")
                airline_iata = extra.get("airline_iata")

        pos = flight
        status = resolve_flight_status(
            flight_status,
            altitude_ft=pos.altitude_ft,
            on_ground=pos.on_ground,
        )

        return FlightDetail(
            flight_id=flight.flight_id,
            callsign=flight.callsign,
            departure_airport=dep,
            arrival_airport=arr,
            aircraft_type=ac_type,
            status=status,
            dep_time=dep_time,
            arr_time=arr_time,
            airline_iata=airline_iata,
            last_position=flight,
            track_points=tracks,
        )

    async def get_track(
        self,
        flight_id: str,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[TrackPoint]:
        """Return track points for a flight, optionally bounded by a time range.

        Falls back to in-memory track when SQLite is unavailable or returns nothing.
        """
        if since is not None or until is not None:
            db_track = await self._load_track_from_db(flight_id, since=since, until=until)
            if db_track:
                return db_track

        async with self._lock:
            return list(self._tracks.get(flight_id, []))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _should_persist_track_to_db(self, flight: FlightBrief) -> bool:
        """Limit SQLite track growth while keeping in-memory history dense."""
        last = self._last_track_db_persist.get(flight.flight_id)
        interval = max(1, int(settings.tracks_persist_interval_seconds))
        if last is None:
            self._last_track_db_persist[flight.flight_id] = flight.updated_at
            return True
        elapsed = (flight.updated_at - last).total_seconds()
        if elapsed >= interval:
            self._last_track_db_persist[flight.flight_id] = flight.updated_at
            return True
        return False

    async def _load_detail_extra(self, callsign: str) -> dict | None:
        async with self._lock:
            mem = dict(self._commercial.get(callsign) or {})

        db_row: dict | None = None
        try:
            db = get_db()
        except RuntimeError:
            db_row = None
        else:
            try:
                async with db.execute(
                    "SELECT * FROM flight_details_extra WHERE callsign = ?",
                    (callsign,),
                ) as cursor:
                    row = await cursor.fetchone()
                    db_row = dict(row) if row else None
            except Exception as exc:
                logger.warning("_load_detail_extra failed: %s", exc)

        if not mem and not db_row:
            return None

        merged: dict = dict(db_row) if db_row else {}
        for key, value in mem.items():
            if value is not None:
                merged[key] = value
        return merged or None

    async def _load_track_from_db(
        self,
        flight_id: str,
        *,
        since: datetime | None,
        until: datetime | None,
    ) -> list[TrackPoint]:
        try:
            db = get_db()
        except RuntimeError:
            return []

        clauses = ["flight_id = ?"]
        params: list = [flight_id]
        if since is not None:
            clauses.append("ts >= ?")
            params.append(since.isoformat())
        if until is not None:
            clauses.append("ts <= ?")
            params.append(until.isoformat())

        sql = f"SELECT ts, lat, lon, altitude_ft, speed_kts FROM tracks WHERE {' AND '.join(clauses)} ORDER BY ts"
        try:
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
            return [
                TrackPoint(
                    ts=datetime.fromisoformat(row["ts"]).replace(tzinfo=timezone.utc),
                    lat=row["lat"],
                    lon=row["lon"],
                    altitude_ft=row["altitude_ft"],
                    speed_kts=row["speed_kts"],
                )
                for row in rows
            ]
        except Exception as exc:
            logger.warning("_load_track_from_db failed: %s", exc)
            return []
