"""Conversation API endpoints"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    SearchQuery,
    SearchResult,
)
from app.crud import conversation as crud
from app.ollama_client import ollama_client
from app.services.classifier import infer_project, infer_topics

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


@router.post("/store", response_model=ConversationResponse)
async def store_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Store a conversation with automatic embedding generation

    - Generates embedding using qwen3-embedding:8b (Ollama)
    - Stores in PostgreSQL with pgvector
    - Returns stored conversation with ID
    """
    try:
        # Extract text for embedding
        if "messages" in conversation.content:
            messages = conversation.content["messages"]
            flattened_messages = [str(msg.get("content", "")) for msg in messages if "content" in msg]
            text_content = " ".join(flattened_messages)
            message_count = len(flattened_messages)
            raw_content = "\n\n".join(flattened_messages)
        else:
            text_content = str(conversation.content)
            message_count = 0
            raw_content = None

        # Generate embedding via Ollama
        embedding = await ollama_client.embed(text_content)

        metadata = dict(conversation.metadata or {})
        project = infer_project(
            metadata=conversation.metadata,
            content=conversation.content,
            text=text_content,
            explicit=conversation.project or metadata.get("project"),
        )
        topics = infer_topics(
            text_content,
            existing=conversation.topics or metadata.get("topics"),
        )

        if project:
            metadata["project"] = project
        metadata["topics"] = topics

        # Store in database
        db_conversation = await crud.create_conversation(
            db,
            conversation,
            embedding,
            message_count=message_count,
            raw_content=raw_content,
            project=project,
            topics=topics,
            metadata=metadata,
        )

        response = ConversationResponse(
            id=db_conversation.id,
            source=db_conversation.source,
            source_conversation_id=db_conversation.source_conversation_id,
            title=db_conversation.title,
            content=db_conversation.content,
            metadata=metadata,
            message_count=db_conversation.message_count,
            project=project,
            topics=topics,
            created_at=db_conversation.created_at,
            updated_at=db_conversation.updated_at,
        )

        return response

    except Exception as exc:  # pragma: no cover - surfaced via HTTP response
        logger.exception("Failed to store conversation")
        raise HTTPException(status_code=500, detail=f"Failed to store conversation: {exc}") from exc


@router.post("/search", response_model=list[SearchResult])
async def search_conversations_endpoint(
    query: SearchQuery,
    db: AsyncSession = Depends(get_db)
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
        )

        # Format results
        search_results = []
        for row in results:
            # Extract content preview
            if "messages" in row.content:
                messages = row.content["messages"]
                first_message = messages[0].get("content", "") if messages else ""
                preview = first_message[:200] + "..." if len(first_message) > 200 else first_message
            else:
                content_str = str(row.content)
                preview = content_str[:200] + "..." if len(content_str) > 200 else content_str

            search_results.append(
                SearchResult(
                    id=row.id,
                    title=row.title,
                    source=row.source,
                    project=row.project,
                    topics=row.topics or [],
                    similarity=row.similarity,
                    created_at=row.created_at,
                    content_preview=preview
                )
            )

        return search_results

    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to search conversations")
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc
