"""Conversation deduplication and merging.

Handles hash-based deduplication and merging of continuation conversations.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional, Set

from .base_collector import Conversation, Message

logger = logging.getLogger(__name__)


def get_conversation_hash(conversation: Conversation) -> str:
    """Generate hash for conversation deduplication."""
    content_str = f"{conversation.source}:"
    for msg in conversation.messages:
        content_str += f"{msg.role}:{msg.content}:"
    date_str = conversation.created_at.date().isoformat()
    content_str += date_str
    return hashlib.sha256(content_str.encode()).hexdigest()


def get_message_hash(message: Message) -> str:
    """Generate hash for message deduplication."""
    content_str = f"{message.role}:{message.content}:{message.timestamp.isoformat()}"
    return hashlib.sha256(content_str.encode()).hexdigest()


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate simple word-overlap similarity (0-1)."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union) if union else 0.0


def should_merge(conv1: Conversation, conv2: Conversation) -> bool:
    """Determine if two conversations should be merged."""
    if conv1.source != conv2.source:
        return False

    time_diff = (conv2.created_at - conv1.updated_at).total_seconds()
    if time_diff > 1800:  # 30 minutes
        return False

    if conv1.messages and conv2.messages:
        last_msg = conv1.messages[-1].content[:100]
        first_msg = conv2.messages[0].content[:100]
        if calculate_similarity(last_msg, first_msg) > 0.7:
            return True

    if conv1.thread_id and conv1.thread_id == conv2.thread_id:
        return True

    return False


def merge_conversation_group(
    conversations: List[Conversation],
) -> Optional[Conversation]:
    """Merge a group of related conversations into one."""
    if not conversations:
        return None
    if len(conversations) == 1:
        return conversations[0]

    all_messages: List[Message] = []
    for conv in conversations:
        all_messages.extend(conv.messages)

    unique_messages: List[Message] = []
    seen_hashes: Set[str] = set()
    for msg in all_messages:
        msg_hash = get_message_hash(msg)
        if msg_hash not in seen_hashes:
            seen_hashes.add(msg_hash)
            unique_messages.append(msg)
    unique_messages.sort(key=lambda m: m.timestamp)

    # Pick most informative title
    title = conversations[0].title
    for conv in conversations:
        if conv.title and not conv.title.startswith(conv.source):
            title = conv.title
            break

    # Merge tags
    all_tags: Set[str] = set()
    for conv in conversations:
        if conv.tags:
            all_tags.update(conv.tags)

    # Merge metadata
    merged_metadata: Dict[str, Any] = {}
    for conv in conversations:
        if conv.metadata:
            merged_metadata.update(conv.metadata)
    merged_metadata["merged"] = True
    merged_metadata["merged_count"] = len(conversations)
    merged_metadata["merged_ids"] = [conv.id for conv in conversations]

    return Conversation(
        id=conversations[0].id,
        source=conversations[0].source,
        title=title,
        messages=unique_messages,
        created_at=conversations[0].created_at,
        updated_at=conversations[-1].updated_at,
        thread_id=conversations[0].thread_id,
        project=conversations[0].project,
        tags=list(all_tags),
        metadata=merged_metadata,
    )


def merge_conversations(conversations: List[Conversation]) -> List[Conversation]:
    """Merge conversations that are continuations of each other."""
    if not conversations:
        return []

    conversations.sort(key=lambda c: c.created_at)

    merged: List[Conversation] = []
    current_group = [conversations[0]]

    for conv in conversations[1:]:
        if should_merge(current_group[-1], conv):
            current_group.append(conv)
        else:
            merged_conv = merge_conversation_group(current_group)
            if merged_conv:
                merged.append(merged_conv)
            current_group = [conv]

    if current_group:
        merged_conv = merge_conversation_group(current_group)
        if merged_conv:
            merged.append(merged_conv)

    logger.info(f"Merged {len(conversations)} conversations into {len(merged)}")
    return merged
