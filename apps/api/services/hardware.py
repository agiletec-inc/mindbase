"""Hardware detection and model recommendation."""

import platform
import subprocess

import psutil


def detect_hardware() -> dict:
    """Detect hardware specs and capabilities."""
    system = platform.system()
    machine = platform.machine()

    is_apple_silicon = system == "Darwin" and machine == "arm64"

    ram = psutil.virtual_memory()
    ram_total_gb = ram.total / (1024**3)
    ram_available_gb = ram.available / (1024**3)

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
    """Recommend embedding models based on hardware."""
    ram_gb = hardware["ram_total_gb"]
    recommendations: list[str] = []

    if ram_gb >= 16:
        recommendations.extend(["qwen3-embedding:8b", "bge-m3"])
    if ram_gb >= 8:
        recommendations.append("mxbai-embed-large")
    recommendations.append("nomic-embed-text")

    return recommendations
