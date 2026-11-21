"""Environment-based configuration. Values come from environment variables or backend/.env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DGS Project & Engineering Intelligence Workspace"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://dgs:dgs_local_dev@localhost:5433/dgs_workspace"
    test_database_url: str = (
        "postgresql+psycopg://dgs:dgs_local_dev@localhost:5433/dgs_workspace_test"
    )
    cors_origins: str = "http://localhost:3010"
    log_level: str = "INFO"
    # Voice: "auto" uses local Whisper when installed; "none" disables transcription.
    transcription_provider: str = "auto"
    whisper_model: str = "base"
    # "delete" removes audio as soon as it is transcribed; "keep" retains it until you delete it.
    voice_retention: str = "delete"
    recordings_dir: str = "data/recordings"
    max_upload_mb: int = 50
    # AI assistant defaults (overridable in Administration). The key is only ever read from env.
    ai_provider: str = "disabled"  # disabled | openai_compatible | manual
    ai_base_url: str = ""
    ai_model: str = ""
    ai_api_key: str = ""
    # Connected codebases: background sync interval (0 disables the background loop).
    sync_interval_seconds: int = 180

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
