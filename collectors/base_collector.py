#!/usr/bin/env python3
"""
Base Collector Class
Foundation for all AI conversation collectors with precise data structures
"""

import json
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Individual message in a conversation with complete metadata"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    message_id: Optional[str] = None
    parent_id: Optional[str] = None  # For threading
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure timestamp is timezone-aware"""
        if self.timestamp and not self.timestamp.tzinfo:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
        
        # Generate message_id if not provided
        if not self.message_id:
            content_hash = hashlib.sha256(
                f"{self.role}:{self.content}".encode()
            ).hexdigest()[:16]
            self.message_id = f"msg_{content_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO timestamp"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat() if self.timestamp else None
        return data

@dataclass
class Conversation:
    """Complete conversation with all messages and metadata"""
    id: str
    source: str  # 'claude-desktop', 'cursor', 'chatgpt', etc.
    title: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    thread_id: Optional[str] = None  # Original thread/conversation ID
    project: Optional[str] = None
    workspace: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure timestamps are timezone-aware and generate ID if needed"""
        if self.created_at and not self.created_at.tzinfo:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        if self.updated_at and not self.updated_at.tzinfo:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
        
        # Generate conversation ID if not provided
        if not self.id:
            source_hash = hashlib.sha256(
                f"{self.source}:{self.thread_id}:{self.created_at}".encode()
            ).hexdigest()[:16]
            self.id = f"conv_{source_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO timestamps"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        data['messages'] = [msg.to_dict() if isinstance(msg, Message) else msg 
                           for msg in self.messages]
        return data
    
    def get_message_count(self) -> int:
        """Get total number of messages"""
        return len(self.messages)
    
    def get_user_messages(self) -> List[Message]:
        """Get only user messages"""
        return [msg for msg in self.messages if msg.role == 'user']
    
    def get_assistant_messages(self) -> List[Message]:
        """Get only assistant messages"""
        return [msg for msg in self.messages if msg.role == 'assistant']
    
    def get_word_count(self) -> int:
        """Get total word count across all messages"""
        total_words = 0
        for msg in self.messages:
            total_words += len(msg.content.split())
        return total_words
    
    def get_duration(self) -> float:
        """Get conversation duration in seconds"""
        if not self.messages:
            return 0
        
        first_msg = min(self.messages, key=lambda m: m.timestamp)
        last_msg = max(self.messages, key=lambda m: m.timestamp)
        duration = (last_msg.timestamp - first_msg.timestamp).total_seconds()
        return max(0, duration)

