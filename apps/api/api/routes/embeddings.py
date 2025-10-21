"""Embedding model management API endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import platform
import psutil
import subprocess
from typing import Literal

from app.ollama_client import ollama_client
from app.config import get_settings

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])
settings = get_settings()


# === Pydantic Models ===


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


# === Model Database ===

MODEL_CATALOG = {
    "qwen3-embedding:8b": {
        "size": "4.7GB",
        "dimensions": 1024,
        "mteb_score": 70.58,
        "ram_required": "8-16GB",
        "description": "#1 MTEB multilingual + code",
    },
    "mxbai-embed-large": {
        "size": "670MB",
        "dimensions": 1024,
        "mteb_score": 64.68,
        "ram_required": "2-8GB",
        "description": "Balanced performance/size",
    },
    "nomic-embed-text": {
        "size": "140MB",
        "dimensions": 768,
        "mteb_score": 62.39,
        "ram_required": "2-4GB",
        "description": "Fast inference, low memory",
    },
    "bge-m3": {
        "size": "1.2GB",
        "dimensions": 1024,
        "mteb_score": None,  # Top tier but exact score not provided
        "ram_required": "8-16GB",
        "description": "Multilingual + long context (8192 tokens)",
    },
    "bge-large-en-v1.5": {
        "size": "1.4GB",
        "dimensions": 1024,
        "mteb_score": 63.98,
        "ram_required": "8-16GB",
        "description": "English-focused, high STS performance",
    },
}


# === Hardware Detection ===


def detect_hardware() -> dict:
    """Detect hardware specs and capabilities"""
    system = platform.system()
    machine = platform.machine()

    # Detect Apple Silicon
    is_apple_silicon = system == "Darwin" and machine == "arm64"

    # Get RAM
    ram = psutil.virtual_memory()
    ram_total_gb = ram.total / (1024**3)
    ram_available_gb = ram.available / (1024**3)

    # Detect GPU
    gpu_type = "none"
    if is_apple_silicon:
        gpu_type = "metal"
    elif system == "Linux":
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                gpu_type = "cuda"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return {
        "platform": f"{system.lower()}_{machine}",
        "is_apple_silicon": is_apple_silicon,
        "cpu_cores": psutil.cpu_count(logical=False),
        "ram_total_gb": ram_total_gb,
        "ram_available_gb": ram_available_gb,
        "gpu_type": gpu_type,
        "ollama_install_method": "brew" if is_apple_silicon else "docker",
    }


def recommend_models(hardware: dict) -> list[str]:
    """Recommend embedding models based on hardware"""
    ram_gb = hardware["ram_total_gb"]

    recommendations = []

    # Tier 1: High-end (16GB+ RAM)
    if ram_gb >= 16:
        recommendations.extend([
            "qwen3-embedding:8b",  # Best overall
            "bge-m3",              # Long context
        ])

    # Tier 2: Mid-range (8-16GB RAM)
    if ram_gb >= 8:
        recommendations.append("mxbai-embed-large")

    # Tier 3: Always available (low resource)
    recommendations.append("nomic-embed-text")

    return recommendations


# === API Endpoints ===


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """
    List all available embedding models with hardware recommendations

    Returns:
        - current: Currently active model
        - available: List of all available models with status
        - hardware: Detected hardware specs
        - recommendations: Recommended models for this hardware
    """
    try:
        # Detect hardware
        hardware = detect_hardware()

        # Get installed models from Ollama
        installed_models = await ollama_client.list_models()

        # Build available models list
        available = []
        for model_name, info in MODEL_CATALOG.items():
            is_installed = model_name in installed_models
            available.append(ModelInfo(
                name=model_name,
                size=info["size"],
                dimensions=info["dimensions"],
                mteb_score=info["mteb_score"],
                ram_required=info["ram_required"],
                status="installed" if is_installed else "not_installed",
            ))

        # Get recommendations
        recommended_model_names = recommend_models(hardware)
        recommendations = [
            {
                "model": model_name,
                "reason": MODEL_CATALOG[model_name]["description"],
            }
            for model_name in recommended_model_names
            if model_name in MODEL_CATALOG
        ]

        # Current model
        current_model = settings.EMBEDDING_MODEL

        return ModelListResponse(
            current=current_model,
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
    """
    Install a new embedding model via Ollama

    Args:
        model: Model name (e.g., "mxbai-embed-large")
        quantization: Optional quantization level (f16, q8_0, q4_k_m)

    Returns:
        Installation status and job ID for tracking
    """
    try:
        # Validate model exists in catalog
        if request.model not in MODEL_CATALOG:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown model: {request.model}. Available: {list(MODEL_CATALOG.keys())}",
            )

        # Build model tag with quantization if specified
        model_tag = request.model
        if request.quantization:
            model_tag = f"{request.model}:{request.quantization}"

        # Pull model via Ollama (this is synchronous, consider async task queue)
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
    """
    Switch the active embedding model

    Args:
        model: Model name to activate

    Returns:
        Previous and current model, restart requirement status

    Note:
        This updates the runtime configuration. To persist across restarts,
        update .env file with EMBEDDING_MODEL=<model_name>
    """
    try:
        # Validate model exists
        if request.model not in MODEL_CATALOG:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown model: {request.model}",
            )

        # Check if model is installed
        installed_models = await ollama_client.list_models()
        if request.model not in installed_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model not installed: {request.model}. Run POST /api/embeddings/models/install first.",
            )

        # Switch model
        previous_model = ollama_client.model
        ollama_client.model = request.model

        return ModelSwitchResponse(
            status="success",
            previous=previous_model,
            current=request.model,
            restart_required=False,  # Hot-swappable at runtime
            message=f"Switched from {previous_model} to {request.model}",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch model: {str(e)}")


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """
    Remove an installed embedding model

    Args:
        model_name: Model to remove

    Returns:
        Deletion status and freed space

    Note:
        Cannot delete the currently active model
    """
    try:
        # Prevent deleting active model
        if model_name == ollama_client.model:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete active model: {model_name}. Switch to another model first.",
            )

        # Delete model via Ollama
        result = await ollama_client.delete_model(model_name)

        if result:
            freed_space = MODEL_CATALOG.get(model_name, {}).get("size", "Unknown")
            return {
                "status": "success",
                "freed_space": freed_space,
                "message": f"Model {model_name} deleted successfully",
            }
        else:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@router.get("/system/specs", response_model=SystemSpecsResponse)
async def get_system_specs():
    """
    Get hardware specifications and model recommendations

    Returns:
        - Platform details (OS, CPU, RAM, GPU)
        - Recommended models for this hardware
        - Maximum recommended model size
    """
    try:
        hardware = detect_hardware()
        recommended_models = recommend_models(hardware)

        # Calculate max recommended model size based on RAM
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
        raise HTTPException(status_code=500, detail=f"Failed to get system specs: {str(e)}")
