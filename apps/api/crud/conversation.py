"""Conversation CRUD operations (create only — search is in crud/search.py)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.conversation import Conversation, RawConversation
from apps.api.schemas.conversation import ConversationCreate


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
    summary: Optional[str] = None,
) -> Conversation:
    """Upsert the derived conversation record linked to a raw entry.

    Uses ON CONFLICT (source, source_conversation_id) DO UPDATE so that
    re-storing the same source conversation updates content, summary, and
    timestamps rather than raising a unique-constraint violation.
    """

    insert_stmt = pg_insert(Conversation).values(
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
        summary=summary,
    )

    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[Conversation.source, Conversation.source_conversation_id],
        set_={
            "raw_id": insert_stmt.excluded.raw_id,
            "content": insert_stmt.excluded.content,
            "raw_content": insert_stmt.excluded.raw_content,
            "metadata": insert_stmt.excluded.metadata,
            "message_count": insert_stmt.excluded.message_count,
            "title": insert_stmt.excluded.title,
            "project": insert_stmt.excluded.project,
            "topics": insert_stmt.excluded.topics,
            "summary": insert_stmt.excluded.summary,
            "updated_at": func.now(),
        },
    ).returning(Conversation.id)

    result = await db.execute(upsert_stmt)
    row = result.fetchone()
    await db.flush()

    fetched = await db.execute(select(Conversation).where(Conversation.id == row[0]))
    return fetched.scalar_one()


async def list_conversations(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    source: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Conversation]:
    """Return derived conversations, newest first (backend is the store-of-record)."""
    stmt = select(Conversation).order_by(Conversation.created_at.desc())
    if source:
        stmt = stmt.where(Conversation.source == source)
    if project:
        stmt = stmt.where(Conversation.project == project)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession, conversation_id: UUID
) -> Optional[Conversation]:
    """Fetch a single derived conversation by id (with its full content payload)."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()
