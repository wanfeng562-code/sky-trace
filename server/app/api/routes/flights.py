from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ApiResponse
from app.state import flight_store, unified_pipeline

router = APIRouter(prefix="/api/v1", tags=["flights"])


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

    return ApiResponse(
        data={
            "total": len(flights),
            "on_ground_count": on_ground,
            "airborne_count": airborne,
            "by_category": by_category,
            "by_altitude_band": by_altitude,
            "by_speed_band": by_speed,
            "top_callsign_prefixes": [{"prefix": p, "count": c} for p, c in top_prefixes],
        }
    )


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
    data["departure_weather"] = dep_weather
    data["arrival_weather"] = arr_weather

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
