#!/usr/bin/env python3
"""
Claude Desktop Collector
Collects conversations from Claude Desktop application
Handles LevelDB Session Storage and IndexedDB
"""

import os
import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import struct

from base_collector import BaseCollector, Conversation, Message

logger = logging.getLogger(__name__)

class ClaudeDesktopCollector(BaseCollector):
    """Collector for Claude Desktop conversations"""
    
    def __init__(self):
        super().__init__("claude-desktop")
        
    def get_data_paths(self) -> List[Path]:
        """Claude Desktop data locations"""
        home = Path.home()
        paths = []
        
        # macOS paths
        if os.uname().sysname == "Darwin":
            paths.extend([
                home / "Library/Application Support/Claude",
                home / "Library/Application Support/Claude/Session Storage",
                home / "Library/Application Support/Claude/IndexedDB",
                home / "Library/Application Support/Claude/Local Storage",
            ])
        
        # Linux paths
        paths.extend([
            home / ".config/Claude",
            home / ".config/Claude/Session Storage",
            home / ".config/Claude/IndexedDB",
            home / ".config/Claude/Local Storage",
        ])
        
        # Windows paths
        paths.extend([
            home / "AppData/Roaming/Claude",
            home / "AppData/Roaming/Claude/Session Storage",
            home / "AppData/Roaming/Claude/IndexedDB",
            home / "AppData/Roaming/Claude/Local Storage",
        ])
        
        return [p for p in paths if p.exists()]
    
    def collect(self, since_date: Optional[datetime] = None) -> List[Conversation]:
        """Collect Claude Desktop conversations"""
        logger.info(f"Collecting {self.source_name} conversations...")
        all_conversations = []
        
        for data_path in self.get_data_paths():
            logger.info(f"Checking path: {data_path}")
            
            # Try different storage types
            if "Session Storage" in str(data_path):
                conversations = self._collect_from_session_storage(data_path, since_date)
                all_conversations.extend(conversations)
            
            elif "IndexedDB" in str(data_path):
                conversations = self._collect_from_indexeddb(data_path, since_date)
                all_conversations.extend(conversations)
            
            elif "Local Storage" in str(data_path):
                conversations = self._collect_from_local_storage(data_path, since_date)
                all_conversations.extend(conversations)
            
            # Also check for JSON export files
            json_files = list(data_path.glob("*.json"))
            for json_file in json_files:
                if "conversation" in json_file.name.lower() or "chat" in json_file.name.lower():
                    conversations = self._collect_from_json_export(json_file, since_date)
                    all_conversations.extend(conversations)
        
        # Deduplicate and filter
        all_conversations = self.deduplicate_conversations(all_conversations)
        all_conversations = self.filter_by_date(all_conversations, since_date)
        
        # Update stats
        self.update_stats(all_conversations)
        self.conversations = all_conversations
        
        logger.info(f"Collected {len(all_conversations)} conversations from {self.source_name}")
        return all_conversations
    
    def _collect_from_session_storage(self, storage_path: Path, 
                                     since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from LevelDB Session Storage"""
        conversations = []
        
        try:
            # LevelDB is complex to parse directly, try alternative approaches
            # Look for LOG files that might contain conversation data
            log_files = list(storage_path.glob("*.log"))
            log_files.extend(list(storage_path.glob("LOG*")))
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Parse any JSON-like structures in the log
                        conversations.extend(self._extract_conversations_from_text(content))
                except Exception as e:
                    logger.debug(f"Could not read log file {log_file}: {e}")
            
            # Try to read .ldb files as text (sometimes contains JSON)
            ldb_files = list(storage_path.glob("*.ldb"))
            for ldb_file in ldb_files:
                try:
                    with open(ldb_file, 'rb') as f:
                        content = f.read()
                        # Try to extract JSON from binary data
                        text_content = self._extract_text_from_binary(content)
                        conversations.extend(self._extract_conversations_from_text(text_content))
                except Exception as e:
                    logger.debug(f"Could not read LDB file {ldb_file}: {e}")
            
        except Exception as e:
            logger.warning(f"Error reading Session Storage: {e}")
        
        return conversations
    
    def _collect_from_indexeddb(self, indexeddb_path: Path, 
                               since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from IndexedDB"""
        conversations = []
        
        # IndexedDB files are usually SQLite databases
        db_files = list(indexeddb_path.glob("*.db"))
        db_files.extend(list(indexeddb_path.glob("*.sqlite")))
        db_files.extend(list(indexeddb_path.glob("*.sqlite3")))
        
        for db_file in db_files:
            try:
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table_name in tables:
                    table_name = table_name[0]
                    
                    # Look for conversation-related tables
                    if any(keyword in table_name.lower() for keyword in 
                          ['conversation', 'chat', 'message', 'thread', 'session']):
                        
                        try:
                            cursor.execute(f"SELECT * FROM {table_name}")
                            rows = cursor.fetchall()
                            
                            # Get column names
                            column_names = [desc[0] for desc in cursor.description]
                            
                            for row in rows:
                                row_dict = dict(zip(column_names, row))
                                conv = self._parse_indexeddb_row(row_dict)
                                if conv:
                                    conversations.append(conv)
                        
                        except Exception as e:
                            logger.debug(f"Error reading table {table_name}: {e}")
                
                conn.close()
                
            except Exception as e:
                logger.debug(f"Could not read IndexedDB file {db_file}: {e}")
        
        return conversations
    
    def _collect_from_local_storage(self, storage_path: Path, 
                                   since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from Local Storage (usually SQLite)"""
        conversations = []
        
        # Local Storage is typically in a SQLite database
        db_files = list(storage_path.glob("*.db"))
        db_files.extend(list(storage_path.glob("*.sqlite")))
        
        for db_file in db_files:
            try:
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                
                # Local Storage typically has a simple key-value structure
                try:
                    cursor.execute("SELECT key, value FROM ItemTable")
                    rows = cursor.fetchall()
                    
                    for key, value in rows:
                        # Look for conversation data
                        if any(keyword in key.lower() for keyword in 
                              ['conversation', 'chat', 'message', 'thread']):
                            
                            try:
                                data = json.loads(value)
                                conv = self._parse_json_conversation(data)
                                if conv:
                                    conversations.append(conv)
                            except:
                                pass
                
                except Exception as e:
                    logger.debug(f"Could not read ItemTable: {e}")
                
                conn.close()
                
            except Exception as e:
                logger.debug(f"Could not read Local Storage file {db_file}: {e}")
        
        return conversations
    
    def _collect_from_json_export(self, json_file: Path, 
                                 since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from JSON export files"""
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
                if 'conversations' in data:
                    for item in data['conversations']:
                        conv = self._parse_json_conversation(item)
                        if conv:
                            conversations.append(conv)
                else:
                    # Single conversation
                    conv = self._parse_json_conversation(data)
                    if conv:
                        conversations.append(conv)
        
        except Exception as e:
            logger.warning(f"Error reading JSON file {json_file}: {e}")
        
        return conversations
    
    def _extract_text_from_binary(self, binary_data: bytes) -> str:
        """Extract readable text from binary data"""
        # Simple extraction of ASCII/UTF-8 strings
        text_parts = []
        current_string = []
        
        for byte in binary_data:
            if 32 <= byte <= 126:  # Printable ASCII
                current_string.append(chr(byte))
            else:
                if len(current_string) > 10:  # Minimum string length
                    text_parts.append(''.join(current_string))
                current_string = []
        
        if current_string:
            text_parts.append(''.join(current_string))
        
        return ' '.join(text_parts)
    
    def _extract_conversations_from_text(self, text: str) -> List[Conversation]:
        """Extract conversation data from text content"""
        conversations = []
        
        # Look for JSON-like structures
        import re
        
        # Find JSON objects
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                data = json.loads(match)
                
                # Check if this looks like conversation data
                if any(key in data for key in ['messages', 'conversation', 'chat', 'thread']):
                    conv = self._parse_json_conversation(data)
                    if conv:
                        conversations.append(conv)
            
            except:
                pass
        
        return conversations
    
    def _parse_indexeddb_row(self, row_dict: Dict[str, Any]) -> Optional[Conversation]:
        """Parse a row from IndexedDB into a Conversation"""
        try:
            # Look for conversation ID
            conv_id = (row_dict.get('id') or 
                      row_dict.get('conversation_id') or 
                      row_dict.get('thread_id') or
                      row_dict.get('uuid'))
            
            if not conv_id:
                return None
            
            # Extract messages
            messages = []
            
            # Messages might be stored as JSON in a column
            for key in ['messages', 'content', 'data', 'value']:
                if key in row_dict and row_dict[key]:
                    try:
                        if isinstance(row_dict[key], str):
                            msg_data = json.loads(row_dict[key])
                        else:
                            msg_data = row_dict[key]
                        
                        if isinstance(msg_data, list):
                            for msg in msg_data:
                                parsed_msg = self._parse_message(msg)
                                if parsed_msg:
                                    messages.append(parsed_msg)
                        elif isinstance(msg_data, dict):
                            parsed_msg = self._parse_message(msg_data)
                            if parsed_msg:
                                messages.append(parsed_msg)
                    
                    except:
                        pass
            
            if not messages:
                return None
            
            # Extract timestamps
            created_at = self.normalize_timestamp(
                row_dict.get('created_at') or 
                row_dict.get('created') or
                row_dict.get('timestamp') or
                datetime.now(timezone.utc)
            )
            
            updated_at = self.normalize_timestamp(
                row_dict.get('updated_at') or 
                row_dict.get('modified') or
                created_at
            )
            
            # Extract title
            title = (row_dict.get('title') or 
                    row_dict.get('name') or
                    self.extract_title({'messages': messages}))
            
            return Conversation(
                id=str(conv_id),
                source=self.source_name,
                title=title,
                messages=messages,
                created_at=created_at,
                updated_at=updated_at,
                thread_id=str(conv_id),
                metadata={'raw_data': row_dict}
            )
        
        except Exception as e:
            logger.debug(f"Error parsing IndexedDB row: {e}")
            return None
    
    def _parse_json_conversation(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """Parse JSON data into a Conversation"""
        try:
            # Extract conversation ID
            conv_id = (data.get('id') or 
                      data.get('conversation_id') or
                      data.get('uuid') or
                      data.get('thread_id'))
            
            # Extract messages
            messages = []
            
            if 'messages' in data:
                msg_list = data['messages']
                if isinstance(msg_list, list):
                    for msg in msg_list:
                        parsed_msg = self._parse_message(msg)
                        if parsed_msg:
                            messages.append(parsed_msg)
            
            # Alternative message structures
            elif 'chat' in data and isinstance(data['chat'], list):
                for msg in data['chat']:
                    parsed_msg = self._parse_message(msg)
                    if parsed_msg:
                        messages.append(parsed_msg)
            
            elif 'conversation' in data and isinstance(data['conversation'], dict):
                if 'messages' in data['conversation']:
                    for msg in data['conversation']['messages']:
                        parsed_msg = self._parse_message(msg)
                        if parsed_msg:
                            messages.append(parsed_msg)
            
            if not messages:
                return None
            
            # Extract timestamps
            created_at = self.normalize_timestamp(
                data.get('created_at') or 
                data.get('created') or
                data.get('start_time') or
                datetime.now(timezone.utc)
            )
            
            updated_at = self.normalize_timestamp(
                data.get('updated_at') or 
                data.get('modified') or
                data.get('end_time') or
                created_at
            )
            
            # Extract metadata
            title = data.get('title') or self.extract_title(data)
            project = data.get('project') or data.get('workspace')
            tags = data.get('tags', [])
            
            return Conversation(
                id=str(conv_id) if conv_id else None,
                source=self.source_name,
                title=title,
                messages=messages,
                created_at=created_at,
                updated_at=updated_at,
                thread_id=str(conv_id) if conv_id else None,
                project=project,
                tags=tags,
                metadata={'source_format': 'json'}
            )
        
        except Exception as e:
            logger.debug(f"Error parsing JSON conversation: {e}")
            return None
    
    def _parse_message(self, msg_data: Any) -> Optional[Message]:
        """Parse message data into a Message object"""
        try:
            if isinstance(msg_data, str):
                # Simple string message
                return Message(
                    role='user',
                    content=msg_data,
                    timestamp=datetime.now(timezone.utc)
                )
            
            elif isinstance(msg_data, dict):
                # Extract role
                role = (msg_data.get('role') or 
                       msg_data.get('sender') or
                       msg_data.get('author') or
                       msg_data.get('from') or
                       'user')
                
                # Normalize role
                role = role.lower()
                if role in ['human', 'user', 'me']:
                    role = 'user'
                elif role in ['claude', 'assistant', 'ai', 'bot']:
                    role = 'assistant'
                elif role not in ['system']:
                    role = 'assistant'  # Default to assistant for unknown roles
                
                # Extract content
                content = (msg_data.get('content') or 
                          msg_data.get('text') or
                          msg_data.get('message') or
                          msg_data.get('body') or
                          '')
                
                # Handle content that might be nested
                if isinstance(content, dict):
                    content = content.get('text') or str(content)
                elif isinstance(content, list):
                    # Join multiple content parts
                    content_parts = []
                    for part in content:
                        if isinstance(part, str):
                            content_parts.append(part)
                        elif isinstance(part, dict):
                            content_parts.append(part.get('text', str(part)))
                    content = '\n'.join(content_parts)
                
                if not content:
                    return None
                
                # Extract timestamp
                timestamp = self.normalize_timestamp(
                    msg_data.get('timestamp') or
                    msg_data.get('created_at') or
                    msg_data.get('time') or
                    msg_data.get('sent_at') or
                    datetime.now(timezone.utc)
                )
                
                # Extract metadata
                metadata = {}
                for key in ['model', 'tokens', 'completion_tokens', 'prompt_tokens']:
                    if key in msg_data:
                        metadata[key] = msg_data[key]
                
                return Message(
                    role=role,
                    content=str(content),
                    timestamp=timestamp,
                    message_id=msg_data.get('id') or msg_data.get('message_id'),
                    parent_id=msg_data.get('parent_id') or msg_data.get('reply_to'),
                    metadata=metadata
                )
            
        except Exception as e:
            logger.debug(f"Error parsing message: {e}")
            return None