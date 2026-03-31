"""Data quality validation for conversations.

Validates conversation quality and generates quality reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .base_collector import Conversation


@dataclass
class NormalizationStats:
    """Statistics from normalization process."""

    total_input: int = 0
    total_output: int = 0
    duplicates_removed: int = 0
    invalid_removed: int = 0
    messages_normalized: int = 0
    timestamps_fixed: int = 0
    roles_standardized: int = 0
    content_cleaned: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "total_input": self.total_input,
            "total_output": self.total_output,
            "duplicates_removed": self.duplicates_removed,
            "invalid_removed": self.invalid_removed,
            "messages_normalized": self.messages_normalized,
            "timestamps_fixed": self.timestamps_fixed,
            "roles_standardized": self.roles_standardized,
            "content_cleaned": self.content_cleaned,
        }


def validate_conversation_quality(conversation: Conversation) -> List[str]:
    """Validate quality of a single conversation. Returns list of issues."""
    issues: List[str] = []

    if len(conversation.messages) < 2:
        issues.append("Conversation has less than 2 messages")

    roles = set(msg.role for msg in conversation.messages)
    if "user" not in roles:
        issues.append("No user messages found")
    if "assistant" not in roles:
        issues.append("No assistant messages found")

    empty_messages = sum(
        1 for msg in conversation.messages if not msg.content or not msg.content.strip()
    )
    if empty_messages > 0:
        issues.append(f"{empty_messages} empty messages found")

    for i in range(1, len(conversation.messages)):
        if conversation.messages[i].timestamp < conversation.messages[i - 1].timestamp:
            issues.append("Messages not in chronological order")
            break

    for msg in conversation.messages:
        if len(msg.content) < 2:
            issues.append(f"Suspiciously short message: {msg.content[:50]}")
        elif len(msg.content) > 50000:
            issues.append(f"Suspiciously long message: {len(msg.content)} characters")

    return issues


def validate_data_quality(
    conversations: List[Conversation],
) -> Tuple[List[Conversation], Dict[str, Any]]:
    """Validate data quality and return valid conversations with quality report."""
    valid_conversations: List[Conversation] = []
    quality_report: Dict[str, Any] = {
        "total_conversations": len(conversations),
        "valid_conversations": 0,
        "invalid_conversations": 0,
        "quality_issues": [],
        "statistics": {},
    }

    for conv in conversations:
        issues = validate_conversation_quality(conv)
        if not issues:
            valid_conversations.append(conv)
            quality_report["valid_conversations"] += 1
        else:
            quality_report["invalid_conversations"] += 1
            quality_report["quality_issues"].append(
                {"conversation_id": conv.id, "source": conv.source, "issues": issues}
            )

    if valid_conversations:
        quality_report["statistics"] = calculate_statistics(valid_conversations)

    return valid_conversations, quality_report


def calculate_statistics(conversations: List[Conversation]) -> Dict[str, Any]:
    """Calculate statistics for valid conversations."""
    total_messages = sum(len(conv.messages) for conv in conversations)
    total_words = sum(
        sum(len(msg.content.split()) for msg in conv.messages) for conv in conversations
    )
    message_lengths = [
        len(msg.content) for conv in conversations for msg in conv.messages
    ]
    avg_message_length = (
        sum(message_lengths) / len(message_lengths) if message_lengths else 0
    )

    source_counts: Dict[str, int] = {}
    for conv in conversations:
        source_counts[conv.source] = source_counts.get(conv.source, 0) + 1

    return {
        "total_messages": total_messages,
        "total_words": total_words,
        "avg_messages_per_conversation": total_messages / len(conversations),
        "avg_message_length": avg_message_length,
        "sources": dict(
            sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        ),
        "date_range": {
            "earliest": min(conv.created_at for conv in conversations).isoformat(),
            "latest": max(conv.updated_at for conv in conversations).isoformat(),
        },
    }
