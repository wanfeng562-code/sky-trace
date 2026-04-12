import math
import random
from datetime import datetime, timezone

from app.models.schemas import FlightBrief


class MockCollector:
    """Generate synthetic flight data for local development.

    TODO: Replace this with a real data source adapter and retry/backoff policy.
    """

    def __init__(self) -> None:
        self._t = 0.0

    def collect(self) -> list[FlightBrief]:
        self._t += 0.15
        now = datetime.now(timezone.utc)
        flights: list[FlightBrief] = []

        for idx in range(1, 6):
            base_lat = 23.0 + idx * 0.3
            base_lon = 112.0 + idx * 0.4
            lat = base_lat + math.sin(self._t + idx) * 0.1
            lon = base_lon + math.cos(self._t + idx) * 0.1
            flights.append(
                FlightBrief(
                    flight_id=f"mock-{idx}",
                    callsign=f"ST{idx:03d}",
                    lat=round(lat, 6),
                    lon=round(lon, 6),
                    heading=int((self._t * 60 + idx * 25) % 360),
                    speed_kts=random.randint(320, 470),
                    altitude_ft=random.randint(22000, 38000),
                    updated_at=now,
                )
            )

        return flights
