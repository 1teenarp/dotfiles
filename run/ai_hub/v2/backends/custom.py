"""Custom backend — tmux + arbitrary command."""

import subprocess
from pathlib import Path

from backends import BackendBase, register_backend
from config import LOG_DIR, SESSION_PREFIX


@register_backend("custom")
class CustomBackend(BackendBase):

    @property
    def session_name(self) -> str:
        return f"{SESSION_PREFIX}{self.key}"

    @property
    def log_file(self) -> str:
        return str(LOG_DIR / f"service-{self.key}.log")

    def start(self):
        if self.is_running():
            print(f"{self.key} is already running")
            return

        repo = self.config["repo"]  # the command to run
        port = self.config["port"]
        flags = self.flags_to_args()

        cmd = (
            f"bash -c '{repo} --host 0.0.0.0 --port {port} {flags}' "
            f"> {self.log_file} 2>&1"
        )

        subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.session_name, cmd],
            check=True,
        )

    def stop(self):
        if not self.is_running():
            return
        subprocess.run(
            ["tmux", "kill-session", "-t", self.session_name],
            capture_output=True,
        )

    def is_running(self) -> bool:
        result = subprocess.run(
            ["tmux", "list-sessions"],
            capture_output=True, text=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith(f"{self.session_name}:"):
                return True
        return False

    def logs(self, lines: int = 50) -> str:
        log = Path(self.log_file)
        if not log.exists():
            return "(no logs)"
        all_lines = log.read_text().splitlines()
        return "\n".join(all_lines[-lines:])
