"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = Field(default="dev-only-change-me", min_length=8)
    database_url: str = "sqlite:///./data/studymate.db"
    upload_dir: Path = Path("./data/uploads")
    chroma_url: str = "http://localhost:8000"
    enable_chroma: bool = False
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    max_upload_mb: int = 20
    token_expire_seconds: int = 604800
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    request_timeout_seconds: int = 45
    stale_processing_minutes: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
