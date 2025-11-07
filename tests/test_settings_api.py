"""Tests for the settings API endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.services import settings_store


@pytest.mark.asyncio
async def test_settings_roundtrip(async_client: AsyncClient, tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings_store.override_settings_path(path)

    default_payload = {
        "apiBaseUrl": "http://localhost:18002",
        "workspaceRoot": "/workspaces/mindbase",
        "repoRoot": "/Users/me/github/mindbase",
        "refreshIntervalMs": 10000,
        "collectors": [{"id": "claude-code", "label": "Claude Code", "workspace": "mindbase"}],
        "pipelines": [{"id": "raw", "label": "RAW Ingestion"}],
    }
    path.write_text(json.dumps(default_payload), encoding="utf-8")

    try:
        resp = await async_client.get("/settings")
        assert resp.status_code == 200
        assert resp.json()["repoRoot"] == "/Users/me/github/mindbase"

        updated_payload = dict(default_payload)
        updated_payload["repoRoot"] = "/tmp/mindbase"
        resp = await async_client.put("/settings", json=updated_payload)
        assert resp.status_code == 200
        assert resp.json()["repoRoot"] == "/tmp/mindbase"

        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["repoRoot"] == "/tmp/mindbase"
    finally:
        settings_store.override_settings_path(None)
