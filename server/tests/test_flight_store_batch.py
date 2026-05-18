"""Tests for batched flight_store writes."""

from __future__ import annotations

import asyncio

from app.services import db as db_module
from app.services.flight_store import FlightStore


def test_upsert_detail_extra_batch_single_commit(tmp_path, monkeypatch) -> None:
    async def _run() -> None:
        monkeypatch.setattr(db_module.settings, "sqlite_path", str(tmp_path / "fs.db"))
        await db_module.init_db()
        store = FlightStore()
        n = await store.upsert_detail_extra_batch(
            [
                {
                    "callsign": "CES123",
                    "departure_airport": "PVG",
                    "arrival_airport": "PEK",
                    "aircraft_type": "A320",
                    "status": "en-route",
                    "source": "test",
                },
                {
                    "callsign": "CCA456",
                    "departure_airport": "PEK",
                    "arrival_airport": "CAN",
                    "aircraft_type": "B738",
                    "status": "en-route",
                    "source": "test",
                },
            ]
        )
        assert n == 2
        extra = await store._load_detail_extra("CES123")
        assert extra and extra["departure_airport"] == "PVG"
        await db_module.close_db()

    asyncio.run(_run())
