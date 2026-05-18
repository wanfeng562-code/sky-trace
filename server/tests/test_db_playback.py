"""Unit tests for playback snapshot query helpers."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from app.services import db as db_module


def test_query_playback_frames_skips_corrupt_json(tmp_path, monkeypatch) -> None:
    async def _run() -> None:
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_module.settings, "sqlite_path", str(db_path))

        await db_module.init_db()
        now = datetime(2026, 4, 24, 6, 0, tzinfo=timezone.utc)
        good_ts = now.isoformat()
        bad_ts = (now + timedelta(minutes=5)).isoformat()

        await db_module.save_flight_snapshot(
            good_ts,
            json.dumps([{"id": "icao24-abc", "lat": 1.0, "lon": 2.0}]),
        )
        await db_module.save_flight_snapshot(bad_ts, "not-json")

        frames = await db_module.query_playback_frames(
            now.isoformat(),
            (now + timedelta(minutes=10)).isoformat(),
            300,
        )

        assert len(frames) == 1
        assert frames[0]["ts"] == good_ts
        assert frames[0]["flights"][0]["id"] == "icao24-abc"

        await db_module.close_db()

    asyncio.run(_run())


def test_persist_playback_snapshot_purges_old_rows(tmp_path, monkeypatch) -> None:
    async def _run() -> None:
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_module.settings, "sqlite_path", str(db_path))

        await db_module.init_db()
        old = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        await db_module.save_flight_snapshot(old, "[]")

        snap_removed, tracks_removed = await db_module.persist_playback_snapshot(
            datetime.now(timezone.utc).isoformat(),
            "[]",
            snapshot_ttl_hours=24,
            tracks_ttl_hours=24,
        )

        assert snap_removed >= 1
        assert tracks_removed == 0

        await db_module.close_db()

    asyncio.run(_run())
