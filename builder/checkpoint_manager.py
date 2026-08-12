"""
checkpoint_manager.py
---------------------
Handles saving and loading project checkpoints to/from disk.

Checkpoints are stored at:
  <project_root>/checkpoints/<project_id>/checkpoint.json

Each checkpoint file contains:
  {
    "project_id": "...",
    "project_title": "...",
    "stage": "ARCHITECTURE",
    "saved_at": "2026-03-07T14:00:00",
    "project_data": { ... all stage data ... }
  }
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

# Resolve project root relative to this file:
# builder/checkpoint_manager.py  →  ../../  →  ai-website-builder/
_MODULE_DIR = Path(__file__).resolve().parent          # builder/
_PROJECT_ROOT = _MODULE_DIR.parent                     # ai-website-builder/
CHECKPOINTS_DIR: Path = _PROJECT_ROOT / "checkpoints"


def _ensure_dir() -> None:
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)


def checkpoint_path(project_id: str) -> Path:
    return CHECKPOINTS_DIR / project_id / "checkpoint.json"


def save_checkpoint_history(project_id: str, project_data: dict, stage: str) -> None:
    """
    Append a stage snapshot beside the latest checkpoint.

    The main checkpoint file remains the source of truth for normal loads; this
    history exists so recovery flows can inspect what a stage looked like before
    a later regeneration overwrote it.
    """
    _ensure_dir()
    history_dir = CHECKPOINTS_DIR / project_id / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    entry_path = history_dir / f"{stage}_{timestamp}.json"
    payload = {
        "stage": stage,
        "saved_at": timestamp,
        "project_data": project_data,
    }
    entry_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    same_stage = sorted(history_dir.glob(f"{stage}_*.json"), reverse=True)
    for stale in same_stage[3:]:
        stale.unlink(missing_ok=True)


def load_checkpoint_history(project_id: str, stage: str) -> list[dict]:
    """Return saved stage snapshots, newest first."""
    history_dir = CHECKPOINTS_DIR / project_id / "history"
    if not history_dir.exists():
        return []
    entries: list[dict] = []
    for path in sorted(history_dir.glob(f"{stage}_*.json"), reverse=True):
        try:
            entries.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return entries


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_checkpoint(
    project_id: str,
    project_data: dict,
    stage: str,
    user_id: int | None = None,
) -> Path:
    """
    Persist current project state to disk.
    Returns the path of the written file.
    """
    _ensure_dir()
    project_dir = CHECKPOINTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    title = (
        (project_data.get("cleaned_spec") or {}).get("project_title")
        or project_data.get("plain_text", "")[:40]
        or project_id
    )

    dest = checkpoint_path(project_id)
    existing_user_id: int | None = None
    if dest.exists():
        try:
            existing_payload = json.loads(dest.read_text(encoding="utf-8"))
            existing_user_id = existing_payload.get("user_id")
        except Exception:
            existing_user_id = None

    payload = {
        "project_id": project_id,
        "project_title": title,
        "stage": stage,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "project_data": project_data,
        "user_id": user_id if user_id is not None else existing_user_id,
    }

    # A unique temp file prevents concurrent backend/generator saves from
    # writing into the same .tmp path before the atomic replace.
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=project_dir,
            prefix="checkpoint-",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(serialized)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, dest)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
    return dest


def load_checkpoint(project_id: str) -> tuple[dict, str]:
    """
    Load a project checkpoint from disk.
    Returns (project_data dict, stage string).
    Raises FileNotFoundError if the checkpoint does not exist.
    """
    path = checkpoint_path(project_id)
    if not path.exists():
        raise FileNotFoundError(f"No checkpoint found for project '{project_id}'")

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["project_data"], payload["stage"]


def list_projects() -> list[dict]:
    """
    Scan the checkpoints directory and return a list of project summaries:
    [ { project_id, project_title, stage, saved_at }, ... ]
    Sorted by saved_at descending (most recent first).
    """
    _ensure_dir()
    results: list[dict] = []

    for child in CHECKPOINTS_DIR.iterdir():
        if not child.is_dir():
            continue
        cp_file = child / "checkpoint.json"
        if not cp_file.exists():
            continue
        try:
            payload = json.loads(cp_file.read_text(encoding="utf-8"))
            results.append(
                {
                    "project_id": payload.get("project_id", child.name),
                    "project_title": payload.get("project_title", child.name),
                    "stage": payload.get("stage", "PLAIN_TEXT"),
                    "saved_at": payload.get("saved_at", ""),
                    "user_id": payload.get("user_id"),
                }
            )
        except Exception:
            continue  # skip corrupted checkpoints

    results.sort(key=lambda x: x["saved_at"], reverse=True)
    return results


def delete_checkpoint(project_id: str) -> None:
    """
    Permanently remove a project's checkpoint directory.
    """
    project_dir = CHECKPOINTS_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)


def get_checkpoint_owner(project_id: str) -> Optional[int]:
    path = checkpoint_path(project_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        owner = payload.get("user_id")
        return int(owner) if owner is not None else None
    except Exception:
        return None


def get_project_title(project_id: str) -> Optional[str]:
    """
    Quick helper — reads only the title from the checkpoint without loading
    the full project_data blob.
    """
    path = checkpoint_path(project_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("project_title")
    except Exception:
        return None
