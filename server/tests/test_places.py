"""Tests for shared place name cache API."""

from __future__ import annotations

import asyncio

from app.services import db as db_module


def test_upsert_and_get_place_names(tmp_path, monkeypatch) -> None:
    async def _run() -> None:
        monkeypatch.setattr(
            db_module.settings, "sqlite_path", str(tmp_path / "places.db")
        )
        await db_module.init_db()
        n = await db_module.upsert_place_names(
            [
                {
                    "cache_key": "ap.zh:PEK",
                    "name_zh": "北京首都",
                    "name_en": "Beijing Capital",
                    "source_text": "Beijing",
                },
            ]
        )
        assert n == 1
        rows = await db_module.get_place_names(["ap.zh:PEK", "missing"])
        assert len(rows) == 1
        assert rows[0]["name_zh"] == "北京首都"
        await db_module.close_db()

    asyncio.run(_run())
