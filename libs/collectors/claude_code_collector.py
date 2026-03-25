#!/usr/bin/env python3
"""
Claude Code Collector
Collects conversations from Claude Code CLI application
Data source: ~/.claude/projects/*/*.jsonl (JSON Lines format)

Each JSONL file represents a single session. Lines have a 'type' field:
  - 'user': user message (role=user in message.content)
  - 'assistant': assistant response (role=assistant in message.content)
  - 'system': system prompt injection
  - 'progress': progress indicator (skip)
  - 'file-history-snapshot': file state snapshot (skip)

Key fields per line:
  - sessionId: unique session ID (matches filename)
  - uuid: unique message ID
  - parentUuid: parent message for threading
  - timestamp: ISO 8601 timestamp
  - message.role: 'user' | 'assistant'
  - message.content: list of content blocks or string
  - cwd: working directory at time of message
  - gitBranch: active git branch
  - slug: human-readable session slug
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from .base_collector import BaseCollector, Conversation, Message

logger = logging.getLogger(__name__)

# Message types that contain actual conversation content
CONTENT_TYPES = {"user", "assistant"}
# Message types to skip entirely
SKIP_TYPES = {"file-history-snapshot", "progress"}


class ClaudeCodeCollector(BaseCollector):
    """Collector for Claude Code CLI conversations (JSONL format)"""

    def __init__(self):
        super().__init__("claude-code")

    def get_data_paths(self) -> List[Path]:
        """Claude Code project data locations: ~/.claude/projects/*/"""
        claude_dir = Path.home() / ".claude" / "projects"
        if not claude_dir.exists():
            logger.warning(f"Claude Code projects directory not found: {claude_dir}")
            return []

        paths = []
        for project_dir in claude_dir.iterdir():
            if project_dir.is_dir():
                jsonl_files = list(project_dir.glob("*.jsonl"))
                if jsonl_files:
                    paths.append(project_dir)

        logger.info(f"Found {len(paths)} Claude Code project directories")
        return paths

    def collect(self, since_date: Optional[datetime] = None) -> List[Conversation]:
        """Collect Claude Code conversations from all project directories"""
        logger.info(f"Collecting {self.source_name} conversations...")
        all_conversations = []

        for project_dir in self.get_data_paths():
            project_name = self._extract_project_name(project_dir.name)
            jsonl_files = sorted(project_dir.glob("*.jsonl"))

            for jsonl_file in jsonl_files:
                try:
                    conv = self._parse_session_file(jsonl_file, project_name)
                    if conv and self.validate_conversation(conv):
                        all_conversations.append(conv)
                except Exception as e:
                    logger.warning(f"Error parsing {jsonl_file}: {e}")
                    self.stats["errors"] += 1

        # Deduplicate and filter by date
        all_conversations = self.deduplicate_conversations(all_conversations)
        all_conversations = self.filter_by_date(all_conversations, since_date)

        # Update stats
        self.update_stats(all_conversations)
        self.conversations = all_conversations

        logger.info(
            f"Collected {len(all_conversations)} conversations from {self.source_name}"
        )
        return all_conversations

    def _extract_project_name(self, dir_name: str) -> str:
        """
        Extract human-readable project name from directory name.
        Directory names are path-encoded: '-Users-kazuki-github-org-repo'
        → extract last meaningful segment(s) as project name.
        """
        # Split by '-' and filter out common path segments
        parts = dir_name.split("-")
        # Remove empty strings and common prefixes
        skip_segments = {"", "Users", "home"}
        meaningful = [p for p in parts if p not in skip_segments]

        if len(meaningful) >= 2:
            # Return last 2 segments (typically org/repo or parent/project)
            return "/".join(meaningful[-2:])
        elif meaningful:
            return meaningful[-1]
        return dir_name

    def _parse_session_file(
        self, jsonl_file: Path, project_name: str
    ) -> Optional[Conversation]:
        """Parse a single JSONL session file into a Conversation"""
        session_id = jsonl_file.stem
        messages: List[Message] = []
        session_metadata = {}
        earliest_timestamp = None
        latest_timestamp = None

        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug(f"Invalid JSON at {jsonl_file}:{line_num}")
                    continue

                entry_type = entry.get("type")

                # Skip non-content types
                if entry_type in SKIP_TYPES or entry_type not in CONTENT_TYPES:
                    # Capture metadata from system entries
                    if entry_type == "system" and not session_metadata:
                        session_metadata = self._extract_session_metadata(entry)
                    continue

                # Parse the message
                msg = self._parse_entry(entry)
                if msg:
                    messages.append(msg)

                    # Track timestamps
                    if earliest_timestamp is None or msg.timestamp < earliest_timestamp:
                        earliest_timestamp = msg.timestamp
                    if latest_timestamp is None or msg.timestamp > latest_timestamp:
                        latest_timestamp = msg.timestamp

                # Capture metadata from first content entry
                if not session_metadata:
                    session_metadata = self._extract_session_metadata(entry)

        if not messages:
            return None

        # Use file modification time as fallback
        if not earliest_timestamp:
            file_mtime = datetime.fromtimestamp(
                jsonl_file.stat().st_mtime, tz=timezone.utc
            )
            earliest_timestamp = file_mtime
            latest_timestamp = file_mtime

        # Generate title from first user message
        title = self._generate_title(messages)

        return Conversation(
            id=f"claude-code:{session_id}",
            source=self.source_name,
            title=title,
            messages=messages,
            created_at=earliest_timestamp,
            updated_at=latest_timestamp,
            thread_id=session_id,
            project=project_name,
            workspace=session_metadata.get("cwd"),
            tags=self._extract_tags(session_metadata),
            metadata={
                "session_id": session_id,
                "slug": session_metadata.get("slug"),
                "git_branch": session_metadata.get("gitBranch"),
                "version": session_metadata.get("version"),
                "cwd": session_metadata.get("cwd"),
            },
        )

    def _parse_entry(self, entry: dict) -> Optional[Message]:
        """Parse a single JSONL entry into a Message"""
        message_data = entry.get("message")
        if not message_data:
            return None

        role = message_data.get("role")
        if role not in ("user", "assistant"):
            return None

        # Extract text content from content blocks
        content = self._extract_content(message_data.get("content", ""))
        if not content or not content.strip():
            return None

        # Parse timestamp
        timestamp_str = entry.get("timestamp")
        timestamp = (
            self.normalize_timestamp(timestamp_str)
            if timestamp_str
            else datetime.now(timezone.utc)
        )

        # Build metadata
        metadata = {}
        if message_data.get("model"):
            metadata["model"] = message_data["model"]
        if message_data.get("id"):
            metadata["api_message_id"] = message_data["id"]
        if entry.get("toolUseResult"):
            metadata["tool_use_result"] = entry["toolUseResult"]

        return Message(
            role=role,
            content=content,
            timestamp=timestamp,
            message_id=entry.get("uuid"),
            parent_id=entry.get("parentUuid"),
            metadata=metadata,
        )

    def _extract_content(self, content) -> str:
        """
        Extract text content from Claude Code message content.
        Content can be a string or a list of content blocks.
        """
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict):
                    block_type = block.get("type")

                    if block_type == "text":
                        text_parts.append(block.get("text", ""))

                    elif block_type == "tool_use":
                        # Summarize tool usage
                        tool_name = block.get("name", "unknown")
                        tool_input = block.get("input", {})
                        # Compact representation of tool call
                        summary = f"[Tool: {tool_name}]"
                        if isinstance(tool_input, dict):
                            # Include key params for context
                            if "file_path" in tool_input:
                                summary += f" {tool_input['file_path']}"
                            elif "command" in tool_input:
                                cmd = str(tool_input["command"])[:100]
                                summary += f" $ {cmd}"
                            elif "pattern" in tool_input:
                                summary += f" pattern={tool_input['pattern']}"
                        text_parts.append(summary)

                    elif block_type == "tool_result":
                        # Include tool results for context
                        result_content = block.get("content", "")
                        if isinstance(result_content, str) and result_content:
                            # Truncate long results
                            truncated = result_content[:500]
                            if len(result_content) > 500:
                                truncated += "..."
                            text_parts.append(f"[Result: {truncated}]")

                    elif block_type == "thinking":
                        # Skip thinking blocks (internal reasoning)
                        pass

            return "\n".join(text_parts)

        return str(content)

    def _extract_session_metadata(self, entry: dict) -> dict:
        """Extract session-level metadata from a JSONL entry"""
        return {
            "sessionId": entry.get("sessionId"),
            "cwd": entry.get("cwd"),
            "gitBranch": entry.get("gitBranch"),
            "slug": entry.get("slug"),
            "version": entry.get("version"),
        }

    def _extract_tags(self, metadata: dict) -> List[str]:
        """Extract tags from session metadata"""
        tags = ["claude-code"]
        if metadata.get("gitBranch"):
            tags.append(f"branch:{metadata['gitBranch']}")
        return tags

    def _generate_title(self, messages: List[Message]) -> str:
        """Generate conversation title from first user message"""
        for msg in messages:
            if msg.role == "user":
                # Skip tool result messages
                if msg.content.startswith("[Result:") or msg.content.startswith(
                    "[Tool:"
                ):
                    continue
                title = msg.content[:100]
                if len(msg.content) > 100:
                    title += "..."
                return title

        return "Claude Code session"
