"""Filesystem-backed settings store shared by CLI and menubar."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_PATH = Path.home() / ".config" / "mindbase" / "settings.json"
_OVERRIDE_PATH: Path | None = None


def override_settings_path(path: Path | None) -> None:
    """For tests: override the destination file."""
    global _OVERRIDE_PATH
    _OVERRIDE_PATH = path


def _resolve_path() -> Path:
    if _OVERRIDE_PATH:
        path = _OVERRIDE_PATH
    else:
        env = os.getenv("MINDBASE_SETTINGS_PATH")
        if env:
            path = Path(os.path.expanduser(env))
        else:
            path = DEFAULT_SETTINGS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_settings() -> Dict[str, Any]:
    """Load stored settings, returning defaults if missing."""
    path = _resolve_path()
    if not path.exists():
        return {}

    contents = path.read_text(encoding="utf-8")
    try:
        return json.loads(contents) if contents.strip() else {}
    except json.JSONDecodeError as e:
        logger.warning(f"Corrupted settings file at {path}: {e}. Using defaults.")
        return {}


def save_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist settings to disk."""
    path = _resolve_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def get_active_embedding() -> tuple[str, str]:
    """Single source of truth for the active embedding ``(provider, model)``.

    Reads the persisted settings store first; falls back to the env defaults
    (``config.Settings``) as the initial seed when the store has no choice yet.
    Every embedding decision point resolves through here so switching the model
    (via ``PUT /api/embeddings/models/active`` or ``PUT /settings``) takes effect
    without a restart and survives one.
    """
    from apps.api.config import get_settings  # lazy: avoid import cycle

    data = load_settings()
    settings = get_settings()
    provider = (
        data.get("embeddingProvider") or settings.EMBEDDING_PROVIDER or "ollama"
    ).lower()
    model = data.get("embeddingModel")
    if not model:
        model = (
            settings.OPENAI_EMBEDDING_MODEL
            if provider == "openai"
            else settings.EMBEDDING_MODEL
        )
    return provider, model


def set_active_embedding(provider: str, model: str) -> tuple[str, str]:
    """Persist the active embedding ``(provider, model)`` to the settings store."""
    data = load_settings()
    data["embeddingProvider"] = provider
    data["embeddingModel"] = model
    save_settings(data)
    return provider, model


def get_repo_root(default: Optional[str] = None) -> Path:
    """Resolve repo root from settings or fallback."""
    data = load_settings()
    repo = data.get("repoRoot") or default or os.getenv("REPO_ROOT")
    if repo:
        return Path(os.path.expanduser(repo)).resolve()
    # fallback to repo root (two dirs up from this file)
    return Path(__file__).resolve().parents[3]
