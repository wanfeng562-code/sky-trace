from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file's package root (server/), not CWD.
# This ensures the correct .env is loaded regardless of where uvicorn is launched from.
_SERVER_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _SERVER_ROOT / ".env"


class Settings(BaseSettings):
    """Centralized runtime settings loaded from environment variables."""

    app_name: str = "Sky-Trace-Server"
    app_env: str = "development"
    app_profile: Literal["development", "release"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"

    # Legacy switches retained for compatibility with older scripts.
    data_source_mode: str = "hybrid"
    fetch_interval_seconds: int = 5

    # Unified collector runtime policy.
    realtime_source: Literal["opensky", "mock"] = "opensky"
    realtime_fallback_to_mock: bool = True

    # Development profile OpenSky polling policy:
    # - use_active_window=False: always use idle_interval (flat 90 s, ~960 calls/day, 3840 pts/day)
    # - use_active_window=True: burst to active_interval during start_hour:start_minute window
    dev_realtime_use_active_window: bool = False
    dev_realtime_active_interval_seconds: int = 15
    dev_realtime_idle_interval_seconds: int = 90
    dev_realtime_active_start_hour: int = 8
    dev_realtime_active_start_minute: int = 0
    dev_realtime_daily_budget_calls: int = 1000

    dev_realtime_interval_seconds: int = 30
    dev_environment_interval_seconds: int = 300
    dev_commercial_interval_seconds: int = 86400

    release_realtime_interval_seconds: int = 10
    release_environment_interval_seconds: int = 120
    release_commercial_interval_seconds: int = 86400

    http_timeout_seconds: int = 30

    opensky_base_url: str = "https://opensky-network.org/api"
    opensky_username: str = ""
    opensky_password: str = ""
    opensky_bbox: str = ""

    # AirLabs on-demand flight enrichment (replaces AeroDataBox airport-scan)
    # Free tier: 1,000 requests/month.  Fill in AIRLABS_API_KEY in .env to enable.
    airlabs_api_key: str = ""
    airlabs_base_url: str = "https://airlabs.co/api/v9"
    # How long a cached bulk enrichment record stays fresh (hours). Default 24 h
    # aligns with the daily refresh cadence so records never become stale.
    airlabs_enrich_ttl_hours: int = 24

    openweather_api_key: str = ""
    openweather_city: str = "Guangzhou"
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"
    # Reference coordinates for /air_pollution (falls back to city coord from weather response)
    openweather_lat: float = 23.1
    openweather_lon: float = 113.3
    # Comma-separated IATA codes for multi-hub global weather collection.
    # Leave empty to use the built-in default list of 20 global aviation hubs.
    openweather_hubs: str = ""

    sqlite_path: str = "./data/sky_trace.db"

    cors_allow_origins: str = "http://localhost:5173"
    ws_heartbeat_seconds: int = 20

    # Historical playback settings
    # Interval between saved fleet snapshots (seconds).  Lower = finer playback,
    # higher storage consumption.  Default 300 s → ≈ 288 snapshots/day.
    playback_snapshot_interval_seconds: int = 300
    # How long playback snapshots are retained before cleanup (hours).
    playback_ttl_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def development_realtime_active_window_seconds(self) -> int:
        """Compute active-window duration from daily budget and two polling intervals."""

        active = max(1, int(self.dev_realtime_active_interval_seconds))
        idle = max(1, int(self.dev_realtime_idle_interval_seconds))
        budget = max(1, int(self.dev_realtime_daily_budget_calls))

        baseline_calls = 86400 / idle
        delta = (1 / active) - (1 / idle)

        if delta <= 0:
            return 86400 if budget > baseline_calls else 0

        window_seconds = (budget - baseline_calls) / delta
        return max(0, min(86400, int(round(window_seconds))))

    def development_realtime_active_end_hhmm(self) -> str:
        start_seconds = max(0, int(self.dev_realtime_active_start_hour)) * 3600 + max(
            0, int(self.dev_realtime_active_start_minute)
        ) * 60
        end_seconds = (start_seconds + self.development_realtime_active_window_seconds()) % 86400
        end_hour = end_seconds // 3600
        end_minute = (end_seconds % 3600) // 60
        return f"{end_hour:02d}:{end_minute:02d}"

    def development_realtime_is_active_now(self, now: datetime | None = None) -> bool:
        if not self.dev_realtime_use_active_window:
            return False

        if now is None:
            local_now = datetime.now().astimezone()
        elif now.tzinfo is None:
            local_now = now
        else:
            local_now = now.astimezone()

        current_seconds = local_now.hour * 3600 + local_now.minute * 60 + local_now.second
        start_seconds = max(0, int(self.dev_realtime_active_start_hour)) * 3600 + max(
            0, int(self.dev_realtime_active_start_minute)
        ) * 60
        duration = self.development_realtime_active_window_seconds()

        if duration <= 0:
            return False
        if duration >= 86400:
            return True

        end_seconds = (start_seconds + duration) % 86400
        if start_seconds < end_seconds:
            return start_seconds <= current_seconds < end_seconds
        return current_seconds >= start_seconds or current_seconds < end_seconds

    def development_realtime_interval_seconds(self, now: datetime | None = None) -> int:
        if self.dev_realtime_use_active_window and self.development_realtime_is_active_now(now):
            return max(1, int(self.dev_realtime_active_interval_seconds))
        return max(1, int(self.dev_realtime_idle_interval_seconds))

    def interval_seconds(self, layer: Literal["realtime", "environment", "commercial"]) -> int:
        if self.app_profile == "release":
            mapping = {
                "realtime": self.release_realtime_interval_seconds,
                "environment": self.release_environment_interval_seconds,
                "commercial": self.release_commercial_interval_seconds,
            }
        else:
            if layer == "realtime" and self.dev_realtime_use_active_window:
                return self.development_realtime_interval_seconds()
            mapping = {
                "realtime": self.dev_realtime_interval_seconds,
                "environment": self.dev_environment_interval_seconds,
                "commercial": self.dev_commercial_interval_seconds,
            }
        return max(1, int(mapping[layer]))


settings = Settings()
