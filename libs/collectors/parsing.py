"""Shared parsing utilities for all conversation collectors.

Consolidates duplicated logic for:
- Message parsing (role extraction, content extraction, timestamp handling)
- Timestamp normalization (ISO, Unix, various string formats)
- Title extraction from conversation data
- Role normalization with source-specific aliases
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base_collector import Message

logger = logging.getLogger(__name__)

# Source-specific role aliases mapping to normalized roles.
# Each collector can pass its own or use a shared set.

COMMON_USER_ALIASES = ["human", "user", "prompt"]
COMMON_ASSISTANT_ALIASES = ["ai", "assistant", "completion", "response"]

ROLE_ALIASES: Dict[str, Dict[str, List[str]]] = {
    "cursor": {
        "user": COMMON_USER_ALIASES,
        "assistant": COMMON_ASSISTANT_ALIASES,
    },
    "windsurf": {
        "user": COMMON_USER_ALIASES,
        "assistant": [*COMMON_ASSISTANT_ALIASES, "cascade", "codeium"],
    },
    "claude-desktop": {
        "user": [*COMMON_USER_ALIASES, "human_turn"],
        "assistant": [*COMMON_ASSISTANT_ALIASES, "assistant_turn", "claude"],
    },
    "chatgpt": {
        "user": COMMON_USER_ALIASES,
        "assistant": [*COMMON_ASSISTANT_ALIASES, "bot", "chatgpt", "gpt"],
    },
    "gemini": {
        "user": [*COMMON_USER_ALIASES, "0"],
        "assistant": [*COMMON_ASSISTANT_ALIASES, "model", "1"],
    },
    "claude-code": {
        "user": COMMON_USER_ALIASES,
        "assistant": [*COMMON_ASSISTANT_ALIASES, "claude"],
    },
}

# Common field names used to extract role from message dicts
ROLE_FIELDS = ["role", "sender", "author", "type", "from"]

# Common field names used to extract content from message dicts
CONTENT_FIELDS = ["content", "text", "message", "body", "value"]

# Common field names used to extract timestamp from message dicts
TIMESTAMP_FIELDS = [
    "timestamp",
    "created_at",
    "createdAt",
    "create_time",
    "date",
    "time",
    "updated_at",
    "updatedAt",
]


def normalize_role(
    raw_role: str,
    source: str | None = None,
) -> str:
    """Normalize a raw role string to 'user', 'assistant', or 'system'.

    Uses source-specific aliases if source is provided.
    """
    role = raw_role.strip().lower()

    if role in ("system",):
        return "system"

    aliases = ROLE_ALIASES.get(source or "", {})

    for normalized, alias_list in aliases.items():
        if role in alias_list:
            return normalized

    # Fallback to common aliases if source didn't match
    if role in COMMON_USER_ALIASES:
        return "user"
    if role in COMMON_ASSISTANT_ALIASES:
        return "assistant"

    return "user"  # default


def extract_role(msg_data: dict, source: str | None = None) -> str:
    """Extract and normalize role from a message dict."""
    for field in ROLE_FIELDS:
        value = msg_data.get(field)
        if isinstance(value, str) and value.strip():
            return normalize_role(value, source)
        if isinstance(value, dict) and "role" in value:
            return normalize_role(value["role"], source)
    return "user"


def extract_content(msg_data: dict) -> str:
    """Extract text content from a message dict.

    Handles nested structures (lists, dicts with 'text' keys, etc.)
    """
    for field in CONTENT_FIELDS:
        value = msg_data.get(field)
        if value is None:
            continue

        if isinstance(value, str) and value.strip():
            return value.strip()

        if isinstance(value, list):
            # Handle parts/blocks arrays (OpenAI, Claude, etc.)
            texts = []
            for part in value:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict):
                    text = part.get("text") or part.get("content") or part.get("value")
                    if isinstance(text, str):
                        texts.append(text)
            result = "\n".join(texts).strip()
            if result:
                return result

        if isinstance(value, dict):
            text = value.get("text") or value.get("content") or value.get("value")
            if isinstance(text, str) and text.strip():
                return text.strip()

    return ""


def extract_timestamp(msg_data: dict) -> datetime:
    """Extract and normalize timestamp from a message dict."""
    for field in TIMESTAMP_FIELDS:
        value = msg_data.get(field)
        if value is not None:
            return normalize_timestamp(value)
    return datetime.now(timezone.utc)


def normalize_timestamp(timestamp: Any) -> datetime:
    """Normalize various timestamp formats to timezone-aware datetime.

    Handles: datetime objects, Unix timestamps (seconds/milliseconds),
    ISO strings, and various date formats.
    """
    if isinstance(timestamp, datetime):
        return (
            timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        )

    if isinstance(timestamp, (int, float)):
        if timestamp > 1e10:  # Milliseconds
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    if isinstance(timestamp, str):
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp, fmt)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        try:
            from dateutil import parser

            dt = parser.parse(timestamp)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    logger.warning(f"Could not parse timestamp: {timestamp}, using current time")
    return datetime.now(timezone.utc)


def parse_message(
    msg_data: Any,
    source: str | None = None,
) -> Optional[Message]:
    """Parse a message from various formats into a Message object.

    This is the unified replacement for _parse_message methods across collectors.
    Source-specific logic is handled via role aliases and content extraction.
    """
    if isinstance(msg_data, str):
        if not msg_data.strip():
            return None
        return Message(
            role="user",
            content=msg_data.strip(),
            timestamp=datetime.now(timezone.utc),
        )

    if not isinstance(msg_data, dict):
        return None

    role = extract_role(msg_data, source)
    content = extract_content(msg_data)

    if not content:
        return None

    timestamp = extract_timestamp(msg_data)

    return Message(
        role=role,
        content=content,
        timestamp=timestamp,
        message_id=msg_data.get("id") or msg_data.get("message_id"),
        parent_id=msg_data.get("parent_id") or msg_data.get("parentMessageId"),
        metadata={
            k: v
            for k, v in msg_data.items()
            if k not in {*ROLE_FIELDS, *CONTENT_FIELDS, *TIMESTAMP_FIELDS, "id", "message_id", "parent_id", "parentMessageId"}
            and isinstance(v, (str, int, float, bool))
        },
    )


def extract_title(
    conversation_data: Any,
    source_name: str = "Unknown",
) -> str:
    """Extract or generate a conversation title.

    Tries common title fields, then falls back to first message content.
    """
    if isinstance(conversation_data, dict):
        for field in ["title", "name", "subject", "topic"]:
            value = conversation_data.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()[:200]

        messages = conversation_data.get("messages")
        if isinstance(messages, list) and messages:
            first = messages[0]
            if isinstance(first, dict) and "content" in first:
                content = str(first["content"])[:100]
                return content + ("..." if len(str(first["content"])) > 100 else "")

    return f"Conversation from {source_name}"
