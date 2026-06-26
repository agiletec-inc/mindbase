"""Conversation CRUD operations (create only — search is in crud/search.py)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
    summary: Optional[str] = None,
) -> Conversation:
    """Upsert the derived conversation record linked to a raw entry.

    Uses ON CONFLICT (source, source_conversation_id) DO UPDATE so that
    re-storing the same source conversation updates content, summary, and
    timestamps rather than raising a unique-constraint violation.

    Note: conv_metadata maps to the DB column "metadata" (Column("metadata", ...)).
    The excluded pseudo-table uses DB column names, so we reference "metadata" there.
    """

    # Build the INSERT using DB column names for columns that have an alias.
    # conv_metadata → DB column "metadata"; pass via model's mapped attr in values().
    insert_stmt = pg_insert(Conversation).values(
        raw_id=raw_record.id,
        source=conversation.source,
        source_conversation_id=conversation.source_conversation_id,
        workspace_path=workspace_path,
        title=conversation.title,
        content=conversation.content,
        raw_content=raw_content,
        conv_metadata=metadata,  # ORM attr name maps to "metadata" column
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
            # Use DB column names for excluded references.
            # conv_metadata → "metadata"; all others match the Python attr name.
            "raw_id": insert_stmt.excluded.raw_id,
            "content": insert_stmt.excluded.content,
            "raw_content": insert_stmt.excluded.raw_content,
            "metadata": insert_stmt.excluded.metadata,  # DB col name, not Python attr
            "message_count": insert_stmt.excluded.message_count,
            "title": insert_stmt.excluded.title,
            "project": insert_stmt.excluded.project,
            "topics": insert_stmt.excluded.topics,
            "summary": insert_stmt.excluded.summary,
            "updated_at": func.now(),
        },
    ).returning(Conversation.id)

    result = await db.execute(upsert_stmt)
    conversation_id = result.scalar_one()
    await db.flush()

    fetched = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    db_conversation = fetched.scalar_one()
    return db_conversation