class BaseCollector(ABC):
    """Abstract base class for all conversation collectors"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.conversations: List[Conversation] = []
        self.last_sync_timestamp: Optional[datetime] = None
        self.stats = {
            'total_conversations': 0,
            'total_messages': 0,
            'total_words': 0,
            'errors': 0,
            'warnings': 0
        }
    
    @abstractmethod
    def get_data_paths(self) -> List[Path]:
        """Get potential data file paths for this source"""
        pass
    
    @abstractmethod
    def collect(self, since_date: Optional[datetime] = None) -> List[Conversation]:
        """Collect conversations from the source"""
        pass
    
    def validate_conversation(self, conversation: Conversation) -> bool:
        """Validate conversation data integrity"""
        if not conversation.id:
            logger.warning(f"Conversation missing ID")
            return False
        
        if not conversation.messages:
            logger.warning(f"Conversation {conversation.id} has no messages")
            return False
        
        if not conversation.created_at:
            logger.warning(f"Conversation {conversation.id} missing created_at")
            return False
        
        # Validate messages
        for msg in conversation.messages:
            if not msg.role or not msg.content:
                logger.warning(f"Invalid message in conversation {conversation.id}")
                return False
            
            if msg.role not in ['user', 'assistant', 'system']:
                logger.warning(f"Unknown role '{msg.role}' in conversation {conversation.id}")
                return False
        
        return True
    
    def normalize_timestamp(self, timestamp: Any) -> datetime:
        """Normalize various timestamp formats to datetime"""
        if isinstance(timestamp, datetime):
            return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        
        if isinstance(timestamp, (int, float)):
            # Assume Unix timestamp
            if timestamp > 1e10:  # Milliseconds
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        if isinstance(timestamp, str):
            # Try various formats
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S%z',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    if not dt.tzinfo:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
            
            # If all formats fail, try ISO parse
            try:
                from dateutil import parser
                dt = parser.parse(timestamp)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except:
                pass
        
        # Default to now if parsing fails
        logger.warning(f"Could not parse timestamp: {timestamp}, using current time")
        return datetime.now(timezone.utc)
    
    def extract_title(self, conversation_data: Any) -> str:
        """Extract or generate conversation title"""
        # Try common title fields
        if isinstance(conversation_data, dict):
            for field in ['title', 'name', 'subject', 'topic']:
                if field in conversation_data and conversation_data[field]:
                    return str(conversation_data[field])[:200]
        
        # Generate from first message if available
        if isinstance(conversation_data, dict) and 'messages' in conversation_data:
            messages = conversation_data['messages']
            if messages and len(messages) > 0:
                first_msg = messages[0]
                if isinstance(first_msg, dict) and 'content' in first_msg:
                    content = str(first_msg['content'])[:100]
                    return content + ('...' if len(first_msg['content']) > 100 else '')
        
        # Default title
        return f"Conversation from {self.source_name}"
    
    def deduplicate_conversations(self, conversations: List[Conversation]) -> List[Conversation]:
        """Remove duplicate conversations based on ID and content hash"""
        seen_ids = set()
        seen_hashes = set()
        unique_conversations = []
        
        for conv in conversations:
            # Check ID
            if conv.id in seen_ids:
                logger.debug(f"Skipping duplicate conversation ID: {conv.id}")
                continue
            
            # Check content hash
            content_hash = self._get_conversation_hash(conv)
            if content_hash in seen_hashes:
                logger.debug(f"Skipping duplicate conversation content: {conv.id}")
                continue
            
            seen_ids.add(conv.id)
            seen_hashes.add(content_hash)
            unique_conversations.append(conv)
        
        return unique_conversations
    
    def _get_conversation_hash(self, conversation: Conversation) -> str:
        """Generate hash from conversation content"""
        content_str = ""
        for msg in conversation.messages:
            content_str += f"{msg.role}:{msg.content}:"
        
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def filter_by_date(self, conversations: List[Conversation], 
                      since_date: Optional[datetime]) -> List[Conversation]:
        """Filter conversations by date"""
        if not since_date:
            return conversations
        
        # Ensure since_date is timezone-aware
        if not since_date.tzinfo:
            since_date = since_date.replace(tzinfo=timezone.utc)
        
        filtered = []
        for conv in conversations:
            if conv.updated_at and conv.updated_at >= since_date:
                filtered.append(conv)
            elif conv.created_at and conv.created_at >= since_date:
                filtered.append(conv)
        
        return filtered
    
    def update_stats(self, conversations: List[Conversation]):
        """Update collection statistics"""
        self.stats['total_conversations'] = len(conversations)
        self.stats['total_messages'] = sum(conv.get_message_count() for conv in conversations)
        self.stats['total_words'] = sum(conv.get_word_count() for conv in conversations)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        return self.stats.copy()
    
    def save_checkpoint(self, checkpoint_file: Path):
        """Save collection checkpoint for incremental sync"""
        checkpoint_data = {
            'source': self.source_name,
            'last_sync': datetime.now(timezone.utc).isoformat(),
            'stats': self.stats,
            'conversation_ids': [conv.id for conv in self.conversations]
        }
        
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logger.info(f"Saved checkpoint to {checkpoint_file}")
    
    def load_checkpoint(self, checkpoint_file: Path) -> Optional[Dict[str, Any]]:
        """Load collection checkpoint"""
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            if 'last_sync' in checkpoint_data:
                self.last_sync_timestamp = self.normalize_timestamp(checkpoint_data['last_sync'])
            
            logger.info(f"Loaded checkpoint from {checkpoint_file}")
            return checkpoint_data
        
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return None
