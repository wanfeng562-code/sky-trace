from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Literal

import aiohttp

from app.core.config import settings
from app.models.schemas import FlightBrief
from app.services.flight_store import FlightStore
from app.services.mock_collector import MockCollector

logger = logging.getLogger(__name__)
LayerName = Literal["realtime", "environment", "commercial"]


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

    def __init__(self, flight_store: FlightStore, mock_collector: MockCollector) -> None:
        self._flight_store = flight_store
        self._mock_collector = mock_collector
        self._lock = asyncio.Lock()

        self._weather_cache: dict[str, Any] = {}
        self._commercial_cache: dict[str, Any] = {}
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
                "source": "aerodatabox+aviationstack",
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

    async def start(self) -> None:
        if self._running:
            return

        timeout = aiohttp.ClientTimeout(total=settings.http_timeout_seconds)
        self._session = aiohttp.ClientSession(timeout=timeout)
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
                await self._record_failure(layer, str(exc))
                logger.warning("%s collection failed: %s", layer, exc)
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
                updates = self._mock_collector.collect()
                source = "mock-fallback"
                note = f"OpenSky failed, fallback to mock: {reason}"
            if not updates and settings.realtime_fallback_to_mock:
                updates = self._mock_collector.collect()
                source = "mock-fallback"
                note = "OpenSky returned empty snapshot, fallback to mock"
        else:
            updates = self._mock_collector.collect()

        await self._flight_store.apply_updates(updates)
        await self._record_success("realtime", source=source, count=len(updates), note=note)

    async def _collect_environment(self) -> None:
        if not settings.openweather_api_key:
            await self._record_success(
                "environment",
                source="openweather",
                count=0,
                note="OPENWEATHER_API_KEY missing, environment refresh skipped",
            )
            return

        payload = await self._fetch_openweather_snapshot()
        async with self._lock:
            self._weather_cache = payload
        await self._record_success("environment", source="openweather", count=1)

    async def _collect_commercial(self) -> None:
        has_aero = bool(settings.aerodatabox_api_key)
        has_aviationstack = bool(settings.aviationstack_access_key)

        if not has_aero and not has_aviationstack:
            await self._record_success(
                "commercial",
                source="aerodatabox+aviationstack",
                count=0,
                note="No commercial API keys configured, commercial refresh skipped",
            )
            return

        merged: dict[str, Any] = {
            "fetched_at": _utc_now(),
            "profile": settings.app_profile,
            "sources": {},
        }
        refreshed = 0

        if has_aero:
            try:
                merged["sources"]["aerodatabox"] = await self._fetch_aerodatabox_snapshot()
                refreshed += 1
            except Exception as exc:  # pragma: no cover - network side effect
                merged["sources"]["aerodatabox"] = {"error": str(exc)}

        if has_aviationstack:
            try:
                merged["sources"]["aviationstack"] = await self._fetch_aviationstack_snapshot()
                refreshed += 1
            except Exception as exc:  # pragma: no cover - network side effect
                merged["sources"]["aviationstack"] = {"error": str(exc)}

        if refreshed == 0:
            errors = [
                value.get("error")
                for value in merged["sources"].values()
                if isinstance(value, dict) and value.get("error")
            ]
            raise RuntimeError("; ".join(errors) if errors else "commercial refresh failed")

        async with self._lock:
            self._commercial_cache = merged
        await self._record_success("commercial", source="aerodatabox+aviationstack", count=refreshed)

    async def _fetch_opensky_snapshot(self) -> list[FlightBrief]:
        session = self._require_session()

        params: dict[str, float] = {}
        if settings.opensky_bbox:
            try:
                lamin, lamax, lomin, lomax = [float(item.strip()) for item in settings.opensky_bbox.split(",")]
                params = {"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}
            except ValueError as exc:
                raise RuntimeError("OPENSKY_BBOX format invalid") from exc

        auth = None
        if settings.opensky_username and settings.opensky_password:
            auth = aiohttp.BasicAuth(settings.opensky_username, settings.opensky_password)

        url = f"{settings.opensky_base_url.rstrip('/')}/states/all"
        async with session.get(url, params=params or None, auth=auth) as resp:
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

            flights.append(
                FlightBrief(
                    flight_id=f"icao24-{icao24}",
                    callsign=callsign,
                    lat=round(lat, 6),
                    lon=round(lon, 6),
                    heading=heading,
                    speed_kts=speed_kts,
                    altitude_ft=altitude_ft,
                    updated_at=now,
                )
            )

        return flights

    async def _fetch_openweather_snapshot(self) -> dict[str, Any]:
        session = self._require_session()
        url = f"{settings.openweather_base_url.rstrip('/')}/weather"
        params = {
            "q": settings.openweather_city,
            "appid": settings.openweather_api_key,
            "units": "metric",
        }

        async with session.get(url, params=params) as resp:
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

    async def _fetch_aerodatabox_snapshot(self) -> dict[str, Any]:
        session = self._require_session()
        path = settings.aerodatabox_test_path.lstrip("/")
        url = f"{settings.aerodatabox_base_url.rstrip('/')}/{path}"
        headers = {
            "x-rapidapi-key": settings.aerodatabox_api_key,
            "x-rapidapi-host": settings.aerodatabox_api_host,
        }
        params = {"withLeg": str(settings.aerodatabox_with_leg).lower()}

        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"AeroDataBox HTTP {resp.status}: {text[:200]}")
            payload = await resp.json(content_type=None)

        arrivals = payload.get("arrivals") if isinstance(payload, dict) else []
        departures = payload.get("departures") if isinstance(payload, dict) else []

        return {
            "fetched_at": _utc_now(),
            "arrivals_count": len(arrivals) if isinstance(arrivals, list) else None,
            "departures_count": len(departures) if isinstance(departures, list) else None,
            "raw": payload,
        }

    async def _fetch_aviationstack_snapshot(self) -> dict[str, Any]:
        session = self._require_session()
        url = f"{settings.aviationstack_base_url.rstrip('/')}/flights"
        params = {
            "access_key": settings.aviationstack_access_key,
            "limit": settings.aviationstack_limit,
        }

        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Aviationstack HTTP {resp.status}: {text[:200]}")
            payload = await resp.json(content_type=None)

        data = payload.get("data") if isinstance(payload, dict) else None

        return {
            "fetched_at": _utc_now(),
            "item_count": len(data) if isinstance(data, list) else None,
            "pagination": payload.get("pagination") if isinstance(payload, dict) else None,
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
