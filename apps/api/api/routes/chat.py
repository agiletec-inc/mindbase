"""Chat (LLM) API endpoints.

The backend owns chat orchestration — model selection (settings SSoT), RAG over the
user's past conversations, prompt assembly, the Ollama call, and persistence — so
clients stay thin: they POST a message and render the streamed reply.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api import crud
from apps.api.database import get_db
from apps.api.ollama_client import ollama_client
from apps.api.schemas.conversation import ChatRequest, ConversationCreate
from apps.api.services import settings_store
from apps.api.services.deriver import process_raw_conversation

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.get("/models")
async def list_chat_models():
    """Installed Ollama models available for chat, plus the active one (SSoT)."""
    try:
        installed = await ollama_client.list_models()
    except Exception as exc:  # pragma: no cover - surfaced via API response
        raise HTTPException(status_code=500, detail=f"Failed to list models: {exc}")
    return {
        "current": settings_store.get_chat_settings()["model"],
        "available": installed,
    }


def _rag_preview(content: dict) -> str:
    messages = content.get("messages") if isinstance(content, dict) else None
    if messages:
        text = " ".join(str(m.get("content", "")) for m in messages)
    else:
        text = str(content)
    return text[:200]


async def _retrieve_context(
    db: AsyncSession, message: str, limit: int, threshold: float
) -> str:
    """Embed the message with the active embedding and pull related past turns."""
    if limit <= 0:
        return ""
    provider, model = settings_store.get_active_embedding()
    query_embedding = await ollama_client.embed(message, provider=provider, model=model)
    rows = await crud.search_conversation_embeddings(
        db=db,
        query_embedding=query_embedding,
        provider=provider,
        model=model,
        limit=limit,
        threshold=threshold,
    )
    if not rows:
        return ""
    blocks = [
        f"- [{row.source}] {row.title or 'untitled'}: {_rag_preview(row.content)}"
        for row in rows
    ]
    return "\n\nRelevant past conversations:\n" + "\n".join(blocks)


async def _persist_turn(db: AsyncSession, message: str, reply: str, model: str) -> None:
    """Store the completed chat turn as a conversation (backend store-of-record)."""
    payload = ConversationCreate(
        source="mindbase-chat",
        title=message[:100],
        content={
            "messages": [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ]
        },
        metadata={"model": model, "app": "mindbase-chat"},
    )
    raw = await crud.create_raw_conversation(
        db,
        payload,
        raw_payload=payload.model_dump(mode="json"),
        raw_metadata=dict(payload.metadata or {}),
        workspace_path=None,
        captured_at=datetime.utcnow(),
    )
    await process_raw_conversation(db, raw)
    await db.commit()


@router.post("")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Stream a chat reply (SSE). The backend does RAG + prompt + LLM + persist."""
    chat_cfg = settings_store.get_chat_settings()
    model = request.model or chat_cfg["model"]

    try:
        context = await _retrieve_context(
            db, request.message, request.rag_limit, request.rag_threshold
        )
    except Exception:  # RAG is best-effort; never block the reply
        logger.exception("chat RAG failed; continuing without context")
        context = ""

    messages = [{"role": "system", "content": chat_cfg["systemPrompt"] + context}]
    messages += [{"role": m.role, "content": m.content} for m in request.history]
    messages.append({"role": "user", "content": request.message})
    options = {
        "temperature": chat_cfg["temperature"],
        "num_predict": chat_cfg["maxTokens"],
    }

    async def event_stream():
        reply = ""
        try:
            async for delta in ollama_client.chat(
                messages, model=model, options=options
            ):
                reply += delta
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        except Exception as exc:  # pragma: no cover - surfaced as a stream event
            logger.exception("chat stream failed")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return
        if request.store and reply:
            try:
                await _persist_turn(db, request.message, reply, model)
            except Exception:
                logger.exception("chat persist failed (turn not stored)")
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
