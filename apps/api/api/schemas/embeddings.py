"""Pydantic schemas for embedding model management endpoints."""

from pydantic import BaseModel, Field
from typing import Literal


class ModelInfo(BaseModel):
    """Embedding model information"""

    name: str
    size: str
    dimensions: int
    mteb_score: float | None = None
    ram_required: str
    status: Literal["installed", "not_installed", "installing"]
    quantization: str | None = None


class ModelListResponse(BaseModel):
    """Response for model list endpoint"""

    current: str
    available: list[ModelInfo]
    hardware: dict
    recommendations: list[dict]


class ModelInstallRequest(BaseModel):
    """Request body for model installation"""

    model: str
    quantization: str | None = None


class ModelInstallResponse(BaseModel):
    """Response for model installation"""

    status: Literal["installing", "success", "error"]
    progress: str | None = None
    job_id: str | None = None
    message: str | None = None


class ModelSwitchRequest(BaseModel):
    """Request body for switching active model"""

    model: str


class ModelSwitchResponse(BaseModel):
    """Response for model switch"""

    status: Literal["success", "error"]
    previous: str
    current: str
    restart_required: bool
    message: str | None = None


class SystemSpecsResponse(BaseModel):
    """System hardware specifications"""

    platform: str
    cpu_cores: int
    ram_total: str
    ram_available: str
    gpu: str
    is_apple_silicon: bool
    ollama_install_method: Literal["brew", "docker"]
    recommended_models: list[str]
    max_model_size: str


class EmbeddingGenerateRequest(BaseModel):
    """Request body for embedding generation"""

    text: str = Field(..., min_length=1, description="Text to embed")


class EmbeddingGenerateResponse(BaseModel):
    """Response model for embedding generation"""

    embedding: list[float]
    dimensions: int
    model: str
