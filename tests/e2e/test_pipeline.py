"""
End-to-end tests for complete MindBase pipeline.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_conversation_storage_and_search(sample_conversation_data, db_session):
    """Test complete conversation storage and semantic search pipeline."""
    from app.main import app

    client = TestClient(app)

    # 1. Store conversation
    store_response = client.post("/conversations/store", json=sample_conversation_data)
    assert store_response.status_code == 200
    stored_data = store_response.json()
    assert "conversation_id" in stored_data
    conversation_id = stored_data["conversation_id"]

    # 2. Search for conversation
    search_payload = {
        "query": "test message",
        "limit": 10,
        "threshold": 0.5,
    }
    search_response = client.post("/conversations/search", json=search_payload)
    assert search_response.status_code == 200
    results = search_response.json()

    # 3. Verify search results contain stored conversation
    assert len(results) > 0
    conversation_ids = [r["conversation_id"] for r in results]
    assert conversation_id in conversation_ids


@pytest.mark.e2e
@pytest.mark.slow
def test_health_check_all_services():
    """Test health check reports all services as healthy."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # All services should be healthy
    for service, status in data["services"].items():
        assert status["status"] == "healthy", f"{service} is not healthy"
