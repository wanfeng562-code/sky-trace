"""Regression: retired tile providers must not be exposed by the backend."""
import asyncio

from app.api.routes.map_proxy import get_tile_stats, router


def test_only_metadata_route_is_exposed() -> None:
    assert [route.path for route in router.routes] == ["/api/v1/tiles/stats"]


def test_browser_direct_usage_is_not_reported_as_zero() -> None:
    data = asyncio.run(get_tile_stats())["data"]
    assert data["provider"] == "tianditu"
    assert data["mode"] == "browser-direct"
    assert data["requests"] is None
