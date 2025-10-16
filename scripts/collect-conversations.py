#!/usr/bin/env python3
"""
Mind-Base Conversation Collector
Automatically collects conversations from local AI tools and syncs to Mind-Base
Supports: Claude Desktop, ChatGPT Desktop, Cursor, WindSurf, Claude Code
"""

import os
import json
import sqlite3
import logging
import argparse
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import requests
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mind-base-collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ConversationData:
    """Standardized conversation data structure"""
    source: str
    source_conversation_id: str
    title: str
    content: Dict[str, Any]
    source_created_at: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ConversationCollector:
    """Base class for conversation collectors"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.conversations: List[ConversationData] = []
        
    def collect(self, since_date: Optional[datetime] = None) -> List[ConversationData]:
        """Collect conversations from the source"""
        raise NotImplementedError
        
    def get_data_paths(self) -> List[Path]:
        """Get potential data file paths for this source"""
        raise NotImplementedError

class ClaudeDesktopCollector(ConversationCollector):
    """Collector for Claude Desktop conversations"""
    
    def __init__(self):
        super().__init__("claude-desktop")
        
    def get_data_paths(self) -> List[Path]:
        """Claude Desktop data locations"""
        home = Path.home()
        return [
            home / "Library/Application Support/Claude/conversations.db",
            home / "Library/Application Support/Claude/conversations.json",
            home / ".config/Claude/conversations.db",
            home / "AppData/Roaming/Claude/conversations.db",  # Windows
        ]
    
    def collect(self, since_date: Optional[datetime] = None) -> List[ConversationData]:
        """Collect Claude Desktop conversations"""
        logger.info(f"Collecting {self.source_name} conversations...")
        
        for db_path in self.get_data_paths():
            if db_path.exists():
                logger.info(f"Found Claude data at: {db_path}")
                if db_path.suffix == '.db':
                    return self._collect_from_sqlite(db_path, since_date)
                elif db_path.suffix == '.json':
                    return self._collect_from_json(db_path, since_date)
        
        logger.warning(f"No Claude Desktop data found")
        return []
    
    def _collect_from_sqlite(self, db_path: Path, since_date: Optional[datetime]) -> List[ConversationData]:
        """Collect from SQLite database"""
        conversations = []
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get conversation schema
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"Available tables: {tables}")
            
            # Try common table names
            for table_name in ['conversations', 'chats', 'messages', 'threads']:
                if table_name in tables:
                    query = f"SELECT * FROM {table_name}"
                    if since_date:
                        query += f" WHERE created_at >= '{since_date.isoformat()}'"
                    
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    
                    # Get column names
                    column_names = [description[0] for description in cursor.description]
                    
                    for row in rows:
                        row_dict = dict(zip(column_names, row))
                        conv = self._parse_conversation_row(row_dict)
                        if conv:
                            conversations.append(conv)
                    
                    break
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error reading Claude SQLite database: {e}")
            
        return conversations
    
    def _collect_from_json(self, json_path: Path, since_date: Optional[datetime]) -> List[ConversationData]:
        """Collect from JSON file"""
        conversations = []
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                conv_list = data
            elif isinstance(data, dict):
                conv_list = data.get('conversations', data.get('chats', []))
            else:
                logger.warning(f"Unexpected JSON structure in {json_path}")
                return []
            
            for conv_data in conv_list:
                conv = self._parse_conversation_data(conv_data)
                if conv and (not since_date or self._is_after_date(conv, since_date)):
                    conversations.append(conv)
                    
        except Exception as e:
            logger.error(f"Error reading Claude JSON file: {e}")
            
        return conversations
    
    def _parse_conversation_row(self, row: Dict[str, Any]) -> Optional[ConversationData]:
        """Parse SQLite row into ConversationData"""
        try:
            # Extract conversation ID
            conv_id = row.get('id') or row.get('conversation_id') or row.get('uuid')
            if not conv_id:
                return None
            
            # Extract title
            title = row.get('title') or row.get('name') or f"Conversation {conv_id}"
            
            # Extract messages/content
            content = {}
            if 'messages' in row:
                content['messages'] = json.loads(row['messages']) if isinstance(row['messages'], str) else row['messages']
            elif 'content' in row:
                content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
            else:
                # Build content from row data
                content = {k: v for k, v in row.items() if k not in ['id', 'title', 'created_at', 'updated_at']}
            
            # Extract timestamp
            created_at = row.get('created_at') or row.get('created') or datetime.now().isoformat()
            
            return ConversationData(
                source=self.source_name,
                source_conversation_id=str(conv_id),
                title=title[:100],  # Limit title length
                content=content,
                source_created_at=created_at,
                metadata={'raw_data': row}
            )
            
        except Exception as e:
            logger.warning(f"Error parsing conversation row: {e}")
            return None
    
    def _parse_conversation_data(self, data: Dict[str, Any]) -> Optional[ConversationData]:
        """Parse JSON conversation data"""
        try:
            conv_id = data.get('id') or data.get('uuid') or data.get('conversation_id')
            if not conv_id:
                return None
            
            title = data.get('title') or data.get('name') or f"Conversation {conv_id}"
            created_at = data.get('created_at') or data.get('timestamp') or datetime.now().isoformat()
            
            return ConversationData(
                source=self.source_name,
                source_conversation_id=str(conv_id),
                title=title[:100],
                content=data,
                source_created_at=created_at,
                metadata={'json_source': True}
            )
            
        except Exception as e:
            logger.warning(f"Error parsing conversation data: {e}")
            return None
    
    def _is_after_date(self, conv: ConversationData, since_date: datetime) -> bool:
        """Check if conversation is after the given date"""
        try:
            conv_date = datetime.fromisoformat(conv.source_created_at.replace('Z', '+00:00'))
            return conv_date >= since_date
        except:
            return True  # Include if we can't parse date

class ChatGPTCollector(ConversationCollector):
    """Collector for ChatGPT Desktop conversations"""
    
    def __init__(self):
        super().__init__("chatgpt")
        
    def get_data_paths(self) -> List[Path]:
        """ChatGPT data locations"""
        home = Path.home()
        return [
            home / "Library/Application Support/com.openai.chat/conversations.db",
            home / "Library/Application Support/ChatGPT/conversations.json",
            home / ".config/chatgpt/conversations.db",
            home / "AppData/Roaming/ChatGPT/conversations.db",  # Windows
        ]
    
    def collect(self, since_date: Optional[datetime] = None) -> List[ConversationData]:
        """Collect ChatGPT conversations"""
        logger.info(f"Collecting {self.source_name} conversations...")
        
        # Similar implementation to Claude Desktop
        # For now, return empty list as ChatGPT structure may vary
        logger.warning("ChatGPT collection not yet implemented - add specific parsing logic")
        return []

class CursorCollector(ConversationCollector):
    """Collector for Cursor AI conversations"""
    
    def __init__(self):
        super().__init__("cursor")
        
    def get_data_paths(self) -> List[Path]:
        """Cursor data locations"""
        home = Path.home()
        return [
            home / "Library/Application Support/Cursor/conversations.db",
            home / "Library/Application Support/Cursor/chat_history.json",
            home / ".config/cursor/conversations.db",
            home / "AppData/Roaming/Cursor/conversations.db",  # Windows
        ]
    
    def collect(self, since_date: Optional[datetime] = None) -> List[ConversationData]:
        """Collect Cursor conversations"""
        logger.info(f"Collecting {self.source_name} conversations...")
        logger.warning("Cursor collection not yet implemented - add specific parsing logic")
        return []

class WindSurfCollector(ConversationCollector):
    """Collector for WindSurf conversations"""
    
    def __init__(self):
        super().__init__("windsurf")
        
    def get_data_paths(self) -> List[Path]:
        """WindSurf data locations"""
        home = Path.home()
        return [
            home / "Library/Application Support/WindSurf/conversations.db",
            home / ".config/windsurf/conversations.db",
            home / "AppData/Roaming/WindSurf/conversations.db",  # Windows
        ]
    
    def collect(self, since_date: Optional[datetime] = None) -> List[ConversationData]:
        """Collect WindSurf conversations"""
        logger.info(f"Collecting {self.source_name} conversations...")
        logger.warning("WindSurf collection not yet implemented - add specific parsing logic")
        return []

class ClaudeCodeCollector(ConversationCollector):
    """Collector for Claude Code (MCP Memory) conversations"""
    
    def __init__(self):
        super().__init__("claude-code")
        
    def get_data_paths(self) -> List[Path]:
        """Claude Code MCP Memory data locations"""
        return [
            Path("/var/lib/docker/volumes/claude-code-memory/_data/"),
            Path.home() / ".claude/memory/",
            Path("/tmp/claude-code-memory/"),
        ]
    
    def collect(self, since_date: Optional[datetime] = None) -> List[ConversationData]:
        """Collect Claude Code conversations from MCP Memory"""
        logger.info(f"Collecting {self.source_name} conversations...")
        
        # This would integrate with the MCP Memory server
        # For now, return empty list - implement MCP Memory integration
        logger.warning("Claude Code MCP Memory collection not yet implemented")
        return []

class MindBaseSyncer:
    """Syncs collected conversations to Mind-Base Supabase instance"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        })
    
    def sync_conversations(self, conversations: List[ConversationData]) -> Dict[str, Any]:
        """Sync conversations to Mind-Base"""
        if not conversations:
            return {'success': True, 'message': 'No conversations to sync'}
        
        logger.info(f"Syncing {len(conversations)} conversations to Mind-Base...")
        
        # Prepare request payload
        payload = {
            'conversations': [asdict(conv) for conv in conversations],
            'sourceInfo': {
                'version': '1.0.0',
                'platform': 'python-collector',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        try:
            response = self.session.post(
                f'{self.base_url}/functions/v1/mind-sync',
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Sync completed: {result.get('summary', {})}")
                return result
            else:
                error_msg = f"Sync failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Sync error: {e}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

def get_collector(source: str) -> ConversationCollector:
    """Get collector for the specified source"""
    collectors = {
        'claude-desktop': ClaudeDesktopCollector,
        'chatgpt': ChatGPTCollector,
        'cursor': CursorCollector,
        'windsurf': WindSurfCollector,
        'claude-code': ClaudeCodeCollector,
    }
    
    if source not in collectors:
        raise ValueError(f"Unknown source: {source}. Available: {list(collectors.keys())}")
    
    return collectors[source]()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Collect and sync AI conversations to Mind-Base')
    parser.add_argument('--source', choices=['claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'claude-code', 'all'], 
                       default='all', help='Source to collect from')
    parser.add_argument('--since', type=str, help='Collect conversations since date (YYYY-MM-DD)')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for syncing')
    parser.add_argument('--dry-run', action='store_true', help='Collect but don\'t sync')
    parser.add_argument('--supabase-url', type=str, 
                       default=os.getenv('SUPABASE_URL', 'http://mind-base.localhost:8000'),
                       help='Supabase URL')
    parser.add_argument('--supabase-key', type=str,
                       default=os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
                       help='Supabase service role key')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse since date
    since_date = None
    if args.since:
        try:
            since_date = datetime.strptime(args.since, '%Y-%m-%d')
        except ValueError:
            logger.error(f"Invalid date format: {args.since}. Use YYYY-MM-DD")
            return 1
    
    # Determine sources to collect from
    sources = ['claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'claude-code'] if args.source == 'all' else [args.source]
    
    # Collect conversations
    all_conversations = []
    for source in sources:
        try:
            collector = get_collector(source)
            conversations = collector.collect(since_date)
            all_conversations.extend(conversations)
            logger.info(f"Collected {len(conversations)} conversations from {source}")
        except Exception as e:
            logger.error(f"Error collecting from {source}: {e}")
    
    logger.info(f"Total collected: {len(all_conversations)} conversations")
    
    # Sync to Mind-Base
    if not args.dry_run and all_conversations:
        if not args.supabase_key:
            logger.error("Supabase service role key required for syncing")
            return 1
        
        syncer = MindBaseSyncer(args.supabase_url, args.supabase_key)
        
        # Sync in batches
        for i in range(0, len(all_conversations), args.batch_size):
            batch = all_conversations[i:i + args.batch_size]
            result = syncer.sync_conversations(batch)
            
            if not result.get('success'):
                logger.error(f"Batch sync failed: {result.get('error')}")
                return 1
    
    logger.info("Collection and sync completed successfully")
    return 0

if __name__ == '__main__':
    exit(main())