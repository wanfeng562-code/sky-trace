"""Map tile reverse proxy.

Forwards map tile / style / font / sprite requests from the browser to
MapTiler Cloud or Stadia Maps through the server-side HTTP proxy configured
in ``HTTP_PROXY``.  This ensures all external tile traffic routes through the
operator's egress proxy rather than originating directly from the end-user's
browser (which may be blocked in certain network environments).

Endpoints
---------
GET /api/v1/tiles/maptiler/{path:path}
    Proxy to https://api.maptiler.com/{path}?{query}

GET /api/v1/tiles/stadia/{path:path}
    Proxy to https://tiles.stadiamaps.com/{path}?{query}

Usage in MapLibre GL JS
-----------------------
Set ``transformRequest`` to rewrite external tile/font/sprite URLs to these
proxy endpoints so every map resource goes through the backend:

    new maplibregl.Map({
      transformRequest: (url) => {
        if (url.startsWith('https://api.maptiler.com'))
          return { url: '/api/v1/tiles/maptiler' + url.slice('https://api.maptiler.com'.length) };
        if (url.startsWith('https://tiles.stadiamaps.com'))
          return { url: '/api/v1/tiles/stadia' + url.slice('https://tiles.stadiamaps.com'.length) };
        return { url };
      }
    });
"""

from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass

import aiohttp
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tiles", tags=["map-proxy"])

# Per-provider request counters (process-lifetime, reset on server restart).
_proxy_stats: dict[str, int] = {"maptiler": 0, "stadia": 0}

# Runtime metrics for cache/retry/serve-stale behaviors.
_proxy_runtime_stats: dict[str, int] = {
    "cache_hit": 0,
    "cache_miss": 0,
    "cache_stale_served": 0,
    "retries": 0,
    "upstream_errors": 0,
}

# Module-level aiohttp session (lazy init, shared across requests).
_proxy_session: aiohttp.ClientSession | None = None


@dataclass
class _CacheEntry:
    content: bytes
    status_code: int
    headers: dict[str, str]
    expires_at: float
    stale_until: float
    created_at: float


# Keep an in-process micro-cache for style/sprite/font resources.
_cache_lock = asyncio.Lock()
_proxy_cache: dict[str, _CacheEntry] = {}
_proxy_cache_bytes = 0

# Cache limits are conservative to avoid memory pressure.
_PROXY_CACHE_MAX_ITEMS = 300
_PROXY_CACHE_MAX_BYTES = 64 * 1024 * 1024  # 64 MiB
_PROXY_CACHE_TTL_SECONDS = 300
_PROXY_CACHE_STALE_SECONDS = 900

# Request headers that are safe and useful to forward to upstream CDNs.
_FORWARD_REQUEST_HEADERS = (
    "if-none-match",
    "if-modified-since",
    "accept",
    "accept-encoding",
)

# Response headers worth preserving for cache behavior and decoding.
_UPSTREAM_PASSTHROUGH_HEADERS = (
    "etag",
    "last-modified",
    "expires",
    "vary",
    "content-encoding",
)


def _cacheable_path(path: str) -> bool:
    lower = path.lower()
    return (
        "style.json" in lower
        or "/fonts/" in lower
        or "/glyphs/" in lower
        or "/sprites/" in lower
    )


def _cache_control_for(path: str, content_type: str) -> str:
    lower_path = path.lower()
    lower_ct = content_type.lower()
    is_immutable = (
        "/fonts/" in lower_path
        or "/glyphs/" in lower_path
        or "/sprites/" in lower_path
        or lower_ct.startswith("image/")
        or lower_ct.startswith("application/x-protobuf")
        or lower_ct.startswith("application/octet-stream")
    )
    if is_immutable:
        return "public, max-age=86400, immutable"
    return "public, max-age=300"


def _response_headers(base: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Access-Control-Allow-Origin": "*",
    }
    if base:
        headers.update(base)
    return headers


