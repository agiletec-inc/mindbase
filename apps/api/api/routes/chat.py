"""Chat (LLM) API endpoints.

The backend owns chat orchestration (model selection, RAG, prompt assembly, LLM
invocation, persistence) so clients can be thin renderers. Part A exposes the
model list + active selection; POST /api/chat streaming lands in Part B.
"""

from fastapi import APIRouter, HTTPException

from apps.api.ollama_client import ollama_client
from apps.api.services import settings_store

router = APIRouter(prefix="/api/chat", tags=["chat"])


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
