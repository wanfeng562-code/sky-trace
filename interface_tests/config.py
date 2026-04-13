from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    opensky_username: str
    opensky_password: str
    opensky_bbox: str

    aerodatabox_api_key: str
    aerodatabox_api_host: str
    aerodatabox_base_url: str
    aerodatabox_test_path: str
    aerodatabox_with_leg: bool

    aviationstack_access_key: str
    aviationstack_base_url: str

    openweather_api_key: str
    openweather_city: str


def _as_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    env_path = Path(__file__).with_name(".env")
    load_dotenv(env_path)

    return Settings(
        opensky_username=os.getenv("OPENSKY_USERNAME", ""),
        opensky_password=os.getenv("OPENSKY_PASSWORD", ""),
        opensky_bbox=os.getenv("OPENSKY_BBOX", ""),
        aerodatabox_api_key=os.getenv("AERODATABOX_API_KEY", ""),
        aerodatabox_api_host=os.getenv("AERODATABOX_API_HOST", "aerodatabox.p.rapidapi.com"),
        aerodatabox_base_url=os.getenv("AERODATABOX_BASE_URL", "https://aerodatabox.p.rapidapi.com"),
        aerodatabox_test_path=os.getenv(
            "AERODATABOX_TEST_PATH",
            "flights/airports/iata/SZX/2026-04-13T00:00/2026-04-13T12:00",
        ),
        aerodatabox_with_leg=_as_bool(os.getenv("AERODATABOX_WITH_LEG", "true"), default=True),
        aviationstack_access_key=os.getenv("AVIATIONSTACK_ACCESS_KEY", ""),
        aviationstack_base_url=os.getenv("AVIATIONSTACK_BASE_URL", "http://api.aviationstack.com/v1"),
        openweather_api_key=os.getenv("OPENWEATHER_API_KEY", ""),
        openweather_city=os.getenv("OPENWEATHER_CITY", "Guangzhou"),
    )
