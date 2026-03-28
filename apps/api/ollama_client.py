"""Embedding client with OpenAI primary + Ollama fallback."""

from __future__ import annotations

import logging
from typing import Iterable, List

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Async embedding client that uses OpenAI API (primary) with Ollama fallback."""

    def __init__(
        self,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        ollama_url: str | None = None,
        ollama_model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = get_settings()
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.openai_model = openai_model or settings.OPENAI_EMBEDDING_MODEL
        self.ollama_url = (ollama_url or settings.OLLAMA_URL).rstrip("/")
        self.ollama_model = ollama_model or settings.EMBEDDING_MODEL
        self.timeout = timeout

        # Track which provider is active
        self._provider = "openai" if self.openai_api_key else "ollama"
        logger.info(
            "Embedding provider: %s (model: %s)",
            self._provider,
            self.openai_model if self._provider == "openai" else self.ollama_model,
        )

    @property
    def model(self) -> str:
        """Return the active model name."""
        if self._provider == "openai":
            return self.openai_model
        return self.ollama_model

    @model.setter
    def model(self, value: str) -> None:
        """Set the active model (for backward compatibility with embeddings route)."""
        if self._provider == "openai":
            self.openai_model = value
        else:
            self.ollama_model = value

    async def _openai_embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.openai_model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Sort by index to ensure correct ordering
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]

    async def _ollama_embed(self, text: str) -> List[float]:
        """Generate embedding using Ollama API (single text)."""
        url = f"{self.ollama_url}/api/embeddings"
        payload = {"model": self.ollama_model, "prompt": text}

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        embedding = data.get("embedding") or data.get("embeddings", [None])[0]
        if embedding is None:
            raise ValueError("Embedding not returned by Ollama")
        return embedding

    async def embed(self, text: str) -> List[float]:
        """Generate an embedding vector for the supplied text."""
        if self._provider == "openai":
            try:
                results = await self._openai_embed([text])
                return results[0]
            except Exception as exc:
                logger.warning(
                    "OpenAI embedding failed, falling back to Ollama: %s", exc
                )
                self._provider = "ollama"

        return await self._ollama_embed(text)

    async def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        """Generate embeddings for a collection of texts."""
        text_list = list(texts)
        if not text_list:
            return []

        if self._provider == "openai":
            try:
                # OpenAI supports batch embedding natively (max 2048 inputs)
                results: List[List[float]] = []
                batch_size = 2048
                for i in range(0, len(text_list), batch_size):
                    batch = text_list[i : i + batch_size]
                    batch_results = await self._openai_embed(batch)
                    results.extend(batch_results)
                return results
            except Exception as exc:
                logger.warning(
                    "OpenAI batch embedding failed, falling back to Ollama: %s", exc
                )
                self._provider = "ollama"

        # Ollama: sequential embedding
        embeddings: List[List[float]] = []
        for text in text_list:
            embeddings.append(await self._ollama_embed(text))
        return embeddings

    async def health_check(self) -> bool:
        """Return True if the embedding service responds successfully."""
        if self._provider == "openai":
            try:
                # Quick test with minimal input
                await self._openai_embed(["test"])
                return True
            except Exception as exc:
                logger.warning("OpenAI health check failed: %s", exc)

        # Fallback: check Ollama
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.ollama_url}/api/version")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_models(self) -> List[str]:
        """Retrieve installed Ollama model names."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [model.get("name", "") for model in data.get("models", [])]
        except httpx.HTTPError:
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Ensure an Ollama model is available locally."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/pull", json={"model": model_name}
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            return False

    async def delete_model(self, model_name: str) -> bool:
        """Delete a locally cached Ollama model."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.ollama_url}/api/models/{model_name}"
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            return False

    async def generate_embedding(self, text: str) -> List[float]:
        """Compatibility wrapper for integration tests."""
        return await self.embed(text)

    async def generate_batch_embeddings(
        self, texts: Iterable[str]
    ) -> List[List[float]]:
        """Compatibility wrapper for integration tests."""
        return await self.embed_batch(texts)


# Shared instance used by API routes (backward-compatible name)
ollama_client = EmbeddingClient()
