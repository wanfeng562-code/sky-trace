"""Basemap service metadata. Legacy overseas tile proxy endpoints are retired."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/tiles", tags=["map-service"])

@router.get("/stats", summary="Basemap service metadata")
async def get_tile_stats() -> dict:
    return {"data": {
        "provider": "tianditu", "mode": "browser-direct", "requests": None,
        "note": "浏览器直接调用天地图；用量和额度请查看天地图应用控制台。",
    }}
