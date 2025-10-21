"""Configuration settings"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://mindbase:mindbase_dev@postgres:5432/mindbase"

    # Ollama
    OLLAMA_URL: str = "http://ollama:11434"
    EMBEDDING_MODEL: str = "qwen3-embedding:8b"
    EMBEDDING_DIMENSIONS: int = 1024

    # API
    DEBUG: bool = True
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
