"""Smoke tests for the health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["services"]["database"] == "connected"
    assert payload["services"]["ollama"] == "available"
