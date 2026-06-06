"""CRUD for the multi-provider conversation_embeddings table.

Each (conversation, provider, model) row stores its vector in the
dimension-bucket column matching the vector length, so providers with different
dimensions coexist. Search is an exact cosine scan (no ANN index — see the
migration for why), filtered to one provider/model so the query embedding and
the stored vectors come from the same model.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import EMBEDDING_DIM_COLUMNS

DEFAULT_RECENCY_WEIGHT = 0.15


def column_for_dim(dim: int) -> str:
    """Return the vector column name for an embedding dimension."""
    try:
        return EMBEDDING_DIM_COLUMNS[dim]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported embedding dimension {dim}. Add a vec_{dim} column to "
            "conversation_embeddings (migration) and EMBEDDING_DIM_COLUMNS to "
            "support this model."
        ) from exc


async def upsert_conversation_embedding(
    db: AsyncSession,
    conversation_id,
    provider: str,
    model: str,
    vector: Sequence[float],
) -> None:
    """Insert or replace the embedding for one (conversation, provider, model)."""
    dim = len(vector)
    col = column_for_dim(dim)
    stmt = text(
        f"""
        INSERT INTO conversation_embeddings
            (conversation_id, provider, model, dim, {col})
        VALUES (:cid, :provider, :model, :dim, CAST(:vec AS vector))
        ON CONFLICT (conversation_id, provider, model)
        DO UPDATE SET {col} = EXCLUDED.{col}, dim = EXCLUDED.dim, created_at = NOW()
        """
    )
    await db.execute(
        stmt,
        {
            "cid": str(conversation_id),
            "provider": provider,
            "model": model,
            "dim": dim,
            "vec": str(list(vector)),
        },
    )


async def list_conversations_missing_embedding(
    db: AsyncSession,
    provider: str,
    model: str,
    limit: int = 500,
) -> List[dict]:
    """Return conversations that have no embedding for the given provider/model."""
    stmt = text(
        """
        SELECT c.id, c.content, c.raw_content
        FROM conversations c
        WHERE NOT EXISTS (
            SELECT 1 FROM conversation_embeddings e
            WHERE e.conversation_id = c.id
              AND e.provider = :provider
              AND e.model = :model
        )
        ORDER BY c.created_at DESC
        LIMIT :limit
        """
    )
    result = await db.execute(
        stmt, {"provider": provider, "model": model, "limit": limit}
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def count_conversations_missing_embedding(
    db: AsyncSession,
    provider: str,
    model: str,
) -> int:
    """Count conversations with no embedding for the given provider/model."""
    stmt = text(
        """
        SELECT COUNT(*)
        FROM conversations c
        WHERE NOT EXISTS (
            SELECT 1 FROM conversation_embeddings e
            WHERE e.conversation_id = c.id
              AND e.provider = :provider
              AND e.model = :model
        )
        """
    )
    result = await db.execute(stmt, {"provider": provider, "model": model})
    return int(result.scalar() or 0)


async def search_conversation_embeddings(
    db: AsyncSession,
    query_embedding: List[float],
    provider: str,
    model: str,
    limit: int = 10,
    threshold: float = 0.8,
    source: Optional[str] = None,
    project: Optional[str] = None,
    topic: Optional[str] = None,
    workspace_path: Optional[str] = None,
    recency_weight: float = DEFAULT_RECENCY_WEIGHT,
    recency_tau_seconds: int = 1209600,  # 14 days
    recency_boost_days: int = 3,
    recency_boost_value: float = 0.05,
):
    """Search one provider/model's embeddings with recency-weighted ranking.

    Mirrors crud.search.search_conversations' scoring, but scans the
    per-provider conversation_embeddings table joined back to conversations.
    """
    col = column_for_dim(len(query_embedding))

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

    sim = f"GREATEST(0, 1 - (e.{col} <=> CAST(:embedding AS vector)))"
    recency = (
        "LEAST(1.0, EXP(-EXTRACT(EPOCH FROM (NOW() - "
        "COALESCE(c.created_at, to_timestamp(0)))) / :tau_seconds) + CASE WHEN "
        "c.created_at >= NOW() - (:boost_days * INTERVAL '1 day') THEN :boost_value "
        "ELSE 0 END)"
    )

    query_text = f"""
    SELECT c.*,
           {sim} AS semantic_score,
           {recency} AS recency_score,
           ({sim} * :semantic_weight + {recency} * :recency_weight) AS combined_score,
           {sim} AS similarity
    FROM conversation_embeddings e
    JOIN conversations c ON c.id = e.conversation_id
    WHERE e.provider = :provider
          AND e.model = :model
          AND e.{col} IS NOT NULL
          AND {sim} >= :threshold
    """

    if source:
        query_text += " AND c.source = :source"
    if project:
        query_text += " AND c.project = :project"
    if topic:
        query_text += " AND c.topics IS NOT NULL AND :topic = ANY(c.topics)"
    if workspace_path:
        query_text += " AND c.workspace_path = :workspace_path"

    query_text += " ORDER BY combined_score DESC LIMIT :limit"

    params: dict = {
        "embedding": str(query_embedding),
        "provider": provider,
        "model": model,
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
