"""Integration tests for MindBase conversation endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
@pytest.mark.asyncio
async def test_store_conversation_persists_metadata(
    async_client: AsyncClient,
) -> None:
    """POST /conversations/store should persist project/topics metadata."""
    payload = {
        "source": "claude-code",
        "source_conversation_id": f"test-{uuid.uuid4()}",
        "title": "Timeline stitching prototype",
        "content": {
            "messages": [
                {"role": "user", "content": "Docker compose deployment failed"},
                {"role": "assistant", "content": "Check docker-compose logs"},
            ],
            "project": "platform",
        },
        "metadata": {"tags": ["deployment"]},
    }

    response = await async_client.post("/conversations/store", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["project"] == "platform"
    assert data["topics"] == ["Docker-First Development"]

    # Verify persistence
    search_response = await async_client.post(
        "/conversations/search",
        json={
            "query": "docker compose",
            "project": "platform",
            "limit": 1,
            "threshold": 0.1,
        },
    )
    assert search_response.status_code == 200
    results = search_response.json()
    assert any(item["id"] == data["id"] for item in results)
    assert any(item["topics"] == ["Docker-First Development"] for item in results)


@pytest.mark.asyncio
async def test_search_conversations_supports_filters(
    async_client: AsyncClient,
) -> None:
    """POST /conversations/search should support project/topic filters."""
    base_payload = {
        "source": "cursor",
        "title": "LLM search tuning",
        "content": {
            "messages": [
                {
                    "role": "user",
                    "content": "Docker containers crash when running docker-compose deployments",
                },
                {
                    "role": "assistant",
                    "content": "Let's adjust the Makefile to restart the container service.",
                },
            ]
        },
        "metadata": {},
    }

    for project in ("platform", "docs"):
        payload = base_payload | {
            "source_conversation_id": f"{project}-{uuid.uuid4()}",
            "content": base_payload["content"] | {"project": project},
        }
        response = await async_client.post("/conversations/store", json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["project"] == project

    response = await async_client.post(
        "/conversations/search",
        json={
            "query": "docker compose",
            "project": "platform",
            "limit": 5,
            "threshold": 0.1,
        },
    )

    assert response.status_code == 200, response.text
    results = response.json()
    assert len(results) == 1
    assert results[0]["project"] == "platform"
    assert "Docker-First Development" in results[0]["topics"]


@pytest.mark.asyncio
async def test_search_requires_query(async_client: AsyncClient) -> None:
    """Missing query payload should raise validation error."""
    response = await async_client.post(
        "/conversations/search",
        json={"limit": 5},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_store_requires_source(async_client: AsyncClient) -> None:
    """Missing required fields should trigger validation error."""
    response = await async_client.post(
        "/conversations/store",
        json={"title": "Missing source"},
    )
    assert response.status_code == 422
