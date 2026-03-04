"""Constants and paths for the inference manager."""

import os
from pathlib import Path

# Paths
HOME = Path.home()
REGISTRY_FILE = Path(__file__).parent / "models.yaml"
V1_REGISTRY_FILE = Path(__file__).parent.parent / "models.yaml"
V1_FAVORITES_FILE = HOME / ".model-favorites"
CACHE_DIR = HOME / ".cache" / "llama.cpp"
LOG_DIR = HOME / ".inference-logs"
FLASK_PORT = 5000

# Port allocation
DEFAULT_PORT_RANGE = (30000, 31000)

# Backend defaults
DEFAULT_BACKEND = "llama"
LLAMA_DEFAULT_FLAGS = {
    "ctx-size": "0",
    "jinja": "",
    "ub": "2048",
    "b": "2048",
}

VLLM_DEFAULT_IMAGE = "nvcr.io/nvidia/vllm:25.11-py3"

# Tmux session prefix
SESSION_PREFIX = "svc-"

# Docker container prefix
DOCKER_PREFIX = "vllm-"

# Ensure log dir exists
LOG_DIR.mkdir(parents=True, exist_ok=True)
