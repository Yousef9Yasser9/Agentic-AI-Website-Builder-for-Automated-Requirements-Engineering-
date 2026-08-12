"""
Repair common generator import layout issues before Streamlit loads modules.

If an empty ``deterministic_backend/`` package exists beside the real implementation,
Python imports the package and ``ensure_valid_models`` (and seed) fail with ImportError.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def repair_deterministic_backend_layout(project_root: Path | None = None) -> None:
    """Remove broken shadow packages; drop legacy single-file module if package exists."""
    root = Path(project_root or Path(__file__).resolve().parent.parent)
    gen = root / "generated_apps" / "generator"
    pkg = gen / "deterministic_backend"
    legacy_mod = gen / "deterministic_backend.py"
    impl = pkg / "_impl.py"

    if pkg.is_dir() and not impl.is_file():
        shutil.rmtree(pkg, ignore_errors=True)
        _purge_import_cache(gen)

    if legacy_mod.is_file() and pkg.is_dir() and impl.is_file():
        legacy_mod.unlink(missing_ok=True)

    if pkg.is_dir() and impl.is_file():
        _purge_import_cache(gen)


def _purge_import_cache(gen_dir: Path) -> None:
    prefix = "generated_apps.generator.deterministic_backend"
    for name in list(sys.modules):
        if name == prefix or name.startswith(prefix + "."):
            del sys.modules[name]
    stale = gen_dir / "deterministic_backend.py"
    if stale.is_file():
        stale.unlink(missing_ok=True)
