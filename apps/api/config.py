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

    # Embedding provider selection: "ollama" | "openai".
    # Explicit and config-driven — no implicit key-presence fallback. The active
    # provider decides which embedder store/search use; per-provider vectors
    # coexist in conversation_embeddings so providers can be compared.
    EMBEDDING_PROVIDER: str = "ollama"

    # OpenAI Embedding
    OPENAI_API_KEY: str | None = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Ollama Embedding
    OLLAMA_URL: str
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSIONS: int

    # Ollama chat model for Japanese session summarisation.
    # Must be a model present on the Ollama instance (not an embedding model).
    SUMMARY_MODEL: str

    # Max characters of input text per embedding call. Embedding models have a
    # fixed context window (bge-m3: 8192 tokens) and error on overflow, so long
    # transcripts are head-truncated to this budget before embedding. ~8000
    # chars stays safely under 8192 tokens across Japanese/English/code.
    EMBEDDING_MAX_CHARS: int = 8000

    # API
    DEBUG: bool = False
    API_TITLE: str = "MindBase API"
    API_VERSION: str = "1.1.0"
    API_DESCRIPTION: str = "AI Conversation Knowledge Management System"
    DERIVE_ON_STORE: bool = True
    MINDBASE_SETTINGS_PATH: str | None = None
    DERIVER_BATCH_SIZE: int = 5
    DERIVER_IDLE_SECONDS: int = 5
    DERIVER_MAX_RETRIES: int = 3

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Search Recency Settings
    SEARCH_RECENCY_TAU_SECONDS: int = 1209600  # 14 days decay constant
    SEARCH_RECENCY_WEIGHT: float = 0.15  # Weight for recency in combined score
    SEARCH_RECENCY_BOOST_DAYS: int = 3  # Days for recency boost
    SEARCH_RECENCY_BOOST_VALUE: float = 0.05  # Boost value for recent items

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
