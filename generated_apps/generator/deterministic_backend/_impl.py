"""
Deterministic backend writers for generated FastAPI apps.

Implementation module for ``generated_apps.generator.deterministic_backend``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from builder.app_contract import build_app_contract, resource_path


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "generated-app"


def entity_class_name(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", str(name)))


def resource_name(entity_name: str) -> str:
    return resource_path(entity_name)


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


def make_jinja_env(templates_dir: str | Path) -> Environment:
    """Jinja2 environment with all custom filters required by backend templates."""
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    env.filters["tojson"] = lambda v, **kw: json.dumps(v, ensure_ascii=False)
    env.filters["pascal"] = lambda v: "".join(
        (x[0].upper() + x[1:] if x else "") for x in re.split(r"[^a-zA-Z0-9]+", str(v))
    )
    env.filters["slugify"] = slugify
    env.filters["resource_name"] = resource_name
    return env


def _templates_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        cand = parent / "templates"
        if cand.is_dir():
            return cand
    raise FileNotFoundError("templates folder not found (searched from deterministic_backend)")


def write_deterministic_schemas(out_dir: str | Path, project_data: Dict[str, Any]) -> Path:
    """Render schemas.py from the stable Jinja2 template."""
    out_path = Path(out_dir)
    env = make_jinja_env(_templates_dir())
    tpl = env.get_template("fastapi_app/app/schemas.py.j2")
    cleaned = project_data.get("cleaned_spec", {}) or {}
    title = cleaned.get("project_title") or "Generated App"
    architecture = project_data.get("architecture", {}) or {}
    contract = build_app_contract(project_data)
    normalized_dm = {"entities": [_contract_entity_dict(spec) for spec in contract.business_entities()]}
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
    schema_file = out_path / "app" / "schemas.py"
    schema_file.parent.mkdir(parents=True, exist_ok=True)
    schema_file.write_text(rendered, encoding="utf-8")
    return schema_file


def write_deterministic_crud(out_dir: str | Path, project_data: Dict[str, Any]) -> Path:
    """Render generic_crud.py from the stable Jinja2 template."""
    out_path = Path(out_dir)
    env = make_jinja_env(_templates_dir())
    tpl = env.get_template("fastapi_app/routers/generic_crud.py.j2")
    cleaned = project_data.get("cleaned_spec", {}) or {}
    title = cleaned.get("project_title") or "Generated App"
    architecture = project_data.get("architecture", {}) or {}
    contract = build_app_contract(project_data)
    enriched_entities = [_contract_entity_dict(spec) for spec in contract.business_entities()]
    rendered = tpl.render(
        project_title=title,
        data_model={"entities": enriched_entities},
        contract=contract.to_dict(),
        architecture=architecture,
        cleaned_spec=cleaned,
        requirements=project_data.get("requirements", {}) or {},
        user_stories=project_data.get("user_stories", {}) or {},
        project_slug=slugify(title),
    )
    crud_file = out_path / "app" / "routers" / "generic_crud.py"
    crud_file.parent.mkdir(parents=True, exist_ok=True)
    crud_file.write_text(rendered, encoding="utf-8")
    return crud_file


def write_deterministic_models(out_dir: str | Path, project_data: Dict[str, Any]) -> Path:
    from builder.models_seed_guard import write_deterministic_models as _write

    return _write(out_dir, project_data)


def ensure_valid_models(
    out_dir: str | Path,
    project_data: Dict[str, Any],
    log: Optional[Callable[[str], None]] = None,
) -> List[str]:
    """Delegate to builder.models_seed_guard (stable import for Streamlit)."""
    from builder.models_seed_guard import ensure_valid_models as _ensure

    return _ensure(out_dir, project_data, log=log)


def write_deterministic_seed(out_dir: str | Path, project_data: Dict[str, Any]) -> Path:
    from builder.models_seed_guard import write_deterministic_seed as _write

    return _write(out_dir, project_data)


DETERMINISTIC_BACKEND_FILES = frozenset({
    "app/main.py",
    "app/models.py",
    "app/schemas.py",
    "app/routers/generic_crud.py",
    "seed.py",
    "frontend_templates/index.html",
    "frontend_templates/app.html",
})


def render_deterministic_file(
    out_dir: Path,
    out_rel: str,
    project_data: Dict[str, Any],
    theme: Optional[Dict[str, Any]] = None,
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """Write one backend file using the deterministic engine. Returns True on success."""
    _log = log or (lambda _m: None)
    try:
        if out_rel == "app/models.py":
            write_deterministic_models(out_dir, project_data)
        elif out_rel == "app/schemas.py":
            write_deterministic_schemas(out_dir, project_data)
        elif out_rel == "app/routers/generic_crud.py":
            write_deterministic_crud(out_dir, project_data)
        elif out_rel == "seed.py":
            write_deterministic_seed(out_dir, project_data)
        elif out_rel == "app/main.py":
            from generated_apps.generator.repo_generator import _write_main_routes
            _write_main_routes(out_dir, project_data)
        elif out_rel in {"frontend_templates/app.html", "frontend_templates/index.html"}:
            from generated_apps.generator.repo_generator import _write_frontend_shell
            arch = project_data.get("architecture", {}) or {}
            th = theme or arch.get("theme", {}) or {}
            ui_sel = project_data.get("ui_selection", {}) or {}
            if ui_sel.get("theme_vars"):
                th = {**th, **ui_sel["theme_vars"]}
            _write_frontend_shell(out_dir, project_data, th)
        else:
            return False
        _log(f"[deterministic] Wrote {out_rel}")
        return True
    except Exception as exc:
        _log(f"[error] Deterministic write failed for {out_rel}: {exc}")
        return False


def apply_deterministic_guard(
    out_dir: str | Path,
    project_data: Dict[str, Any],
    theme: Optional[Dict[str, Any]] = None,
    log: Optional[Callable[[str], None]] = None,
) -> List[str]:
    """
    Overwrite all critical backend/frontend shell files with deterministic implementations.
    Returns list of relative paths written.
    """
    from generated_apps.generator.repo_generator import _write_frontend_shell, _write_main_routes

    _log = log or (lambda _m: None)
    root = Path(out_dir)
    written: List[str] = []

    write_deterministic_models(root, project_data)
    written.append("app/models.py")

    arch = project_data.get("architecture", {}) or {}
    th = dict(theme or arch.get("theme", {}) or {})
    ui_sel = project_data.get("ui_selection", {}) or {}
    if ui_sel.get("theme_vars"):
        th = {**th, **ui_sel["theme_vars"]}

    _write_main_routes(root, project_data)
    written.append("app/main.py")
    write_deterministic_schemas(root, project_data)
    written.append("app/schemas.py")
    write_deterministic_crud(root, project_data)
    written.append("app/routers/generic_crud.py")
    write_deterministic_seed(root, project_data)
    written.append("seed.py")
    _write_frontend_shell(root, project_data, th)
    written.append("frontend_templates/index.html")
    written.append("frontend_templates/app.html")

    return written
