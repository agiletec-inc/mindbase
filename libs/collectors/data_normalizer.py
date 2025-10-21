#!/usr/bin/env python3
"""
Data Normalizer
Normalizes collected conversation data from various sources into a unified format
Handles deduplication, validation, and standardization
"""

import json
import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
import re

from base_collector import Conversation, Message

logger = logging.getLogger(__name__)

@dataclass
class NormalizationStats:
    """Statistics from normalization process"""
    total_input: int = 0
    total_output: int = 0
    duplicates_removed: int = 0
    invalid_removed: int = 0
    messages_normalized: int = 0
    timestamps_fixed: int = 0
    roles_standardized: int = 0
    content_cleaned: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {
            'total_input': self.total_input,
            'total_output': self.total_output,
            'duplicates_removed': self.duplicates_removed,
            'invalid_removed': self.invalid_removed,
            'messages_normalized': self.messages_normalized,
            'timestamps_fixed': self.timestamps_fixed,
            'roles_standardized': self.roles_standardized,
            'content_cleaned': self.content_cleaned
        }

class DataNormalizer:
    """Normalizes conversation data from multiple sources"""
    
    def __init__(self):
        self.stats = NormalizationStats()
        self.seen_conversation_hashes: Set[str] = set()
        self.seen_message_hashes: Set[str] = set()
        
        # Role normalization mappings
        self.role_mappings = {
            'user': ['user', 'human', 'me', 'question', 'prompt', 'input'],
            'assistant': ['assistant', 'ai', 'bot', 'claude', 'chatgpt', 'gpt', 
                         'cursor', 'windsurf', 'response', 'completion', 'output'],
            'system': ['system', 'instruction', 'context']
        }
        
        # Content cleaning patterns
        self.content_patterns = [
            # Remove excessive whitespace
            (r'\s+', ' '),
            # Remove control characters
            (r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ''),
            # Normalize line endings
            (r'\r\n|\r', '\n'),
            # Remove zero-width characters
            (r'[\u200B\u200C\u200D\uFEFF]', ''),
        ]
    
    def normalize_conversations(self, 
                              conversations: List[Conversation],
                              source: Optional[str] = None) -> List[Conversation]:
        """
        Normalize a list of conversations
        
        Args:
            conversations: List of conversations to normalize
            source: Optional source filter
            
        Returns:
            List of normalized conversations
        """
        logger.info(f"Normalizing {len(conversations)} conversations...")
        self.stats.total_input = len(conversations)
        
        normalized = []
        
        for conv in conversations:
            # Apply source filter if specified
            if source and conv.source != source:
                continue
            
            # Normalize the conversation
            norm_conv = self._normalize_conversation(conv)
            
            if norm_conv:
                # Check for duplicates
                conv_hash = self._get_conversation_hash(norm_conv)
                if conv_hash not in self.seen_conversation_hashes:
                    self.seen_conversation_hashes.add(conv_hash)
                    normalized.append(norm_conv)
                else:
                    self.stats.duplicates_removed += 1
                    logger.debug(f"Skipping duplicate conversation: {norm_conv.id}")
            else:
                self.stats.invalid_removed += 1
        
        self.stats.total_output = len(normalized)
        logger.info(f"Normalization complete: {self.stats.total_output} conversations retained")
        
        return normalized
    
    def _normalize_conversation(self, conversation: Conversation) -> Optional[Conversation]:
        """Normalize a single conversation"""
        try:
            # Validate basic structure
            if not conversation.messages:
                logger.debug(f"Skipping conversation {conversation.id}: no messages")
                return None
            
            # Normalize messages
            normalized_messages = []
            for msg in conversation.messages:
                norm_msg = self._normalize_message(msg)
                if norm_msg:
                    # Check for duplicate messages within conversation
                    msg_hash = self._get_message_hash(norm_msg)
                    if msg_hash not in self.seen_message_hashes:
                        self.seen_message_hashes.add(msg_hash)
                        normalized_messages.append(norm_msg)
            
            if not normalized_messages:
                logger.debug(f"Skipping conversation {conversation.id}: no valid messages after normalization")
                return None
            
            # Sort messages by timestamp
            normalized_messages.sort(key=lambda m: m.timestamp)
            
            # Update conversation with normalized messages
            conversation.messages = normalized_messages
            
            # Normalize timestamps
            if not conversation.created_at or not conversation.created_at.tzinfo:
                conversation.created_at = normalized_messages[0].timestamp
                self.stats.timestamps_fixed += 1
            
            if not conversation.updated_at or not conversation.updated_at.tzinfo:
                conversation.updated_at = normalized_messages[-1].timestamp
                self.stats.timestamps_fixed += 1
            
            # Normalize title
            conversation.title = self._normalize_title(conversation)
            
            # Add normalization metadata
            if not conversation.metadata:
                conversation.metadata = {}
            conversation.metadata['normalized'] = True
            conversation.metadata['normalization_timestamp'] = datetime.now(timezone.utc).isoformat()
            
            return conversation
            
        except Exception as e:
            logger.warning(f"Error normalizing conversation {conversation.id}: {e}")
            return None
    
    def _normalize_message(self, message: Message) -> Optional[Message]:
        """Normalize a single message"""
        try:
            self.stats.messages_normalized += 1
            
            # Normalize role
            original_role = message.role.lower()
            normalized_role = self._normalize_role(original_role)
            if normalized_role != original_role:
                message.role = normalized_role
                self.stats.roles_standardized += 1
            
            # Clean content
            cleaned_content = self._clean_content(message.content)
            if cleaned_content != message.content:
                message.content = cleaned_content
                self.stats.content_cleaned += 1
            
            # Validate content
            if not message.content or len(message.content.strip()) == 0:
                return None
            
            # Ensure timestamp is timezone-aware
            if not message.timestamp.tzinfo:
                message.timestamp = message.timestamp.replace(tzinfo=timezone.utc)
                self.stats.timestamps_fixed += 1
            
            return message
            
        except Exception as e:
            logger.debug(f"Error normalizing message: {e}")
            return None
    
    def _normalize_role(self, role: str) -> str:
        """Normalize message role to standard values"""
        role = role.lower().strip()
        
        for standard_role, variations in self.role_mappings.items():
            if role in variations:
                return standard_role
        
        # Default to assistant for unknown roles
        logger.debug(f"Unknown role '{role}', defaulting to 'assistant'")
        return 'assistant'
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize message content"""
        if not content:
            return content
        
        # Apply cleaning patterns
        for pattern, replacement in self.content_patterns:
            content = re.sub(pattern, replacement, content)
        
        # Strip leading/trailing whitespace
        content = content.strip()
        
        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def _normalize_title(self, conversation: Conversation) -> str:
        """Generate or normalize conversation title"""
        if conversation.title and len(conversation.title.strip()) > 0:
            # Clean existing title
            title = self._clean_content(conversation.title)
            # Limit length
            if len(title) > 200:
                title = title[:197] + '...'
            return title
        
        # Generate title from first user message
        for msg in conversation.messages:
            if msg.role == 'user':
                title = msg.content[:100]
                if len(msg.content) > 100:
                    title += '...'
                return title
        
        # Fallback title
        return f"{conversation.source} conversation"
    
    def _get_conversation_hash(self, conversation: Conversation) -> str:
        """Generate hash for conversation deduplication"""
        # Hash based on source, messages content, and rough timestamp
        content_str = f"{conversation.source}:"
        
        for msg in conversation.messages:
            content_str += f"{msg.role}:{msg.content}:"
        
        # Include date (not time) to allow same conversation on different days
        date_str = conversation.created_at.date().isoformat()
        content_str += date_str
        
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def _get_message_hash(self, message: Message) -> str:
        """Generate hash for message deduplication"""
        content_str = f"{message.role}:{message.content}:{message.timestamp.isoformat()}"
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def merge_conversations(self, 
                          conversations: List[Conversation]) -> List[Conversation]:
        """
        Merge conversations that are continuations of each other
        
        Args:
            conversations: List of conversations to merge
            
        Returns:
            List of merged conversations
        """
        if not conversations:
            return []
        
        # Sort by created_at
        conversations.sort(key=lambda c: c.created_at)
        
        merged = []
        current_group = [conversations[0]]
        
        for conv in conversations[1:]:
            # Check if this conversation should be merged with the current group
            if self._should_merge(current_group[-1], conv):
                current_group.append(conv)
            else:
                # Merge current group and start new one
                merged_conv = self._merge_conversation_group(current_group)
                if merged_conv:
                    merged.append(merged_conv)
                current_group = [conv]
        
        # Merge last group
        if current_group:
            merged_conv = self._merge_conversation_group(current_group)
            if merged_conv:
                merged.append(merged_conv)
        
        logger.info(f"Merged {len(conversations)} conversations into {len(merged)}")
        return merged
    
    def _should_merge(self, conv1: Conversation, conv2: Conversation) -> bool:
        """Determine if two conversations should be merged"""
        # Same source
        if conv1.source != conv2.source:
            return False
        
        # Time proximity (within 30 minutes)
        time_diff = (conv2.created_at - conv1.updated_at).total_seconds()
        if time_diff > 1800:  # 30 minutes
            return False
        
        # Similar context (check for overlapping last/first messages)
        if conv1.messages and conv2.messages:
            last_msg = conv1.messages[-1].content[:100]
            first_msg = conv2.messages[0].content[:100]
            
            # Check for similarity
            if self._calculate_similarity(last_msg, first_msg) > 0.7:
                return True
        
        # Same thread ID
        if conv1.thread_id and conv1.thread_id == conv2.thread_id:
            return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity (0-1)"""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _merge_conversation_group(self, 
                                 conversations: List[Conversation]) -> Optional[Conversation]:
        """Merge a group of conversations into one"""
        if not conversations:
            return None
        
        if len(conversations) == 1:
            return conversations[0]
        
        # Merge all messages
        all_messages = []
        for conv in conversations:
            all_messages.extend(conv.messages)
        
        # Remove duplicate messages
        unique_messages = []
        seen_hashes = set()
        
        for msg in all_messages:
            msg_hash = self._get_message_hash(msg)
            if msg_hash not in seen_hashes:
                seen_hashes.add(msg_hash)
                unique_messages.append(msg)
        
        # Sort by timestamp
        unique_messages.sort(key=lambda m: m.timestamp)
        
        # Create merged conversation
        merged = Conversation(
            id=conversations[0].id,  # Use first conversation's ID
            source=conversations[0].source,
            title=self._generate_merged_title(conversations),
            messages=unique_messages,
            created_at=conversations[0].created_at,
            updated_at=conversations[-1].updated_at,
            thread_id=conversations[0].thread_id,
            project=conversations[0].project,
            tags=self._merge_tags(conversations),
            metadata=self._merge_metadata(conversations)
        )
        
        return merged
    
    def _generate_merged_title(self, conversations: List[Conversation]) -> str:
        """Generate title for merged conversation"""
        # Use the most informative title
        for conv in conversations:
            if conv.title and not conv.title.startswith(conv.source):
                return conv.title
        
        return conversations[0].title
    
    def _merge_tags(self, conversations: List[Conversation]) -> List[str]:
        """Merge tags from multiple conversations"""
        all_tags = set()
        for conv in conversations:
            if conv.tags:
                all_tags.update(conv.tags)
        return list(all_tags)
    
    def _merge_metadata(self, conversations: List[Conversation]) -> Dict[str, Any]:
        """Merge metadata from multiple conversations"""
        merged_metadata = {}
        
        for conv in conversations:
            if conv.metadata:
                merged_metadata.update(conv.metadata)
        
        # Add merge information
        merged_metadata['merged'] = True
        merged_metadata['merged_count'] = len(conversations)
        merged_metadata['merged_ids'] = [conv.id for conv in conversations]
        
        return merged_metadata
    
    def validate_data_quality(self, 
                            conversations: List[Conversation]) -> Tuple[List[Conversation], Dict[str, Any]]:
        """
        Validate data quality and return valid conversations with quality report
        
        Args:
            conversations: List of conversations to validate
            
        Returns:
            Tuple of (valid_conversations, quality_report)
        """
        valid_conversations = []
        quality_report = {
            'total_conversations': len(conversations),
            'valid_conversations': 0,
            'invalid_conversations': 0,
            'quality_issues': [],
            'statistics': {}
        }
        
        for conv in conversations:
            issues = self._validate_conversation_quality(conv)
            
            if not issues:
                valid_conversations.append(conv)
                quality_report['valid_conversations'] += 1
            else:
                quality_report['invalid_conversations'] += 1
                quality_report['quality_issues'].append({
                    'conversation_id': conv.id,
                    'source': conv.source,
                    'issues': issues
                })
        
        # Calculate statistics
        if valid_conversations:
            quality_report['statistics'] = self._calculate_statistics(valid_conversations)
        
        return valid_conversations, quality_report
    
    def _validate_conversation_quality(self, conversation: Conversation) -> List[str]:
        """Validate quality of a single conversation"""
        issues = []
        
        # Check for minimum message count
        if len(conversation.messages) < 2:
            issues.append("Conversation has less than 2 messages")
        
        # Check for balanced conversation (both user and assistant messages)
        roles = set(msg.role for msg in conversation.messages)
        if 'user' not in roles:
            issues.append("No user messages found")
        if 'assistant' not in roles:
            issues.append("No assistant messages found")
        
        # Check for empty messages
        empty_messages = sum(1 for msg in conversation.messages 
                           if not msg.content or len(msg.content.strip()) == 0)
        if empty_messages > 0:
            issues.append(f"{empty_messages} empty messages found")
        
        # Check for timestamp consistency
        for i in range(1, len(conversation.messages)):
            if conversation.messages[i].timestamp < conversation.messages[i-1].timestamp:
                issues.append("Messages not in chronological order")
                break
        
        # Check for suspiciously short or long messages
        for msg in conversation.messages:
            if len(msg.content) < 2:
                issues.append(f"Suspiciously short message: {msg.content[:50]}")
            elif len(msg.content) > 50000:
                issues.append(f"Suspiciously long message: {len(msg.content)} characters")
        
        return issues
    
    def _calculate_statistics(self, conversations: List[Conversation]) -> Dict[str, Any]:
        """Calculate statistics for valid conversations"""
        total_messages = sum(len(conv.messages) for conv in conversations)
        total_words = sum(
            sum(len(msg.content.split()) for msg in conv.messages)
            for conv in conversations
        )
        
        message_lengths = [
            len(msg.content)
            for conv in conversations
            for msg in conv.messages
        ]
        
        avg_message_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
        
        return {
            'total_messages': total_messages,
            'total_words': total_words,
            'avg_messages_per_conversation': total_messages / len(conversations),
            'avg_message_length': avg_message_length,
            'sources': dict(self._count_by_source(conversations)),
            'date_range': {
                'earliest': min(conv.created_at for conv in conversations).isoformat(),
                'latest': max(conv.updated_at for conv in conversations).isoformat()
            }
        }
    
    def _count_by_source(self, conversations: List[Conversation]) -> List[Tuple[str, int]]:
        """Count conversations by source"""
        source_counts = {}
        for conv in conversations:
            source_counts[conv.source] = source_counts.get(conv.source, 0) + 1
        
        return sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get normalization statistics"""
        return self.stats.to_dict()
    
    def reset_stats(self):
        """Reset normalization statistics"""
        self.stats = NormalizationStats()
        self.seen_conversation_hashes.clear()
        self.seen_message_hashes.clear()