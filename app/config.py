"""Centralised configuration via environment variables / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+psycopg2://whisper:whisperpass@localhost:5432/whisperdb"

    whisper_model_size: str = "small"  # tiny, base, small, medium, large-v3
    whisper_device: str = "cpu"        # cpu or cuda
    whisper_compute_type: str = "int8"  # int8, float16, float32
    whisper_default_language: str = "fa"


settings = Settings()
