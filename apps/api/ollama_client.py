"""Async Ollama client used across the MindBase API."""

from __future__ import annotations

from typing import Any, Iterable, List

import httpx

from app.config import get_settings


class OllamaClient:
    """Lightweight async client for Ollama REST endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_URL).rstrip("/")
        self.model = model or settings.EMBEDDING_MODEL
        self.timeout = timeout

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

    async def health_check(self) -> bool:
        """Return True if the Ollama service responds successfully."""
        try:
            await self._request("GET", "/api/version")
            return True
        except httpx.HTTPError:
            return False

    async def list_models(self) -> List[str]:
        """Retrieve installed model names."""
        try:
            response = await self._request("GET", "/api/tags")
            data = response.json()
            return [model.get("name", "") for model in data.get("models", [])]
        except httpx.HTTPError:
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Ensure a model is available locally."""
        try:
            await self._request("POST", "/api/pull", json={"model": model_name})
            return True
        except httpx.HTTPError:
            return False

    async def delete_model(self, model_name: str) -> bool:
        """Delete a locally cached model."""
        try:
            await self._request("DELETE", f"/api/models/{model_name}")
            return True
        except httpx.HTTPError:
            return False

    async def embed(self, text: str) -> List[float]:
        """Generate an embedding vector for the supplied text."""
        payload = {"model": self.model, "prompt": text}
        response = await self._request("POST", "/api/embeddings", json=payload)
        data = response.json()
        embedding = data.get("embedding") or data.get("embeddings", [None])[0]
        if embedding is None:
            raise ValueError("Embedding not returned by Ollama")
        return embedding

    async def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        """Generate embeddings for a collection of texts."""
        embeddings: List[List[float]] = []
        for text in texts:
            embeddings.append(await self.embed(text))
        return embeddings

    async def generate_embedding(self, text: str) -> List[float]:
        """Compatibility wrapper for integration tests."""
        return await self.embed(text)

    async def generate_batch_embeddings(self, texts: Iterable[str]) -> List[List[float]]:
        """Compatibility wrapper for integration tests."""
        return await self.embed_batch(texts)


# Shared instance used by API routes
ollama_client = OllamaClient()
