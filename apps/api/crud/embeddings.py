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

from apps.api.models.conversation import EMBEDDING_DIM_COLUMNS

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
    # id is supplied here (gen_random_uuid) rather than relying on a column
    # default: the table is created from the SQLAlchemy model, whose id default
    # is Python-side (uuid.uuid4) and does not apply to this raw INSERT.
    stmt = text(
        f"""
        INSERT INTO conversation_embeddings
            (id, conversation_id, provider, model, dim, {col})
        VALUES (gen_random_uuid(), :cid, :provider, :model, :dim, CAST(:vec AS vector))
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
    """Filter and return API search results ranked by the shared database function."""
    column_for_dim(len(query_embedding))
    query_text = """
    SELECT c.*, r.semantic_score, r.recency_score, r.combined_score,
           r.semantic_score AS similarity
    FROM mindbase_rank_conversation_embeddings(
        CAST(:embedding AS vector), :provider, :model, :recency_weight,
        :tau_seconds, :boost_days, :boost_value
    ) r
    JOIN conversations c ON c.id = r.conversation_id
    WHERE r.semantic_score >= :threshold
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
        "tau_seconds": recency_tau_seconds,
        "boost_days": recency_boost_days,
        "boost_value": recency_boost_value,
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
    return result.fetchall()
