"""
Strict Python syntax validation for generated / repaired source files.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


CORE_PYTHON_FILES = (
    "app/main.py",
    "app/models.py",
    "app/schemas.py",
    "app/db.py",
    "app/deps.py",
    "app/auth.py",
    "app/routers/auth.py",
    "app/routers/generic_crud.py",
    "seed.py",
)


@dataclass
class SyntaxIssue:
    path: str
    message: str
    lineno: Optional[int] = None


def validate_python_syntax(source: str, filename: str = "<generated>") -> Tuple[bool, Optional[str], Optional[int]]:
    """Return (ok, error_message, line_number)."""
    if not source or len(source.strip()) < 10:
        return False, "File is empty or too short", None
    try:
        ast.parse(source, filename=filename)
        return True, None, None
    except SyntaxError as exc:
        return False, str(exc.msg or exc), exc.lineno


def validate_project_python_files(
    project_dir: str | Path,
    relative_paths: Optional[List[str]] = None,
) -> List[SyntaxIssue]:
    """Validate syntax of core generated Python files."""
    root = Path(project_dir)
    paths = relative_paths or list(CORE_PYTHON_FILES)
    issues: List[SyntaxIssue] = []
    for rel in paths:
        fp = root / rel
        if not fp.exists():
            issues.append(SyntaxIssue(rel, "File missing"))
            continue
        source = fp.read_text(encoding="utf-8")
        ok, msg, lineno = validate_python_syntax(source, rel)
        if not ok:
            issues.append(SyntaxIssue(rel, msg or "Syntax error", lineno))
    return issues
