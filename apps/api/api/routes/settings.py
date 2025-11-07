"""Settings API endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.conversation import AppSettings
from app.services import settings_store

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettings)
async def get_settings() -> AppSettings:
    data = settings_store.load_settings()
    try:
        return AppSettings(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid settings file: {exc}") from exc


@router.put("", response_model=AppSettings)
async def update_settings(payload: AppSettings) -> AppSettings:
    settings_store.save_settings(payload.model_dump())
    return payload
