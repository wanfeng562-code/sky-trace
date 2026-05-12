from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ApiResponse
from app.services.unified_pipeline import HUB_INFO
from app.state import flight_store, unified_pipeline

router = APIRouter(prefix="/api/v1", tags=["flights"])


def _to_weather_info(hub_payload: dict | None) -> dict | None:
    """Normalize hub weather to frontend `WeatherInfo` (temp_c, humidity_pct, …)."""
    if not isinstance(hub_payload, dict):
        return None

    # get_hub_weather_for_iata → {"weather": <openweather snapshot>, "air_quality": …}
    inner = hub_payload.get("weather")
    if isinstance(inner, dict) and (
        inner.get("provider") == "openweather" or "temperature_c" in inner or "raw" in inner
    ):
        snap = inner
    else:
        snap = hub_payload

    if not isinstance(snap, dict) or not snap:
        return None

    raw = snap.get("raw")
    if not isinstance(raw, dict):
        raw = {}
    main_from_raw = raw.get("main")
    if not isinstance(main_from_raw, dict):
        main_from_raw = {}
    # Prefer snapshot fields; fall back to OpenWeather raw payload
    t_val: float | int | None = snap.get("temperature_c", snap.get("temp_c"))
    if t_val is None and main_from_raw:
        t_val = main_from_raw.get("temp")
    if t_val is not None and not isinstance(t_val, (int, float)):
        try:
            t_val = float(t_val)
        except (TypeError, ValueError):
            t_val = None

    h_val = snap.get("humidity", snap.get("humidity_pct"))
    if h_val is None and main_from_raw:
        h_val = main_from_raw.get("humidity")
    if h_val is not None:
        try:
            h_val = int(round(float(h_val)))
        except (TypeError, ValueError):
            h_val = None

    wind = snap.get("wind")
    if (not isinstance(wind, dict) or not wind) and isinstance(raw.get("wind"), dict):
        wind = raw.get("wind", {})
    if not isinstance(wind, dict):
        wind = {}
    wspd = wind.get("speed", snap.get("wind_speed_mps"))
    if wspd is not None:
        try:
            wspd = float(wspd)
        except (TypeError, ValueError):
            wspd = None
    wdeg = wind.get("deg", snap.get("wind_deg"))
    if wdeg is not None:
        try:
            wdeg = int(round(float(wdeg)))
        except (TypeError, ValueError):
            wdeg = None

    cond = snap.get("weather")
    if isinstance(cond, list) and cond and isinstance(cond[0], dict):
        cond = cond[0]
    if not isinstance(cond, dict):
        cond = {}
    desc: str | None = cond.get("description")
    if not desc and raw.get("weather"):
        wlist = raw.get("weather")
        if isinstance(wlist, list) and wlist and isinstance(wlist[0], dict):
            desc = wlist[0].get("description")
    if not desc:
        desc = snap.get("description")

    vis = snap.get("visibility_m", raw.get("visibility"))
    if vis is not None:
        try:
            vis = int(float(vis))
        except (TypeError, ValueError):
            vis = None

    if all(
        x is None
        for x in (t_val, h_val, wspd, wdeg, vis)
    ) and not (isinstance(desc, str) and desc.strip()):
        return None

    return {
        "temp_c": t_val,
        "humidity_pct": h_val,
        "wind_speed_mps": wspd,
        "wind_deg": wdeg,
        "description": desc,
        "visibility_m": vis,
    }


@router.get("/flights")
async def list_flights(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    callsign: str | None = Query(default=None, description="Partial callsign filter (case-insensitive)"),
    lat_min: float | None = Query(default=None),
    lat_max: float | None = Query(default=None),
    lon_min: float | None = Query(default=None),
    lon_max: float | None = Query(default=None),
) -> ApiResponse:
    """Return current flight snapshot with optional callsign / bounding-box filters."""

    flights = await flight_store.list_flights(
        callsign=callsign,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
    )
    start = (page - 1) * page_size
    end = start + page_size
    items = flights[start:end]

    return ApiResponse(
        data={
            "total": len(flights),
            "items": [f.model_dump(mode="json") for f in items],
        }
    )


