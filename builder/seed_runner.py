"""
Reliable seed execution for generated FastAPI projects.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_repo_env(repo: Path, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Load DATABASE_URL and PYTHONPATH from the generated project .env."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo.resolve())

    env_file = repo / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip('"').strip("'")

    env.setdefault("DATABASE_URL", "sqlite:///./app.db")
    if extra:
        env.update(extra)
    return env


def load_project_data(repo: Path) -> Dict[str, Any]:
    artifacts = repo / "_builder_artifacts" / "project_data.json"
    if artifacts.exists():
        return json.loads(artifacts.read_text(encoding="utf-8"))
    return {}


def repair_seed_script(repo: Path, project_data: Optional[Dict[str, Any]] = None) -> Path:
    """Regenerate seed.py from the deterministic Jinja2 template."""
    from builder.models_seed_guard import write_deterministic_seed

    data = project_data or load_project_data(repo)
    return write_deterministic_seed(repo, data)


def _repair_models_if_needed(repo: Path, project_data: Optional[Dict[str, Any]] = None) -> List[str]:
    from builder.models_seed_guard import ensure_valid_models

    data = project_data or load_project_data(repo)
    return ensure_valid_models(repo, data)


def run_seed(
    repo: Path,
    python_exe: str,
    *,
    project_data: Optional[Dict[str, Any]] = None,
    extra_env: Optional[Dict[str, str]] = None,
    timeout: int = 120,
    retry_with_repair: bool = False,
) -> Tuple[bool, str]:
    """
    Run the generated seed.py with the project environment.

    Returns:
        (success, combined_output)
    """
    repo = Path(repo)
    if retry_with_repair:
        _repair_models_if_needed(repo, project_data)
    seed_script = repo / "seed.py"
    if not seed_script.exists():
        if retry_with_repair:
            repair_seed_script(repo, project_data)
        if not seed_script.exists():
            return False, "seed.py not found"

    env = load_repo_env(repo, extra_env)

    def _execute() -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(python_exe), str(seed_script.name)],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )

    result = _execute()
    output = (result.stdout or "") + "\n" + (result.stderr or "")

    if result.returncode == 0:
        return True, output

    if retry_with_repair:
        _repair_models_if_needed(repo, project_data)
        repair_seed_script(repo, project_data)
        result = _execute()
        output += "\n--- RETRY AFTER SEED REPAIR ---\n" + (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode == 0:
            return True, output

        if "InvalidRequestError" in output or "__tablename__" in output or "declarative base" in output:
            from builder.models_seed_guard import write_deterministic_models

            write_deterministic_models(repo, project_data or load_project_data(repo))
            _repair_models_if_needed(repo, project_data)
            repair_seed_script(repo, project_data)
            result = _execute()
            output += "\n--- RETRY AFTER DETERMINISTIC MODELS ---\n" + (result.stdout or "") + "\n" + (result.stderr or "")
            if result.returncode == 0:
                return True, output

    return False, output
