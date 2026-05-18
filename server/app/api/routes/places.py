"""Place / airport display name cache (SQLite, shared across clients)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.models.schemas import ApiResponse
from app.services.db import get_place_names, upsert_place_names

router = APIRouter(prefix="/api/v1", tags=["places"])


class PlaceNameItem(BaseModel):
    cache_key: str = Field(min_length=1, max_length=180)
    name_zh: str = Field(min_length=1, max_length=500)
    name_en: str | None = Field(default=None, max_length=500)
    source_text: str | None = Field(default=None, max_length=500)


class PlaceNameBatchIn(BaseModel):
    items: list[PlaceNameItem] = Field(min_length=1, max_length=500)


@router.get("/places/names")
async def list_place_names(
    keys: str = Query(
        ...,
        description="Comma-separated cache keys, e.g. ap.zh:PEK,place.zh:CN-BJ",
    ),
) -> ApiResponse:
    """Return cached simplified Chinese names for the given keys."""
    key_list = [k.strip() for k in keys.split(",") if k.strip()]
    rows = await get_place_names(key_list)
    return ApiResponse(data={"items": rows})


@router.put("/places/names")
async def put_place_names(body: PlaceNameBatchIn) -> ApiResponse:
    """Upsert display names (client-side 简繁转换结果可同步到此)."""
    count = await upsert_place_names(
        [item.model_dump() for item in body.items],
    )
    return ApiResponse(data={"upserted": count})
