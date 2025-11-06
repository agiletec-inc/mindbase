"""Heuristic project/topic classification for MindBase conversations."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional


TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "Docker-First Development": ["docker", "docker-compose", "container", "workspace", "volume"],
    "Turborepo Monorepo": ["turborepo", "pnpm", "monorepo", "workspace", "package.json"],
    "Supabase Self-Host": ["supabase", "realtime", "edge function", "kong", "auth"],
    "Multi-Tenancy": ["multi-tenant", "tenant", "organization_id", "row level security", "rls"],
    "Testing Strategy": ["unit test", "integration test", "playwright", "vitest", "coverage"],
    "SuperClaude Framework": ["superclaude", "pm agent", "mcp", "skill", "persona"],
    "AlmaLinux HomeServer": ["almalinux", "restic", "tdarr", "nas", "samba"],
    "Performance Optimization": ["performance", "optimization", "cache", "latency", "profiling"],
    "API Design": ["api", "endpoint", "openapi", "fastapi", "rest"],
    "Security": ["authentication", "authorization", "jwt", "encryption", "secret"],
}

# Map of known projects to representative keywords
PROJECT_KEYWORDS: Dict[str, Iterable[str]] = {
    "mindbase": ["mindbase", "vector memory", "conversation archive"],
    "superclaude": ["superclaude", "pm agent", "autonomous agent"],
    "airis-gateway": ["airis", "mcp gateway", "mindbase mcp"],
}

# Keys in metadata/content that may contain project identifiers
PROJECT_HINT_KEYS = ("project", "workspace", "project_path", "repo", "repository", "slug")


def _normalise_text(text: Optional[str]) -> str:
    return text.lower() if text else ""


def infer_topics(text: str, existing: Optional[List[str]] = None) -> List[str]:
    """Infer topics from free-form text using keyword heuristics."""
    if existing:
        filtered = [topic for topic in existing if topic]
        if filtered:
            return filtered

    text_lc = _normalise_text(text)
    detected: List[str] = []

    for topic, keywords in TOPIC_KEYWORDS.items():
        matches = sum(1 for keyword in keywords if keyword in text_lc)
        if matches >= 2:
            detected.append(topic)

    if not detected:
        detected.append("General")

    return detected


def infer_project(
    *,
    metadata: Optional[dict],
    content: Optional[dict],
    text: str,
    explicit: Optional[str] = None,
) -> Optional[str]:
    """Detect project hints from payload metadata/content or text."""
    if explicit:
        return explicit

    # Check structured metadata/content first
    for source_dict in (metadata or {}, content or {}):
        if isinstance(source_dict, dict):
            for key in PROJECT_HINT_KEYS:
                value = source_dict.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

    # Heuristic keyword detection on raw text
    text_lc = _normalise_text(text)
    for project, keywords in PROJECT_KEYWORDS.items():
        if any(keyword in text_lc for keyword in keywords):
            return project

    return None
