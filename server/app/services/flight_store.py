import asyncio
from collections import defaultdict

from app.models.schemas import FlightBrief, FlightDetail, TrackPoint


class FlightStore:
    """In-memory store for latest flights and short track history.

    TODO: Replace with repository layer backed by SQLite + cache for persistence.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._flights: dict[str, FlightBrief] = {}
        self._tracks: dict[str, list[TrackPoint]] = defaultdict(list)

    async def apply_updates(self, updates: list[FlightBrief]) -> None:
        async with self._lock:
            for flight in updates:
                self._flights[flight.flight_id] = flight
                self._tracks[flight.flight_id].append(
                    TrackPoint(
                        lat=flight.lat,
                        lon=flight.lon,
                        altitude_ft=flight.altitude_ft,
                        speed_kts=flight.speed_kts,
                    )
                )
                # Keep only a short in-memory window to avoid unbounded growth.
                self._tracks[flight.flight_id] = self._tracks[flight.flight_id][-200:]

    async def list_flights(self) -> list[FlightBrief]:
        async with self._lock:
            return list(self._flights.values())

    async def get_flight(self, flight_id: str) -> FlightDetail | None:
        async with self._lock:
            flight = self._flights.get(flight_id)
            if not flight:
                return None
            return FlightDetail(
                flight_id=flight.flight_id,
                callsign=flight.callsign,
                departure_airport="ZGGG",
                arrival_airport="ZBAA",
                aircraft_type="A320",
                status="enroute",
                last_position=flight,
                track_points=self._tracks.get(flight_id, []),
            )

    async def get_track(self, flight_id: str) -> list[TrackPoint]:
        async with self._lock:
            return list(self._tracks.get(flight_id, []))