def _copy_forward_headers(request: Request) -> dict[str, str]:
    out: dict[str, str] = {}
    for k in _FORWARD_REQUEST_HEADERS:
        v = request.headers.get(k)
        if v:
            out[k] = v
    return out


def _copy_upstream_headers(upstream_headers: aiohttp.typedefs.LooseHeaders) -> dict[str, str]:
    copied: dict[str, str] = {}
    for k in _UPSTREAM_PASSTHROUGH_HEADERS:
        v = upstream_headers.get(k)
        if v:
            copied[k.title()] = v
    return copied


async def _cache_get(target: str, now: float) -> _CacheEntry | None:
    async with _cache_lock:
        entry = _proxy_cache.get(target)
        if not entry:
            _proxy_runtime_stats["cache_miss"] += 1
            return None
        if entry.stale_until <= now:
            # Hard-expired cache entry; evict lazily.
            global _proxy_cache_bytes
            _proxy_cache_bytes -= len(entry.content)
            _proxy_cache.pop(target, None)
            _proxy_runtime_stats["cache_miss"] += 1
            return None
        _proxy_runtime_stats["cache_hit"] += 1
        return entry


async def _cache_set(target: str, entry: _CacheEntry) -> None:
    global _proxy_cache_bytes
    async with _cache_lock:
        old = _proxy_cache.get(target)
        if old:
            _proxy_cache_bytes -= len(old.content)
        _proxy_cache[target] = entry
        _proxy_cache_bytes += len(entry.content)

        # Remove oldest entries first (dict insertion order is preserved).
        while _proxy_cache and (
            len(_proxy_cache) > _PROXY_CACHE_MAX_ITEMS
            or _proxy_cache_bytes > _PROXY_CACHE_MAX_BYTES
        ):
            oldest_key = next(iter(_proxy_cache.keys()))
            oldest = _proxy_cache.pop(oldest_key)
            _proxy_cache_bytes -= len(oldest.content)


async def _session() -> aiohttp.ClientSession:
    global _proxy_session
    if _proxy_session is None or _proxy_session.closed:
        timeout = aiohttp.ClientTimeout(total=35, connect=8, sock_read=25)
        connector = aiohttp.TCPConnector(
            limit=256,
            limit_per_host=64,
            ttl_dns_cache=300,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )
        _proxy_session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            auto_decompress=False,
            headers={"User-Agent": "Sky-Trace-TileProxy/1.0"},
        )
    return _proxy_session


# Content-types that should be cached aggressively by the browser.
_TILE_MIME_PREFIXES = ("image/", "application/x-protobuf", "application/octet-stream")


