"""Conversation CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import text
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
    embedding: List[float],
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


async def search_conversations(
    db: AsyncSession,
    query_embedding: List[float],
    limit: int = 10,
    threshold: float = 0.8,
    source: str | None = None,
    project: str | None = None,
    topic: str | None = None,
    workspace_path: str | None = None,
    recency_weight: float = 0.15,
    recency_tau_seconds: int = 1209600,  # 14 days
    recency_boost_days: int = 3,
    recency_boost_value: float = 0.05,
) -> List[Conversation]:
    """Search conversations using vector similarity with recency ranking.

    Scores are normalized to 0-1 range:
    - semantic_score: cosine similarity (0-1)
    - recency_score: exponential decay + boost, capped at 1.0
    - combined_score: weighted sum (weights normalized to sum to 1)
    """

    # Normalize weights to sum to 1
    semantic_weight = 1.0 - recency_weight

    query_text = """
    SELECT *,
           (1 - (embedding <=> CAST(:embedding AS vector))) AS semantic_score,
           LEAST(
               1.0,
               EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(created_at, to_timestamp(0)))) / :tau_seconds)
               + CASE
                   WHEN created_at >= NOW() - (:boost_days * INTERVAL '1 day')
                   THEN :boost_value
                   ELSE 0
                 END
           ) AS recency_score,
           (
               (1 - (embedding <=> CAST(:embedding AS vector))) * :semantic_weight
               + LEAST(
                   1.0,
                   EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(created_at, to_timestamp(0)))) / :tau_seconds)
                   + CASE
                       WHEN created_at >= NOW() - (:boost_days * INTERVAL '1 day')
                       THEN :boost_value
                       ELSE 0
                     END
               ) * :recency_weight
           ) AS combined_score,
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

    if workspace_path:
        query_text += " AND workspace_path = :workspace_path"

    query_text += " ORDER BY combined_score DESC LIMIT :limit"

    params = {
        "embedding": str(query_embedding),
        "threshold": threshold,
        "limit": limit,
        "tau_seconds": recency_tau_seconds,
        "boost_days": recency_boost_days,
        "boost_value": recency_boost_value,
        "semantic_weight": semantic_weight,
        "recency_weight": recency_weight,
    }
    if source:
        params["source"] = source
    if project:
        params["project"] = project
    if topic:
        params["topic"] = topic
    if workspace_path:
        params["workspace_path"] = workspace_path

    result = await db.execute(text(query_text), params)
    conversations = result.fetchall()

    return conversations
