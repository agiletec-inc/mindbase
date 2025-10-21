"""Configuration settings"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings

    ⚠️ WARNING: NEVER hardcode ports or URLs here.
    All configuration MUST come from environment variables.
    See .env.example for required variables.
    """

    # Database - REQUIRED from environment
    DATABASE_URL: str

    # Ollama - REQUIRED from environment
    OLLAMA_URL: str
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSIONS: int

    # API
    DEBUG: bool = False
    API_TITLE: str = "MindBase API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "AI Conversation Knowledge Management System"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
