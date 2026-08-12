"""
Start and stop the generated FastAPI app for live HTTP runtime tests.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Optional

import httpx


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _sqlite_db_path_from_url(project_dir: Path, database_url: str) -> Optional[Path]:
    prefix = "sqlite:///"
    if not str(database_url or "").startswith(prefix):
        return None
    raw = str(database_url)[len(prefix):]
    if raw in {"", ":memory:"}:
        return None
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = project_dir / db_path
    return db_path.resolve()


def reset_sqlite_runtime_database(
    project_dir: str | Path,
    env: Dict[str, str],
    log: Optional[Callable[[str], None]] = None,
    label: str = "runtime",
) -> Optional[Path]:
    project_path = Path(project_dir).resolve()
    database_url = env.get("DATABASE_URL", "sqlite:///./runtime_live.db")
    db_path = _sqlite_db_path_from_url(project_path, database_url)
    if not db_path:
        return None

    try:
        db_path.relative_to(project_path)
    except ValueError:
        if log:
            log(f"[db:warn] Refusing to reset SQLite DB outside project: {db_path}")
        return None

    removed = []
    for candidate in [db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")]:
        if candidate.exists() and candidate.is_file():
            candidate.unlink()
            removed.append(candidate.name)
    if removed and log:
        log(f"[db] Reset SQLite {label} database: {', '.join(removed)}")
    return db_path


class RuntimeAppServer:
    """Context manager that runs uvicorn for the generated project."""

    def __init__(
        self,
        project_dir: str,
        python_exe: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        startup_timeout: float = 45.0,
        reset_database: bool = False,
        log: Optional[Callable[[str], None]] = None,
    ):
        self.project_dir = Path(project_dir)
        self.python_exe = python_exe or sys.executable
        self.env = dict(env or os.environ)
        self.startup_timeout = startup_timeout
        self.reset_database = reset_database
        self.log = log
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._proc: Optional[subprocess.Popen] = None
        self.log_path = self.project_dir / ".runtime_server.log"

    def __enter__(self) -> "RuntimeAppServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def start(self) -> None:
        self.env["DATABASE_URL"] = self.env.get("DATABASE_URL", "sqlite:///./runtime_live.db")
        self.env["RUNTIME_TEST_BASE_URL"] = self.base_url
        if self.reset_database:
            reset_sqlite_runtime_database(self.project_dir, self.env, self.log, "runtime")

        from builder.seed_runner import run_seed

        ok, seed_out = run_seed(
            self.project_dir,
            self.python_exe,
            extra_env=self.env,
            timeout=120,
            retry_with_repair=False,
        )
        if not ok:
            raise RuntimeError(f"seed.py failed before server start:\n{seed_out[-4000:]}")

        log_f = open(self.log_path, "w", encoding="utf-8")
        self._proc = subprocess.Popen(
            [
                self.python_exe,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            cwd=str(self.project_dir),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            env=self.env,
        )

        deadline = time.time() + self.startup_timeout
        last_err = ""
        while time.time() < deadline:
            if self._proc.poll() is not None:
                log_f.flush()
                log = self.log_path.read_text(encoding="utf-8", errors="replace")
                raise RuntimeError(f"Server exited early (code {self._proc.returncode}):\n{log[-4000:]}")

            try:
                r = httpx.get(f"{self.base_url}/health", timeout=2.0)
                if r.status_code == 200:
                    return
                last_err = f"health returned {r.status_code}"
            except Exception as e:
                last_err = str(e)
            time.sleep(0.5)

        self.stop()
        log = self.log_path.read_text(encoding="utf-8", errors="replace") if self.log_path.exists() else ""
        raise RuntimeError(f"Server did not become healthy: {last_err}\n{log[-4000:]}")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def restart(self) -> None:
        """Restart so runtime tests execute the source changed by a healing pass."""
        self.stop()
        time.sleep(0.5)
        self.start()

    def read_logs(self, tail: int = 4000) -> str:
        if self.log_path.exists():
            return self.log_path.read_text(encoding="utf-8", errors="replace")[-tail:]
        return ""
