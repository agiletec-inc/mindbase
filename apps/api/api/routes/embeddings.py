"""Embedding model management API endpoints."""

from fastapi import APIRouter, HTTPException

from apps.api.ollama_client import ollama_client
from apps.api.api.schemas.embeddings import (
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    ModelInfo,
    ModelInstallRequest,
    ModelInstallResponse,
    ModelListResponse,
    ModelSwitchRequest,
    ModelSwitchResponse,
    SystemSpecsResponse,
)
from apps.api.services import settings_store
from apps.api.services.hardware import detect_hardware, recommend_models
from apps.api.services.model_catalog import MODEL_CATALOG

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """List all available embedding models with hardware recommendations."""
    try:
        hardware = detect_hardware()
        installed_models = await ollama_client.list_models()

        available = []
        for model_name, info in MODEL_CATALOG.items():
            is_installed = model_name in installed_models
            available.append(
                ModelInfo(
                    name=model_name,
                    size=info["size"],
                    dimensions=info["dimensions"],
                    mteb_score=info["mteb_score"],
                    ram_required=info["ram_required"],
                    status="installed" if is_installed else "not_installed",
                )
            )

        recommended_model_names = recommend_models(hardware)
        recommendations = [
            {
                "model": model_name,
                "reason": MODEL_CATALOG[model_name]["description"],
            }
            for model_name in recommended_model_names
            if model_name in MODEL_CATALOG
        ]

        return ModelListResponse(
            current=settings_store.get_active_embedding()[1],
            available=available,
            hardware={
                "platform": hardware["platform"],
                "cpu_cores": hardware["cpu_cores"],
                "ram_total": f"{hardware['ram_total_gb']:.1f}GB",
                "ram_available": f"{hardware['ram_available_gb']:.1f}GB",
                "gpu": hardware["gpu_type"],
                "is_apple_silicon": hardware["is_apple_silicon"],
            },
            recommendations=recommendations,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/models/install", response_model=ModelInstallResponse)
async def install_model(request: ModelInstallRequest):
    """Install a new embedding model via Ollama."""
    try:
        if request.model not in MODEL_CATALOG:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown model: {request.model}. Available: {list(MODEL_CATALOG.keys())}",
            )

        model_tag = request.model
        if request.quantization:
            model_tag = f"{request.model}:{request.quantization}"

        result = await ollama_client.pull_model(model_tag)

        return ModelInstallResponse(
            status="success" if result else "error",
            progress="100%",
            message=f"Model {model_tag} installed successfully",
        )
    except Exception as e:
        return ModelInstallResponse(
            status="error",
            message=f"Failed to install model: {str(e)}",
        )


@router.put("/models/active", response_model=ModelSwitchResponse)
async def switch_active_model(request: ModelSwitchRequest):
    """Switch the active embedding model."""
    try:
        if request.model not in MODEL_CATALOG:
            raise HTTPException(
                status_code=400, detail=f"Unknown model: {request.model}"
            )

        installed_models = await ollama_client.list_models()
        if request.model not in installed_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model not installed: {request.model}. Run POST /api/embeddings/models/install first.",
            )

        previous_model = settings_store.get_active_embedding()[1]
        # Cloud-catalog models (text-embedding-3-large) are OpenAI; the rest Ollama.
        provider = (
            "openai"
            if MODEL_CATALOG[request.model].get("size") == "cloud"
            else "ollama"
        )
        # Persist to the settings store (the single source of truth) so the switch
        # survives a restart and takes effect without one.
        settings_store.set_active_embedding(provider, request.model)

        return ModelSwitchResponse(
            status="success",
            previous=previous_model,
            current=request.model,
            restart_required=False,
            message=f"Switched from {previous_model} to {request.model}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch model: {str(e)}")


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Remove an installed embedding model."""
    try:
        if model_name == settings_store.get_active_embedding()[1]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete active model: {model_name}. Switch to another model first.",
            )

        result = await ollama_client.delete_model(model_name)

        if result:
            freed_space = MODEL_CATALOG.get(model_name, {}).get("size", "Unknown")
            return {
                "status": "success",
                "freed_space": freed_space,
                "message": f"Model {model_name} deleted successfully",
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"Model not found: {model_name}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@router.get("/system/specs", response_model=SystemSpecsResponse)
async def get_system_specs():
    """Get hardware specifications and model recommendations."""
    try:
        hardware = detect_hardware()
        recommended_models = recommend_models(hardware)

        ram_gb = hardware["ram_total_gb"]
        if ram_gb >= 32:
            max_size = "20GB"
        elif ram_gb >= 16:
            max_size = "10GB"
        elif ram_gb >= 8:
            max_size = "5GB"
        else:
            max_size = "2GB"

        return SystemSpecsResponse(
            platform=hardware["platform"],
            cpu_cores=hardware["cpu_cores"],
            ram_total=f"{hardware['ram_total_gb']:.1f}GB",
            ram_available=f"{hardware['ram_available_gb']:.1f}GB",
            gpu=hardware["gpu_type"],
            is_apple_silicon=hardware["is_apple_silicon"],
            ollama_install_method=hardware["ollama_install_method"],
            recommended_models=recommended_models,
            max_model_size=max_size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system specs: {str(e)}"
        )


@router.post("/generate", response_model=EmbeddingGenerateResponse)
async def generate_embedding(request: EmbeddingGenerateRequest):
    """Generate an embedding vector for arbitrary text."""
    try:
        provider, model = settings_store.get_active_embedding()
        embedding = await ollama_client.embed(
            request.text, provider=provider, model=model
        )
        return EmbeddingGenerateResponse(
            embedding=embedding,
            dimensions=len(embedding),
            model=model,
        )
    except Exception as e:  # pragma: no cover - surfaced via API response
        raise HTTPException(
            status_code=500, detail=f"Failed to generate embedding: {str(e)}"
        )
