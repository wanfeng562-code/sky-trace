from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

from app.models.schemas import FlightBrief, FlightDetail, TrackPoint
from app.services.db import get_db

logger = logging.getLogger(__name__)


class FlightStore:
    """Flight snapshot + track store backed by in-memory cache and SQLite."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._flights: dict[str, FlightBrief] = {}
        self._tracks: dict[str, list[TrackPoint]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    async def apply_updates(self, updates: list[FlightBrief]) -> None:
        """Upsert flight positions in memory and persist to SQLite."""
        async with self._lock:
            for flight in updates:
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

        await self._persist_updates(updates)

    async def _persist_updates(self, updates: list[FlightBrief]) -> None:
        try:
            db = get_db()
        except RuntimeError:
            return  # DB not ready yet; skip silently

        try:
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
            await db.executemany(
                """
                INSERT INTO tracks (flight_id, ts, lat, lon, altitude_ft, speed_kts)
                VALUES (:flight_id, :ts, :lat, :lon, :altitude_ft, :speed_kts)
                """,
                [
                    {
                        "flight_id": f.flight_id,
                        "ts": f.updated_at.isoformat(),
                        "lat": f.lat,
                        "lon": f.lon,
                        "altitude_ft": f.altitude_ft,
                        "speed_kts": f.speed_kts,
                    }
                    for f in updates
                ],
            )
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
    ) -> None:
        """Persist commercial-API-enriched detail fields for a callsign."""
        try:
            db = get_db()
        except RuntimeError:
            return

        now = datetime.now(timezone.utc).isoformat()
        try:
            await db.execute(
                """
                INSERT INTO flight_details_extra
                    (callsign, departure_airport, arrival_airport, aircraft_type, status, source, updated_at)
                VALUES (:callsign, :dep, :arr, :ac, :status, :source, :now)
                ON CONFLICT (callsign) DO UPDATE SET
                    departure_airport = excluded.departure_airport,
                    arrival_airport   = excluded.arrival_airport,
                    aircraft_type     = excluded.aircraft_type,
                    status            = excluded.status,
                    source            = excluded.source,
                    updated_at        = excluded.updated_at
                """,
                {
                    "callsign": callsign,
                    "dep": departure_airport,
                    "arr": arrival_airport,
                    "ac": aircraft_type,
                    "status": status,
                    "source": source,
                    "now": now,
                },
            )
            await db.commit()
        except Exception as exc:
            logger.warning("SQLite upsert_detail_extra failed: %s", exc)

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

        return flights

    async def get_flight(self, flight_id: str) -> FlightDetail | None:
        async with self._lock:
            flight = self._flights.get(flight_id)
            if not flight:
                return None
            tracks = list(self._tracks.get(flight_id, []))

        # Attempt to enrich from commercial DB row.
        dep = arr = ac_type = flight_status = None
        if flight.callsign:
            extra = await self._load_detail_extra(flight.callsign)
            if extra:
                dep = extra["departure_airport"]
                arr = extra["arrival_airport"]
                ac_type = extra["aircraft_type"]
                flight_status = extra["status"]

        return FlightDetail(
            flight_id=flight.flight_id,
            callsign=flight.callsign,
            departure_airport=dep,
            arrival_airport=arr,
            aircraft_type=ac_type,
            status=flight_status or "enroute",
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

    async def _load_detail_extra(self, callsign: str) -> dict | None:
        try:
            db = get_db()
        except RuntimeError:
            return None

        try:
            async with db.execute(
                "SELECT * FROM flight_details_extra WHERE callsign = ?",
                (callsign,),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as exc:
            logger.warning("_load_detail_extra failed: %s", exc)
            return None

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
