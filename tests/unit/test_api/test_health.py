"""
Unit tests for health check endpoints.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_check():
    """Test health check endpoint returns 200."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


@pytest.mark.unit
def test_health_check_structure():
    """Test health check response structure."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    data = response.json()

    # Check required fields
    required_fields = ["status", "timestamp", "version", "services"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Check services status
    assert isinstance(data["services"], dict)
    assert "database" in data["services"]
    assert "ollama" in data["services"]
