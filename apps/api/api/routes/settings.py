"""Settings API endpoints."""

from fastapi import APIRouter, HTTPException

from apps.api.schemas.conversation import AppSettings
from apps.api.services import settings_store

router = APIRouter(prefix="/settings", tags=["settings"])


def _render(data: dict) -> AppSettings:
    """Render AppSettings, always reflecting the live SSoT (embedding + chat)."""
    provider, model = settings_store.get_active_embedding()
    chat = settings_store.get_chat_settings()
    merged = {
        **data,
        "embeddingProvider": provider,
        "embeddingModel": model,
        "chatModel": chat["model"],
        "chatTemperature": chat["temperature"],
        "chatMaxTokens": chat["maxTokens"],
        "chatSystemPrompt": chat["systemPrompt"],
    }
    return AppSettings(**merged)


@router.get("", response_model=AppSettings)
async def get_settings() -> AppSettings:
    try:
        return _render(settings_store.load_settings())
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Invalid settings file: {exc}"
        ) from exc


@router.put("", response_model=AppSettings)
async def update_settings(payload: AppSettings) -> AppSettings:
    # Merge over existing so omitted (null) fields don't clobber stored values.
    merged = {**settings_store.load_settings(), **payload.model_dump(exclude_none=True)}
    # Embedding selection goes through the single setter so the SSoT keys stay
    # canonical and consistent with PUT /api/embeddings/models/active.
    if payload.embeddingProvider or payload.embeddingModel:
        current = settings_store.get_active_embedding()
        provider = payload.embeddingProvider or current[0]
        model = payload.embeddingModel or current[1]
        merged["embeddingProvider"], merged["embeddingModel"] = provider, model
    # Chat selection persists through its single setter too.
    if any(
        v is not None
        for v in (
            payload.chatModel,
            payload.chatTemperature,
            payload.chatMaxTokens,
            payload.chatSystemPrompt,
        )
    ):
        chat = settings_store.set_chat_settings(
            model=payload.chatModel,
            temperature=payload.chatTemperature,
            max_tokens=payload.chatMaxTokens,
            system_prompt=payload.chatSystemPrompt,
        )
        merged.update(
            chatModel=chat["model"],
            chatTemperature=chat["temperature"],
            chatMaxTokens=chat["maxTokens"],
            chatSystemPrompt=chat["systemPrompt"],
        )
    settings_store.save_settings(merged)
    return _render(merged)
