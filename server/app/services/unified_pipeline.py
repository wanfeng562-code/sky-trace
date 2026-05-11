from __future__ import annotations

import asyncio
import json
import logging
import math
import random
from datetime import datetime, timezone
from typing import Any, Literal

import aiohttp

from app.core.config import settings
from app.models.schemas import FlightBrief, WsEvent
from app.services.flight_store import FlightStore
from app.services.mock_collector import MockCollector

logger = logging.getLogger(__name__)
LayerName = Literal["realtime", "environment", "commercial"]

# OpenSky OAuth2 token endpoint (client credentials flow).
_OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)

# Static lat/lon for top global aviation hubs used as weather sampling points.
# Keyed by IATA airport code; overridable via OPENWEATHER_HUBS in .env.
_HUB_COORDS: dict[str, tuple[float, float]] = {
    "CAN": (23.3925, 113.2988),   # Guangzhou Baiyun
    "SZX": (22.6395, 113.8108),   # Shenzhen Bao'an
    "PEK": (40.0799, 116.5833),   # Beijing Capital
    "PVG": (31.1434, 121.8052),   # Shanghai Pudong
    "HKG": (22.3080, 113.9185),   # Hong Kong
    "NRT": (35.7647, 140.3864),   # Tokyo Narita
    "ICN": (37.4602, 126.4407),   # Seoul Incheon
    "SIN": (1.3644,  103.9915),   # Singapore Changi
    "DXB": (25.2528,  55.3644),   # Dubai
    "DOH": (25.2609,  51.6138),   # Doha Hamad
    "LHR": (51.4775,  -0.4614),   # London Heathrow
    "CDG": (49.0097,   2.5479),   # Paris CDG
    "FRA": (50.0379,   8.5622),   # Frankfurt
    "AMS": (52.3086,   4.7639),   # Amsterdam Schiphol
    "JFK": (40.6413,  -73.7781),  # New York JFK
    "LAX": (33.9425, -118.4081),  # Los Angeles
    "ORD": (41.9742,  -87.9073),  # Chicago O'Hare
    "ATL": (33.6367,  -84.4281),  # Atlanta
    "SYD": (-33.9399, 151.1753),  # Sydney Kingsford Smith
    "GRU": (-23.4356,  -46.4731), # São Paulo Guarulhos
}
_DEFAULT_HUBS: list[str] = list(_HUB_COORDS.keys())

