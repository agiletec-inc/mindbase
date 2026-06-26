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
    # Seed default for the active embedding model. The live source of truth is the
    # settings store (services/settings_store.get_active_embedding); this env value
    # only seeds it when the store has no choice yet.
    EMBEDDING_MODEL: str = "bge-m3"
    # Vestigial: the real dimension is derived from the embedding vector length
    # (crud.column_for_dim). Kept only for the legacy conversations.embedding column.
    EMBEDDING_DIMENSIONS: int = 1024

    # Chat (LLM) — seed defaults only. The live source of truth is the settings
    # store (services/settings_store.get_chat_settings); these seed it when unset.
    CHAT_MODEL: str = "qwen2.5:3b"
    CHAT_TEMPERATURE: float = 0.7
    CHAT_MAX_TOKENS: int = 2048
    CHAT_SYSTEM_PROMPT: str = (
        "You are MindBase, a helpful assistant with access to the user's past "
        "conversations. Use the provided context when relevant."
    )

    # Ollama chat model for Japanese session summarisation.
    # Must be a model present on the Ollama instance (not an embedding model).
    SUMMARY_MODEL: str = "qwen3:14b"

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
