"""
Collector package exports
"""

from .base_collector import BaseCollector, Conversation, Message
from .claude_collector import ClaudeDesktopCollector
from .claude_code_collector import ClaudeCodeCollector
from .chatgpt_collector import ChatGPTCollector
from .cursor_collector import CursorCollector
from .windsurf_collector import WindsurfCollector
from .gemini_collector import GeminiCollector
from .data_normalizer import DataNormalizer
from .parsing import parse_message, normalize_timestamp, normalize_role, extract_title
from .deduplication import merge_conversations, get_conversation_hash
from .validation import validate_data_quality, NormalizationStats

__all__ = [
    "BaseCollector",
    "Conversation",
    "Message",
    "ClaudeDesktopCollector",
    "ClaudeCodeCollector",
    "ChatGPTCollector",
    "CursorCollector",
    "WindsurfCollector",
    "GeminiCollector",
    "DataNormalizer",
    "parse_message",
    "normalize_timestamp",
    "normalize_role",
    "extract_title",
    "merge_conversations",
    "get_conversation_hash",
    "validate_data_quality",
    "NormalizationStats",
]
