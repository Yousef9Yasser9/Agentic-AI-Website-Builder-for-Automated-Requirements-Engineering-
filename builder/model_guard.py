"""
Repair LLM-generated models.py: shadow classes, duplicate mapped classes, syntax issues.

Common LLM/refactor bugs:
  class User(Base): ...full model...
  class User(Base):
      __repr__ = lambda self: ...   # overwrites User — breaks SQLAlchemy
  class User:
      def __repr__(self): ...
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Tuple


def _inherits_base(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == "Base":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Base":
            return True
    return False


def _has_tablename(node: ast.ClassDef) -> bool:
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    return True
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if stmt.target.id == "__tablename__":
                return True
    return False


def _column_assignments(node: ast.ClassDef) -> int:
    count = 0
    for stmt in node.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            target = None
            if isinstance(stmt, ast.Assign) and stmt.targets:
                target = stmt.targets[0]
            elif isinstance(stmt, ast.AnnAssign):
                target = stmt.target
            if isinstance(target, ast.Name) and target.id not in ("__tablename__", "__table_args__"):
                if "Column" in ast.dump(stmt):
                    count += 1
    return count


def _class_score(node: ast.ClassDef) -> int:
    """Higher score = more complete SQLAlchemy model."""
    if not _inherits_base(node):
        return 0
    score = 10 if _has_tablename(node) else 0
    score += _column_assignments(node) * 5
    score += len(node.body)
    return score


def deduplicate_model_classes(source: str) -> Tuple[str, List[str]]:
    """
    When the same model name appears multiple times, keep the best definition
    (has __tablename__ and columns) and remove weaker duplicates.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, []

    by_name: dict[str, list[ast.ClassDef]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            by_name.setdefault(node.name, []).append(node)

    remove_ranges: List[Tuple[int, int, str]] = []
    for name, nodes in by_name.items():
        if len(nodes) <= 1:
            continue
        mapped = [n for n in nodes if _inherits_base(n)]
        if len(mapped) <= 1:
            # Shadow without Base when mapped exists
            if mapped and any(not _inherits_base(n) for n in nodes):
                best = mapped[0]
                for n in nodes:
                    if not _inherits_base(n) and n is not best:
                        end = getattr(n, "end_lineno", n.lineno)
                        remove_ranges.append((n.lineno, end, name))
            continue

        best = max(mapped, key=_class_score)
        for n in mapped:
            if n is not best:
                end = getattr(n, "end_lineno", n.lineno)
                remove_ranges.append((n.lineno, end, name))

        for n in nodes:
            if not _inherits_base(n):
                end = getattr(n, "end_lineno", n.lineno)
                remove_ranges.append((n.lineno, end, name))

    if not remove_ranges:
        return source, []

    lines = source.splitlines(keepends=True)
    removed: List[str] = []
    for start, end, name in sorted(remove_ranges, key=lambda x: x[0], reverse=True):
        if name not in removed:
            removed.append(name)
        del lines[start - 1 : end]

    cleaned = "".join(lines).rstrip() + "\n"
    return cleaned, removed


def strip_shadow_model_classes(source: str) -> Tuple[str, List[str]]:
    """Drop plain `class Name:` blocks when a mapped `class Name(Base):` exists."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, []

    mapped_names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and _inherits_base(node)
    }

    remove_ranges: List[Tuple[int, int, str]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not _inherits_base(node):
            if node.name in mapped_names:
                end = getattr(node, "end_lineno", node.lineno)
                remove_ranges.append((node.lineno, end, node.name))

    if not remove_ranges:
        return source, []

    lines = source.splitlines(keepends=True)
    removed: List[str] = []
    for start, end, name in sorted(remove_ranges, key=lambda x: x[0], reverse=True):
        removed.append(name)
        del lines[start - 1 : end]

    cleaned = "".join(lines).rstrip() + "\n"
    return cleaned, removed


def repair_models_source(source: str) -> Tuple[str, List[str]]:
    """Full models.py text repair. Returns (cleaned_source, list of fixes applied)."""
    fixes: List[str] = []
    cleaned, removed_shadow = strip_shadow_model_classes(source)
    if removed_shadow:
        fixes.extend(f"removed shadow {n}" for n in removed_shadow)

    cleaned, removed_dup = deduplicate_model_classes(cleaned)
    if removed_dup:
        fixes.extend(f"removed duplicate {n}" for n in removed_dup)

    return cleaned, fixes


def models_are_loadable(models_path: Path, repo: Path) -> Tuple[bool, str]:
    """Import models in a subprocess-safe check (compile + tablename scan)."""
    if not models_path.exists():
        return False, "models.py missing"
    source = models_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f"syntax error: {exc}"

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and _inherits_base(node):
            if node.name == "GUID":
                continue
            if not _has_tablename(node):
                return False, f"class {node.name}(Base) missing __tablename__"
            if _column_assignments(node) == 0:
                return False, f"class {node.name}(Base) has no Column fields"

    if "class User(Base)" in source or "class User (" in source:
        if not re.search(r"class User\(Base\):[\s\S]*?__tablename__", source):
            return False, "User model is not a valid mapped class"

    return True, ""


def repair_models_file(models_path: Path) -> List[str]:
    """Repair models.py in place. Returns human-readable fix descriptions."""
    if not models_path.exists():
        return []
    original = models_path.read_text(encoding="utf-8")
    cleaned, fixes = repair_models_source(original)
    if fixes:
        models_path.write_text(cleaned, encoding="utf-8")
    return fixes