async def _proxy_request(base_url: str, path: str, request: Request) -> Response:
    """Forward *path* (with original query string) to *base_url* via configured proxy."""
    qs = str(request.url.query)
    target = f"{base_url}/{path}"
    if qs:
        target += f"?{qs}"

    http_proxy = settings.http_proxy or None
    sess = await _session()
    now = time.time()
    use_cache = _cacheable_path(path)
    cached_entry = await _cache_get(target, now) if use_cache else None

    # Serve fresh cache immediately to avoid unnecessary upstream trips.
    if cached_entry and cached_entry.expires_at > now:
        cached_headers = dict(cached_entry.headers)
        cached_headers["X-Proxy-Cache"] = "HIT"
        return Response(
            content=cached_entry.content,
            status_code=cached_entry.status_code,
            headers=_response_headers(cached_headers),
        )

    try:
        forward_headers = _copy_forward_headers(request)
        for attempt in range(2):
            async with sess.get(
                target,
                proxy=http_proxy,
                allow_redirects=True,
                headers=forward_headers,
            ) as upstream:
                if upstream.status == 304:
                    passthrough = _copy_upstream_headers(upstream.headers)
                    passthrough["Cache-Control"] = _cache_control_for(path, "")
                    passthrough["X-Proxy-Cache"] = "REVALIDATED"
                    return Response(
                        status_code=304,
                        headers=_response_headers(passthrough),
                    )

                if upstream.status in (502, 503, 504) and attempt == 0:
                    _proxy_runtime_stats["retries"] += 1
                    await asyncio.sleep(0.12)
                    continue

                if upstream.status >= 400:
                    _proxy_runtime_stats["upstream_errors"] += 1
                    logger.warning("Tile proxy upstream %d: %s", upstream.status, target)
                    raise HTTPException(status_code=upstream.status, detail="Upstream tile error")

                content = await upstream.read()
                ct = upstream.headers.get("Content-Type", "application/octet-stream")

                # Determine browser cache control from content/path characteristics.
                is_tile = any(ct.startswith(p) for p in _TILE_MIME_PREFIXES)
                cache_ctrl = (
                    "public, max-age=86400, immutable"
                    if is_tile
                    else _cache_control_for(path, ct)
                )

                response_headers = _copy_upstream_headers(upstream.headers)
                response_headers["Content-Type"] = ct
                response_headers["Cache-Control"] = cache_ctrl
                response_headers["X-Proxy-Cache"] = "MISS"

                if use_cache:
                    await _cache_set(
                        target,
                        _CacheEntry(
                            content=content,
                            status_code=upstream.status,
                            headers=response_headers,
                            expires_at=now + _PROXY_CACHE_TTL_SECONDS,
                            stale_until=now + _PROXY_CACHE_TTL_SECONDS + _PROXY_CACHE_STALE_SECONDS,
                            created_at=now,
                        ),
                    )

                return Response(
                    content=content,
                    status_code=upstream.status,
                    headers=_response_headers(response_headers),
                )
    except aiohttp.ClientConnectorError as exc:
        _proxy_runtime_stats["upstream_errors"] += 1
        logger.warning("Tile proxy connection error → %s: %s", target, exc)
        if cached_entry and cached_entry.stale_until > now:
            stale_headers = dict(cached_entry.headers)
            stale_headers["X-Proxy-Cache"] = "STALE"
            stale_headers["Warning"] = '110 - "Response is stale"'
            _proxy_runtime_stats["cache_stale_served"] += 1
            return Response(
                content=cached_entry.content,
                status_code=cached_entry.status_code,
                headers=_response_headers(stale_headers),
            )
        raise HTTPException(status_code=502, detail="Tile proxy connection failed") from exc
    except aiohttp.ServerTimeoutError as exc:
        _proxy_runtime_stats["upstream_errors"] += 1
        logger.warning("Tile proxy timeout → %s", target)
        if cached_entry and cached_entry.stale_until > now:
            stale_headers = dict(cached_entry.headers)
            stale_headers["X-Proxy-Cache"] = "STALE"
            stale_headers["Warning"] = '110 - "Response is stale"'
            _proxy_runtime_stats["cache_stale_served"] += 1
            return Response(
                content=cached_entry.content,
                status_code=cached_entry.status_code,
                headers=_response_headers(stale_headers),
            )
        raise HTTPException(status_code=504, detail="Tile proxy timeout") from exc


@router.get("/maptiler/{path:path}", summary="MapTiler Cloud tile proxy")
async def proxy_maptiler(path: str, request: Request) -> Response:
    """Proxy MapTiler Cloud tile / style / font requests via the configured HTTP proxy."""
    _proxy_stats["maptiler"] += 1
    return await _proxy_request("https://api.maptiler.com", path, request)


@router.get("/stadia/{path:path}", summary="Stadia Maps tile proxy")
async def proxy_stadia(path: str, request: Request) -> Response:
    """Proxy Stadia Maps tile / style requests via the configured HTTP proxy."""
    _proxy_stats["stadia"] += 1
    return await _proxy_request("https://tiles.stadiamaps.com", path, request)


@router.get("/stats", summary="Tile proxy request stats")
async def get_tile_stats() -> dict:
    """Return cumulative tile proxy request counts since server start."""
    return {
        "data": {
            **dict(_proxy_stats),
            **dict(_proxy_runtime_stats),
            "cache_items": len(_proxy_cache),
            "cache_bytes": _proxy_cache_bytes,
        }
    }
