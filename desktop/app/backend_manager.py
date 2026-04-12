from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class BackendManager:
    """Start and stop the local FastAPI backend process.

    TODO: Add robust health probing and auto-restart policy.
    """

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        if self._process and self._process.poll() is None:
            return

        project_root = Path(__file__).resolve().parents[2]
        server_dir = project_root / "server"

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]

        self._process = subprocess.Popen(cmd, cwd=server_dir.as_posix())

    def stop(self) -> None:
        if not self._process:
            return

        if self._process.poll() is None:
            self._process.terminate()
            self._process.wait(timeout=5)

        self._process = None
