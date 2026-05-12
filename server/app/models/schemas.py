from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class FlightBrief(BaseModel):
    flight_id: str
    callsign: str | None = None
    lat: float
    lon: float
    heading: int | None = None
    speed_kts: int | None = None
    altitude_ft: int | None = None
    aircraft_category: int | None = None  # OpenSky extended=1: 0=unknown,2=light,4=large,6=heavy,8=rotorcraft,14=UAV
    departure_airport: str | None = None
    arrival_airport: str | None = None
    airline_iata: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrackPoint(BaseModel):
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lat: float
    lon: float
    altitude_ft: int | None = None
    speed_kts: int | None = None


class FlightDetail(BaseModel):
    flight_id: str
    callsign: str | None = None
    departure_airport: str | None = None
    arrival_airport: str | None = None
    aircraft_type: str | None = None
    status: str = "enroute"
    dep_time: str | None = None
    arr_time: str | None = None
    airline_iata: str | None = None
    last_position: FlightBrief
    track_points: list[TrackPoint] = Field(default_factory=list)


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any = None


class WsEvent(BaseModel):
    event: str
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Any
