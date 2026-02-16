"""
Application configuration via environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    max_upload_size_mb: int = 200
    session_ttl_seconds: int = 7200  # 2 hours
    display_image_max_dim: int = 4000
    jpeg_quality: int = 85
    cors_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_prefix = "TIITBA_"


settings = Settings()
