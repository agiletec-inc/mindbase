"""Conversation API endpoints"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import get_settings
from apps.api import crud
from apps.api.database import get_db
from apps.api.ollama_client import ollama_client
from apps.api.schemas.conversation import (
    ConversationCreate,
    ConversationQueuedResponse,
    ConversationResponse,
    ReembedRequest,
    ReembedResponse,
    SearchQuery,
    SearchResult,
)
from apps.api.services.deriver import (
    _extract_text_from_content,
    process_raw_conversation,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("/store", response_model=ConversationResponse | ConversationQueuedResponse)
async def store_conversation(
    conversation: ConversationCreate, db: AsyncSession = Depends(get_db)
):
    """
    Store a conversation with automatic embedding generation

    - Generates embedding using OpenAI text-embedding-3-large (Ollama fallback)
    - Stores in PostgreSQL with pgvector
    - Returns stored conversation with ID
    """
    try:
        raw_payload = conversation.model_dump(mode="json")
        raw_metadata = dict(conversation.metadata or {})

        workspace_path = (
            conversation.workspace
            or conversation.content.get("workspace")
            or raw_metadata.get("workspace_path")
        )
        if workspace_path:
            raw_metadata.setdefault("workspace_path", workspace_path)

        raw_record = await crud.create_raw_conversation(
            db,
            conversation,
            raw_payload=raw_payload,
            raw_metadata=raw_metadata,
            workspace_path=workspace_path,
            captured_at=conversation.source_created_at or datetime.utcnow(),
        )

        if settings.DERIVE_ON_STORE:
            response = await process_raw_conversation(db, raw_record)
            await db.commit()
            return response

        await db.commit()
        return ConversationQueuedResponse(raw_id=raw_record.id)

    except Exception as exc:  # pragma: no cover - surfaced via HTTP response
        logger.exception("Failed to store conversation")
        raise HTTPException(
            status_code=500, detail=f"Failed to store conversation: {exc}"
        ) from exc


@router.post("/search", response_model=list[SearchResult])
async def search_conversations_endpoint(
    query: SearchQuery, db: AsyncSession = Depends(get_db)
):
    """
    Semantic search across conversations

    - Embeds the query with the requested (or active) provider/model
    - Scans that provider/model's vectors in conversation_embeddings
    - Returns ranked results by similarity. Pass `provider`/`model` to compare
      providers over the same query.
    """
    try:
        # Resolve provider/model: the query must be embedded with the same model
        # whose stored vectors we search against.
        provider = query.provider or ollama_client.active_provider
        model = query.model or ollama_client.default_model(provider)

        query_embedding = await ollama_client.embed(
            query.query, provider=provider, model=model
        )

        results = await crud.search_conversation_embeddings(
            db=db,
            query_embedding=query_embedding,
            provider=provider,
            model=model,
            limit=query.limit,
            threshold=query.threshold,
            source=query.source,
            project=query.project,
            topic=query.topic,
            workspace_path=query.workspace_path,
        )

        # Format results
        search_results = []
        for row in results:
            # Extract content preview
            if "messages" in row.content:
                messages = row.content["messages"]
                first_message = messages[0].get("content", "") if messages else ""
                preview = (
                    first_message[:200] + "..."
                    if len(first_message) > 200
                    else first_message
                )
            else:
                content_str = str(row.content)
                preview = (
                    content_str[:200] + "..." if len(content_str) > 200 else content_str
                )

            search_results.append(
                SearchResult(
                    id=row.id,
                    title=row.title,
                    source=row.source,
                    project=row.project,
                    topics=row.topics or [],
                    similarity=row.similarity,
                    workspace_path=row.workspace_path,
                    raw_id=row.raw_id,
                    created_at=row.created_at,
                    content_preview=preview,
                )
            )

        return search_results

    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to search conversations")
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc


@router.post("/reembed", response_model=ReembedResponse)
async def reembed_conversations(
    request: ReembedRequest, db: AsyncSession = Depends(get_db)
):
    """
    Backfill embeddings for an existing corpus with another provider/model.

    Conversations are ingested under the active provider only. To compare a
    second provider, call this to embed conversations that don't yet have a
    vector for the given provider/model. Idempotent: only missing ones are
    embedded, so it can be called repeatedly until `remaining` reaches 0.
    """
    try:
        model = request.model or ollama_client.default_model(request.provider)

        pending = await crud.list_conversations_missing_embedding(
            db, provider=request.provider, model=model, limit=request.limit
        )

        embedded = 0
        for row in pending:
            text_content, _, _ = _extract_text_from_content(row["content"])
            vector = await ollama_client.embed(
                text_content or " ", provider=request.provider, model=model
            )
            await crud.upsert_conversation_embedding(
                db, row["id"], request.provider, model, vector
            )
            embedded += 1

        await db.commit()

        remaining = await crud.count_conversations_missing_embedding(
            db, provider=request.provider, model=model
        )

        return ReembedResponse(
            provider=request.provider,
            model=model,
            embedded=embedded,
            remaining=remaining,
        )

    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to reembed conversations")
        raise HTTPException(status_code=500, detail=f"Reembed failed: {exc}") from exc
