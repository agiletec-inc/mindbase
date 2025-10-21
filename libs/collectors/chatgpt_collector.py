#!/usr/bin/env python3
"""
ChatGPT Collector
Collects AI conversations from ChatGPT Desktop application
Handles various storage formats used by OpenAI
"""

import os
import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import re

from base_collector import BaseCollector, Conversation, Message

logger = logging.getLogger(__name__)

class ChatGPTCollector(BaseCollector):
    """Collector for ChatGPT Desktop conversations"""
    
    def __init__(self):
        super().__init__("chatgpt")
        
    def get_data_paths(self) -> List[Path]:
        """ChatGPT data locations"""
        home = Path.home()
        paths = []
        
        # macOS paths
        if os.uname().sysname == "Darwin":
            paths.extend([
                home / "Library/Application Support/com.openai.chat",
                home / "Library/Application Support/OpenAI",
                home / "Library/Application Support/ChatGPT",
                home / "Library/Caches/com.openai.chat",
                home / "Library/WebKit/com.openai.chat",
            ])
        
        # Linux paths
        paths.extend([
            home / ".config/openai",
            home / ".config/chatgpt",
            home / ".config/com.openai.chat",
            home / ".cache/openai",
            home / ".cache/chatgpt",
            home / ".local/share/openai",
            home / ".local/share/chatgpt",
        ])
        
        # Windows paths
        paths.extend([
            home / "AppData/Roaming/OpenAI",
            home / "AppData/Roaming/ChatGPT",
            home / "AppData/Roaming/com.openai.chat",
            home / "AppData/Local/OpenAI",
            home / "AppData/Local/ChatGPT",
        ])
        
        # Also check for browser-based storage if using web wrapper
        browser_paths = []
        for base_path in paths:
            if base_path.exists():
                # Look for browser storage subdirectories
                browser_paths.extend(base_path.glob("**/IndexedDB"))
                browser_paths.extend(base_path.glob("**/Local Storage"))
                browser_paths.extend(base_path.glob("**/Session Storage"))
                browser_paths.extend(base_path.glob("**/WebSQL"))
        
        paths.extend(browser_paths)
        
        return [p for p in paths if p.exists()]
    
    def collect(self, since_date: Optional[datetime] = None) -> List[Conversation]:
        """Collect ChatGPT conversations"""
        logger.info(f"Collecting {self.source_name} conversations...")
        all_conversations = []
        
        for data_path in self.get_data_paths():
            logger.info(f"Checking path: {data_path}")
            
            # Check for different storage types
            if "IndexedDB" in str(data_path):
                conversations = self._collect_from_indexeddb(data_path, since_date)
                all_conversations.extend(conversations)
            
            elif "Local Storage" in str(data_path) or "Session Storage" in str(data_path):
                conversations = self._collect_from_webstorage(data_path, since_date)
                all_conversations.extend(conversations)
            
            # Check for SQLite databases
            db_files = list(data_path.glob("*.db"))
            db_files.extend(list(data_path.glob("*.sqlite")))
            db_files.extend(list(data_path.glob("*.sqlite3")))
            
            for db_file in db_files:
                conversations = self._collect_from_sqlite(db_file, since_date)
                all_conversations.extend(conversations)
            
            # Check for JSON files
            json_files = list(data_path.glob("*.json"))
            json_files.extend(list(data_path.glob("**/conversations.json")))
            json_files.extend(list(data_path.glob("**/chats.json")))
            json_files.extend(list(data_path.glob("**/history.json")))
            
            for json_file in json_files:
                conversations = self._collect_from_json(json_file, since_date)
                all_conversations.extend(conversations)
            
            # Check for log files
            log_files = list(data_path.glob("*.log"))
            log_files.extend(list(data_path.glob("**/*.log")))
            
            for log_file in log_files:
                if "chat" in log_file.name.lower() or "conversation" in log_file.name.lower():
                    conversations = self._collect_from_logs(log_file, since_date)
                    all_conversations.extend(conversations)
        
        # Deduplicate and filter
        all_conversations = self.deduplicate_conversations(all_conversations)
        all_conversations = self.filter_by_date(all_conversations, since_date)
        
        # Update stats
        self.update_stats(all_conversations)
        self.conversations = all_conversations
        
        logger.info(f"Collected {len(all_conversations)} conversations from {self.source_name}")
        return all_conversations
    
    def _collect_from_indexeddb(self, indexeddb_path: Path, 
                               since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from IndexedDB storage"""
        conversations = []
        
        # IndexedDB is typically stored as SQLite files
        db_files = list(indexeddb_path.glob("*.db"))
        db_files.extend(list(indexeddb_path.glob("*.sqlite")))
        
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
                          ['conversation', 'chat', 'message', 'thread', 'completion']):
                        
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
                
                conn.close()
                
            except Exception as e:
                logger.debug(f"Could not read IndexedDB file {db_file}: {e}")
        
        return conversations
    
    def _collect_from_webstorage(self, storage_path: Path, 
                                since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from Web Storage (Local/Session Storage)"""
        conversations = []
        
        # Web storage is typically in SQLite or LevelDB format
        storage_files = list(storage_path.glob("*.db"))
        storage_files.extend(list(storage_path.glob("*.ldb")))
        storage_files.extend(list(storage_path.glob("*.log")))
        
        for storage_file in storage_files:
            if storage_file.suffix == '.db':
                # SQLite format
                conversations.extend(self._collect_from_sqlite(storage_file, since_date))
            else:
                # LevelDB or log format - extract text
                try:
                    with open(storage_file, 'rb') as f:
                        content = f.read()
                        text_content = self._extract_text_from_binary(content)
                        conversations.extend(self._extract_conversations_from_text(text_content))
                except Exception as e:
                    logger.debug(f"Could not read storage file {storage_file}: {e}")
        
        return conversations
    
    def _collect_from_sqlite(self, db_file: Path, 
                           since_date: Optional[datetime]) -> List[Conversation]:
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
                
                # Look for conversation-related tables
                if any(keyword in table_name.lower() for keyword in 
                      ['conversation', 'chat', 'message', 'completion', 'history']):
                    
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
            
            # Also check for key-value storage tables
            for kv_table in ['ItemTable', 'data', 'storage']:
                try:
                    cursor.execute(f"SELECT key, value FROM {kv_table}")
                    rows = cursor.fetchall()
                    
                    for key, value in rows:
                        if any(keyword in key.lower() for keyword in 
                              ['conversation', 'chat', 'message', 'completion']):
                            
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
                for key in ['conversations', 'chats', 'messages', 'history', 'threads']:
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
    
    def _collect_from_logs(self, log_file: Path, 
                         since_date: Optional[datetime]) -> List[Conversation]:
        """Collect from log files"""
        conversations = []
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Parse log entries for conversations
            current_messages = []
            current_conv_id = None
            
            for line in lines:
                # Look for conversation start markers
                if 'New conversation' in line or 'Session started' in line:
                    # Save previous conversation if exists
                    if current_messages:
                        conv = self._create_conversation_from_messages(current_messages, current_conv_id)
                        if conv:
                            conversations.append(conv)
                    
                    current_messages = []
                    # Extract conversation ID if present
                    conv_id_match = re.search(r'id[:\s]+([a-f0-9-]+)', line, re.IGNORECASE)
                    current_conv_id = conv_id_match.group(1) if conv_id_match else None
                
                # Look for user messages
                elif any(marker in line for marker in ['User:', 'Human:', 'Question:', '>>>']):
                    content = self._extract_message_from_log(line, 'user')
                    if content:
                        timestamp = self._extract_timestamp_from_log(line)
                        msg = Message(
                            role='user',
                            content=content,
                            timestamp=timestamp
                        )
                        current_messages.append(msg)
                
                # Look for assistant messages
                elif any(marker in line for marker in ['Assistant:', 'AI:', 'ChatGPT:', 'Response:', '<<<']):
                    content = self._extract_message_from_log(line, 'assistant')
                    if content:
                        timestamp = self._extract_timestamp_from_log(line)
                        msg = Message(
                            role='assistant',
                            content=content,
                            timestamp=timestamp
                        )
                        current_messages.append(msg)
            
            # Save last conversation
            if current_messages:
                conv = self._create_conversation_from_messages(current_messages, current_conv_id)
                if conv:
                    conversations.append(conv)
        
        except Exception as e:
            logger.debug(f"Error reading log file {log_file}: {e}")
        
        return conversations
    
    def _parse_database_row(self, row_dict: Dict[str, Any]) -> Optional[Conversation]:
        """Parse database row into Conversation"""
        try:
            # Look for conversation ID
            conv_id = (row_dict.get('id') or 
                      row_dict.get('conversation_id') or
                      row_dict.get('thread_id') or
                      row_dict.get('session_id'))
            
            # Extract messages
            messages = []
            
            # Check for messages field
            if 'messages' in row_dict:
                msg_data = row_dict['messages']
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
            elif 'prompt' in row_dict and 'completion' in row_dict:
                # User message
                user_msg = Message(
                    role='user',
                    content=str(row_dict['prompt']),
                    timestamp=self.normalize_timestamp(row_dict.get('timestamp', datetime.now(timezone.utc)))
                )
                messages.append(user_msg)
                
                # Assistant message
                assistant_msg = Message(
                    role='assistant',
                    content=str(row_dict['completion']),
                    timestamp=self.normalize_timestamp(row_dict.get('timestamp', datetime.now(timezone.utc)))
                )
                messages.append(assistant_msg)
            
            # Check for content field with conversation data
            elif 'content' in row_dict:
                content = row_dict['content']
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except:
                        pass
                
                if isinstance(content, dict):
                    return self._parse_json_conversation(content)
            
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
                id=str(conv_id) if conv_id else None,
                source=self.source_name,
                title=title,
                messages=messages,
                created_at=created_at,
                updated_at=updated_at,
                metadata={'source_type': 'database'}
            )
        
        except Exception as e:
            logger.debug(f"Error parsing database row: {e}")
            return None
    
    def _parse_json_conversation(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """Parse JSON data into Conversation"""
        try:
            # Extract conversation ID
            conv_id = (data.get('id') or 
                      data.get('conversation_id') or
                      data.get('thread_id'))
            
            # Extract messages
            messages = []
            
            # Check various message field names
            for field in ['messages', 'conversation', 'chat', 'history']:
                if field in data:
                    msg_list = data[field]
                    if isinstance(msg_list, list):
                        for msg in msg_list:
                            parsed_msg = self._parse_message(msg)
                            if parsed_msg:
                                messages.append(parsed_msg)
                        break
            
            # Check for OpenAI-specific format
            if not messages and 'mapping' in data:
                # OpenAI uses a mapping structure for conversations
                mapping = data['mapping']
                if isinstance(mapping, dict):
                    # Extract messages from mapping
                    for node_id, node_data in mapping.items():
                        if 'message' in node_data:
                            msg = node_data['message']
                            parsed_msg = self._parse_message(msg)
                            if parsed_msg:
                                messages.append(parsed_msg)
                    
                    # Sort messages by timestamp or creation order
                    messages.sort(key=lambda m: m.timestamp)
            
            if not messages:
                return None
            
            # Extract metadata
            created_at = self.normalize_timestamp(
                data.get('create_time') or
                data.get('created_at') or
                data.get('timestamp') or
                datetime.now(timezone.utc)
            )
            
            updated_at = self.normalize_timestamp(
                data.get('update_time') or
                data.get('updated_at') or
                created_at
            )
            
            title = data.get('title') or self.extract_title(data)
            
            # Extract model information if available
            model = data.get('model') or data.get('model_slug')
            
            metadata = {'source_format': 'json'}
            if model:
                metadata['model'] = model
            
            return Conversation(
                id=str(conv_id) if conv_id else None,
                source=self.source_name,
                title=title,
                messages=messages,
                created_at=created_at,
                updated_at=updated_at,
                metadata=metadata
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
                role = msg_data.get('role') or msg_data.get('author', {}).get('role')
                
                if not role:
                    # Try to infer from other fields
                    if 'user' in msg_data:
                        role = 'user'
                    elif 'assistant' in msg_data:
                        role = 'assistant'
                    else:
                        role = 'user'  # Default
                
                # Normalize role
                role = role.lower()
                if role in ['human', 'user']:
                    role = 'user'
                elif role in ['assistant', 'ai', 'bot', 'chatgpt', 'gpt']:
                    role = 'assistant'
                elif role not in ['system']:
                    role = 'assistant'
                
                # Extract content
                content = msg_data.get('content')
                
                # Handle OpenAI format where content might be nested
                if isinstance(content, dict):
                    # Check for 'parts' field (OpenAI format)
                    if 'parts' in content:
                        parts = content['parts']
                        if isinstance(parts, list):
                            content = '\n'.join(str(part) for part in parts)
                        else:
                            content = str(parts)
                    else:
                        content = content.get('text') or str(content)
                elif isinstance(content, list):
                    # Join multiple content parts
                    content = '\n'.join(str(part) for part in content)
                
                # Alternative content fields
                if not content:
                    content = (msg_data.get('text') or 
                              msg_data.get('message') or
                              msg_data.get('value') or
                              '')
                
                if not content:
                    return None
                
                # Extract timestamp
                timestamp = self.normalize_timestamp(
                    msg_data.get('create_time') or
                    msg_data.get('timestamp') or
                    msg_data.get('created_at') or
                    datetime.now(timezone.utc)
                )
                
                # Extract metadata
                metadata = {}
                for key in ['model', 'finish_reason', 'weight', 'metadata']:
                    if key in msg_data:
                        metadata[key] = msg_data[key]
                
                return Message(
                    role=role,
                    content=str(content),
                    timestamp=timestamp,
                    message_id=msg_data.get('id'),
                    parent_id=msg_data.get('parent'),
                    metadata=metadata
                )
        
        except Exception as e:
            logger.debug(f"Error parsing message: {e}")
            return None
    
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
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                data = json.loads(match)
                
                # Check if this looks like conversation data
                if any(key in data for key in ['messages', 'conversation', 'chat', 'mapping']):
                    conv = self._parse_json_conversation(data)
                    if conv:
                        conversations.append(conv)
            
            except:
                pass
        
        return conversations
    
    def _extract_message_from_log(self, line: str, role: str) -> Optional[str]:
        """Extract message content from log line"""
        patterns = {
            'user': ['User:', 'Human:', 'Question:', '>>>', 'Q:'],
            'assistant': ['Assistant:', 'AI:', 'ChatGPT:', 'Response:', '<<<', 'A:']
        }
        
        for pattern in patterns.get(role, []):
            if pattern in line:
                # Extract content after the pattern
                content = line.split(pattern, 1)[1].strip()
                return content if content else None
        
        return None
    
    def _extract_timestamp_from_log(self, line: str) -> datetime:
        """Extract timestamp from log line"""
        import re
        
        # ISO format
        iso_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        match = re.search(iso_pattern, line)
        if match:
            return self.normalize_timestamp(match.group())
        
        # Log format [YYYY-MM-DD HH:MM:SS]
        log_pattern = r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]'
        match = re.search(log_pattern, line)
        if match:
            timestamp_str = match.group().strip('[]')
            return self.normalize_timestamp(timestamp_str)
        
        # Unix timestamp
        unix_pattern = r'\b1[5-7]\d{9}\b'  # Timestamps from 2012 to 2024
        match = re.search(unix_pattern, line)
        if match:
            return self.normalize_timestamp(int(match.group()))
        
        return datetime.now(timezone.utc)
    
    def _create_conversation_from_messages(self, messages: List[Message], 
                                          conv_id: Optional[str] = None) -> Optional[Conversation]:
        """Create conversation from list of messages"""
        if not messages:
            return None
        
        # Sort messages by timestamp
        messages.sort(key=lambda m: m.timestamp)
        
        # Get timestamps
        created_at = messages[0].timestamp
        updated_at = messages[-1].timestamp
        
        # Generate title from first user message
        title = "ChatGPT Conversation"
        for msg in messages:
            if msg.role == 'user':
                title = msg.content[:100] + ('...' if len(msg.content) > 100 else '')
                break
        
        return Conversation(
            id=conv_id,
            source=self.source_name,
            title=title,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            metadata={'source_type': 'logs'}
        )