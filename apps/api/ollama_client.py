"""Ollama client for embedding generation"""

import ollama
from app.config import get_settings

settings = get_settings()


class OllamaClient:
    """Ollama embedding client"""

    def __init__(self):
        self.client = ollama.Client(host=settings.OLLAMA_URL)
        self.model = settings.EMBEDDING_MODEL

    async def embed(self, text: str) -> list[float]:
        """
        Generate embedding for text using qwen3-embedding:8b

        Args:
            text: Input text to embed

        Returns:
            List of 1024 floats (embedding vector)
        """
        response = self.client.embed(
            model=self.model,
            input=text,
        )
        return response["embeddings"][0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings

    async def list_models(self) -> list[str]:
        """
        List all installed Ollama models

        Returns:
            List of installed model names
        """
        try:
            response = self.client.list()
            # Extract model names from response
            models = [model["name"] for model in response.get("models", [])]
            return models
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull (download) a model from Ollama registry

        Args:
            model_name: Model to download (e.g., "qwen3-embedding:8b")

        Returns:
            True if successful, False otherwise
        """
        try:
            # Note: ollama.pull() is synchronous
            self.client.pull(model_name)
            return True
        except Exception as e:
            print(f"Error pulling model {model_name}: {e}")
            return False

    async def delete_model(self, model_name: str) -> bool:
        """
        Delete an installed model

        Args:
            model_name: Model to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete(model_name)
            return True
        except Exception as e:
            print(f"Error deleting model {model_name}: {e}")
            return False


# Global client instance
ollama_client = OllamaClient()
