"""Data Normalizer — normalizes collected conversation data into a unified format.

Deduplication is delegated to deduplication.py.
Quality validation is delegated to validation.py.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base_collector import Conversation, Message
from .deduplication import (
    get_conversation_hash,
    get_message_hash,
    merge_conversations,
)
from .validation import (
    NormalizationStats,
    validate_data_quality,
)

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalizes conversation data from multiple sources."""

    def __init__(self):
        self.stats = NormalizationStats()
        self.seen_conversation_hashes: set[str] = set()
        self.seen_message_hashes: set[str] = set()

        self.role_mappings = {
            "user": ["user", "human", "me", "question", "prompt", "input"],
            "assistant": [
                "assistant",
                "ai",
                "bot",
                "claude",
                "chatgpt",
                "gpt",
                "cursor",
                "windsurf",
                "response",
                "completion",
                "output",
            ],
            "system": ["system", "instruction", "context"],
        }

        self.content_patterns = [
            (r"\s+", " "),
            (r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", ""),
            (r"\r\n|\r", "\n"),
            (r"[\u200B\u200C\u200D\uFEFF]", ""),
        ]

    def normalize_conversations(
        self, conversations: List[Conversation], source: Optional[str] = None
    ) -> List[Conversation]:
        """Normalize a list of conversations."""
        logger.info(f"Normalizing {len(conversations)} conversations...")
        self.stats.total_input = len(conversations)

        normalized = []
        for conv in conversations:
            if source and conv.source != source:
                continue

            norm_conv = self._normalize_conversation(conv)
            if norm_conv:
                conv_hash = get_conversation_hash(norm_conv)
                if conv_hash not in self.seen_conversation_hashes:
                    self.seen_conversation_hashes.add(conv_hash)
                    normalized.append(norm_conv)
                else:
                    self.stats.duplicates_removed += 1
            else:
                self.stats.invalid_removed += 1

        self.stats.total_output = len(normalized)
        logger.info(
            f"Normalization complete: {self.stats.total_output} conversations retained"
        )
        return normalized

    def _normalize_conversation(
        self, conversation: Conversation
    ) -> Optional[Conversation]:
        """Normalize a single conversation."""
        try:
            if not conversation.messages:
                return None

            normalized_messages = []
            for msg in conversation.messages:
                norm_msg = self._normalize_message(msg)
                if norm_msg:
                    msg_hash = get_message_hash(norm_msg)
                    if msg_hash not in self.seen_message_hashes:
                        self.seen_message_hashes.add(msg_hash)
                        normalized_messages.append(norm_msg)

            if not normalized_messages:
                return None

            normalized_messages.sort(key=lambda m: m.timestamp)
            conversation.messages = normalized_messages

            if not conversation.created_at or not conversation.created_at.tzinfo:
                conversation.created_at = normalized_messages[0].timestamp
                self.stats.timestamps_fixed += 1

            if not conversation.updated_at or not conversation.updated_at.tzinfo:
                conversation.updated_at = normalized_messages[-1].timestamp
                self.stats.timestamps_fixed += 1

            conversation.title = self._normalize_title(conversation)

            if not conversation.metadata:
                conversation.metadata = {}
            conversation.metadata["normalized"] = True
            conversation.metadata["normalization_timestamp"] = datetime.now(
                timezone.utc
            ).isoformat()

            return conversation
        except Exception as e:
            logger.warning(f"Error normalizing conversation {conversation.id}: {e}")
            return None

    def _normalize_message(self, message: Message) -> Optional[Message]:
        """Normalize a single message."""
        try:
            self.stats.messages_normalized += 1

            original_role = message.role.lower()
            normalized_role = self._normalize_role(original_role)
            if normalized_role != original_role:
                message.role = normalized_role
                self.stats.roles_standardized += 1

            cleaned_content = self._clean_content(message.content)
            if cleaned_content != message.content:
                message.content = cleaned_content
                self.stats.content_cleaned += 1

            if not message.content or not message.content.strip():
                return None

            if not message.timestamp.tzinfo:
                message.timestamp = message.timestamp.replace(tzinfo=timezone.utc)
                self.stats.timestamps_fixed += 1

            return message
        except Exception as e:
            logger.debug(f"Error normalizing message: {e}")
            return None

    def _normalize_role(self, role: str) -> str:
        """Normalize message role to standard values."""
        role = role.lower().strip()
        for standard_role, variations in self.role_mappings.items():
            if role in variations:
                return standard_role
        return "assistant"

    def _clean_content(self, content: str) -> str:
        """Clean and normalize message content."""
        if not content:
            return content
        for pattern, replacement in self.content_patterns:
            content = re.sub(pattern, replacement, content)
        content = content.strip()
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content

    def _normalize_title(self, conversation: Conversation) -> str:
        """Generate or normalize conversation title."""
        if conversation.title and conversation.title.strip():
            title = self._clean_content(conversation.title)
            if len(title) > 200:
                title = title[:197] + "..."
            return title

        for msg in conversation.messages:
            if msg.role == "user":
                title = msg.content[:100]
                if len(msg.content) > 100:
                    title += "..."
                return title

        return f"{conversation.source} conversation"

    # Delegated methods
    merge_conversations = staticmethod(merge_conversations)
    validate_data_quality = staticmethod(validate_data_quality)

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.to_dict()

    def reset_stats(self):
        self.stats = NormalizationStats()
        self.seen_conversation_hashes.clear()
        self.seen_message_hashes.clear()
