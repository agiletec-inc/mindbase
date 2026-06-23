"""Unit tests for config-driven embedding provider selection."""

import pytest

from apps.api.crud.embeddings import column_for_dim
from apps.api.ollama_client import EmbeddingClient


@pytest.mark.unit
def test_column_for_dim_maps_known_dimensions():
    assert column_for_dim(768) == "vec_768"
    assert column_for_dim(1024) == "vec_1024"
    assert column_for_dim(3072) == "vec_3072"
    assert column_for_dim(4096) == "vec_4096"


@pytest.mark.unit
def test_column_for_dim_rejects_unknown_dimension():
    with pytest.raises(ValueError, match="Unsupported embedding dimension"):
        column_for_dim(512)


def _client(provider: str) -> EmbeddingClient:
    return EmbeddingClient(
        provider=provider,
        openai_api_key="sk-test",
        openai_model="text-embedding-3-large",
        ollama_url="http://ollama:11434",
        ollama_model="bge-m3",
    )


@pytest.mark.unit
def test_active_provider_and_model_follow_config():
    ollama = _client("ollama")
    assert ollama.active_provider == "ollama"
    assert ollama.active_model == "bge-m3"

    openai = _client("openai")
    assert openai.active_provider == "openai"
    assert openai.active_model == "text-embedding-3-large"


@pytest.mark.unit
def test_provider_selection_is_case_insensitive():
    assert _client("OpenAI").active_provider == "openai"


@pytest.mark.unit
def test_resolve_overrides_provider_and_model():
    client = _client("ollama")
    assert client._resolve(None, None) == ("ollama", "bge-m3")
    assert client._resolve("openai", None) == ("openai", "text-embedding-3-large")
    assert client._resolve("ollama", "qwen3-embedding:8b") == (
        "ollama",
        "qwen3-embedding:8b",
    )


@pytest.mark.unit
async def test_embed_routes_to_selected_provider(monkeypatch):
    client = _client("ollama")
    calls = {}

    async def fake_ollama(text, model):
        calls["ollama"] = (text, model)
        return [0.0] * 1024

    async def fake_openai(texts, model):
        calls["openai"] = (texts, model)
        return [[0.0] * 3072]

    monkeypatch.setattr(client, "_ollama_embed", fake_ollama)
    monkeypatch.setattr(client, "_openai_embed", fake_openai)

    # Active provider (ollama)
    vec = await client.embed("hello")
    assert len(vec) == 1024
    assert calls["ollama"] == ("hello", "bge-m3")

    # Override to openai for comparison
    vec = await client.embed("hello", provider="openai")
    assert len(vec) == 3072
    assert calls["openai"] == (["hello"], "text-embedding-3-large")


@pytest.mark.unit
async def test_embed_raises_on_unknown_provider():
    client = _client("ollama")
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        await client.embed("hello", provider="bogus")


@pytest.mark.unit
async def test_openai_without_key_raises():
    client = EmbeddingClient(
        provider="openai",
        openai_api_key="",
        ollama_url="http://ollama:11434",
        ollama_model="bge-m3",
    )
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        await client.embed("hello")
