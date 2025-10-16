"""Conversation API endpoints"""

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

router = APIRouter(prefix="/conversations", tags=["conversations"])


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
            text_content = " ".join([msg.get("content", "") for msg in messages if "content" in msg])
        else:
            text_content = str(conversation.content)

        # Generate embedding via Ollama
        embedding = await ollama_client.embed(text_content)

        # Store in database
        db_conversation = await crud.create_conversation(db, conversation, embedding)

        return db_conversation

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store conversation: {str(e)}")


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
            source=query.source
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
                    similarity=row.similarity,
                    created_at=row.created_at,
                    content_preview=preview
                )
            )

        return search_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
