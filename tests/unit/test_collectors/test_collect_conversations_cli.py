"""
Tests for scripts.collect-conversations CLI utilities.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest

from collectors.base_collector import BaseCollector, Conversation, Message


def load_cli_module():
    """Load the CLI script as a module for testing."""
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "collect-conversations.py"
    spec = importlib.util.spec_from_file_location("collect_conversations_cli", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DummyCollector(BaseCollector):
    """Minimal collector returning a single conversation."""

    def __init__(self, source_name: str = "dummy"):
        super().__init__(source_name)
        self._conversation = Conversation(
            id="conv-1",
            source=source_name,
            title="Dummy Conversation",
            messages=[
                Message(
                    role="user",
                    content="Hello",
                    timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
                Message(
                    role="assistant",
                    content="Hi there",
                    timestamp=datetime(2025, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
                ),
            ],
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
            thread_id="thread-1",
            metadata={"origin": "test"},
        )

    def get_data_paths(self) -> List[Path]:
        return []

    def collect(self, since_date=None) -> List[Conversation]:
        return [self._conversation]


@pytest.fixture(autouse=True)
def restore_argv():
    """Ensure sys.argv is restored between tests."""
    original = sys.argv[:]
    yield
    sys.argv = original


def test_cli_dry_run(monkeypatch):
    """Dry-run should collect data but skip API sync."""
    module = load_cli_module()

    monkeypatch.setattr(
        module,
        "COLLECTOR_REGISTRY",
        {"dummy": DummyCollector},
        raising=False,
    )

    sys.argv = [
        str(Path(module.__file__).name),
        "--source",
        "dummy",
        "--dry-run",
        "--verbose",
    ]

    exit_code = module.main()
    assert exit_code == 0


def test_cli_sync(monkeypatch):
    """Successful sync should call MindBase API for each conversation."""
    module = load_cli_module()

    monkeypatch.setattr(
        module,
        "COLLECTOR_REGISTRY",
        {"dummy": DummyCollector},
        raising=False,
    )

    stored_payloads: List[dict] = []

    class DummySyncer(module.MindBaseAPISyncer):
        def __init__(self, base_url, api_key=None, timeout=30):
            self.base_url = base_url
            self.api_key = api_key
            self.timeout = timeout

        def store_conversation(self, payload):
            stored_payloads.append(payload)
            return {"id": "mock-id"}

    monkeypatch.setattr(module, "MindBaseAPISyncer", DummySyncer, raising=False)

    sys.argv = [
        str(Path(module.__file__).name),
        "--source",
        "dummy",
        "--api-url",
        "http://test",
        "--batch-size",
        "1",
    ]

    exit_code = module.main()

    assert exit_code == 0
    assert len(stored_payloads) == 1
    payload = stored_payloads[0]
    assert payload["source"] == "dummy"
    assert "messages" in payload["content"]
    assert payload["content"]["messages"][0]["role"] == "user"
