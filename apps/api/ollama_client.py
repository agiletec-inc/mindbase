"""Embedding client with explicit, config-driven provider selection.

The active provider is chosen by ``settings.EMBEDDING_PROVIDER`` ("ollama" |
"openai") — there is no implicit key-presence fallback and no silent switch on
error: a failing provider raises so misconfiguration is visible. ``embed`` and
``embed_batch`` accept ``provider`` / ``model`` overrides so the same text can be
embedded by a different provider for side-by-side comparison.

Model management (pull, delete, list) is delegated to services/model_manager.py.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Iterable, List, Tuple

import httpx

from apps.api.config import get_settings
from apps.api.services.model_manager import ModelManager

logger = logging.getLogger(__name__)

OPENAI = "openai"
OLLAMA = "ollama"


class EmbeddingClient:
    """Async embedding client with an explicit, config-selected provider."""

    def __init__(
        self,
        provider: str | None = None,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        ollama_url: str | None = None,
        ollama_model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = get_settings()
        self.provider = (provider or settings.EMBEDDING_PROVIDER or OLLAMA).lower()
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.openai_model = openai_model or settings.OPENAI_EMBEDDING_MODEL
        self.ollama_url = (ollama_url or settings.OLLAMA_URL).rstrip("/")
        self.ollama_model = ollama_model or settings.EMBEDDING_MODEL
        self.max_chars = settings.EMBEDDING_MAX_CHARS
        self.timeout = timeout

        logger.info(
            "Embedding provider: %s (model: %s)", self.provider, self.active_model
        )

        # Delegate model management
        self._model_manager = ModelManager(ollama_url=self.ollama_url, timeout=timeout)

    # ------------------------------------------------------------------ helpers
    @property
    def active_provider(self) -> str:
        return self.provider

    def default_model(self, provider: str) -> str:
        """Return the configured default model for a provider."""
        return self.openai_model if provider == OPENAI else self.ollama_model

    @property
    def active_model(self) -> str:
        return self.default_model(self.provider)

    @property
    def model(self) -> str:
        """Active model name (kept for the embeddings management route)."""
        return self.active_model

    @model.setter
    def model(self, value: str) -> None:
        if self.provider == OPENAI:
            self.openai_model = value
        else:
            self.ollama_model = value

    def _resolve(self, provider: str | None, model: str | None) -> Tuple[str, str]:
        prov = (provider or self.provider).lower()
        return prov, (model or self.default_model(prov))

    def _clip(self, text: str) -> str:
        """Head-truncate to the model's context budget to avoid overflow errors."""
        return text[: self.max_chars]

    # ------------------------------------------------------------------ backends
    async def _openai_embed(self, texts: List[str], model: str) -> List[List[float]]:
        """Generate embeddings using the OpenAI API."""
        if not self.openai_api_key:
            raise RuntimeError(
                "Embedding provider 'openai' selected but OPENAI_API_KEY is not set"
            )
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "input": texts}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]

    async def _ollama_embed(self, text: str, model: str) -> List[float]:
        """Generate an embedding using the Ollama API (single text).

        Token density varies (dense JSON/base64 in tool messages can exceed the
        model context even after the char-based clip), so on a context-length
        overflow the input is halved and retried until it fits.
        """
        url = f"{self.ollama_url}/api/embeddings"
        prompt = text
        async with httpx.AsyncClient(timeout=300.0) as client:
            while True:
                response = await client.post(
                    url, json={"model": model, "prompt": prompt}
                )
                if (
                    response.status_code == 500
                    and "context length" in response.text
                    and len(prompt) > 256
                ):
                    prompt = prompt[: len(prompt) // 2]
                    continue
                response.raise_for_status()
                break
            data = response.json()

        embedding = data.get("embedding") or data.get("embeddings", [None])[0]
        if embedding is None:
            raise ValueError("Embedding not returned by Ollama")
        return embedding

    # ------------------------------------------------------------------- public
    async def embed(
        self, text: str, provider: str | None = None, model: str | None = None
    ) -> List[float]:
        """Embed a single text with the active (or overridden) provider/model."""
        prov, mdl = self._resolve(provider, model)
        text = self._clip(text)
        if prov == OPENAI:
            results = await self._openai_embed([text], mdl)
            return results[0]
        if prov == OLLAMA:
            return await self._ollama_embed(text, mdl)
        raise ValueError(f"Unknown embedding provider: {prov!r}")

    async def embed_batch(
        self,
        texts: Iterable[str],
        provider: str | None = None,
        model: str | None = None,
    ) -> List[List[float]]:
        """Embed a collection of texts with the active (or overridden) provider."""
        text_list = list(texts)
        if not text_list:
            return []

        prov, mdl = self._resolve(provider, model)
        text_list = [self._clip(t) for t in text_list]
        if prov == OPENAI:
            results: List[List[float]] = []
            batch_size = 2048
            for i in range(0, len(text_list), batch_size):
                batch = text_list[i : i + batch_size]
                results.extend(await self._openai_embed(batch, mdl))
            return results
        if prov == OLLAMA:
            return [await self._ollama_embed(text, mdl) for text in text_list]
        raise ValueError(f"Unknown embedding provider: {prov!r}")

    async def chat(
        self,
        messages: List[dict],
        model: str,
        options: dict | None = None,
    ) -> AsyncIterator[str]:
        """Stream an Ollama chat completion, yielding content deltas.

        Chat orchestration (RAG, prompt assembly, persistence) lives in the API
        route; this is just the transport so the LLM call stays on the server and
        clients never talk to Ollama directly.
        """
        url = f"{self.ollama_url}/api/chat"
        payload: dict = {"model": model, "messages": messages, "stream": True}
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    delta = (data.get("message") or {}).get("content")
                    if delta:
                        yield delta
                    if data.get("done"):
                        break

    async def health_check(self) -> bool:
        """Return True if the active provider responds successfully."""
        if self.provider == OPENAI:
            try:
                await self._openai_embed(["test"], self.openai_model)
                return True
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning("OpenAI health check failed: %s", exc)
                return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.ollama_url}/api/version")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    # --------------------------------------------------- delegated model mgmt
    async def list_models(self) -> List[str]:
        return await self._model_manager.list_models()

    async def pull_model(self, model_name: str) -> bool:
        return await self._model_manager.pull_model(model_name)

    async def delete_model(self, model_name: str) -> bool:
        return await self._model_manager.delete_model(model_name)

    # ----------------------------------------------------- compatibility wraps
    async def generate_embedding(self, text: str) -> List[float]:
        return await self.embed(text)

    async def generate_batch_embeddings(
        self, texts: Iterable[str]
    ) -> List[List[float]]:
        return await self.embed_batch(texts)


# Shared instance used by API routes
ollama_client = EmbeddingClient()
