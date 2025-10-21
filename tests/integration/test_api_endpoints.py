"""
Integration tests for API endpoints.

Tests conversation storage and semantic search endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.asyncio
class TestConversationEndpoints:
    """Test /conversations/* endpoints."""

    async def test_store_conversation(self, client: AsyncClient, sample_conversation_data: dict):
        """Test POST /conversations/store creates conversation."""
        response = await client.post(
            "/conversations/store",
            json=sample_conversation_data
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["source"] == "claude-code"
        assert data["title"] == "Test Conversation"

    async def test_store_conversation_generates_embedding(
        self,
        client: AsyncClient,
        sample_conversation_data: dict,
        db_session: AsyncSession
    ):
        """Test conversation storage generates embedding vector."""
        response = await client.post(
            "/conversations/store",
            json=sample_conversation_data
        )

        assert response.status_code == 200
        conversation_id = response.json()["id"]

        # Verify embedding was generated
        from app.models.conversation import Conversation
        result = await db_session.execute(
            "SELECT embedding FROM conversations WHERE id = :id",
            {"id": conversation_id}
        )
        row = result.fetchone()

        assert row is not None
        assert row["embedding"] is not None
        # nomic-embed-text produces 768-dimensional vectors
        assert len(row["embedding"]) == 768

    async def test_search_conversations(
        self,
        client: AsyncClient,
        sample_conversation_data: dict
    ):
        """Test POST /conversations/search finds similar conversations."""
        # Store a conversation first
        await client.post("/conversations/store", json=sample_conversation_data)

        # Search for it
        response = await client.post(
            "/conversations/search",
            json={
                "query": "test message",
                "limit": 10,
                "threshold": 0.5
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert len(data["results"]) > 0
        assert data["results"][0]["similarity"] > 0.5

    async def test_search_filters_by_source(
        self,
        client: AsyncClient,
        sample_conversation_data: dict
    ):
        """Test search can filter by source."""
        # Store conversations from different sources
        await client.post(
            "/conversations/store",
            json={**sample_conversation_data, "source": "claude-code"}
        )
        await client.post(
            "/conversations/store",
            json={**sample_conversation_data, "source": "chatgpt", "thread_id": "different"}
        )

        # Search with source filter
        response = await client.post(
            "/conversations/search",
            json={
                "query": "test",
                "source": "claude-code",
                "limit": 10
            }
        )

        assert response.status_code == 200
        results = response.json()["results"]

        # All results should be from claude-code
        for result in results:
            assert result["source"] == "claude-code"

    async def test_store_validates_required_fields(self, client: AsyncClient):
        """Test store endpoint validates required fields."""
        response = await client.post(
            "/conversations/store",
            json={"title": "Missing source"}
        )

        assert response.status_code == 422  # Validation error

    async def test_search_requires_query(self, client: AsyncClient):
        """Test search endpoint requires query parameter."""
        response = await client.post(
            "/conversations/search",
            json={"limit": 10}
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.asyncio
class TestEmbeddingEndpoint:
    """Test /embeddings/generate endpoint."""

    async def test_generate_embedding(self, client: AsyncClient):
        """Test POST /embeddings/generate creates vector."""
        response = await client.post(
            "/embeddings/generate",
            json={"text": "This is a test sentence"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "embedding" in data
        assert len(data["embedding"]) == 768  # nomic-embed-text
        assert all(isinstance(x, float) for x in data["embedding"])

    async def test_generate_embedding_validates_text(self, client: AsyncClient):
        """Test embedding generation requires text."""
        response = await client.post(
            "/embeddings/generate",
            json={}
        )

        assert response.status_code == 422


@pytest.fixture
async def client():
    """Create test client."""
    from httpx import AsyncClient
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
