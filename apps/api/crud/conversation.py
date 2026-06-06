"""Conversation CRUD operations (create only — search is in crud/search.py)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, RawConversation
from app.schemas.conversation import ConversationCreate


async def create_raw_conversation(
    db: AsyncSession,
    conversation: ConversationCreate,
    *,
    raw_payload: dict,
    raw_metadata: dict,
    workspace_path: Optional[str],
    captured_at: Optional[datetime],
) -> RawConversation:
    """Persist a raw conversation payload."""

    raw_record = RawConversation(
        source=conversation.source,
        source_conversation_id=conversation.source_conversation_id,
        workspace_path=workspace_path,
        payload=raw_payload,
        raw_metadata=raw_metadata or {},
        captured_at=captured_at,
    )
    db.add(raw_record)
    await db.flush()
    return raw_record


async def create_conversation_record(
    db: AsyncSession,
    conversation: ConversationCreate,
    *,
    raw_record: RawConversation,
    embedding: Optional[List[float]] = None,
    workspace_path: Optional[str],
    message_count: int,
    raw_content: Optional[str],
    project: Optional[str],
    topics: List[str],
    metadata: dict,
) -> Conversation:
    """Create the derived conversation record linked to a raw entry."""

    db_conversation = Conversation(
        raw_id=raw_record.id,
        source=conversation.source,
        source_conversation_id=conversation.source_conversation_id,
        workspace_path=workspace_path,
        title=conversation.title,
        content=conversation.content,
        raw_content=raw_content,
        conv_metadata=metadata,
        source_created_at=conversation.source_created_at,
        embedding=embedding,
        message_count=message_count,
        project=project,
        topics=topics,
    )
    db.add(db_conversation)
    await db.flush()
    await db.refresh(db_conversation)
    return db_conversation