# Public mapping used by the /airports API endpoint.
# Each entry: { iata, name, lat, lon }
HUB_INFO: dict[str, dict] = {
    "CAN": {"iata": "CAN", "name": "广州白云",        "lat": 23.3925,  "lon": 113.2988},
    "SZX": {"iata": "SZX", "name": "深圳宝安",        "lat": 22.6395,  "lon": 113.8108},
    "PEK": {"iata": "PEK", "name": "北京首都",        "lat": 40.0799,  "lon": 116.5833},
    "PVG": {"iata": "PVG", "name": "上海浦东",        "lat": 31.1434,  "lon": 121.8052},
    "HKG": {"iata": "HKG", "name": "香港国际",        "lat": 22.3080,  "lon": 113.9185},
    "NRT": {"iata": "NRT", "name": "东京成田",        "lat": 35.7647,  "lon": 140.3864},
    "ICN": {"iata": "ICN", "name": "首尔仁川",        "lat": 37.4602,  "lon": 126.4407},
    "SIN": {"iata": "SIN", "name": "新加坡樟宜",      "lat": 1.3644,   "lon": 103.9915},
    "DXB": {"iata": "DXB", "name": "迪拜国际",        "lat": 25.2528,  "lon": 55.3644},
    "DOH": {"iata": "DOH", "name": "多哈哈马德",      "lat": 25.2609,  "lon": 51.6138},
    "LHR": {"iata": "LHR", "name": "伦敦希思罗",      "lat": 51.4775,  "lon": -0.4614},
    "CDG": {"iata": "CDG", "name": "巴黎戴高乐",      "lat": 49.0097,  "lon": 2.5479},
    "FRA": {"iata": "FRA", "name": "法兰克福",        "lat": 50.0379,  "lon": 8.5622},
    "AMS": {"iata": "AMS", "name": "阿姆斯特丹史基浦","lat": 52.3086,  "lon": 4.7639},
    "JFK": {"iata": "JFK", "name": "纽约肯尼迪",      "lat": 40.6413,  "lon": -73.7781},
    "LAX": {"iata": "LAX", "name": "洛杉矶国际",      "lat": 33.9425,  "lon": -118.4081},
    "ORD": {"iata": "ORD", "name": "芝加哥奥黑尔",    "lat": 41.9742,  "lon": -87.9073},
    "ATL": {"iata": "ATL", "name": "亚特兰大哈兹菲尔德","lat": 33.6367, "lon": -84.4281},
    "SYD": {"iata": "SYD", "name": "悉尼金斯福德史密斯","lat": -33.9399,"lon": 151.1753},
    "GRU": {"iata": "GRU", "name": "圣保罗瓜鲁柳斯",  "lat": -23.4356, "lon": -46.4731},
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two lat/lon points."""
    R = 6_371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class UnifiedDataPipeline:
    """Collect data from multiple providers and expose unified cache/state."""

    def __init__(
        self,
        flight_store: FlightStore,
        mock_collector: MockCollector,
        broadcast_manager: Any = None,
    ) -> None:
        self._flight_store = flight_store
        self._mock_collector = mock_collector
        self._broadcast_manager = broadcast_manager
        self._lock = asyncio.Lock()

        self._weather_cache: dict[str, Any] = {}
        self._air_quality_cache: dict[str, Any] = {}
        self._commercial_cache: dict[str, Any] = {}

        # Periodic fleet snapshots for historical playback.
        self._last_snapshot_saved_at: datetime | None = None

        # Per-API daily quota counters.  Reset automatically when date changes.
        self._quota: dict[str, dict[str, Any]] = {
            "opensky": {"date": None, "calls": 0, "daily_budget": settings.dev_realtime_daily_budget_calls},
            "openweather": {"date": None, "calls": 0},
            "airlabs": {"date": None, "calls": 0},
        }

        self._status: dict[str, dict[str, Any]] = {
            "profile": {
                "profile": settings.app_profile,
                "realtime_interval_seconds": settings.interval_seconds("realtime"),
                "environment_interval_seconds": settings.interval_seconds("environment"),
                "commercial_interval_seconds": settings.interval_seconds("commercial"),
                "default_realtime_source": settings.realtime_source,
                "realtime_fallback_to_mock": settings.realtime_fallback_to_mock,
            },
            "realtime": {
                "source": settings.realtime_source,
                "last_success_at": None,
                "last_error_at": None,
                "last_error": None,
                "last_count": 0,
                "success_count": 0,
                "failure_count": 0,
            },
            "environment": {
                "source": "openweather",
                "last_success_at": None,
                "last_error_at": None,
                "last_error": None,
                "last_count": 0,
                "success_count": 0,
                "failure_count": 0,
            },
            "commercial": {
                "source": "airlabs",
                "last_success_at": None,
                "last_error_at": None,
                "last_error": None,
                "last_count": 0,
                "success_count": 0,
                "failure_count": 0,
            },
        }

        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._session: aiohttp.ClientSession | None = None
        self._proxy: str | None = None

        # OAuth2 Bearer token cache for OpenSky (client-credentials flow).
        self._opensky_token: str | None = None
        self._opensky_token_expires_at: float = 0.0  # monotonic seconds

        # FR24 background collector cache.
        # Populated by _fr24_background_loop every ~90 s; never blocks realtime cycle.
        self._fr24_cache: list[FlightBrief] = []
        self._fr24_bg_task: asyncio.Task | None = None
        # Set to True when FR24 returns 403 Forbidden; the loop stops and
        # the realtime layer falls back to OpenSky-only.
        self._fr24_disabled: bool = False
        # Maps our flight_id ("fr24-{icao24}") → FR24 internal flight ID.
        # Used by fetch_fr24_flight_detail() to call get_flight_details().
        self._fr24_id_map: dict[str, str] = {}

    async def start(self) -> None:
        if self._running:
            return

        timeout = aiohttp.ClientTimeout(total=settings.http_timeout_seconds)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self._proxy = settings.http_proxy or None
        if self._proxy:
            logger.info("HTTP proxy configured: %s", self._proxy)
        self._running = True
        self._tasks = [
            asyncio.create_task(self._run_layer("realtime"), name="collector-realtime"),
            asyncio.create_task(self._run_layer("environment"), name="collector-environment"),
            asyncio.create_task(self._run_layer("commercial"), name="collector-commercial"),
        ]
        if settings.fr24_proxy_url:
            self._fr24_bg_task = asyncio.create_task(
                self._fr24_background_loop(), name="collector-fr24"
            )
        logger.info(
            "unified pipeline started with profile=%s realtime=%ss env=%ss commercial=%ss",
            settings.app_profile,
            settings.interval_seconds("realtime"),
            settings.interval_seconds("environment"),
            settings.interval_seconds("commercial"),
        )
        if settings.opensky_client_id and settings.opensky_client_secret:
            logger.info("OpenSky auth: OAuth2 client credentials (4 000 credits/day)")
        elif settings.opensky_username and settings.opensky_password:
            logger.warning(
                "OpenSky auth: Basic auth is deprecated since 2024 and is now treated as "
                "anonymous (400 credits/day ÷ 4 credits/global-call = ~100 calls). "
                "Set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET for full 4 000 credits/day. "
                "Create a client at https://opensky-network.org/my-opensky/account"
            )
        else:
            logger.warning(
                "OpenSky auth: no credentials configured — running as anonymous "
                "(400 credits/day, 10-second time resolution)."
            )

        if settings.fr24_proxy_url:
            logger.info(
                "FlightRadar24: Cloudflare Worker proxy configured (%s)",
                settings.fr24_proxy_url,
            )
        else:
            logger.debug(
                "FlightRadar24: FR24_PROXY_URL not set — FR24 supplemental source disabled. "
                "Deploy a worker at https://github.com/DimaD16/cloudflare-workers-fr24-proxy"
            )

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._fr24_bg_task and not self._fr24_bg_task.done():
            self._fr24_bg_task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self._fr24_bg_task:
            try:
                await self._fr24_bg_task
            except asyncio.CancelledError:
                pass

        self._tasks = []
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("unified pipeline stopped")

    async def get_status(self) -> dict[str, Any]:
        async with self._lock:
            profile = dict(self._status["profile"])
            profile["realtime_interval_seconds"] = settings.interval_seconds("realtime")
            profile["environment_interval_seconds"] = settings.interval_seconds("environment")
            profile["commercial_interval_seconds"] = settings.interval_seconds("commercial")

            if settings.app_profile == "development" and settings.dev_realtime_use_active_window:
                profile["dev_realtime_active_interval_seconds"] = settings.dev_realtime_active_interval_seconds
                profile["dev_realtime_idle_interval_seconds"] = settings.dev_realtime_idle_interval_seconds
                profile["dev_realtime_active_start"] = (
                    f"{settings.dev_realtime_active_start_hour:02d}:{settings.dev_realtime_active_start_minute:02d}"
                )
                profile["dev_realtime_active_end"] = settings.development_realtime_active_end_hhmm()
                profile["dev_realtime_is_active_now"] = settings.development_realtime_is_active_now()

            return {
                "profile": profile,
                "realtime": dict(self._status["realtime"]),
                "environment": dict(self._status["environment"]),
                "commercial": dict(self._status["commercial"]),
            }

    async def get_weather_cache(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self._weather_cache)

    async def get_air_quality_cache(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self._air_quality_cache)

    async def get_commercial_cache(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self._commercial_cache)

    async def _run_layer(self, layer: LayerName) -> None:
        while self._running:
            try:
                if layer == "realtime":
                    await self._collect_realtime()
                elif layer == "environment":
                    await self._collect_environment()
                else:
                    await self._collect_commercial()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                msg = str(exc).strip() or exc.__class__.__name__
                await self._record_failure(layer, msg)
                logger.warning("%s collection failed [%s]: %s", layer, type(exc).__name__, msg)
            await asyncio.sleep(settings.interval_seconds(layer))

    async def _collect_realtime(self) -> None:
        source = settings.realtime_source
        updates: list[FlightBrief] = []
        note: str | None = None

        if source == "opensky":
            try:
                updates = await self._fetch_opensky_snapshot()
            except Exception as exc:
                if not settings.realtime_fallback_to_mock:
                    raise
                reason = str(exc).strip() or exc.__class__.__name__
                logger.warning("OpenSky failed (%s: %s), falling back to mock data", type(exc).__name__, reason)
                updates = self._mock_collector.collect()
                source = "mock-fallback"
                note = f"OpenSky failed, fallback to mock: {reason}"
            if not updates and settings.realtime_fallback_to_mock:
                logger.warning("OpenSky returned empty snapshot, falling back to mock data")
                updates = self._mock_collector.collect()
                source = "mock-fallback"
                note = "OpenSky returned empty snapshot, fallback to mock"
        else:
            updates = self._mock_collector.collect()

        await self._flight_store.apply_updates(updates)

        # Merge cached FR24 data (collected asynchronously in the background).
        # FR24 flights use a distinct "fr24-" prefix so they don't collide with
        # OpenSky/mock flight IDs. Only merge when we have live primary data.
        # When FR24 is disabled (403 received) we silently skip this step,
        # falling back to OpenSky as the sole realtime source.
        if updates and self._fr24_cache and not self._fr24_disabled:
            await self._flight_store.apply_updates(self._fr24_cache)
            logger.debug("FR24 cache merged: %d supplemental flights", len(self._fr24_cache))

        await self._record_success("realtime", source=source, count=len(updates), note=note)

        # Persist a compact snapshot for historical playback (throttled).
        if updates:
            await self._maybe_save_snapshot(updates)

        if self._broadcast_manager and updates:
            # Build the broadcast payload: OpenSky flights + FR24 flights that
            # don't duplicate an already-tracked icao24 from OpenSky.
            broadcast_flights: list[FlightBrief] = list(updates)
            if self._fr24_cache and not self._fr24_disabled:
                opensky_icao24s = {
                    f.flight_id[7:] for f in updates if f.flight_id.startswith("icao24-")
                }
                for fr24_f in self._fr24_cache:
                    fid = fr24_f.flight_id
                    # Skip fr24 entry when OpenSky already tracks the same aircraft
                    if fid.startswith("fr24-") and fid[5:] in opensky_icao24s:
                        continue
                    broadcast_flights.append(fr24_f)
            event = WsEvent(
                event="snapshot",
                ts=_utc_now(),
                data=[f.model_dump(mode="json") for f in broadcast_flights],
            )
            await self._broadcast_manager.broadcast(event)

    async def _collect_environment(self) -> None:
        if not settings.openweather_api_key:
            await self._record_success(
                "environment",
                source="openweather",
                count=0,
                note="OPENWEATHER_API_KEY missing, environment refresh skipped",
            )
            return

        # Resolve hub list: config override → built-in default
        if settings.openweather_hubs:
            hub_list = [h.strip().upper() for h in settings.openweather_hubs.split(",") if h.strip()]
        else:
            hub_list = _DEFAULT_HUBS

        hubs: dict[str, tuple[float, float]] = {
            iata: _HUB_COORDS[iata] for iata in hub_list if iata in _HUB_COORDS
        }
        if not hubs:
            # Absolute fallback: use configured lat/lon as a single unnamed point
            logger.warning("No valid hub airports resolved; falling back to config lat/lon")
            hubs = {"_PRIMARY": (settings.openweather_lat, settings.openweather_lon)}

        sem = asyncio.Semaphore(5)  # max 5 concurrent requests to OpenWeather

        async def _fetch_point(
            key: str, lat: float, lon: float, *, do_aq: bool = True
        ) -> tuple[str, dict | None, dict | None]:
            async with sem:
                try:
                    weather = await self._fetch_openweather_by_coords(lat, lon)
                    weather["iata"] = key
                except Exception as exc:
                    logger.warning("Weather fetch failed for %s: %s [%s]", key, exc, type(exc).__name__)
                    return key, None, None
                aq: dict | None = None
                if do_aq:
                    try:
                        aq = await self._fetch_openweather_air_quality(lat, lon)
                        aq["iata"] = key
                    except Exception as exc:
                        logger.warning("Air quality fetch failed for %s: %s", key, exc)
                return key, weather, aq

        # ── Hub fetch (with retry) ──────────────────────────────────────────
        results = await asyncio.gather(
            *[_fetch_point(iata, lat, lon, do_aq=True) for iata, (lat, lon) in hubs.items()],
            return_exceptions=True,
        )

        # One-shot retry for hubs whose weather fetch returned None (e.g. transient timeout)
        failed_hubs: dict[str, tuple[float, float]] = {
            r[0]: hubs[r[0]]
            for r in results
            if isinstance(r, tuple) and r[1] is None and r[0] in hubs
        }
        if failed_hubs:
            logger.info(
                "Retrying %d failed hub(s) after 5 s: %s",
                len(failed_hubs),
                sorted(failed_hubs),
            )
            await asyncio.sleep(5)
            retry_results = await asyncio.gather(
                *[_fetch_point(iata, lat, lon, do_aq=True) for iata, (lat, lon) in failed_hubs.items()],
                return_exceptions=True,
            )
            # Drop original None-results for retried hubs, append retry outcomes
            results = [
                r for r in results
                if not (isinstance(r, tuple) and r[0] in failed_hubs)
            ] + list(retry_results)

        new_weather: dict[str, dict] = {}
        new_aq: dict[str, dict] = {}
        ok_count = 0
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Hub weather fetch error: %s [%s]", result, type(result).__name__)
                continue
            key, w, aq = result
            if w is None:
                continue
            new_weather[key] = w
            if aq:
                new_aq[key] = aq
            ok_count += 1

        # ── Dynamic 5° grid cells based on active flight positions ─────────
        # Build the set of 5° cells already covered by fixed hub airports.
        hub_cells: set[tuple[int, int]] = {
            (int(lat / 5) * 5, int(lon / 5) * 5) for _, (lat, lon) in hubs.items()
        }

        # Collect unique 5° grid cells from current active flights.
        try:
            active_flights = await self._flight_store.list_flights()
        except Exception as exc:
            active_flights = []
            logger.debug("Failed to get active flights for grid sampling: %s", exc)

        grid_cells: set[tuple[int, int]] = set()
        for f in active_flights:
            cell = (int(f.lat / 5) * 5, int(f.lon / 5) * 5)
            if cell not in hub_cells:
                grid_cells.add(cell)

        # Limit to 80 extra grid cells; sample randomly if more.
        _MAX_GRID = 80
        selected_cells: list[tuple[int, int]] = (
            random.sample(sorted(grid_cells), _MAX_GRID)
            if len(grid_cells) > _MAX_GRID
            else list(grid_cells)
        )

        if selected_cells:
            # Representative point: centre of each 5° cell.
            grid_points: dict[str, tuple[float, float]] = {
                f"GRD_{clat:+d}_{clon:+d}": (clat + 2.5, clon + 2.5)
                for clat, clon in selected_cells
            }
            grid_results = await asyncio.gather(
                *[_fetch_point(key, lat, lon, do_aq=False) for key, (lat, lon) in grid_points.items()],
                return_exceptions=True,
            )
            grid_ok = 0
            for result in grid_results:
                if isinstance(result, Exception):
                    logger.debug("Grid weather fetch error: %s", result)
                    continue
                key, w, _ = result
                if w is not None:
                    new_weather[key] = w
                    grid_ok += 1
            logger.info(
                "environment grid: %d/%d cells OK (covering ~%d active flights)",
                grid_ok, len(selected_cells), len(active_flights),
            )

        async with self._lock:
            self._weather_cache = new_weather
            self._air_quality_cache = new_aq

        total_ok = ok_count + (grid_ok if selected_cells else 0)
        logger.info("environment collected: %d/%d hubs OK, %d total points", ok_count, len(hubs), total_ok)
        await self._record_success("environment", source="openweather", count=total_ok)

    async def _collect_commercial(self) -> None:
        """Fetch bulk AirLabs /flights snapshot for the configured bbox and upsert all records.

        One API call per ``commercial_interval_seconds`` (default 24 h in dev,
        meaning ≈ 30 calls / month) regardless of how many flights are in the area.
        This is far more quota-efficient than the previous per-callsign approach.
        """
        if not settings.airlabs_api_key:
            await self._record_success(
                "commercial",
                source="airlabs",
                count=0,
                note="AIRLABS_API_KEY missing – bulk enrichment disabled",
            )
            return

        flights = await self._fetch_airlabs_bulk_snapshot()
        count = 0
        for f in flights:
            cs = f.get("flight_icao") or f.get("flight_iata")
            if not cs:
                continue
            dep = f.get("dep_iata") or f.get("dep_icao")
            arr = f.get("arr_iata") or f.get("arr_icao")
            ac = f.get("aircraft_icao")
            status = f.get("status") or "en-route"
            await self._flight_store.upsert_detail_extra(
                cs,
                departure_airport=dep,
                arrival_airport=arr,
                aircraft_type=ac,
                status=status,
                source="airlabs",
            )
            count += 1

        logger.info("AirLabs bulk snapshot: %d flights enriched", count)
        await self._record_success("commercial", source="airlabs", count=count)

    async def _fetch_airlabs_bulk_snapshot(self) -> list[dict[str, Any]]:
        """Call AirLabs /flights with the configured bbox and return the raw list.

        The response is a plain JSON array – each element contains ``flight_icao``,
        ``dep_iata``, ``arr_iata``, ``aircraft_icao``, ``status`` and more.
        One call here covers *all* flights in the area, so quota cost is O(1)
        rather than O(unique callsigns).

        AirLabs bbox format: SW-lat, SW-lon, NE-lat, NE-lon
        Our OPENSKY_BBOX format: lamin, lamax, lomin, lomax
        Conversion: lamin,lomin → SW; lamax,lomax → NE
        """
        session = self._require_session()
        url = f"{settings.airlabs_base_url.rstrip('/')}/flights"
        params: dict[str, str] = {"api_key": settings.airlabs_api_key}

        if settings.opensky_bbox:
            try:
                lamin, lamax, lomin, lomax = [
                    float(x.strip()) for x in settings.opensky_bbox.split(",")
                ]
                params["bbox"] = f"{lamin},{lomin},{lamax},{lomax}"
            except ValueError:
                logger.warning("OPENSKY_BBOX format invalid, fetching without bbox")

        async with session.get(url, params=params, proxy=self._proxy) as resp:
            if resp.status == 429:
                logger.warning("AirLabs rate-limited (429) on bulk snapshot, skipping")
                return []
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"AirLabs HTTP {resp.status}: {text[:200]}")
            payload = await resp.json(content_type=None)

        if not isinstance(payload, list):
            # Free plan wraps response as {"request":{...}, "response":[...]}
            if isinstance(payload, dict) and isinstance(payload.get("response"), list):
                return payload["response"]
            # Log the shape for diagnosis without leaking full payload
            keys = list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
            logger.warning("AirLabs bulk snapshot: unexpected response shape (keys=%s)", keys)
            return []

        return payload

    async def _fetch_airlabs_realtime_positions(self) -> list[FlightBrief]:
        """Extract real-time ADS-B position data from the AirLabs /flights snapshot.

        Reuses the same bulk call result as ``_fetch_airlabs_bulk_snapshot`` when
        called independently, keeping quota cost at O(1) per interval.

        Unit conversions:
          - ``alt``   (metres)  → feet  × 3.28084
          - ``speed`` (km/h)    → knots × 0.539957
          - ``lng``   (AirLabs) → stored as ``lon``
        """
        raw = await self._fetch_airlabs_bulk_snapshot()
        now = _utc_now()
        flights: list[FlightBrief] = []

        for f in raw:
            lat = _safe_float(f.get("lat"))
            lng = _safe_float(f.get("lng"))
            if lat is None or lng is None:
                continue

            alt_m = _safe_float(f.get("alt"))
            speed_kmh = _safe_float(f.get("speed"))
            heading_raw = _safe_float(f.get("dir"))

            altitude_ft = int(round(alt_m * 3.28084)) if alt_m is not None else None
            speed_kts = int(round(speed_kmh * 0.539957)) if speed_kmh is not None else None
            heading = int(round(heading_raw)) % 360 if heading_raw is not None else None

            hex_icao = str(f.get("hex") or "").strip().lower()
            callsign = (
                str(f.get("flight_icao") or f.get("flight_iata") or f.get("reg_number") or "").strip()
                or None
            )
            if not hex_icao and not callsign:
                continue

            flight_id = f"airlabs-{hex_icao}" if hex_icao else f"airlabs-{callsign}"
            flights.append(
                FlightBrief(
                    flight_id=flight_id,
                    callsign=callsign,
                    lat=round(lat, 6),
                    lon=round(lng, 6),
                    heading=heading,
                    speed_kts=speed_kts,
                    altitude_ft=altitude_ft,
                    aircraft_category=None,
                    updated_at=now,
                )
            )

        logger.debug("AirLabs realtime positions: %d flights with valid lat/lon", len(flights))
        return flights

    # ------------------------------------------------------------------
    # FR24 background collector
    # ------------------------------------------------------------------

    # Static zone table: parent zones that hit the ~1500 server cap have been
    # replaced with finer subdivisions.  Each region is expected to return well
    # under 1500 flights.  Requests are spread over ~90 s with 1-3 s random
    # jitter between them to avoid anomaly-detection on the FR24 side.
    _FR24_ZONES: list[tuple[str, dict]] = [
        ("europe",          {"tl_y": 72.57, "tl_x": -16.96, "br_y": 33.57, "br_x":  53.05}),
        ("na_north",        {"tl_y": 72.82, "tl_x":-177.97, "br_y": 41.92, "br_x": -52.48}),
        ("na_northwest",    {"tl_y": 54.12, "tl_x":-134.13, "br_y": 38.32, "br_x": -96.75}),
        ("na_northeast",    {"tl_y": 53.72, "tl_x": -98.76, "br_y": 38.22, "br_x": -57.36}),
        ("na_southwest",    {"tl_y": 38.92, "tl_x":-133.98, "br_y": 22.62, "br_x": -96.75}),
        ("na_southeast",    {"tl_y": 38.52, "tl_x": -98.62, "br_y": 22.52, "br_x": -57.36}),
        ("na_s_west",       {"tl_y": 41.92, "tl_x":-177.83, "br_y":  3.82, "br_x":-110.00}),
        ("na_s_east_n",     {"tl_y": 41.92, "tl_x":-110.00, "br_y": 22.00, "br_x": -80.00}),
        ("na_s_east_n2",    {"tl_y": 41.92, "tl_x": -80.00, "br_y": 22.00, "br_x": -52.48}),
        ("na_s_east_s",     {"tl_y": 22.00, "tl_x":-110.00, "br_y":  3.82, "br_x": -52.48}),
        ("southamerica",    {"tl_y": 16.00, "tl_x": -96.00, "br_y":-57.00, "br_x": -31.00}),
        ("oceania_west",    {"tl_y": 19.62, "tl_x":  88.40, "br_y":-55.08, "br_x": 134.00}),
        ("oceania_east",    {"tl_y": 19.62, "tl_x": 134.00, "br_y":-55.08, "br_x": 180.00}),
        ("asia_west",       {"tl_y": 79.98, "tl_x":  40.91, "br_y": 12.48, "br_x":  90.00}),
        ("asia_central",    {"tl_y": 55.00, "tl_x":  90.00, "br_y": 12.48, "br_x": 113.50}),
        ("asia_siberia",    {"tl_y": 79.98, "tl_x":  90.00, "br_y": 55.00, "br_x": 113.50}),
        ("asia_japan_nw",   {"tl_y": 60.38, "tl_x": 113.50, "br_y": 40.00, "br_x": 130.00}),
        ("asia_japan_ne",   {"tl_y": 60.38, "tl_x": 130.00, "br_y": 40.00, "br_x": 145.00}),
        ("asia_japan_sw",   {"tl_y": 40.00, "tl_x": 113.50, "br_y": 22.58, "br_x": 130.00}),
        ("asia_japan_se",   {"tl_y": 40.00, "tl_x": 130.00, "br_y": 22.58, "br_x": 145.00}),
        ("asia_japan_east", {"tl_y": 60.38, "tl_x": 145.00, "br_y": 22.58, "br_x": 176.47}),
        ("africa",          {"tl_y": 39.00, "tl_x": -29.00, "br_y":-39.00, "br_x":  55.00}),
        ("atlantic",        {"tl_y": 52.62, "tl_x": -50.90, "br_y": 15.62, "br_x":  -4.75}),
        ("maldives",        {"tl_y": 10.72, "tl_x":  63.10, "br_y": -6.08, "br_x":  86.53}),
        ("northatlantic",   {"tl_y": 82.62, "tl_x": -84.53, "br_y": 59.02, "br_x":   4.45}),
    ]

    async def _fr24_background_loop(self) -> None:
        """Continuously collect FR24 data in the background, refreshing every ~90 s.

        **Traffic-anomaly-protection design (two-layer random sleep):**

        Layer 1 — inter-request jitter (1-4 s):
          25 zones × avg 2.5 s gap = ~60-70 s for the entire scan round.
          Requests are naturally spread; no burst.

        Layer 2 — post-collection cool-down (20-30 s):
          After all zones are queried and the cache is updated we pause for a
          random 20-30 s window before starting the next round.  This ensures
          that FR24 sees sporadic activity (total cycle ≈ 80-100 s) rather than
          a continuous stream of requests.

        **403 degradation:**
          If any zone query returns HTTP 403 Forbidden the loop sets
          `_fr24_disabled = True`, clears the cache, logs a warning and stops.
          `_collect_realtime` then falls back to OpenSky as the sole source.

        **Commercial enrichment:**
          FR24 free queries already expose origin_airport_iata,
          destination_airport_iata, aircraft_code, number, airline_iata and
          registration for every flight.  We upsert this into `flight_store`
          so the commercial layer gains wide-coverage enrichment at zero
          additional API quota cost.
        """
        proxy_url = settings.fr24_proxy_url.strip()
        try:
            from FlightRadar24 import FlightRadar24API  # type: ignore[import]
        except ImportError:
            logger.warning("ddima16-flightradarapi not installed — FR24 background collector disabled")
            return

        import os as _os

        _proxy_keys = ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy")

        while self._running and not self._fr24_disabled:
            http_proxy = (settings.http_proxy or "").strip() or None
            _saved = {k: _os.environ.get(k) for k in _proxy_keys}
            if http_proxy:
                for k in _proxy_keys:
                    _os.environ[k] = http_proxy

            loop = asyncio.get_event_loop()
            seen_ids: set[str] = set()
            collected: list = []
            got_403 = False

            def _query_zone(zone_coords: dict) -> list:
                fr = FlightRadar24API(proxy_url=proxy_url)
                bounds = fr.get_bounds(zone_coords)
                return fr.get_flights(bounds=bounds)

            n = len(self._FR24_ZONES)
            for i, (zname, zone_coords) in enumerate(self._FR24_ZONES, 1):
                if not self._running or got_403:
                    break
                try:
                    zone_flights = await loop.run_in_executor(None, _query_zone, zone_coords)
                    new_count = 0
                    for f in zone_flights:
                        if f.id not in seen_ids:
                            seen_ids.add(f.id)
                            collected.append(f)
                            new_count += 1
                    logger.debug("FR24 bg %s (%d/%d): %d raw +%d new", zname, i, n, len(zone_flights), new_count)
                except Exception as ze:
                    ze_str = str(ze)
                    if "403" in ze_str or "forbidden" in ze_str.lower():
                        logger.warning(
                            "FR24 403 Forbidden on zone %s — disabling FR24 supplemental "
                            "source. Realtime layer will use OpenSky only.", zname
                        )
                        got_403 = True
                        break
                    logger.debug("FR24 bg zone %s failed: %s", zname, ze)

                # Layer-1 jitter: spread 25 zone requests over ~60-70 s
                if i < n and self._running and not got_403:
                    await asyncio.sleep(random.uniform(1.0, 4.0))

            # Restore env vars regardless of outcome
            for k in _proxy_keys:
                if _saved[k] is None:
                    _os.environ.pop(k, None)
                else:
                    _os.environ[k] = _saved[k]

            if got_403:
                self._fr24_disabled = True
                self._fr24_cache = []
                return

            if collected:
                now = _utc_now()
                new_cache: list[FlightBrief] = []
                new_id_map: dict[str, str] = {}
                for f in collected:
                    lat = _safe_float(getattr(f, "latitude", None))
                    lon = _safe_float(getattr(f, "longitude", None))
                    if lat is None or lon is None:
                        continue
                    altitude_ft_raw = _safe_float(getattr(f, "altitude", None))
                    speed_kts_raw = _safe_float(getattr(f, "ground_speed", None))
                    heading_raw = _safe_float(getattr(f, "heading", None))
                    icao24 = str(getattr(f, "icao_24bit", "") or "").strip().lower()
                    callsign = str(getattr(f, "callsign", "") or "").strip() or None
                    if not icao24 and not callsign:
                        continue
                    fid = f"fr24-{icao24}" if icao24 else f"fr24-{callsign}"
                    fr24_internal_id = str(getattr(f, "id", "") or "").strip()
                    if fr24_internal_id:
                        new_id_map[fid] = fr24_internal_id
                    new_cache.append(FlightBrief(
                        flight_id=fid,
                        callsign=callsign,
                        lat=round(lat, 6),
                        lon=round(lon, 6),
                        heading=int(round(heading_raw)) % 360 if heading_raw is not None else None,
                        speed_kts=int(round(speed_kts_raw)) if speed_kts_raw is not None else None,
                        altitude_ft=int(round(altitude_ft_raw)) if altitude_ft_raw is not None else None,
                        aircraft_category=None,
                        updated_at=now,
                    ))

                    # Commercial enrichment: dep/arr airports, aircraft type, airline,
                    # flight number — all available for free in basic FR24 queries.
                    dep = str(getattr(f, "origin_airport_iata", "") or "").strip() or None
                    arr = str(getattr(f, "destination_airport_iata", "") or "").strip() or None
                    ac_type = str(getattr(f, "aircraft_code", "") or "").strip() or None
                    flight_num = str(getattr(f, "number", "") or "").strip() or None
                    al_iata = str(getattr(f, "airline_iata", "") or "").strip() or None
                    al_icao = str(getattr(f, "airline_icao", "") or "").strip() or None
                    # Only upsert when we have at least one useful field
                    if (dep or arr or ac_type or flight_num) and (callsign or flight_num):
                        cs_key = callsign or flight_num
                        # Fire-and-forget; errors are swallowed inside upsert_detail_extra
                        asyncio.ensure_future(
                            self._flight_store.upsert_detail_extra(
                                cs_key,
                                departure_airport=dep,
                                arrival_airport=arr,
                                aircraft_type=ac_type,
                                status=None,
                                source="fr24",
                            )
                        )

                self._fr24_cache = new_cache
                self._fr24_id_map = new_id_map
                logger.info(
                    "FR24 background collect complete: %d unique flights cached, "
                    "%d with internal IDs, commercial enrichment queued",
                    len(new_cache), len(new_id_map),
                )

            # Layer-2 cool-down: 20-30 s quiet window before starting next round.
            # Total cycle = ~60-70 s (scan) + 20-30 s (cool-down) ≈ 80-100 s.
            if self._running:
                await asyncio.sleep(random.uniform(20.0, 30.0))

    async def fetch_fr24_flight_detail(self, flight_id: str) -> dict | None:
        """On-demand call to FR24 get_flight_details() for a single flight.

        ``flight_id`` is our internal key (e.g. ``"fr24-abc123"``).  We look up the
        corresponding FR24 internal flight ID from ``_fr24_id_map`` and then call
        ``get_flight_details()`` in a thread executor to avoid blocking the event loop.

        Returns the raw details dict from the SDK, or ``None`` if unavailable.
        """
        if self._fr24_disabled:
            return None
        proxy_url = settings.fr24_proxy_url.strip()
        if not proxy_url:
            return None
        fr24_internal_id = self._fr24_id_map.get(flight_id)
        if not fr24_internal_id:
            return None

        try:
            from FlightRadar24 import FlightRadar24API  # type: ignore[import]
        except ImportError:
            return None

        import os as _os
        _proxy_keys = ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy")

        def _sync_get_detail() -> dict | None:
            _saved = {k: _os.environ.get(k) for k in _proxy_keys}
            http_proxy = (settings.http_proxy or "").strip() or None
            if http_proxy:
                for k in _proxy_keys:
                    _os.environ[k] = http_proxy
            try:
                fr = FlightRadar24API(proxy_url=proxy_url)
                details = fr.get_flight_details(fr24_internal_id)
                if not details:
                    return None
                # Sanitize: ensure the result is a plain dict
                return dict(details) if not isinstance(details, dict) else details
            finally:
                for k in _proxy_keys:
                    if _saved[k] is None:
                        _os.environ.pop(k, None)
                    else:
                        _os.environ[k] = _saved[k]

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, _sync_get_detail)
        except Exception as exc:
            logger.warning("FR24 on-demand detail fetch failed for %s: %s", flight_id, exc)
            return None
        return result

    async def _fetch_flightradar_snapshot(self) -> list[FlightBrief]:
        """Fetch real-time flights via the ddima16-flightradarapi SDK (Cloudflare-bypass fork).

        Runs the synchronous SDK call in a thread executor to avoid blocking
        the async event loop.  altitude is already in feet, ground_speed in knots.

        Requires FR24_PROXY_URL to be set in .env pointing to a deployed
        Cloudflare Worker proxy: https://github.com/DimaD16/cloudflare-workers-fr24-proxy
        Format: https://<your-worker>.workers.dev/?url=

        Without a valid proxy URL the request will return 403 from FlightRadar24.
        """
        proxy_url = settings.fr24_proxy_url.strip()
        if not proxy_url:
            logger.debug("FR24_PROXY_URL not configured — FlightRadar24 source disabled")
            return []

        try:
            from FlightRadar24 import FlightRadar24API  # type: ignore[import]
        except ImportError:
            logger.warning(
                "ddima16-flightradarapi not installed; run: pip install ddima16-flightradarapi"
            )
            return []

        def _sync_fetch() -> list:
            # The FR24 SDK uses `requests` which reads HTTPS_PROXY/HTTP_PROXY from
            # the environment on each request (trust_env=True).  Inject our
            # http_proxy so requests to the CF Worker go through the local proxy
            # (required in CN network environments).
            import os as _os
            _proxy_keys = ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy")
            _saved = {k: _os.environ.get(k) for k in _proxy_keys}
            http_proxy = (settings.http_proxy or "").strip() or None
            if http_proxy:
                for k in _proxy_keys:
                    _os.environ[k] = http_proxy
            try:
                fr = FlightRadar24API(proxy_url=proxy_url)

                # FR24 single global query is capped at ~1500 by the server.
                # Query every zone + subzone separately, deduplicate by flight
                # ID to maximise coverage (full_count is typically ~14 000+).
                zones = fr.get_zones()
                queries: dict = {}
                for zname, zdata in zones.items():
                    queries[zname] = {k: v for k, v in zdata.items() if k != "subzones"}
                    for sname, sdata in zdata.get("subzones", {}).items():
                        queries[f"{zname}/{sname}"] = sdata

                seen_ids: set = set()
                all_flights: list = []
                for qname, zone in queries.items():
                    bounds = fr.get_bounds(zone)
                    try:
                        for f in fr.get_flights(bounds=bounds):
                            if f.id not in seen_ids:
                                seen_ids.add(f.id)
                                all_flights.append(f)
                    except Exception as ze:
                        logger.debug("FR24 zone %s failed: %s", qname, ze)

                return all_flights
            finally:
                for k in _proxy_keys:
                    if _saved[k] is None:
                        _os.environ.pop(k, None)
                    else:
                        _os.environ[k] = _saved[k]

        loop = asyncio.get_event_loop()
        try:
            raw_flights = await loop.run_in_executor(None, _sync_fetch)
        except Exception as exc:
            logger.warning("FlightRadar24 fetch failed: %s [%s]", exc, type(exc).__name__)
            return []

        now = _utc_now()
        flights: list[FlightBrief] = []

        for f in raw_flights:
            lat = _safe_float(getattr(f, "latitude", None))
            lon = _safe_float(getattr(f, "longitude", None))
            if lat is None or lon is None:
                continue

            altitude_ft_raw = _safe_float(getattr(f, "altitude", None))
            speed_kts_raw = _safe_float(getattr(f, "ground_speed", None))
            heading_raw = _safe_float(getattr(f, "heading", None))

            heading = int(round(heading_raw)) % 360 if heading_raw is not None else None
            altitude_ft = int(round(altitude_ft_raw)) if altitude_ft_raw is not None else None
            speed_kts = int(round(speed_kts_raw)) if speed_kts_raw is not None else None

            icao24 = str(getattr(f, "icao_24bit", "") or "").strip().lower()
            callsign = str(getattr(f, "callsign", "") or "").strip() or None

            if not icao24 and not callsign:
                continue

            flight_id = f"fr24-{icao24}" if icao24 else f"fr24-{callsign}"
            flights.append(
                FlightBrief(
                    flight_id=flight_id,
                    callsign=callsign,
                    lat=round(lat, 6),
                    lon=round(lon, 6),
                    heading=heading,
                    speed_kts=speed_kts,
                    altitude_ft=altitude_ft,
                    aircraft_category=None,
                    updated_at=now,
                )
            )

        logger.debug("FlightRadar24 snapshot: %d flights fetched", len(flights))
        return flights

    async def _get_opensky_auth(
        self,
    ) -> tuple[dict[str, str] | None, aiohttp.BasicAuth | None]:
        """Return (extra_headers, auth) for OpenSky requests.

        Priority:
        1. OAuth2 Bearer token via client_id + client_secret  (4 000 credits/day)
        2. Legacy Basic auth via username + password           (treated as anonymous →
           400 credits/day since OpenSky deprecated Basic auth in 2024)
        3. No credentials                                      (anonymous, 400 credits/day)
        """
        import time

        if settings.opensky_client_id and settings.opensky_client_secret:
            # Reuse cached token when it still has more than 30 s of lifetime left.
            if self._opensky_token and time.monotonic() < self._opensky_token_expires_at - 30:
                return {"Authorization": f"Bearer {self._opensky_token}"}, None

            session = self._require_session()
            async with session.post(
                _OPENSKY_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.opensky_client_id,
                    "client_secret": settings.opensky_client_secret,
                },
                proxy=self._proxy,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(
                        f"OpenSky OAuth2 token request failed ({resp.status}): {text[:200]}"
                    )
                token_data = await resp.json(content_type=None)

            self._opensky_token = token_data["access_token"]
            expires_in = int(token_data.get("expires_in", 1800))
            self._opensky_token_expires_at = time.monotonic() + expires_in
            logger.info("OpenSky OAuth2 token acquired, expires in %ds", expires_in)
            return {"Authorization": f"Bearer {self._opensky_token}"}, None

        if settings.opensky_username and settings.opensky_password:
            return None, aiohttp.BasicAuth(settings.opensky_username, settings.opensky_password)

        return None, None

    async def _fetch_opensky_snapshot(self) -> list[FlightBrief]:
        session = self._require_session()

        # extended=1 requests aircraft category field (index 17) at no extra credit cost
        params: dict[str, Any] = {"extended": 1}
        if settings.opensky_bbox:
            try:
                lamin, lamax, lomin, lomax = [float(item.strip()) for item in settings.opensky_bbox.split(",")]
                params.update({"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax})
            except ValueError as exc:
                raise RuntimeError("OPENSKY_BBOX format invalid") from exc

        extra_headers, auth = await self._get_opensky_auth()

        url = f"{settings.opensky_base_url.rstrip('/')}/states/all"
        async with session.get(
            url, params=params or None, auth=auth, headers=extra_headers, proxy=self._proxy
        ) as resp:
            remaining = resp.headers.get("X-Rate-Limit-Remaining")
            if remaining is not None:
                logger.debug("OpenSky credits remaining today: %s", remaining)
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"OpenSky HTTP {resp.status}: {text[:200]}")
            payload = await resp.json(content_type=None)

        states = payload.get("states") or []
        now = _utc_now()
        flights: list[FlightBrief] = []

        for row in states:
            if not isinstance(row, list) or len(row) < 11:
                continue

            lon = _safe_float(row[5])
            lat = _safe_float(row[6])
            if lon is None or lat is None:
                continue

            speed_ms = _safe_float(row[9])
            altitude_m = _safe_float(row[7])
            heading_raw = _safe_float(row[10])

            speed_kts = int(round(speed_ms * 1.943844)) if speed_ms is not None else None
            altitude_ft = int(round(altitude_m * 3.28084)) if altitude_m is not None else None
            heading = int(round(heading_raw)) % 360 if heading_raw is not None else None

            icao24 = (str(row[0]).strip() if row[0] else "").lower()
            callsign = str(row[1]).strip() if row[1] else None
            if not icao24:
                continue

            # extended=1: index 17 is aircraft category (may be absent in old responses)
            category = int(row[17]) if len(row) >= 18 and row[17] is not None else None

            flights.append(
                FlightBrief(
                    flight_id=f"icao24-{icao24}",
                    callsign=callsign,
                    lat=round(lat, 6),
                    lon=round(lon, 6),
                    heading=heading,
                    speed_kts=speed_kts,
                    altitude_ft=altitude_ft,
                    aircraft_category=category,
                    updated_at=now,
                )
            )

        return flights

    async def _fetch_openweather_by_coords(self, lat: float, lon: float) -> dict[str, Any]:
        """Fetch current weather for a lat/lon coordinate via OpenWeather /weather."""
        session = self._require_session()
        url = f"{settings.openweather_base_url.rstrip('/')}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": settings.openweather_api_key,
            "units": "metric",
        }

        async with session.get(url, params=params, proxy=self._proxy) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"OpenWeather HTTP {resp.status}: {text[:200]}")
            payload = await resp.json(content_type=None)

        weather = payload.get("weather") or []
        main = payload.get("main") or {}
        wind = payload.get("wind") or {}

        return {
            "provider": "openweather",
            "city": payload.get("name"),
            "lat": lat,
            "lon": lon,
            "fetched_at": _utc_now(),
            "weather": weather[0] if weather else None,
            "temperature_c": main.get("temp"),
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "wind": wind,
            "raw": payload,
        }

    async def _fetch_openweather_snapshot(self) -> dict[str, Any]:
        session = self._require_session()
        url = f"{settings.openweather_base_url.rstrip('/')}/weather"
        params = {
            "q": settings.openweather_city,
            "appid": settings.openweather_api_key,
            "units": "metric",
        }

        async with session.get(url, params=params, proxy=self._proxy) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"OpenWeather HTTP {resp.status}: {text[:200]}")
            payload = await resp.json(content_type=None)

        weather = payload.get("weather") or []
        main = payload.get("main") or {}
        wind = payload.get("wind") or {}

        return {
            "provider": "openweather",
            "city": payload.get("name") or settings.openweather_city,
            "fetched_at": _utc_now(),
            "weather": weather[0] if weather else None,
            "temperature_c": main.get("temp"),
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "wind": wind,
            "raw": payload,
        }

    async def _fetch_openweather_air_quality(self, lat: float, lon: float) -> dict[str, Any]:
        session = self._require_session()
        url = f"{settings.openweather_base_url.rstrip('/')}/air_pollution"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": settings.openweather_api_key,
        }

        async with session.get(url, params=params, proxy=self._proxy) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"OpenWeather air_pollution HTTP {resp.status}: {text[:200]}")
            payload = await resp.json(content_type=None)

        items = payload.get("list") or []
        aqi = None
        components: dict[str, Any] = {}
        if items:
            first = items[0]
            aqi = (first.get("main") or {}).get("aqi")
            components = first.get("components") or {}

        return {
            "provider": "openweather",
            "lat": lat,
            "lon": lon,
            "fetched_at": _utc_now(),
            "aqi": aqi,
            "components": components,
            "raw": payload,
        }

    async def _record_success(
        self,
        layer: LayerName,
        *,
        source: str,
        count: int,
        note: str | None = None,
    ) -> None:
        async with self._lock:
            entry = self._status[layer]
            entry["source"] = source
            entry["last_count"] = count
            entry["last_success_at"] = _utc_now()
            entry["last_error"] = note
            if note:
                entry["last_error_at"] = _utc_now()
            entry["success_count"] = int(entry["success_count"]) + 1

            # Quota tracking: increment the per-API daily counter.
            _quota_key = {"realtime": "opensky", "environment": "openweather", "commercial": "airlabs"}.get(layer)
            if _quota_key and count > 0:
                today = _utc_now().date().isoformat()
                q = self._quota[_quota_key]
                if q["date"] != today:
                    q["date"] = today
                    q["calls"] = 0
                q["calls"] += 1

    async def _record_failure(self, layer: LayerName, message: str) -> None:
        async with self._lock:
            entry = self._status[layer]
            entry["last_error"] = message
            entry["last_error_at"] = _utc_now()
            entry["failure_count"] = int(entry["failure_count"]) + 1

    def _require_session(self) -> aiohttp.ClientSession:
        if not self._session:
            raise RuntimeError("HTTP session is not ready")
        return self._session

    # ------------------------------------------------------------------
    # Snapshot / playback helpers
    # ------------------------------------------------------------------

    async def _maybe_save_snapshot(self, flights: list[FlightBrief]) -> None:
        """Throttled: save a compact fleet snapshot at most once per
        ``playback_snapshot_interval_seconds`` seconds.
        """
        now = _utc_now()
        if self._last_snapshot_saved_at is not None:
            elapsed = (now - self._last_snapshot_saved_at).total_seconds()
            if elapsed < settings.playback_snapshot_interval_seconds:
                return

        compact = [
            {
                "id": f.flight_id,
                "lat": f.lat,
                "lon": f.lon,
                "alt": f.altitude_ft,
                "spd": f.speed_kts,
                "hdg": f.heading,
                "cat": f.aircraft_category,
                "cs": f.callsign,
            }
            for f in flights
        ]
        data_json = json.dumps(compact, separators=(",", ":"))

        try:
            from app.services.db import cleanup_old_snapshots, save_flight_snapshot

            await save_flight_snapshot(now.isoformat(), data_json)
            removed = await cleanup_old_snapshots(settings.playback_ttl_hours)
            if removed:
                logger.debug("Playback TTL cleanup: removed %d old snapshots", removed)
        except Exception as exc:
            logger.warning("Failed to save flight snapshot: %s", exc)
            return

        self._last_snapshot_saved_at = now

    # ------------------------------------------------------------------
    # Weather lookup helpers
    # ------------------------------------------------------------------

    async def get_nearest_hub_weather(self, lat: float, lon: float) -> dict[str, Any]:
        """Return cached weather + AQI for the nearest hub that has cached data.

        Iterates hubs in ascending distance order and returns the first one
        that has an entry in the weather cache.  Falls back to the nearest hub
        (with null weather) if none of the hubs have been collected yet.
        No external API call is made.
        """
        # Sort all hubs by distance from the query point.
        ranked = sorted(
            _HUB_COORDS.items(),
            key=lambda kv: _haversine(lat, lon, kv[1][0], kv[1][1]),
        )

        async with self._lock:
            weather_snap = dict(self._weather_cache)
            aq_snap = dict(self._air_quality_cache)

        # Find the nearest hub that actually has cached data.
        for iata, (hlat, hlon) in ranked:
            if iata in weather_snap:
                return {
                    "hub_iata": iata,
                    "distance_km": round(_haversine(lat, lon, hlat, hlon), 1),
                    "weather": weather_snap[iata],
                    "air_quality": aq_snap.get(iata),
                }

        # Fallback: return nearest hub regardless (cache not populated yet).
        best_iata, (blat, blon) = ranked[0]
        return {
            "hub_iata": best_iata,
            "distance_km": round(_haversine(lat, lon, blat, blon), 1),
            "weather": None,
            "air_quality": None,
        }

    async def get_hub_weather_for_iata(self, iata: str | None) -> dict[str, Any] | None:
        """Return cached weather + AQI for the given IATA code, or None if not cached."""
        if not iata:
            return None
        key = iata.strip().upper()
        async with self._lock:
            weather = self._weather_cache.get(key)
            aq = self._air_quality_cache.get(key)
        if weather is None and aq is None:
            return None
        return {"weather": weather, "air_quality": aq}

    async def fetch_weather_at_coords(self, lat: float, lon: float) -> dict[str, Any] | None:
        """Fetch live OpenWeather data at arbitrary coordinates.

        Used for the flight's current position ("location weather").
        Returns ``None`` when OpenWeather is not configured or the request fails.
        """
        if not settings.openweather_api_key:
            return None
        try:
            return await self._fetch_openweather_by_coords(lat, lon)
        except Exception as exc:
            logger.debug("fetch_weather_at_coords(%.4f, %.4f) failed: %s", lat, lon, exc)
            return None

    # ------------------------------------------------------------------
    # Quota monitoring
    # ------------------------------------------------------------------

    async def get_quota(self) -> dict[str, Any]:
        """Return today’s API call counts and configured budgets."""
        async with self._lock:
            osky = self._quota["opensky"]
            ow = self._quota["openweather"]
            al = self._quota["airlabs"]
            return {
                "opensky": {
                    "today_date": osky["date"],
                    "today_calls": osky["calls"],
                    "daily_budget": osky["daily_budget"],
                    "remaining": max(0, osky["daily_budget"] - osky["calls"]),
                    "note": "4 API credits per call for registered users",
                },
                "openweather": {
                    "today_date": ow["date"],
                    "today_calls": ow["calls"],
                    "note": "Each environment cycle = 20 hub calls (weather + AQI)",
                },
                "airlabs": {
                    "today_date": al["date"],
                    "today_calls": al["calls"],
                    "monthly_budget": 1000,
                    "note": "1 bulk call per commercial cycle covers all flights",
                },
                "playback": {
                    "snapshot_interval_seconds": settings.playback_snapshot_interval_seconds,
                    "ttl_hours": settings.playback_ttl_hours,
                    "last_snapshot_at": self._last_snapshot_saved_at,
                },
            }
