"""Filesystem-backed settings store shared by CLI and menubar."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

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
    except json.JSONDecodeError:
        return {}


def save_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist settings to disk."""
    path = _resolve_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
