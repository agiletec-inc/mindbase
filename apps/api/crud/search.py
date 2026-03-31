"""Conversation search with vector similarity and recency ranking."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation

DEFAULT_RECENCY_WEIGHT = 0.15


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
    - semantic_score: cosine similarity clamped to [0, 1] via GREATEST(0, ...)
    - recency_score: exponential decay + boost, capped at 1.0
    - combined_score: weighted sum (weights normalized to sum to 1)

    Note: pgvector's <=> returns cosine distance (0-2), so 1-distance can be
    negative for very dissimilar vectors. We use GREATEST(0, ...) to clamp.
    """

    # Validate and normalize weights
    semantic_w = 1.0 - recency_weight
    recency_w = recency_weight
    weight_sum = semantic_w + recency_w
    if weight_sum <= 0:
        semantic_w = 1.0 - DEFAULT_RECENCY_WEIGHT
        recency_w = DEFAULT_RECENCY_WEIGHT
    else:
        semantic_w /= weight_sum
        recency_w /= weight_sum

    safe_tau_seconds = max(1, recency_tau_seconds)
    safe_boost_days = max(0, recency_boost_days)
    safe_boost_value = max(0.0, min(1.0, recency_boost_value))

    query_text = """
    SELECT *,
           GREATEST(0, 1 - (embedding <=> CAST(:embedding AS vector))) AS semantic_score,
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
               GREATEST(0, 1 - (embedding <=> CAST(:embedding AS vector))) * :semantic_weight
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
           GREATEST(0, 1 - (embedding <=> CAST(:embedding AS vector))) AS similarity
    FROM conversations
    WHERE embedding IS NOT NULL
          AND GREATEST(0, 1 - (embedding <=> CAST(:embedding AS vector))) >= :threshold
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

    params: dict = {
        "embedding": str(query_embedding),
        "threshold": threshold,
        "limit": limit,
        "tau_seconds": safe_tau_seconds,
        "boost_days": safe_boost_days,
        "boost_value": safe_boost_value,
        "semantic_weight": semantic_w,
        "recency_weight": recency_w,
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
    return result.fetchall()
