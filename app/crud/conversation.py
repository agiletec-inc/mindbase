"""Conversation CRUD operations"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate
from typing import List


async def create_conversation(
    db: AsyncSession,
    conversation: ConversationCreate,
    embedding: List[float]
) -> Conversation:
    """Create a new conversation with embedding"""

    db_conversation = Conversation(
        source=conversation.source,
        source_conversation_id=conversation.source_conversation_id,
        title=conversation.title,
        content=conversation.content,
        conv_metadata=conversation.metadata,
        source_created_at=conversation.source_created_at,
        embedding=embedding,
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
    source: str | None = None
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

    query_text += " ORDER BY embedding <=> CAST(:embedding AS vector) LIMIT :limit"

    # Execute query
    params = {
        "embedding": str(query_embedding),
        "threshold": threshold,
        "limit": limit,
    }

    if source:
        params["source"] = source

    result = await db.execute(text(query_text), params)
    conversations = result.fetchall()

    return conversations
