from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime settings loaded from environment variables."""

    app_name: str = "Sky-Trace-Server"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"

    data_source_mode: str = "mock"
    fetch_interval_seconds: int = 5

    sqlite_path: str = "./data/sky_trace.db"

    cors_allow_origins: str = "http://localhost:5173"
    ws_heartbeat_seconds: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
