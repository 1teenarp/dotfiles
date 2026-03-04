"""Backend abstraction and dispatch."""

from abc import ABC, abstractmethod
from typing import Optional


class BackendBase(ABC):
    """Abstract base class for model backends."""

    def __init__(self, key: str, config: dict):
        self.key = key
        self.config = config

    @abstractmethod
    def start(self):
        """Start the model service."""

    @abstractmethod
    def stop(self):
        """Stop the model service."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the service is currently running."""

    @abstractmethod
    def logs(self, lines: int = 50) -> str:
        """Return recent log output."""

    def flags_to_args(self) -> str:
        """Convert flags dict to CLI argument string.

        {fa: "on", temp: "1.0"} -> "-fa on --temp 1.0"
        Single-char keys get single dash, multi-char get double dash.
        Empty string values produce just the flag (e.g. --jinja).
        """
        flags = self.config.get("flags", {})
        if not flags:
            return ""
        parts = []
        for k, v in flags.items():
            prefix = "-" if len(k) <= 2 else "--"
            if v == "" or v is None:
                parts.append(f"{prefix}{k}")
            else:
                parts.append(f"{prefix}{k} {v}")
        return " ".join(parts)


# Backend dispatch registry
_BACKENDS: dict[str, type[BackendBase]] = {}


def register_backend(name: str):
    """Decorator to register a backend class."""
    def wrapper(cls):
        _BACKENDS[name] = cls
        return cls
    return wrapper


def get_backend(key: str, config: dict) -> BackendBase:
    """Instantiate the appropriate backend for a model config."""
    backend_name = config.get("backend", "llama")
    if backend_name not in _BACKENDS:
        raise ValueError(f"Unknown backend '{backend_name}'. Available: {list(_BACKENDS.keys())}")
    return _BACKENDS[backend_name](key, config)


def load_all_backends():
    """Import all backend modules to trigger registration."""
    from backends import llama, vllm, whisper, custom  # noqa: F401
