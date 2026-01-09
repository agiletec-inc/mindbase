#!/usr/bin/env python3
"""
Cursor Collector
Collects AI conversations from Cursor IDE
Handles Cursor's specific storage format
"""

import os
import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from .base_collector import BaseCollector, Conversation, Message

logger = logging.getLogger(__name__)


class CursorCollector(BaseCollector):
    """Collector for Cursor AI conversations"""

    def __init__(self):
        super().__init__("cursor")

    def get_data_paths(self) -> List[Path]:
        """Cursor data locations"""
        home = Path.home()
        paths = []

        # macOS paths
        if os.uname().sysname == "Darwin":
            paths.extend(
                [
                    home / "Library/Application Support/Cursor",
                    home / "Library/Application Support/Cursor/User",
                    home / "Library/Application Support/Cursor/User/workspaceStorage",
                    home / "Library/Application Support/Cursor/User/globalStorage",
                    home / "Library/Application Support/Cursor/Cache",
                    home / "Library/Application Support/Cursor/Local Storage",
                ]
            )

        # Linux paths
        paths.extend(
            [
                home / ".config/Cursor",
                home / ".config/Cursor/User",
                home / ".config/Cursor/User/workspaceStorage",
                home / ".config/Cursor/User/globalStorage",
                home / ".config/Cursor/Cache",
                home / ".config/Cursor/Local Storage",
            ]
        )

        # Windows paths
        paths.extend(
            [
                home / "AppData/Roaming/Cursor",
                home / "AppData/Roaming/Cursor/User",
                home / "AppData/Roaming/Cursor/User/workspaceStorage",
                home / "AppData/Roaming/Cursor/User/globalStorage",
                home / "AppData/Roaming/Cursor/Cache",
                home / "AppData/Roaming/Cursor/Local Storage",
            ]
        )

        # Also check for Cursor-specific AI data
        cursor_ai_paths = []
        for base_path in paths:
            if base_path.exists():
                # Look for AI-related subdirectories
                cursor_ai_paths.extend(base_path.glob("**/ai*"))
                cursor_ai_paths.extend(base_path.glob("**/chat*"))
                cursor_ai_paths.extend(base_path.glob("**/conversation*"))
                cursor_ai_paths.extend(base_path.glob("**/*cursor*"))

        paths.extend(cursor_ai_paths)

        return [p for p in paths if p.exists()]

    def collect(self, since_date: Optional[datetime] = None) -> List[Conversation]:
        """Collect Cursor conversations"""
        logger.info(f"Collecting {self.source_name} conversations...")
        all_conversations = []

        for data_path in self.get_data_paths():
            logger.info(f"Checking path: {data_path}")

            # Check workspace storage for AI chat data
            if "workspaceStorage" in str(data_path):
                conversations = self._collect_from_workspace_storage(
                    data_path, since_date
                )
                all_conversations.extend(conversations)

            # Check global storage
            elif "globalStorage" in str(data_path):
                conversations = self._collect_from_global_storage(data_path, since_date)
                all_conversations.extend(conversations)

            # Check Local Storage
            elif "Local Storage" in str(data_path):
                conversations = self._collect_from_local_storage(data_path, since_date)
                all_conversations.extend(conversations)

            # Check Cache
            elif "Cache" in str(data_path):
                conversations = self._collect_from_cache(data_path, since_date)
                all_conversations.extend(conversations)

            # Check for SQLite databases
            db_files = list(data_path.glob("*.db"))
            db_files.extend(list(data_path.glob("*.sqlite")))
            for db_file in db_files:
                conversations = self._collect_from_sqlite(db_file, since_date)
                all_conversations.extend(conversations)

            # Check for JSON files
            json_files = list(data_path.glob("*.json"))
            for json_file in json_files:
                # Look for AI-related JSON files
                if any(
                    keyword in json_file.name.lower()
                    for keyword in ["ai", "chat", "conversation", "cursor", "assistant"]
                ):
                    conversations = self._collect_from_json(json_file, since_date)
                    all_conversations.extend(conversations)

        # Also check Cursor's log files for AI interactions
        conversations = self._collect_from_logs(since_date)
        all_conversations.extend(conversations)

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

    def _collect_from_workspace_storage(
        self, storage_path: Path, since_date: Optional[datetime]
    ) -> List[Conversation]:
        """Collect from workspace storage directories"""
        conversations = []

        # Each workspace has its own directory with a hash name
        workspace_dirs = [d for d in storage_path.iterdir() if d.is_dir()]

        for workspace_dir in workspace_dirs:
            # Look for state.vscdb or state.json files
            state_files = list(workspace_dir.glob("state.vscdb"))
            state_files.extend(list(workspace_dir.glob("state.json")))

            for state_file in state_files:
                if state_file.suffix == ".vscdb":
                    # SQLite database
                    convs = self._collect_from_sqlite(state_file, since_date)
                    conversations.extend(convs)
                elif state_file.suffix == ".json":
                    # JSON file
                    convs = self._collect_from_json(state_file, since_date)
                    conversations.extend(convs)

            # Also check for AI-specific files
            ai_files = list(workspace_dir.glob("**/ai*.json"))
            ai_files.extend(list(workspace_dir.glob("**/chat*.json")))
            ai_files.extend(list(workspace_dir.glob("**/cursor*.json")))

            for ai_file in ai_files:
                convs = self._collect_from_json(ai_file, since_date)
                conversations.extend(convs)

        return conversations

    def _collect_from_global_storage(
        self, storage_path: Path, since_date: Optional[datetime]
    ) -> List[Conversation]:
        """Collect from global storage"""
        conversations = []

        # Look for Cursor AI extension data
        cursor_dirs = list(storage_path.glob("*cursor*"))
        cursor_dirs.extend(list(storage_path.glob("*ai*")))

        for cursor_dir in cursor_dirs:
            if cursor_dir.is_dir():
                # Check for database files
                db_files = list(cursor_dir.glob("*.db"))
                db_files.extend(list(cursor_dir.glob("*.sqlite")))

                for db_file in db_files:
                    convs = self._collect_from_sqlite(db_file, since_date)
                    conversations.extend(convs)

                # Check for JSON files
                json_files = list(cursor_dir.glob("*.json"))
                for json_file in json_files:
                    convs = self._collect_from_json(json_file, since_date)
                    conversations.extend(convs)

        return conversations

    def _collect_from_local_storage(
        self, storage_path: Path, since_date: Optional[datetime]
    ) -> List[Conversation]:
        """Collect from Local Storage"""
        conversations = []

        # Local Storage is typically leveldb or SQLite
        db_files = list(storage_path.glob("*.db"))
        db_files.extend(list(storage_path.glob("*.sqlite")))

        for db_file in db_files:
            convs = self._collect_from_sqlite(db_file, since_date)
            conversations.extend(convs)

        return conversations

    def _collect_from_cache(
        self, cache_path: Path, since_date: Optional[datetime]
    ) -> List[Conversation]:
        """Collect from Cache directory"""
        conversations = []

        # Look for cached AI conversations
        cache_files = list(cache_path.glob("**/ai*.json"))
        cache_files.extend(list(cache_path.glob("**/chat*.json")))
        cache_files.extend(list(cache_path.glob("**/conversation*.json")))

        for cache_file in cache_files:
            convs = self._collect_from_json(cache_file, since_date)
            conversations.extend(convs)

        return conversations

    def _collect_from_sqlite(
        self, db_file: Path, since_date: Optional[datetime]
    ) -> List[Conversation]:
        """Collect from SQLite database"""
        conversations = []

        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            for table_name in tables:
                table_name = table_name[0]

                # Look for AI-related tables
                if any(
                    keyword in table_name.lower()
                    for keyword in [
                        "ai",
                        "chat",
                        "conversation",
                        "cursor",
                        "assistant",
                        "completion",
                    ]
                ):

                    try:
                        cursor.execute(f"SELECT * FROM {table_name}")
                        rows = cursor.fetchall()

                        # Get column names
                        column_names = [desc[0] for desc in cursor.description]

                        for row in rows:
                            row_dict = dict(zip(column_names, row))
                            conv = self._parse_database_row(row_dict)
                            if conv:
                                conversations.append(conv)

                    except Exception as e:
                        logger.debug(f"Error reading table {table_name}: {e}")

            # Also check for key-value tables (Cursor-specific)
            try:
                cursor.execute("SELECT key, value FROM ItemTable")
                rows = cursor.fetchall()

                for key, value in rows:
                    # Cursor Composer data
                    if key == "composer.composerData":
                        try:
                            data = json.loads(value)
                            convs = self._parse_cursor_composer_data(data)
                            conversations.extend(convs)
                        except Exception as e:
                            logger.debug(f"Error parsing composer data: {e}")

                    # Cursor AI service prompts
                    elif key == "aiService.prompts":
                        try:
                            data = json.loads(value)
                            convs = self._parse_ai_service_prompts(data)
                            conversations.extend(convs)
                        except Exception as e:
                            logger.debug(f"Error parsing AI prompts: {e}")

                    # Interactive sessions
                    elif key == "interactive.sessions":
                        try:
                            data = json.loads(value)
                            convs = self._parse_interactive_sessions(data)
                            conversations.extend(convs)
                        except Exception as e:
                            logger.debug(f"Error parsing interactive sessions: {e}")

                    # Generic AI-related keys
                    elif any(
                        keyword in key.lower()
                        for keyword in ["ai", "chat", "conversation", "cursor"]
                    ):
                        try:
                            data = json.loads(value)
                            conv = self._parse_json_conversation(data)
                            if conv:
                                conversations.append(conv)
                        except:
                            pass

            except:
                pass

            conn.close()

        except Exception as e:
            logger.debug(f"Could not read SQLite file {db_file}: {e}")

        return conversations

    def _collect_from_json(
        self, json_file: Path, since_date: Optional[datetime]
    ) -> List[Conversation]:
        """Collect from JSON file"""
        conversations = []

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, list):
                for item in data:
                    conv = self._parse_json_conversation(item)
                    if conv:
                        conversations.append(conv)

            elif isinstance(data, dict):
                # Check for conversation arrays
                for key in ["conversations", "chats", "sessions", "threads"]:
                    if key in data and isinstance(data[key], list):
                        for item in data[key]:
                            conv = self._parse_json_conversation(item)
                            if conv:
                                conversations.append(conv)
                        break
                else:
                    # Single conversation
                    conv = self._parse_json_conversation(data)
                    if conv:
                        conversations.append(conv)

        except Exception as e:
            logger.debug(f"Error reading JSON file {json_file}: {e}")

        return conversations

    def _collect_from_logs(self, since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from Cursor log files"""
        conversations = []

        # Find Cursor log directory
        home = Path.home()
        log_paths = []

        if os.uname().sysname == "Darwin":
            log_paths.append(home / "Library/Logs/Cursor")

        log_paths.append(home / ".cursor/logs")

        for log_path in log_paths:
            if not log_path.exists():
                continue

            log_files = list(log_path.glob("*.log"))

            for log_file in log_files:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    # Parse log entries for AI interactions
                    current_conversation = None
                    current_messages = []

                    for line in lines:
                        # Look for AI request/response patterns
                        if "AI Request:" in line or "User:" in line:
                            # Extract user message
                            content = self._extract_message_from_log(line, "user")
                            if content:
                                timestamp = self._extract_timestamp_from_log(line)
                                msg = Message(
                                    role="user", content=content, timestamp=timestamp
                                )
                                current_messages.append(msg)

                        elif "AI Response:" in line or "Assistant:" in line:
                            # Extract assistant message
                            content = self._extract_message_from_log(line, "assistant")
                            if content:
                                timestamp = self._extract_timestamp_from_log(line)
                                msg = Message(
                                    role="assistant",
                                    content=content,
                                    timestamp=timestamp,
                                )
                                current_messages.append(msg)

                        # Check for conversation boundaries
                        elif "New conversation" in line or "Session start" in line:
                            # Save previous conversation if exists
                            if current_messages:
                                conv = self._create_conversation_from_messages(
                                    current_messages
                                )
                                if conv:
                                    conversations.append(conv)
                            current_messages = []

                    # Save last conversation
                    if current_messages:
                        conv = self._create_conversation_from_messages(current_messages)
                        if conv:
                            conversations.append(conv)

                except Exception as e:
                    logger.debug(f"Error reading log file {log_file}: {e}")

        return conversations

    def _parse_database_row(self, row_dict: Dict[str, Any]) -> Optional[Conversation]:
        """Parse database row into Conversation"""
        try:
            # Look for conversation ID
            conv_id = (
                row_dict.get("id")
                or row_dict.get("conversation_id")
                or row_dict.get("session_id")
            )

            # Extract messages
            messages = []

            # Check for messages field
            if "messages" in row_dict:
                msg_data = row_dict["messages"]
                if isinstance(msg_data, str):
                    try:
                        msg_data = json.loads(msg_data)
                    except:
                        pass

                if isinstance(msg_data, list):
                    for msg in msg_data:
                        parsed_msg = self._parse_message(msg)
                        if parsed_msg:
                            messages.append(parsed_msg)

            # Check for prompt/completion pairs
            elif "prompt" in row_dict and "completion" in row_dict:
                # User message
                user_msg = Message(
                    role="user",
                    content=str(row_dict["prompt"]),
                    timestamp=self.normalize_timestamp(
                        row_dict.get("timestamp", datetime.now(timezone.utc))
                    ),
                )
                messages.append(user_msg)

                # Assistant message
                assistant_msg = Message(
                    role="assistant",
                    content=str(row_dict["completion"]),
                    timestamp=self.normalize_timestamp(
                        row_dict.get("timestamp", datetime.now(timezone.utc))
                    ),
                )
                messages.append(assistant_msg)

            if not messages:
                return None

            # Extract timestamps
            created_at = self.normalize_timestamp(
                row_dict.get("created_at")
                or row_dict.get("timestamp")
                or datetime.now(timezone.utc)
            )

            updated_at = self.normalize_timestamp(
                row_dict.get("updated_at") or created_at
            )

            # Create conversation
            return Conversation(
                id=str(conv_id) if conv_id else None,
                source=self.source_name,
                title=self.extract_title({"messages": messages}),
                messages=messages,
                created_at=created_at,
                updated_at=updated_at,
                metadata={"source_type": "database"},
            )

        except Exception as e:
            logger.debug(f"Error parsing database row: {e}")
            return None

    def _parse_json_conversation(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """Parse JSON data into Conversation"""
        try:
            # Extract messages
            messages = []

            # Check various message field names
            for field in ["messages", "chat", "conversation", "interactions"]:
                if field in data:
                    msg_list = data[field]
                    if isinstance(msg_list, list):
                        for msg in msg_list:
                            parsed_msg = self._parse_message(msg)
                            if parsed_msg:
                                messages.append(parsed_msg)
                        break

            # Check for prompt/response structure
            if not messages and "prompt" in data:
                # User message
                user_msg = Message(
                    role="user",
                    content=str(data["prompt"]),
                    timestamp=self.normalize_timestamp(
                        data.get("timestamp", datetime.now(timezone.utc))
                    ),
                )
                messages.append(user_msg)

                # Assistant message
                if "response" in data or "completion" in data:
                    assistant_msg = Message(
                        role="assistant",
                        content=str(data.get("response") or data.get("completion")),
                        timestamp=self.normalize_timestamp(
                            data.get("timestamp", datetime.now(timezone.utc))
                        ),
                    )
                    messages.append(assistant_msg)

            if not messages:
                return None

            # Extract metadata
            conv_id = data.get("id") or data.get("conversation_id")
            created_at = self.normalize_timestamp(
                data.get("created_at")
                or data.get("timestamp")
                or datetime.now(timezone.utc)
            )

            updated_at = self.normalize_timestamp(data.get("updated_at") or created_at)

            # Extract project/file context
            project = (
                data.get("project") or data.get("workspace") or data.get("file_path")
            )

            return Conversation(
                id=str(conv_id) if conv_id else None,
                source=self.source_name,
                title=data.get("title") or self.extract_title(data),
                messages=messages,
                created_at=created_at,
                updated_at=updated_at,
                project=project,
                metadata={"source_type": "json"},
            )

        except Exception as e:
            logger.debug(f"Error parsing JSON conversation: {e}")
            return None

    def _parse_message(self, msg_data: Any) -> Optional[Message]:
        """Parse message data"""
        try:
            if isinstance(msg_data, str):
                return Message(
                    role="user", content=msg_data, timestamp=datetime.now(timezone.utc)
                )

            elif isinstance(msg_data, dict):
                # Extract role
                role = msg_data.get("role") or msg_data.get("type") or "user"
                role = role.lower()

                # Normalize role
                if role in ["human", "user", "prompt"]:
                    role = "user"
                elif role in ["ai", "assistant", "completion", "response"]:
                    role = "assistant"

                # Extract content
                content = (
                    msg_data.get("content")
                    or msg_data.get("text")
                    or msg_data.get("message")
                    or ""
                )

                if not content:
                    return None

                # Extract timestamp
                timestamp = self.normalize_timestamp(
                    msg_data.get("timestamp")
                    or msg_data.get("created_at")
                    or datetime.now(timezone.utc)
                )

                return Message(
                    role=role,
                    content=str(content),
                    timestamp=timestamp,
                    metadata=msg_data.get("metadata", {}),
                )

        except Exception as e:
            logger.debug(f"Error parsing message: {e}")
            return None

    def _extract_message_from_log(self, line: str, role: str) -> Optional[str]:
        """Extract message content from log line"""
        # Simple extraction - can be improved with regex
        patterns = {
            "user": ["User:", "AI Request:", "Prompt:"],
            "assistant": ["Assistant:", "AI Response:", "Completion:"],
        }

        for pattern in patterns.get(role, []):
            if pattern in line:
                # Extract content after the pattern
                content = line.split(pattern, 1)[1].strip()
                return content if content else None

        return None

    def _extract_timestamp_from_log(self, line: str) -> datetime:
        """Extract timestamp from log line"""
        # Try to find timestamp patterns
        import re

        # ISO format
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        match = re.search(iso_pattern, line)
        if match:
            return self.normalize_timestamp(match.group())

        # Log format [YYYY-MM-DD HH:MM:SS]
        log_pattern = r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]"
        match = re.search(log_pattern, line)
        if match:
            timestamp_str = match.group().strip("[]")
            return self.normalize_timestamp(timestamp_str)

        return datetime.now(timezone.utc)

    def _create_conversation_from_messages(
        self, messages: List[Message]
    ) -> Optional[Conversation]:
        """Create conversation from list of messages"""
        if not messages:
            return None

        # Sort messages by timestamp
        messages.sort(key=lambda m: m.timestamp)

        # Get timestamps
        created_at = messages[0].timestamp
        updated_at = messages[-1].timestamp

        # Generate title from first user message
        title = "Cursor AI Conversation"
        for msg in messages:
            if msg.role == "user":
                title = msg.content[:100] + ("..." if len(msg.content) > 100 else "")
                break

        return Conversation(
            id=None,  # Will be auto-generated
            source=self.source_name,
            title=title,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            metadata={"source_type": "logs"},
        )

    def _parse_cursor_composer_data(self, data: Dict[str, Any]) -> List[Conversation]:
        """Parse Cursor Composer data structure"""
        conversations = []

        try:
            # Composer data structure: {"allComposers": [...], "selectedComposerIds": [...]}
            composers = data.get("allComposers", [])

            for composer in composers:
                # Extract composer metadata
                composer_id = composer.get("composerId")
                created_at_ms = composer.get(
                    "createdAt"
                )  # Unix timestamp in milliseconds
                mode = composer.get("unifiedMode", "unknown")

                if not composer_id or not created_at_ms:
                    continue

                # Convert timestamp
                created_at = self.normalize_timestamp(
                    created_at_ms / 1000
                )  # ms to seconds

                # Create placeholder conversation (actual messages would need additional fetching)
                # For now, we create a stub that can be enriched later
                conv = Conversation(
                    id=f"cursor_composer_{composer_id}",
                    source=self.source_name,
                    title=f"Cursor Composer Session ({mode})",
                    messages=[],  # Would need to fetch actual messages
                    created_at=created_at,
                    updated_at=created_at,
                    metadata={
                        "composer_id": composer_id,
                        "mode": mode,
                        "force_mode": composer.get("forceMode"),
                        "has_unread": composer.get("hasUnreadMessages", False),
                    },
                )

                # Only add if we have messages (TODO: implement message fetching)
                # For now, skip empty conversations
                if conv.messages:
                    conversations.append(conv)

        except Exception as e:
            logger.debug(f"Error parsing Cursor composer data: {e}")

        return conversations

    def _parse_ai_service_prompts(self, data: Dict[str, Any]) -> List[Conversation]:
        """Parse Cursor AI Service prompts"""
        conversations = []

        try:
            # AI service prompts structure varies
            # Typically contains prompt-completion pairs
            if isinstance(data, list):
                prompts = data
            elif isinstance(data, dict) and "prompts" in data:
                prompts = data["prompts"]
            else:
                prompts = []

            for prompt_data in prompts:
                messages = []

                # User prompt
                if "prompt" in prompt_data:
                    user_msg = Message(
                        role="user",
                        content=str(prompt_data["prompt"]),
                        timestamp=self.normalize_timestamp(
                            prompt_data.get("timestamp", datetime.now(timezone.utc))
                        ),
                    )
                    messages.append(user_msg)

                # Assistant response
                if "completion" in prompt_data or "response" in prompt_data:
                    assistant_msg = Message(
                        role="assistant",
                        content=str(
                            prompt_data.get("completion") or prompt_data.get("response")
                        ),
                        timestamp=self.normalize_timestamp(
                            prompt_data.get("timestamp", datetime.now(timezone.utc))
                        ),
                    )
                    messages.append(assistant_msg)

                if messages:
                    conv = self._create_conversation_from_messages(messages)
                    if conv:
                        conversations.append(conv)

        except Exception as e:
            logger.debug(f"Error parsing AI service prompts: {e}")

        return conversations

    def _parse_interactive_sessions(self, data: Dict[str, Any]) -> List[Conversation]:
        """Parse Cursor interactive sessions"""
        conversations = []

        try:
            # Interactive sessions structure
            if isinstance(data, list):
                sessions = data
            elif isinstance(data, dict) and "sessions" in data:
                sessions = data["sessions"]
            else:
                sessions = []

            for session in sessions:
                messages = []

                # Extract session messages
                if "messages" in session:
                    for msg_data in session["messages"]:
                        msg = self._parse_message(msg_data)
                        if msg:
                            messages.append(msg)

                if messages:
                    session_id = session.get("id")
                    created_at = self.normalize_timestamp(
                        session.get("createdAt", datetime.now(timezone.utc))
                    )

                    conv = Conversation(
                        id=f"cursor_session_{session_id}" if session_id else None,
                        source=self.source_name,
                        title=session.get("title")
                        or self.extract_title({"messages": messages}),
                        messages=messages,
                        created_at=created_at,
                        updated_at=self.normalize_timestamp(
                            session.get("updatedAt", created_at)
                        ),
                        metadata={
                            "session_id": session_id,
                            "session_type": "interactive",
                        },
                    )
                    conversations.append(conv)

        except Exception as e:
            logger.debug(f"Error parsing interactive sessions: {e}")

        return conversations
