#!/usr/bin/env python3
"""
Windsurf Collector
Collects AI conversations from Windsurf IDE (Codeium-powered)
Handles Windsurf's Cascade chat system
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

class WindsurfCollector(BaseCollector):
    """Collector for Windsurf AI conversations (Cascade)"""

    def __init__(self):
        super().__init__("windsurf")

    def get_data_paths(self) -> List[Path]:
        """Windsurf data locations"""
        home = Path.home()
        paths = []

        # macOS paths
        if os.uname().sysname == "Darwin":
            paths.extend([
                home / "Library/Application Support/Windsurf",
                home / "Library/Application Support/Windsurf/User",
                home / "Library/Application Support/Windsurf/User/workspaceStorage",
                home / "Library/Application Support/Windsurf/User/globalStorage",
                home / "Library/Application Support/Windsurf/Cache",
                home / "Library/Application Support/Windsurf/Local Storage",
            ])

        # Linux paths
        paths.extend([
            home / ".config/Windsurf",
            home / ".config/Windsurf/User",
            home / ".config/Windsurf/User/workspaceStorage",
            home / ".config/Windsurf/User/globalStorage",
            home / ".cache/Windsurf",
        ])

        # Windows paths
        paths.extend([
            home / "AppData/Roaming/Windsurf",
            home / "AppData/Roaming/Windsurf/User",
            home / "AppData/Roaming/Windsurf/User/workspaceStorage",
            home / "AppData/Roaming/Windsurf/User/globalStorage",
        ])

        return [p for p in paths if p.exists()]

    def collect(self, since_date: Optional[datetime] = None) -> List[Conversation]:
        """Collect Windsurf conversations"""
        logger.info(f"Collecting {self.source_name} conversations...")
        all_conversations = []

        for data_path in self.get_data_paths():
            logger.info(f"Checking path: {data_path}")

            # Check workspace storage for Cascade chat data
            if "workspaceStorage" in str(data_path):
                conversations = self._collect_from_workspace_storage(data_path, since_date)
                all_conversations.extend(conversations)

            # Check global storage
            elif "globalStorage" in str(data_path):
                conversations = self._collect_from_global_storage(data_path, since_date)
                all_conversations.extend(conversations)

        # Deduplicate and filter
        all_conversations = self.deduplicate_conversations(all_conversations)
        all_conversations = self.filter_by_date(all_conversations, since_date)

        # Update stats
        self.update_stats(all_conversations)
        self.conversations = all_conversations

        logger.info(f"Collected {len(all_conversations)} conversations from {self.source_name}")
        return all_conversations

    def _collect_from_workspace_storage(self, storage_path: Path,
                                       since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from workspace storage directories"""
        conversations = []

        # Each workspace has its own directory with a hash name
        workspace_dirs = [d for d in storage_path.iterdir() if d.is_dir()]

        for workspace_dir in workspace_dirs:
            # Look for state.vscdb files
            state_files = list(workspace_dir.glob("state.vscdb"))

            for state_file in state_files:
                convs = self._collect_from_sqlite(state_file, since_date)
                conversations.extend(convs)

        return conversations

    def _collect_from_global_storage(self, storage_path: Path,
                                    since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from global storage"""
        conversations = []

        # Look for Windsurf/Cascade-specific directories
        cascade_dirs = list(storage_path.glob("*windsurf*"))
        cascade_dirs.extend(list(storage_path.glob("*cascade*")))
        cascade_dirs.extend(list(storage_path.glob("*codeium*")))

        for cascade_dir in cascade_dirs:
            if cascade_dir.is_dir():
                # Check for database files
                db_files = list(cascade_dir.glob("*.db"))
                db_files.extend(list(cascade_dir.glob("*.sqlite")))

                for db_file in db_files:
                    convs = self._collect_from_sqlite(db_file, since_date)
                    conversations.extend(convs)

                # Check for JSON files
                json_files = list(cascade_dir.glob("*.json"))
                for json_file in json_files:
                    convs = self._collect_from_json(json_file, since_date)
                    conversations.extend(convs)

        return conversations

    def _collect_from_sqlite(self, db_file: Path,
                           since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from SQLite database"""
        conversations = []

        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # Check for ItemTable (VSCode-style storage)
            try:
                cursor.execute("SELECT key, value FROM ItemTable")
                rows = cursor.fetchall()

                for key, value in rows:
                    # Windsurf Cascade chat session store
                    if key == 'chat.ChatSessionStore.index':
                        try:
                            data = json.loads(value)
                            convs = self._parse_cascade_chat_sessions(data)
                            conversations.extend(convs)
                        except Exception as e:
                            logger.debug(f"Error parsing chat session store: {e}")

                    # Windsurf Cascade view state
                    elif 'windsurf.cascadeViewContainerId' in key:
                        try:
                            data = json.loads(value)
                            convs = self._parse_cascade_view_state(data)
                            conversations.extend(convs)
                        except Exception as e:
                            logger.debug(f"Error parsing cascade view state: {e}")

                    # Generic AI-related keys
                    elif any(keyword in key.lower() for keyword in
                          ['cascade', 'chat', 'conversation', 'ai', 'codeium']):
                        try:
                            data = json.loads(value)
                            conv = self._parse_json_conversation(data)
                            if conv:
                                conversations.append(conv)
                        except:
                            pass

            except Exception as e:
                logger.debug(f"ItemTable not found or error: {e}")

            conn.close()

        except Exception as e:
            logger.debug(f"Could not read SQLite file {db_file}: {e}")

        return conversations

    def _collect_from_json(self, json_file: Path,
                         since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from JSON file"""
        conversations = []

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, list):
                for item in data:
                    conv = self._parse_json_conversation(item)
                    if conv:
                        conversations.append(conv)

            elif isinstance(data, dict):
                # Check for conversation arrays
                for key in ['conversations', 'sessions', 'chats', 'entries']:
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

    def _parse_cascade_chat_sessions(self, data: Dict[str, Any]) -> List[Conversation]:
        """Parse Windsurf Cascade chat sessions"""
        conversations = []

        try:
            # ChatSessionStore structure: {"version": 1, "entries": {...}}
            entries = data.get('entries', {})

            for session_id, session_data in entries.items():
                messages = []

                # Extract messages from session
                if 'messages' in session_data:
                    for msg_data in session_data['messages']:
                        msg = self._parse_message(msg_data)
                        if msg:
                            messages.append(msg)

                if messages:
                    created_at = self.normalize_timestamp(
                        session_data.get('createdAt', datetime.now(timezone.utc))
                    )

                    conv = Conversation(
                        id=f"windsurf_cascade_{session_id}",
                        source=self.source_name,
                        title=session_data.get('title') or self.extract_title({'messages': messages}),
                        messages=messages,
                        created_at=created_at,
                        updated_at=self.normalize_timestamp(
                            session_data.get('updatedAt', created_at)
                        ),
                        metadata={
                            'session_id': session_id,
                            'session_type': 'cascade_chat'
                        }
                    )
                    conversations.append(conv)

        except Exception as e:
            logger.debug(f"Error parsing Cascade chat sessions: {e}")

        return conversations

    def _parse_cascade_view_state(self, data: Dict[str, Any]) -> List[Conversation]:
        """Parse Windsurf Cascade view state"""
        conversations = []

        try:
            # View state might contain active chat data
            if 'activeChatId' in data and 'chats' in data:
                chats = data.get('chats', [])

                for chat_data in chats:
                    messages = []

                    if 'messages' in chat_data:
                        for msg_data in chat_data['messages']:
                            msg = self._parse_message(msg_data)
                            if msg:
                                messages.append(msg)

                    if messages:
                        chat_id = chat_data.get('id')
                        created_at = self.normalize_timestamp(
                            chat_data.get('timestamp', datetime.now(timezone.utc))
                        )

                        conv = Conversation(
                            id=f"windsurf_view_{chat_id}" if chat_id else None,
                            source=self.source_name,
                            title=chat_data.get('title') or self.extract_title({'messages': messages}),
                            messages=messages,
                            created_at=created_at,
                            updated_at=created_at,
                            metadata={'chat_id': chat_id, 'session_type': 'cascade_view'}
                        )
                        conversations.append(conv)

        except Exception as e:
            logger.debug(f"Error parsing Cascade view state: {e}")

        return conversations

    def _parse_json_conversation(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """Parse JSON data into Conversation"""
        try:
            # Extract messages
            messages = []

            # Check various message field names
            for field in ['messages', 'chat', 'conversation', 'interactions']:
                if field in data:
                    msg_list = data[field]
                    if isinstance(msg_list, list):
                        for msg in msg_list:
                            parsed_msg = self._parse_message(msg)
                            if parsed_msg:
                                messages.append(parsed_msg)
                        break

            # Check for prompt/response structure
            if not messages and 'prompt' in data:
                # User message
                user_msg = Message(
                    role='user',
                    content=str(data['prompt']),
                    timestamp=self.normalize_timestamp(
                        data.get('timestamp', datetime.now(timezone.utc))
                    )
                )
                messages.append(user_msg)

                # Assistant message
                if 'response' in data or 'completion' in data:
                    assistant_msg = Message(
                        role='assistant',
                        content=str(data.get('response') or data.get('completion')),
                        timestamp=self.normalize_timestamp(
                            data.get('timestamp', datetime.now(timezone.utc))
                        )
                    )
                    messages.append(assistant_msg)

            if not messages:
                return None

            # Extract metadata
            conv_id = data.get('id') or data.get('session_id')
            created_at = self.normalize_timestamp(
                data.get('createdAt') or
                data.get('created_at') or
                data.get('timestamp') or
                datetime.now(timezone.utc)
            )

            updated_at = self.normalize_timestamp(
                data.get('updatedAt') or
                data.get('updated_at') or
                created_at
            )

            # Extract project/file context
            project = (data.get('project') or
                      data.get('workspace') or
                      data.get('file_path'))

            return Conversation(
                id=str(conv_id) if conv_id else None,
                source=self.source_name,
                title=data.get('title') or self.extract_title(data),
                messages=messages,
                created_at=created_at,
                updated_at=updated_at,
                project=project,
                metadata={'source_type': 'json'}
            )

        except Exception as e:
            logger.debug(f"Error parsing JSON conversation: {e}")
            return None

    def _parse_message(self, msg_data: Any) -> Optional[Message]:
        """Parse message data"""
        try:
            if isinstance(msg_data, str):
                return Message(
                    role='user',
                    content=msg_data,
                    timestamp=datetime.now(timezone.utc)
                )

            elif isinstance(msg_data, dict):
                # Extract role
                role = msg_data.get('role') or msg_data.get('type') or 'user'
                role = role.lower()

                # Normalize role
                if role in ['human', 'user', 'prompt']:
                    role = 'user'
                elif role in ['ai', 'assistant', 'cascade', 'codeium', 'completion']:
                    role = 'assistant'

                # Extract content
                content = (msg_data.get('content') or
                          msg_data.get('text') or
                          msg_data.get('message') or
                          '')

                if not content:
                    return None

                # Extract timestamp
                timestamp = self.normalize_timestamp(
                    msg_data.get('timestamp') or
                    msg_data.get('createdAt') or
                    msg_data.get('created_at') or
                    datetime.now(timezone.utc)
                )

                return Message(
                    role=role,
                    content=str(content),
                    timestamp=timestamp,
                    metadata=msg_data.get('metadata', {})
                )

        except Exception as e:
            logger.debug(f"Error parsing message: {e}")
            return None
