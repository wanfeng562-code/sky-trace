"""Stats match the client display split, including unknown-altitude fallback."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.api.routes import flights as routes


def test_status_totals_and_altitude_band_boundaries(monkeypatch):
    values = [None, 0, 100, 101, 25000, 25001]
    rows = [SimpleNamespace(altitude_ft=value, speed_kts=None, aircraft_category=None,
                            callsign="TEST1", flight_id=f"icao24-{i}") for i, value in enumerate(values)]
    monkeypatch.setattr(routes.flight_store, "list_flights", AsyncMock(return_value=rows))
    stats = asyncio.run(routes.get_flight_stats()).data
    assert stats["total"] == 6
    assert stats["airborne_count"] == sum((value or 0) > 100 for value in values)
    assert stats["on_ground_count"] == 3
    assert stats["by_altitude_band"]["unknown"] == 1
    assert stats["by_altitude_band"]["ground"] == 2
    assert stats["by_altitude_band"]["medium_5-25k"] == 1
    assert stats["by_altitude_band"]["high_>25k"] == 1
