"""
Integration tests for Ollama embedding service.
"""
import pytest
from app.ollama_client import OllamaClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_connection(test_settings):
    """Test Ollama service is reachable."""
    client = OllamaClient(
        base_url=test_settings.OLLAMA_URL,
        model=test_settings.EMBEDDING_MODEL,
    )

    is_healthy = await client.health_check()
    assert is_healthy is True, "Ollama service is not healthy"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_embedding(test_settings):
    """Test embedding generation."""
    client = OllamaClient(
        base_url=test_settings.OLLAMA_URL,
        model=test_settings.EMBEDDING_MODEL,
    )

    text = "This is a test sentence for embedding generation."
    embedding = await client.generate_embedding(text)

    assert embedding is not None
    assert len(embedding) == 1024  # qwen3-embedding:8b = 1024 dimensions
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_batch_embeddings(test_settings):
    """Test batch embedding generation."""
    client = OllamaClient(
        base_url=test_settings.OLLAMA_URL,
        model=test_settings.EMBEDDING_MODEL,
    )

    texts = [
        "First test sentence",
        "Second test sentence",
        "Third test sentence",
    ]

    embeddings = await client.generate_batch_embeddings(texts)

    assert len(embeddings) == len(texts)
    for embedding in embeddings:
        assert len(embedding) == 1024
