#!/usr/bin/env python3
"""
Gemini Collector
Collects conversations from Google Gemini (formerly Bard) exports.

Supported data sources:
1. Google Takeout export (JSON files in Takeout/Gemini Apps Activity/)
2. Manual JSON export from Gemini web interface

Google Takeout structure:
  Takeout/
  └── Gemini Apps Activity/
      └── MyActivity.json   (or individual JSON files per conversation)

Each activity entry contains:
  - header: "Gemini Apps"
  - title: conversation title
  - time: ISO 8601 timestamp
  - products: ["Gemini Apps"]
  - activityControls: [...]
  - subtitles: [{name: "From ...", ...}]
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from .base_collector import BaseCollector, Conversation, Message

logger = logging.getLogger(__name__)


class GeminiCollector(BaseCollector):
    """Collector for Google Gemini conversations"""

    def __init__(self, export_path: Optional[str] = None):
        """
        Args:
            export_path: Optional explicit path to Gemini export directory.
                         If not provided, searches common locations.
        """
        super().__init__("gemini")
        self.export_path = export_path

    def get_data_paths(self) -> List[Path]:
        """Find Gemini data export locations"""
        home = Path.home()
        search_paths = []

        # Explicit path
        if self.export_path:
            p = Path(self.export_path)
            if p.exists():
                return [p]
            logger.warning(f"Explicit export path not found: {self.export_path}")

        # Common Google Takeout download locations
        takeout_patterns = [
            home / "Downloads" / "Takeout" / "Gemini Apps Activity",
            home / "Downloads" / "takeout-*" / "Takeout" / "Gemini Apps Activity",
            home / "Documents" / "Takeout" / "Gemini Apps Activity",
            # Japanese locale
            home / "Downloads" / "Takeout" / "Gemini アプリのアクティビティ",
        ]

        for pattern in takeout_patterns:
            if "*" in str(pattern):
                # Glob pattern
                parent = pattern.parent
                name = pattern.name
                if parent.parent.exists():
                    for match in parent.parent.glob(f"{parent.name}"):
                        candidate = match / name
                        if candidate.exists():
                            search_paths.append(candidate)
            elif pattern.exists():
                search_paths.append(pattern)

        # Also check for manually placed JSON files
        manual_dirs = [
            home / "mindbase-imports" / "gemini",
            home / "Documents" / "gemini-export",
        ]
        for d in manual_dirs:
            if d.exists() and list(d.glob("*.json")):
                search_paths.append(d)

        logger.info(f"Found {len(search_paths)} Gemini data paths")
        return search_paths

    def collect(self, since_date: Optional[datetime] = None) -> List[Conversation]:
        """Collect Gemini conversations from exports"""
        logger.info(f"Collecting {self.source_name} conversations...")
        all_conversations = []

        for data_path in self.get_data_paths():
            logger.info(f"Processing Gemini data from: {data_path}")

            # Process all JSON files in the directory
            json_files = sorted(data_path.glob("*.json"))
            for json_file in json_files:
                try:
                    conversations = self._parse_json_file(json_file)
                    all_conversations.extend(conversations)
                except Exception as e:
                    logger.warning(f"Error parsing {json_file}: {e}")
                    self.stats["errors"] += 1

        # Deduplicate and filter
        all_conversations = self.deduplicate_conversations(all_conversations)
        all_conversations = self.filter_by_date(all_conversations, since_date)

        # Update stats
        self.update_stats(all_conversations)
        self.conversations = all_conversations

        logger.info(
            f"Collected {len(all_conversations)} conversations from {self.source_name}"
        )
        return all_conversations

    def _parse_json_file(self, json_file: Path) -> List[Conversation]:
        """Parse a Gemini export JSON file"""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        conversations = []

        if isinstance(data, list):
            # Google Takeout MyActivity.json format: list of activity entries
            # Group entries by conversation (they share time proximity + title)
            grouped = self._group_activity_entries(data)
            for group in grouped:
                conv = self._parse_activity_group(group)
                if conv and self.validate_conversation(conv):
                    conversations.append(conv)

        elif isinstance(data, dict):
            # Single conversation export or custom format
            if "conversations" in data:
                for conv_data in data["conversations"]:
                    conv = self._parse_conversation_dict(conv_data)
                    if conv and self.validate_conversation(conv):
                        conversations.append(conv)
            elif "messages" in data or "turns" in data:
                conv = self._parse_conversation_dict(data)
                if conv and self.validate_conversation(conv):
                    conversations.append(conv)
            else:
                # Try as single activity entry
                conv = self._parse_conversation_dict(data)
                if conv and self.validate_conversation(conv):
                    conversations.append(conv)

        return conversations

    def _group_activity_entries(
        self, entries: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group Google Takeout activity entries into conversations.
        Entries with the same title within a time window are grouped together.
        """
        # Filter to Gemini-related entries
        gemini_entries = []
        for entry in entries:
            products = entry.get("products", [])
            header = entry.get("header", "")
            if "Gemini" in header or "Gemini Apps" in products or "Bard" in header:
                gemini_entries.append(entry)

        if not gemini_entries:
            return []

        # Sort by time
        gemini_entries.sort(key=lambda e: e.get("time", ""))

        # Group by title (conversations share the same title in Takeout)
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for entry in gemini_entries:
            title = entry.get("title", "Untitled")
            if title not in groups:
                groups[title] = []
            groups[title].append(entry)

        return list(groups.values())

    def _parse_activity_group(
        self, entries: List[Dict[str, Any]]
    ) -> Optional[Conversation]:
        """Parse a group of Google Takeout activity entries into a Conversation"""
        if not entries:
            return None

        messages = []
        title = entries[0].get("title", "Gemini conversation")

        for entry in entries:
            # In Takeout format, the title often contains the user's query
            entry_title = entry.get("title", "")
            timestamp_str = entry.get("time", "")
            timestamp = (
                self.normalize_timestamp(timestamp_str)
                if timestamp_str
                else datetime.now(timezone.utc)
            )

            # Subtitles may contain response info
            subtitles = entry.get("subtitles", [])

            # The title is typically the user's prompt
            if entry_title and entry_title != "Gemini Apps":
                messages.append(
                    Message(
                        role="user",
                        content=entry_title,
                        timestamp=timestamp,
                        metadata={"source_format": "takeout_activity"},
                    )
                )

            # Check for response text in subtitles or details
            for subtitle in subtitles:
                subtitle_name = subtitle.get("name", "")
                if subtitle_name and "From" not in subtitle_name:
                    messages.append(
                        Message(
                            role="assistant",
                            content=subtitle_name,
                            timestamp=timestamp,
                            metadata={"source_format": "takeout_subtitle"},
                        )
                    )

            # Check for detailed response text
            if "details" in entry:
                for detail in entry["details"]:
                    detail_text = detail.get("text", "") or detail.get("content", "")
                    if detail_text:
                        messages.append(
                            Message(
                                role="assistant",
                                content=detail_text,
                                timestamp=timestamp,
                                metadata={"source_format": "takeout_detail"},
                            )
                        )

        if not messages:
            return None

        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp)

        earliest = messages[0].timestamp
        latest = messages[-1].timestamp

        return Conversation(
            id=None,  # Will be auto-generated
            source=self.source_name,
            title=title,
            messages=messages,
            created_at=earliest,
            updated_at=latest,
            tags=["gemini"],
            metadata={"source_format": "google_takeout", "entry_count": len(entries)},
        )

    def _parse_conversation_dict(
        self, data: Dict[str, Any]
    ) -> Optional[Conversation]:
        """Parse a conversation dictionary (custom or web export format)"""
        messages = []

        # Handle different message field names
        message_list = (
            data.get("messages")
            or data.get("turns")
            or data.get("chat_history")
            or []
        )

        for msg_data in message_list:
            msg = self._parse_message(msg_data)
            if msg:
                messages.append(msg)

        if not messages:
            return None

        # Extract metadata
        conv_id = (
            data.get("id")
            or data.get("conversation_id")
            or data.get("chat_id")
        )

        title = (
            data.get("title")
            or data.get("name")
            or self.extract_title(data)
        )

        created_at = self.normalize_timestamp(
            data.get("created_at")
            or data.get("create_time")
            or data.get("time")
            or messages[0].timestamp
        )

        updated_at = self.normalize_timestamp(
            data.get("updated_at")
            or data.get("update_time")
            or messages[-1].timestamp
        )

        return Conversation(
            id=str(conv_id) if conv_id else None,
            source=self.source_name,
            title=title,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            thread_id=str(conv_id) if conv_id else None,
            tags=["gemini"],
            metadata={
                "source_format": "json_export",
                "model": data.get("model", "gemini"),
            },
        )

    def _parse_message(self, msg_data: Any) -> Optional[Message]:
        """Parse a single message from various Gemini export formats"""
        if isinstance(msg_data, str):
            return Message(
                role="user",
                content=msg_data,
                timestamp=datetime.now(timezone.utc),
            )

        if not isinstance(msg_data, dict):
            return None

        # Extract role
        role = (
            msg_data.get("role")
            or msg_data.get("author")
            or msg_data.get("sender")
            or "user"
        ).lower()

        # Normalize Gemini-specific roles
        role_map = {
            "user": "user",
            "human": "user",
            "model": "assistant",
            "gemini": "assistant",
            "bard": "assistant",
            "assistant": "assistant",
            "system": "system",
        }
        role = role_map.get(role, "assistant")

        # Extract content
        content = self._extract_content(msg_data)
        if not content or not content.strip():
            return None

        # Extract timestamp
        timestamp = self.normalize_timestamp(
            msg_data.get("timestamp")
            or msg_data.get("create_time")
            or msg_data.get("time")
            or datetime.now(timezone.utc)
        )

        metadata = {}
        if msg_data.get("model"):
            metadata["model"] = msg_data["model"]
        if msg_data.get("citation_metadata"):
            metadata["citations"] = msg_data["citation_metadata"]

        return Message(
            role=role,
            content=content,
            timestamp=timestamp,
            message_id=msg_data.get("id") or msg_data.get("message_id"),
            metadata=metadata,
        )

    def _extract_content(self, msg_data: Dict[str, Any]) -> str:
        """Extract text content from Gemini message data"""
        # Direct text fields
        content = (
            msg_data.get("content")
            or msg_data.get("text")
            or msg_data.get("message")
            or msg_data.get("body")
        )

        if isinstance(content, str):
            return content

        # Nested parts (Gemini API format: {parts: [{text: "..."}]})
        if isinstance(content, dict):
            return content.get("text", "") or str(content)

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict):
                    text = part.get("text", "")
                    if text:
                        text_parts.append(text)
            return "\n".join(text_parts)

        # Try 'parts' field directly on msg_data
        parts = msg_data.get("parts", [])
        if parts:
            text_parts = []
            for part in parts:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict):
                    text = part.get("text", "")
                    if text:
                        text_parts.append(text)
            return "\n".join(text_parts)

        return ""
