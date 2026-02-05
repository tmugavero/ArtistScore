from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    YOUTUBE_API: str
    SPOTIFY_API: str
    SPOTIFY_SECRET: str
    CHARTMETRIC: str
    BRAVE_API: str
    GEMINI_API: str

    # Optional configuration
    CACHE_TTL: int = 3600  # 1 hour cache
    REQUEST_TIMEOUT: int = 30
    MAX_CONCURRENT_REQUESTS: int = 10

    @field_validator("YOUTUBE_API", "SPOTIFY_API", "SPOTIFY_SECRET", "CHARTMETRIC", "BRAVE_API", "GEMINI_API", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from API keys."""
        return v.strip() if isinstance(v, str) else v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
