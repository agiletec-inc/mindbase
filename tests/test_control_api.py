"""Tests for the control endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from app.services import settings_store


@pytest.mark.asyncio
async def test_control_runs_make_target(async_client: AsyncClient, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    makefile = repo_root / "Makefile"
    makefile.write_text(
        "up:\n\t@echo running up\n"
        "down:\n\t@echo running down\n"
        "logs:\n\t@echo logs\n"
        "worker:\n\t@echo worker\n"
        "restart:\n\t@echo restart\n"
    )

    settings_path = tmp_path / "settings.json"
    settings_store.override_settings_path(settings_path)
    settings_store.save_settings(
        {
            "apiBaseUrl": "http://localhost:18002",
            "workspaceRoot": "/tmp",
            "repoRoot": str(repo_root),
            "refreshIntervalMs": 5000,
            "collectors": [],
            "pipelines": [],
        }
    )

    try:
        resp = await async_client.post("/control/up")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["action"] == "up"
        assert "running up" in payload["stdout"]
    finally:
        settings_store.override_settings_path(None)
