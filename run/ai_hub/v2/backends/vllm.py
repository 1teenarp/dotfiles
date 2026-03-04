"""vLLM backend — Docker container lifecycle."""

import subprocess
from pathlib import Path

from backends import BackendBase, register_backend
from config import CACHE_DIR, DOCKER_PREFIX, VLLM_DEFAULT_IMAGE


@register_backend("vllm")
class VllmBackend(BackendBase):

    @property
    def container_name(self) -> str:
        return f"{DOCKER_PREFIX}{self.key}"

    @property
    def docker_image(self) -> str:
        return self.config.get("docker_image", VLLM_DEFAULT_IMAGE)

    def _resolve_model_path(self) -> str:
        """Resolve the GGUF model path inside the container's /models mount."""
        repo = self.config["repo"]
        # repo format: owner/name-GGUF:quant or owner/name-GGUF
        parts = repo.split(":")
        repo_path = parts[0]  # owner/name-GGUF
        return f"/models/{repo_path}"

    def start(self):
        if self.is_running():
            print(f"{self.key} is already running")
            return

        port = self.config["port"]
        flags = self.flags_to_args()
        model_path = self._resolve_model_path()

        cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "--privileged",
            "--gpus", "all",
            "-v", f"{CACHE_DIR}:/models:ro",
            "-p", f"{port}:{port}",
            self.docker_image,
            "vllm", "serve", model_path,
            "--host", "0.0.0.0",
            "--port", str(port),
        ]

        # Append extra flags
        if flags:
            cmd.extend(flags.split())

        subprocess.run(cmd, check=True)

    def stop(self):
        subprocess.run(["docker", "stop", self.container_name], capture_output=True)
        subprocess.run(["docker", "rm", self.container_name], capture_output=True)

    def is_running(self) -> bool:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name=^/{self.container_name}$",
             "--format", "{{.Names}}"],
            capture_output=True, text=True,
        )
        return self.container_name in result.stdout.strip()

    def logs(self, lines: int = 50) -> str:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), self.container_name],
            capture_output=True, text=True,
        )
        return result.stdout + result.stderr
