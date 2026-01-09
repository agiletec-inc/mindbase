"""Conversation API endpoints"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crud import conversation as crud
from app.database import get_db
from app.ollama_client import ollama_client
from app.schemas.conversation import (
    ConversationCreate,
    ConversationQueuedResponse,
    ConversationResponse,
    SearchQuery,
    SearchResult,
)
from app.services.deriver import process_raw_conversation

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("/store", response_model=ConversationResponse | ConversationQueuedResponse)
async def store_conversation(
    conversation: ConversationCreate, db: AsyncSession = Depends(get_db)
):
    """
    Store a conversation with automatic embedding generation

    - Generates embedding using qwen3-embedding:8b (Ollama)
    - Stores in PostgreSQL with pgvector
    - Returns stored conversation with ID
    """
    try:
        raw_payload = conversation.model_dump(mode="python")
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

    - Generates query embedding using qwen3-embedding:8b
    - Performs vector similarity search with pgvector
    - Returns ranked results by similarity
    """
    try:
        # Generate query embedding
        query_embedding = await ollama_client.embed(query.query)

        # Search conversations
        results = await crud.search_conversations(
            db=db,
            query_embedding=query_embedding,
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
