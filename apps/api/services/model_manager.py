"""Ollama model lifecycle management — pull, delete, list."""

from __future__ import annotations

import logging
from typing import List

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manage Ollama models (pull, delete, list)."""

    def __init__(
        self,
        ollama_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = get_settings()
        self.ollama_url = (ollama_url or settings.OLLAMA_URL).rstrip("/")
        self.timeout = timeout

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
