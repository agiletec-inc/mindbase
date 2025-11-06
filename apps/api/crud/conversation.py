"""Conversation CRUD operations"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate
from typing import List, Optional


async def create_conversation(
    db: AsyncSession,
    conversation: ConversationCreate,
    embedding: List[float],
    *,
    message_count: int,
    raw_content: Optional[str],
    project: Optional[str],
    topics: List[str],
    metadata: dict
) -> Conversation:
    """Create a new conversation with embedding"""

    db_conversation = Conversation(
        source=conversation.source,
        source_conversation_id=conversation.source_conversation_id,
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
    await db.commit()
    await db.refresh(db_conversation)

    return db_conversation


async def search_conversations(
    db: AsyncSession,
    query_embedding: List[float],
    limit: int = 10,
    threshold: float = 0.8,
    source: str | None = None,
    project: str | None = None,
    topic: str | None = None
) -> List[Conversation]:
    """Search conversations using vector similarity"""

    # Build query
    query_text = """
    SELECT *,
           (1 - (embedding <=> CAST(:embedding AS vector))) AS similarity
    FROM conversations
    WHERE embedding IS NOT NULL
          AND (1 - (embedding <=> CAST(:embedding AS vector))) >= :threshold
    """

    if source:
        query_text += " AND source = :source"

    if project:
        query_text += " AND project = :project"

    if topic:
        query_text += " AND topics IS NOT NULL AND :topic = ANY(topics)"

    query_text += " ORDER BY embedding <=> CAST(:embedding AS vector) LIMIT :limit"

    # Execute query
    params = {
        "embedding": str(query_embedding),
        "threshold": threshold,
        "limit": limit,
    }

    if source:
        params["source"] = source
    if project:
        params["project"] = project
    if topic:
        params["topic"] = topic

    result = await db.execute(text(query_text), params)
    conversations = result.fetchall()

    return conversations
