"""Embedding model catalog — static configuration data."""

MODEL_CATALOG: dict[str, dict] = {
    "text-embedding-3-large": {
        "size": "cloud",
        "dimensions": 3072,
        "mteb_score": 64.59,
        "ram_required": "N/A (API)",
        "description": "OpenAI cloud API, fast & reliable, ~$0.13/1M tokens",
    },
    "qwen3-embedding:8b": {
        "size": "4.7GB",
        "dimensions": 4096,
        "mteb_score": 70.58,
        "ram_required": "8-16GB",
        "description": "#1 MTEB multilingual + code (local Ollama)",
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
        "mteb_score": None,
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
