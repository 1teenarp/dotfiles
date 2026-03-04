"""YAML registry CRUD, v1 migration, and port auto-assignment."""

import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from config import DEFAULT_BACKEND, DEFAULT_PORT_RANGE, REGISTRY_FILE, V1_FAVORITES_FILE, V1_REGISTRY_FILE


def _empty_registry():
    return {
        "version": 2,
        "port_range": list(DEFAULT_PORT_RANGE),
        "models": {},
    }


def load() -> dict:
    """Load the v2 registry, creating it if missing."""
    if not REGISTRY_FILE.exists():
        data = _empty_registry()
        save(data)
        return data
    with open(REGISTRY_FILE) as f:
        data = yaml.safe_load(f) or _empty_registry()
    if "models" not in data:
        data["models"] = {}
    return data


def save(data: dict):
    """Write registry to disk."""
    with open(REGISTRY_FILE, "w") as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)


def auto_key(repo: str) -> str:
    """Generate a short key from a HuggingFace repo string.

    Examples:
        unsloth/Qwen3.5-122B-A10B-GGUF:Q5_K_S -> qwen3.5-122b-a10b
        Qwen/QwQ-32B-GGUF -> qwq-32b
        ggml-org/gemma-3-1b-it-GGUF:F16 -> gemma-3-1b
    """
    # Strip quant suffix after colon
    name = repo.split(":")[0]
    # Take the model name part (after /)
    if "/" in name:
        name = name.split("/", 1)[1]
    # Remove common suffixes
    for suffix in ["-GGUF", "-gguf", "-Instruct", "-instruct", "-Chat", "-chat", "-it"]:
        name = name.replace(suffix, "")
    # Remove trailing hyphens and lowercase
    name = name.strip("-").lower()
    return name


def auto_port(data: dict) -> int:
    """Find the next free port in the configured port_range."""
    lo, hi = data.get("port_range", list(DEFAULT_PORT_RANGE))
    used = {m.get("port") for m in data["models"].values() if m.get("port")}
    for port in range(lo, hi):
        if port not in used:
            return port
    raise RuntimeError(f"No free ports in range {lo}-{hi}")


def add_model(
    repo: str,
    backend: str = DEFAULT_BACKEND,
    key: Optional[str] = None,
    port: Optional[int] = None,
    flags: Optional[dict] = None,
) -> str:
    """Add a model to the registry. Returns the key used."""
    data = load()
    key = key or auto_key(repo)
    if key in data["models"]:
        raise ValueError(f"Key '{key}' already exists in registry")
    port = port or auto_port(data)
    entry = {
        "backend": backend,
        "repo": repo,
        "port": port,
        "flags": flags or {},
        "starred": False,
        "added": str(date.today()),
    }
    data["models"][key] = entry
    save(data)
    return key


def remove_model(key: str):
    """Remove a model from the registry."""
    data = load()
    if key not in data["models"]:
        raise KeyError(f"Model '{key}' not found")
    del data["models"][key]
    save(data)


def edit_model(key: str, flags: Optional[dict] = None, port: Optional[int] = None,
               backend: Optional[str] = None, repo: Optional[str] = None):
    """Edit an existing model's fields."""
    data = load()
    if key not in data["models"]:
        raise KeyError(f"Model '{key}' not found")
    model = data["models"][key]
    if flags:
        model["flags"].update(flags)
    if port is not None:
        model["port"] = port
    if backend is not None:
        model["backend"] = backend
    if repo is not None:
        model["repo"] = repo
    save(data)


def toggle_star(key: str):
    """Toggle the starred status of a model."""
    data = load()
    if key not in data["models"]:
        raise KeyError(f"Model '{key}' not found")
    data["models"][key]["starred"] = not data["models"][key].get("starred", False)
    save(data)


def set_flags_raw(key: str, flags_dict: dict):
    """Replace the entire flags dict for a model."""
    data = load()
    if key not in data["models"]:
        raise KeyError(f"Model '{key}' not found")
    data["models"][key]["flags"] = flags_dict
    save(data)


def migrate_v1():
    """Migrate v1 models.yaml + favorites into v2 format."""
    if not V1_REGISTRY_FILE.exists():
        print(f"No v1 registry found at {V1_REGISTRY_FILE}")
        return

    with open(V1_REGISTRY_FILE) as f:
        v1 = yaml.safe_load(f) or {}

    v1_models = v1.get("models", {})
    if not v1_models:
        print("No models in v1 registry")
        return

    # Load favorites
    favorites = set()
    if V1_FAVORITES_FILE.exists():
        favorites = set(V1_FAVORITES_FILE.read_text().strip().splitlines())

    data = load()

    for key, cfg in v1_models.items():
        if key in data["models"]:
            continue  # skip already-migrated

        # Parse v1 flags string into dict
        flags_dict = {}
        flags_str = cfg.get("flags", "")
        if flags_str:
            flags_dict = _parse_flags_string(str(flags_str))

        # Map type -> backend
        v1_type = str(cfg.get("type", "LLAMA")).upper()
        backend_map = {"LLAMA": "llama", "LLAM": "llama", "WHISPER": "whisper", "CUSTOM": "custom"}
        backend = backend_map.get(v1_type, "llama")

        entry = {
            "backend": backend,
            "repo": cfg.get("repo", ""),
            "port": cfg.get("port", 0),
            "flags": flags_dict,
            "starred": key in favorites,
            "added": str(date.today()),
        }
        data["models"][key] = entry

    save(data)
    count = len(v1_models)
    print(f"Migrated {count} models from v1 registry")


def _parse_flags_string(flags_str: str) -> dict:
    """Parse a v1 flags string like '-fa on --temp 1.0 -ngl 999' into a dict."""
    flags = {}
    tokens = flags_str.split()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("-"):
            key = token.lstrip("-")
            # Check if next token is a value (not a flag)
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                flags[key] = tokens[i + 1]
                i += 2
            else:
                flags[key] = ""
                i += 1
        else:
            i += 1
    return flags
