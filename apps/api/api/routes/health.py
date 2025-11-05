"""Health check endpoint"""

from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.database import engine
from app.ollama_client import ollama_client

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint with dependency status information."""
    services = {"database": "unknown", "ollama": "unknown"}

    # Database connectivity
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
        services["database"] = "connected"
    except Exception:  # pragma: no cover - surfaced in response payload
        services["database"] = "unavailable"

    # Ollama availability
    try:
        models = await ollama_client.list_models()
        services["ollama"] = "available" if models is not None else "unknown"
    except Exception:  # pragma: no cover
        services["ollama"] = "unavailable"

    return {
        "status": "healthy" if services["database"] == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.1.0",
        "services": services,
    }
