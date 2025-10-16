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


# Global client instance
ollama_client = OllamaClient()
