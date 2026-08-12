"""
Stable models + seed repair for generated apps.

Imported by builder/app.py and builder/seed_runner.py so Build & Run never
depends on a fragile generated_apps.generator.deterministic_backend import path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader

from builder.app_contract import build_app_contract, resource_path
from builder.model_guard import models_are_loadable, repair_models_file


def _find_repo_root() -> Path:
    """Locate ai-website-builder root (folder that contains templates/)."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "templates").is_dir():
            return parent
    raise FileNotFoundError("Could not locate project templates/ directory")


def _templates_dir() -> Path:
    root = _find_repo_root()
    templates = root / "templates"
    if not templates.is_dir():
        raise FileNotFoundError(f"templates folder not found at: {templates}")
    return templates


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_templates_dir())),
        autoescape=False,
        keep_trailing_newline=True,
    )
    env.filters["tojson"] = lambda v, **kw: json.dumps(v, ensure_ascii=False)
    env.filters["pascal"] = lambda v: "".join(
        (x[0].upper() + x[1:] if x else "") for x in re.split(r"[^a-zA-Z0-9]+", str(v))
    )
    env.filters["slugify"] = lambda text: re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-") or "app"
    env.filters["resource_name"] = resource_path
    return env


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "generated-app"


def _contract_entity_dict(spec) -> Dict[str, Any]:
    return {
        "name": spec.raw_name,
        "class_name": spec.class_name,
        "resource": spec.resource,
        "fields": spec.fields,
        "read_roles": spec.read_roles,
        "write_roles": spec.write_roles,
        "role_scope_fields": spec.scope_fields,
        "scope_fields": spec.scope_fields,
        "ui_visible": spec.ui_visible,
        "is_user_entity": spec.is_user_entity,
    }


def write_deterministic_models(out_dir: str | Path, project_data: Dict[str, Any]) -> Path:
    """Render models.py from the stable Jinja2 template."""
    out_path = Path(out_dir)
    env = _make_env()
    tpl = env.get_template("fastapi_app/app/models.py.j2")
    cleaned = project_data.get("cleaned_spec", {}) or {}
    title = cleaned.get("project_title") or "Generated App"
    architecture = project_data.get("architecture", {}) or {}
    dm = project_data.get("data_model", {}) or {}
    contract = build_app_contract(project_data)
    user_specs = [spec for spec in contract.entities if spec.is_user_entity]
    normalized_dm = {
        **dm,
        "entities": [_contract_entity_dict(spec) for spec in [*user_specs, *contract.business_entities()]],
    }
    rendered = tpl.render(
        project_title=title,
        data_model=normalized_dm,
        contract=contract.to_dict(),
        architecture=architecture,
        cleaned_spec=cleaned,
        requirements=project_data.get("requirements", {}) or {},
        user_stories=project_data.get("user_stories", {}) or {},
        project_slug=slugify(title),
    )
    models_file = out_path / "app" / "models.py"
    models_file.parent.mkdir(parents=True, exist_ok=True)
    models_file.write_text(rendered, encoding="utf-8")
    return models_file


def write_deterministic_seed(out_dir: str | Path, project_data: Dict[str, Any]) -> Path:
    """Render seed.py from the stable Jinja2 template."""
    out_path = Path(out_dir)
    env = _make_env()
    tpl = env.get_template("fastapi_app/seed.py.j2")
    cleaned = project_data.get("cleaned_spec", {}) or {}
    title = cleaned.get("project_title") or "Generated App"
    architecture = project_data.get("architecture", {}) or {}
    raw_theme = architecture.get("theme", {}) or {}
    ui_sel = project_data.get("ui_selection", {}) or {}
    theme = {**raw_theme, **(ui_sel.get("theme_vars") or {})}
    dm = project_data.get("data_model", {}) or {}
    contract = build_app_contract(project_data)
    normalized_dm = {**dm, "entities": [_contract_entity_dict(spec) for spec in contract.business_entities()]}
    rendered = tpl.render(
        project_title=title,
        cleaned_spec=cleaned,
        requirements=project_data.get("requirements", {}) or {},
        user_stories=project_data.get("user_stories", {}) or {},
        architecture=architecture,
        data_model=normalized_dm,
        contract=contract.to_dict(),
        demo_accounts=contract.demo_accounts,
        public_role=contract.public_role,
        project_slug=slugify(title),
        project_id=project_data.get("project_id", ""),
        theme=theme,
    )
    seed_file = out_path / "seed.py"
    seed_file.write_text(rendered, encoding="utf-8")
    return seed_file


def _entity_class_name(name: str) -> str:
    return "".join(
        part[:1].upper() + part[1:]
        for part in re.findall(r"[A-Za-z0-9]+", str(name))
    )


def _expected_model_classes(project_data: Dict[str, Any]) -> List[str]:
    classes = ["User"]
    for entity in (project_data.get("data_model", {}) or {}).get("entities", []) or []:
        class_name = _entity_class_name(entity.get("name", ""))
        if class_name and class_name != "User" and class_name not in classes:
            classes.append(class_name)
    return classes


def _models_contract_ok(models_path: Path, project_data: Dict[str, Any]) -> Tuple[bool, str]:
    if not models_path.exists():
        return False, "models.py is missing"
    content = models_path.read_text(encoding="utf-8", errors="ignore")
    stripped = content.strip()
    if stripped in {"...", "pass"} or len(stripped) < 400:
        return False, "models.py is placeholder or too small"
    required_markers = (
        "from app.db import Base",
        "class User(Base):",
        "__tablename__ = \"users\"",
        "password_hash",
        "created_at",
        "updated_at",
    )
    missing = [marker for marker in required_markers if marker not in content]
    if missing:
        return False, "missing auth model markers: " + ", ".join(missing)
    missing_classes = [
        class_name
        for class_name in _expected_model_classes(project_data)
        if f"class {class_name}(Base):" not in content
    ]
    if missing_classes:
        return False, "missing model classes: " + ", ".join(missing_classes)
    if any(marker in content for marker in ("{{", "{%", "{#")):
        return False, "models.py still contains template syntax"
    return True, ""


def ensure_valid_models(
    out_dir: str | Path,
    project_data: Dict[str, Any],
    log: Optional[Callable[[str], None]] = None,
) -> List[str]:
    """
    Repair LLM models.py (duplicate/shadow classes) or replace with deterministic template.
    """
    _log = log or (lambda _m: None)
    root = Path(out_dir)
    models_path = root / "app" / "models.py"
    actions: List[str] = []

    if not models_path.exists():
        _log("[models] models.py missing — writing deterministic models.py")
        write_deterministic_models(root, project_data)
        actions.append("created deterministic models.py")
        return actions

    fixes = repair_models_file(models_path)
    if fixes:
        actions.extend(fixes)
        _log(f"[models] Repaired: {', '.join(fixes[:6])}")

    contract_ok, contract_error = _models_contract_ok(models_path, project_data)
    if not contract_ok:
        _log(f"[models] Contract invalid ({contract_error}) - replacing with deterministic models.py")
        write_deterministic_models(root, project_data)
        repair_models_file(models_path)
        actions.append("replaced placeholder/incomplete models.py")

    ok, err = models_are_loadable(models_path, root)
    if not ok:
        _log(f"[models] Still invalid ({err}) — replacing with deterministic models.py")
        write_deterministic_models(root, project_data)
        repair_models_file(models_path)
        actions.append("replaced with deterministic models.py")
        ok, err = models_are_loadable(models_path, root)
        if not ok:
            raise RuntimeError(f"models.py invalid after deterministic rewrite: {err}")

    return actions
