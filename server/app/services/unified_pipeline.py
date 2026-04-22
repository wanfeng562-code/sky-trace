from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Literal

import aiohttp

from app.core.config import settings
from app.models.schemas import FlightBrief, WsEvent
from app.services.flight_store import FlightStore
from app.services.mock_collector import MockCollector

logger = logging.getLogger(__name__)
LayerName = Literal["realtime", "environment", "commercial"]

# Comprehensive list of the world's top ~100 airports by passenger traffic.
# Used as the default target set for AeroDataBox when no override is configured.
_GLOBAL_AIRPORTS: list[str] = [
    # North America
    "ATL", "LAX", "ORD", "DFW", "DEN", "JFK", "SFO", "SEA", "LAS", "MIA",
    "CLT", "PHX", "MCO", "EWR", "MSP", "BOS", "DTW", "PHL", "IAH", "FLL",
    "BWI", "SLC", "MDW", "DCA", "SAN", "TPA", "PDX", "HNL", "LGA", "STL",
    # Central & South America
    "GRU", "GIG", "MEX", "BOG", "LIM", "SCL", "EZE", "PTY", "YYZ", "YVR", "YUL",
    # Europe
    "LHR", "CDG", "AMS", "FRA", "MAD", "BCN", "FCO", "MXP", "LGW", "MUC",
    "ZRH", "CPH", "ARN", "OSL", "HEL", "DUB", "VIE", "BRU", "LIS", "ATH",
    "IST", "WAW", "PRG", "BUD", "OTP", "TXL", "LIN", "LCY", "STN", "ORY",
    # Middle East & Africa
    "DXB", "AUH", "DOH", "RUH", "JED", "MCT",
    "CAI", "ADD", "JNB", "CPT", "NBO", "LOS", "CMN", "ACC", "DAR", "ABJ",
    # South & Southeast Asia
    "DEL", "BOM", "MAA", "HYD", "BLR", "CCU", "COK",
    "BKK", "KUL", "CGK", "SIN", "MNL", "SGN", "HAN", "RGN", "PNH",
    # East Asia
    "PEK", "PKX", "PVG", "SHA", "CAN", "CTU", "SZX", "WUH", "XMN",
    "KMG", "CSX", "TAO", "NKG", "HGH", "CKG", "URC",
    "HKG", "TPE", "KHH",
    "NRT", "HND", "KIX", "NGO", "FUK", "CTS",
    "ICN", "GMP",
    # Oceania
    "SYD", "MEL", "BNE", "PER", "ADL", "AKL", "CHC",
]


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
        enriched_count = await self._enrich_flight_details_from_commercial(merged)
        await self._record_success("commercial", source="aerodatabox+aviationstack", count=enriched_count)

    async def _enrich_flight_details_from_commercial(self, merged: dict[str, Any]) -> int:
        """Parse commercial API payloads and persist FlightDetail extra fields. Returns upserted count."""
        count = 0
        sources = merged.get("sources") or {}

        # --- AeroDataBox ---
        aero = sources.get("aerodatabox") or {}
        raw_aero = aero.get("raw") or {}
        for direction in ("arrivals", "departures"):
            entries = raw_aero.get(direction) if isinstance(raw_aero, dict) else None
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                number = (entry.get("number") or "").strip().replace(" ", "")
                if not number:
                    continue
                dep_info = entry.get("departure") or {}
                arr_info = entry.get("arrival") or {}
                dep_iata = dep_info.get("airport", {}).get("iata") if isinstance(dep_info, dict) else None
                arr_iata = arr_info.get("airport", {}).get("iata") if isinstance(arr_info, dict) else None
                aircraft = entry.get("aircraft") or {}
                ac_type = aircraft.get("model") if isinstance(aircraft, dict) else None
                status_raw = entry.get("status") or "enroute"
                await self._flight_store.upsert_detail_extra(
                    number,
                    departure_airport=dep_iata,
                    arrival_airport=arr_iata,
                    aircraft_type=ac_type,
                    status=status_raw,
                    source="aerodatabox",
                )
                count += 1

        # --- Aviationstack ---
        avi = sources.get("aviationstack") or {}
        raw_avi = avi.get("raw") or {}
        data_list = raw_avi.get("data") if isinstance(raw_avi, dict) else None
        if isinstance(data_list, list):
            for entry in data_list:
                if not isinstance(entry, dict):
                    continue
                fl_info = entry.get("flight") or {}
                iata_cs = (fl_info.get("iata") or "").strip().replace(" ", "")
                if not iata_cs:
                    continue
                dep_iata = (entry.get("departure") or {}).get("iata")
                arr_iata = (entry.get("arrival") or {}).get("iata")
                aircraft = entry.get("aircraft") or {}
                ac_type = aircraft.get("iata") if isinstance(aircraft, dict) else None
                status_raw = entry.get("flight_status") or "enroute"
                await self._flight_store.upsert_detail_extra(
                    iata_cs,
                    departure_airport=dep_iata,
                    arrival_airport=arr_iata,
                    aircraft_type=ac_type,
                    status=status_raw,
                    source="aviationstack",
                )
                count += 1

        return count

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
        # Build a dynamic 12-hour window ending now (handles cross-midnight correctly).
        from datetime import timedelta
        now = _utc_now()
        start_dt = now - timedelta(hours=12)
        window_start = start_dt.strftime("%Y-%m-%dT%H:%M")
        window_end = now.strftime("%Y-%m-%dT%H:%M")

        # Empty config → use full global airport list; otherwise honour explicit override.
        override = settings.aerodatabox_airport_iata.strip()
        iata_codes = (
            [code.strip() for code in override.split(",") if code.strip()]
            if override
            else _GLOBAL_AIRPORTS
        )
        logger.info("AeroDataBox: querying %d airports", len(iata_codes))
        headers = {
            "x-rapidapi-key": settings.aerodatabox_api_key,
            "x-rapidapi-host": settings.aerodatabox_api_host,
        }
        params = {"withLeg": str(settings.aerodatabox_with_leg).lower()}

        all_arrivals: list[dict] = []
        all_departures: list[dict] = []

        for iata in iata_codes:
            path = f"flights/airports/iata/{iata}/{window_start}/{window_end}"
            url = f"{settings.aerodatabox_base_url.rstrip('/')}/{path}"
            try:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning("AeroDataBox %s HTTP %d: %s", iata, resp.status, text[:200])
                        continue
                    payload = await resp.json(content_type=None)
                arrivals = payload.get("arrivals") if isinstance(payload, dict) else []
                departures = payload.get("departures") if isinstance(payload, dict) else []
                if isinstance(arrivals, list):
                    all_arrivals.extend(arrivals)
                if isinstance(departures, list):
                    all_departures.extend(departures)
                logger.info(
                    "AeroDataBox %s: +%d arrivals +%d departures",
                    iata,
                    len(arrivals) if isinstance(arrivals, list) else 0,
                    len(departures) if isinstance(departures, list) else 0,
                )
            except Exception as exc:
                logger.warning("AeroDataBox %s fetch failed: %s", iata, exc)

            # BASIC plan rate limit: 1 req/s. Sleep between every airport request.
            await asyncio.sleep(1.1)

        return {
            "fetched_at": _utc_now(),
            "arrivals_count": len(all_arrivals),
            "departures_count": len(all_departures),
            "raw": {"arrivals": all_arrivals, "departures": all_departures},
        }

    async def _fetch_aviationstack_snapshot(self) -> dict[str, Any]:
        """Fetch ALL available flights from Aviationstack via automatic pagination."""
        session = self._require_session()
        url = f"{settings.aviationstack_base_url.rstrip('/')}/flights"
        page_size = 100  # Aviationstack maximum per request
        _HARD_LIMIT = 5000  # safety ceiling to avoid runaway billing

        all_data: list[dict] = []
        offset = 0
        total_reported = None

        while True:
            params = {
                "access_key": settings.aviationstack_access_key,
                "limit": page_size,
                "offset": offset,
            }
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Aviationstack HTTP {resp.status}: {text[:200]}")
                payload = await resp.json(content_type=None)

            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list) or len(data) == 0:
                break

            all_data.extend(data)
            pagination = payload.get("pagination") if isinstance(payload, dict) else {}
            if total_reported is None:
                total_reported = (pagination or {}).get("total", 0)

            offset += len(data)
            logger.info(
                "Aviationstack page offset=%d fetched=%d total=%s",
                offset - len(data), len(data), total_reported,
            )

            # Stop when all pages consumed or hard limit reached
            if len(data) < page_size:
                break
            if total_reported and offset >= total_reported:
                break
            if len(all_data) >= _HARD_LIMIT:
                logger.warning(
                    "Aviationstack: reached hard limit %d, stopping pagination", _HARD_LIMIT
                )
                break

            await asyncio.sleep(0.3)  # polite pause between pages

        logger.info("Aviationstack: total fetched=%d (reported total=%s)", len(all_data), total_reported)
        return {
            "fetched_at": _utc_now(),
            "item_count": len(all_data),
            "pagination": {"total": total_reported, "fetched": len(all_data)},
            "raw": {"data": all_data},
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