@router.get("/flights/summary/stats")
async def get_flight_stats() -> ApiResponse:
    """Return aggregated statistics for the current flight snapshot.

    Useful for ECharts pie / bar charts on the frontend.
    Fields:
    - ``total``: total number of tracked flights
    - ``by_category``: distribution by OpenSky aircraft category code
    - ``by_altitude_band``: grouped altitude bands (ground / low / medium / high)
    - ``by_speed_band``: grouped speed bands
    - ``top_callsign_prefixes``: top-20 airline/operator ICAO prefixes by count
    - ``on_ground_count`` / ``airborne_count``: quick on-ground split
    """
    flights = await flight_store.list_flights()

    # --- category distribution -------------------------------------------
    _CATEGORY_LABELS: dict[int, str] = {
        0: "unknown", 1: "no_info", 2: "light", 3: "small",
        4: "large", 5: "high_vortex", 6: "heavy", 7: "high_perf",
        8: "rotorcraft", 9: "glider", 10: "lighter_than_air",
        11: "skydiver", 12: "ultralight", 13: "reserved",
        14: "uav", 15: "space", 16: "emergency_surface",
        17: "service_surface", 18: "point_obstacle",
    }
    by_category: dict[str, int] = {}
    for f in flights:
        label = _CATEGORY_LABELS.get(f.aircraft_category or 0, "unknown")
        by_category[label] = by_category.get(label, 0) + 1

    # --- altitude bands ---------------------------------------------------
    on_ground = 0
    by_altitude: dict[str, int] = {"ground": 0, "low_<5k": 0, "medium_5-25k": 0, "high_>25k": 0, "unknown": 0}
    for f in flights:
        if f.altitude_ft is None:
            by_altitude["unknown"] += 1
        elif f.altitude_ft <= 100:
            by_altitude["ground"] += 1
            on_ground += 1
        elif f.altitude_ft < 5_000:
            by_altitude["low_<5k"] += 1
        elif f.altitude_ft < 25_000:
            by_altitude["medium_5-25k"] += 1
        else:
            by_altitude["high_>25k"] += 1

    # --- speed bands ------------------------------------------------------
    by_speed: dict[str, int] = {
        "stationary_<30kts": 0, "slow_30-150kts": 0,
        "cruise_150-400kts": 0, "fast_>400kts": 0, "unknown": 0,
    }
    for f in flights:
        if f.speed_kts is None:
            by_speed["unknown"] += 1
        elif f.speed_kts < 30:
            by_speed["stationary_<30kts"] += 1
        elif f.speed_kts < 150:
            by_speed["slow_30-150kts"] += 1
        elif f.speed_kts <= 400:
            by_speed["cruise_150-400kts"] += 1
        else:
            by_speed["fast_>400kts"] += 1

    # --- top callsign prefixes (3-char ICAO airline code) -----------------
    prefix_counts: dict[str, int] = {}
    for f in flights:
        if f.callsign and len(f.callsign) >= 3:
            prefix = f.callsign[:3].upper()
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
    top_prefixes = sorted(prefix_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    airborne = len(flights) - on_ground

    # --- data source breakdown -------------------------------------------
    by_source: dict[str, int] = {}
    for f in flights:
        fid = f.flight_id or ""
        if fid.startswith("fr24-"):
            src = "fr24"
        elif fid.startswith("icao24-"):
            src = "opensky"
        elif fid.startswith("mock-"):
            src = "mock"
        else:
            src = "other"
        by_source[src] = by_source.get(src, 0) + 1

    return ApiResponse(
        data={
            "total": len(flights),
            "on_ground_count": on_ground,
            "airborne_count": airborne,
            "by_source": by_source,
            "by_category": by_category,
            "by_altitude_band": by_altitude,
            "by_speed_band": by_speed,
            "top_callsign_prefixes": [{"prefix": p, "count": c} for p, c in top_prefixes],
        }
    )


@router.get("/airports", summary="List monitored hub airports with coordinates")
async def list_airports() -> ApiResponse:
    """Return the static list of monitored hub airports (IATA, name, lat, lon)."""
    return ApiResponse(data=list(HUB_INFO.values()))


@router.get("/flights/{flight_id}")
async def get_flight_detail(flight_id: str) -> ApiResponse:
    """Return one flight detail object, short track history, and airport weather.

    ``departure_weather`` and ``arrival_weather`` are populated from the cached
    environment layer when the airport IATA code is a known hub.  No extra API
    call is made.
    """
    detail = await flight_store.get_flight(flight_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="flight not found")

    data = detail.model_dump(mode="json")

    # Enrich with departure / arrival airport weather from the hub cache.
    dep_weather = await unified_pipeline.get_hub_weather_for_iata(detail.departure_airport)
    arr_weather = await unified_pipeline.get_hub_weather_for_iata(detail.arrival_airport)
    data["departure_weather"] = _to_weather_info(dep_weather)
    data["arrival_weather"] = _to_weather_info(arr_weather)

    # Fetch live weather at the flight's current position.
    pos = detail.last_position
    loc_weather: dict | None = None
    try:
        raw_loc = await unified_pipeline.fetch_weather_at_coords(pos.lat, pos.lon)
        loc_weather = _to_weather_info(raw_loc)
    except Exception:
        pass
    data["current_weather"] = loc_weather

    return ApiResponse(data=data)


@router.get("/flights/{flight_id}/track")
async def get_flight_track(
    flight_id: str,
    since: datetime | None = Query(default=None, description="ISO 8601 UTC start time"),
    until: datetime | None = Query(default=None, description="ISO 8601 UTC end time"),
) -> ApiResponse:
    """Return track points for a flight, optionally bounded by a time range."""

    track = await flight_store.get_track(flight_id, since=since, until=until)
    return ApiResponse(data=[point.model_dump(mode="json") for point in track])


@router.get("/flights/{flight_id}/fr24-details")
async def get_fr24_flight_details(flight_id: str) -> ApiResponse:
    """Fetch on-demand FR24 details for a single flight (machine age, full type name,
    trail, time details, delay, complete airport info).

    Only available for flights in the FR24 supplemental cache (``flight_id`` starting
    with ``fr24-``).  The SDK call is made at request time and takes 1-3 s.

    Returns 404 if the flight is not in the FR24 cache (e.g. OpenSky-only flights).
    Returns 503 if FR24 is disabled (received 403 Forbidden) or not configured.
    """
    fr24_detail = await unified_pipeline.fetch_fr24_flight_detail(flight_id)
    if fr24_detail is None:
        # Distinguish between "no FR24 proxy configured" and "flight not in cache"
        from app.core.config import settings as _settings
        if not _settings.fr24_proxy_url.strip():
            raise HTTPException(
                status_code=503,
                detail="FR24 is not configured (FR24_PROXY_URL not set).",
            )
        raise HTTPException(
            status_code=404,
            detail=(
                "No FR24 detail available for this flight. "
                "Flight may not be in the FR24 cache yet (cache refreshes every ~90 s), "
                "or it is an OpenSky-only flight."
            ),
        )
    return ApiResponse(data=fr24_detail)


@router.get("/airports/{iata}/schedules")
async def get_airport_schedules(
    iata: str,
    direction: str = Query(default="dep", description="'dep' for departures, 'arr' for arrivals"),
) -> ApiResponse:
    """Return departure or arrival schedule for an airport via AirLabs /schedules."""
    if direction not in ("dep", "arr"):
        raise HTTPException(status_code=400, detail="direction must be 'dep' or 'arr'")
    data = await unified_pipeline.fetch_airport_schedules(iata.upper(), direction)
    return ApiResponse(data=data)
