from __future__ import annotations

import asyncio
import json
import logging
import math
from datetime import datetime, timezone
from typing import Any, Literal

import aiohttp

from app.core.config import settings
from app.models.schemas import FlightBrief, WsEvent
from app.services.flight_store import FlightStore
from app.services.mock_collector import MockCollector

logger = logging.getLogger(__name__)
LayerName = Literal["realtime", "environment", "commercial"]

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
        logger.info(
            "unified pipeline started with profile=%s realtime=%ss env=%ss commercial=%ss",
            settings.app_profile,
            settings.interval_seconds("realtime"),
            settings.interval_seconds("environment"),
            settings.interval_seconds("commercial"),
        )

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
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
        await self._record_success("realtime", source=source, count=len(updates), note=note)

        # Persist a compact snapshot for historical playback (throttled).
        if updates:
            await self._maybe_save_snapshot(updates)

        if self._broadcast_manager and updates:
            event = WsEvent(
                event="snapshot",
                ts=_utc_now(),
                data=[f.model_dump(mode="json") for f in updates],
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

        async def _fetch_hub(iata: str, lat: float, lon: float) -> tuple[str, dict | None, dict | None]:
            async with sem:
                try:
                    weather = await self._fetch_openweather_by_coords(lat, lon)
                    weather["iata"] = iata
                except Exception as exc:
                    logger.warning("Weather fetch failed for %s: %s [%s]", iata, exc, type(exc).__name__)
                    return iata, None, None
                try:
                    aq = await self._fetch_openweather_air_quality(lat, lon)
                    aq["iata"] = iata
                except Exception as exc:
                    logger.warning("Air quality fetch failed for %s: %s", iata, exc)
                    aq = None
                return iata, weather, aq

        results = await asyncio.gather(
            *[_fetch_hub(iata, lat, lon) for iata, (lat, lon) in hubs.items()],
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
                *[_fetch_hub(iata, lat, lon) for iata, (lat, lon) in failed_hubs.items()],
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
            iata, w, aq = result
            if w is None:
                continue
            new_weather[iata] = w
            if aq:
                new_aq[iata] = aq
            ok_count += 1

        async with self._lock:
            self._weather_cache = new_weather
            self._air_quality_cache = new_aq

        logger.info("environment collected: %d/%d hubs OK", ok_count, len(hubs))
        await self._record_success("environment", source="openweather", count=ok_count)

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

        auth = None
        if settings.opensky_username and settings.opensky_password:
            auth = aiohttp.BasicAuth(settings.opensky_username, settings.opensky_password)

        url = f"{settings.opensky_base_url.rstrip('/')}/states/all"
        async with session.get(url, params=params or None, auth=auth, proxy=self._proxy) as resp:
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
