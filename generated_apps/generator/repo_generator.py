from __future__ import annotations

import json
import hashlib
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from jinja2 import Environment, FileSystemLoader

from builder.app_contract import build_app_contract, resource_path
from generated_apps.generator.deterministic_backend import (
    apply_deterministic_guard,
    ensure_valid_models,
    make_jinja_env,
    render_deterministic_file,
    write_deterministic_crud,
    write_deterministic_models,
    write_deterministic_schemas,
    write_deterministic_seed,
)

# Re-export for contract_validator / runtime repair (stable public API)
__all__ = [
    "generate_repo",
    "write_deterministic_crud",
    "write_deterministic_schemas",
    "write_deterministic_seed",
    "write_deterministic_models",
    "ensure_valid_models",
    "apply_deterministic_guard",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "generated-app"


def _project_roles(project_data: dict) -> list[str]:
    return build_app_contract(project_data).roles


def _default_public_role(project_data: dict) -> str:
    return build_app_contract(project_data).public_role


@dataclass
class GenerateResult:
    out_dir: str
    project_slug: str


FORCED_SOURCE_FILES = frozenset({
    "app/db.py",
    "app/auth.py",
    "app/deps.py",
    "app/routers/auth.py",
    "app/models.py",
    "app/schemas.py",
    "app/routers/generic_crud.py",
    "app/main.py",
    "seed.py",
    "frontend_templates/index.html",
    "frontend_templates/login.html",
    "frontend_templates/register.html",
    "frontend_templates/app.html",
    "frontend_templates/entity_list.html",
    "frontend_templates/entity_form.html",
})


def _make_env(loader_path: str) -> Environment:
    """Jinja2 env with resource_name filter (delegates to deterministic_backend)."""
    return make_jinja_env(loader_path)


# ---------------------------------------------------------------------------
# LLM output cleaning
# ---------------------------------------------------------------------------
def _clean_llm_code(raw: str, file_type: str = "python") -> str:
    """Strip markdown fences and common LLM chatter from generated code."""
    if not raw:
        return ""

    code = raw.strip()

    fenced_blocks = re.findall(
        r"```(?:python|py|html|javascript|js|css)?\s*(.*?)```",
        code,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced_blocks:
        code = max(fenced_blocks, key=len).strip()

    # Remove triple-backtick fences (```python ... ``` or ```html ... ```)
    code = re.sub(r"^```[\w]*\s*", "", code, flags=re.IGNORECASE)
    code = re.sub(r"\s*```\s*$", "", code).strip()

    # Remove common AI "wrapper" quotes
    if ((code.startswith('"') and code.endswith('"')) or
            (code.startswith("'") and code.endswith("'"))):
        if not (code.startswith('"""') or code.startswith("'''")):
            code = code[1:-1].replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'").strip()

    # Strip trailing AI chatter (lines starting with conversational words)
    chatter_re = re.compile(
        r"\n\s*(?:Note:|This (?:code|file|script)|I have|Here's|Let me know|Hope this).*$",
        re.DOTALL | re.IGNORECASE,
    )
    code = chatter_re.sub("", code).strip()

    if file_type == "python":
        lines = code.splitlines()
        for index, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith(
                ("from ", "import ", "#", '"""', "'''", "@")
            ):
                code = "\n".join(lines[index:]).strip()
                break

    return code


def _validate_python(code: str) -> bool:
    """Return True if code compiles without SyntaxError."""
    if len(code) < 30:
        return False
    try:
        compile(code, "<llm>", "exec")
        return True
    except SyntaxError:
        return False


def _validate_html(code: str) -> bool:
    """Return True for a complete plain HTML document with no template syntax."""
    if len(code) < 50:
        return False
    lower = code.lower()
    if any(marker in code for marker in ("{{", "{%", "{#")):
        return False
    return ("<!doctype html" in lower or "<html" in lower) and "</html>" in lower


def _validate_source_contract(code: str, out_rel: str, project_data: dict) -> tuple[bool, str]:
    required_markers = {
        "app/db.py": ("SessionLocal", "def get_db", "DATABASE_URL", "sqlite:///"),
        "app/auth.py": ("def hash_password", "def create_access_token", "def decode_access_token"),
        "app/deps.py": ("def get_current_user", "def require_admin", ".lower()"),
        "app/routers/auth.py": ("/register", "/login", "/login/form", "PUBLIC_REGISTER_ROLE"),
        "app/models.py": ("class User", "password_hash", "created_at", "updated_at"),
        "app/schemas.py": ("class UserCreate", "class LoginRequest", "class Token"),
        "app/routers/generic_crud.py": ("get_current_user", "model_dump", "HTTPException"),
        "app/main.py": ("/health", "dashboard/stats", "app.html"),
        "seed.py": ("Base.metadata.create_all", "Admin"),
        "frontend_templates/index.html": ("access_token", "apiFetch", "dashboard/stats"),
        "frontend_templates/login.html": ("access_token", "apiFetch", "/api/auth/me"),
        "frontend_templates/register.html": ("access_token", "apiFetch", "/api/auth/register", "/api/auth/login", "/api/auth/me"),
        "frontend_templates/app.html": ("access_token", "apiFetch", "dashboard/stats"),
        "frontend_templates/entity_list.html": ("access_token", "apiFetch", "ENTITY_OVERRIDE"),
        "frontend_templates/entity_form.html": ("access_token", "apiFetch", "SCHEMA_MAP"),
    }
    if out_rel == "seed.py" and "drop_all" in code:
        return False, "seed.py must never drop application data"
    if out_rel.startswith("frontend_templates/") and any(
        marker in code for marker in ("{{", "{%", "{#")
    ):
        return False, "plain HTML cannot contain Jinja/template syntax"
    missing = [marker for marker in required_markers.get(out_rel, ()) if marker not in code]
    if missing:
        return False, f"missing required contract markers: {', '.join(missing)}"

    contract = build_app_contract(project_data)
    entities = contract.business_entities()
    if out_rel == "app/models.py":
        missing_classes = [
            entity.class_name
            for entity in entities
            if f"class {entity.class_name}(Base):" not in code
        ]
        missing_classes = [name for name in missing_classes if name]
        if missing_classes:
            return False, "missing model classes: " + ", ".join(missing_classes)
        if any(marker in code for marker in ("{{", "{%", "{#")):
            return False, "models.py cannot contain template syntax"
    if out_rel == "app/schemas.py":
        missing_schemas: list[str] = []
        for entity in entities:
            class_name = entity.class_name
            for suffix in ("Create", "Update", "Read"):
                marker = f"class {class_name}{suffix}"
                if class_name and marker not in code:
                    missing_schemas.append(f"{class_name}{suffix}")
        if missing_schemas:
            return False, "missing schema classes: " + ", ".join(missing_schemas)

    if out_rel == "app/routers/generic_crud.py":
        ownership_fields = {
            field.get("name")
            for entity in entities
            for field in entity.fields
        } & {"user_id", "owner_id", "created_by", "customer_id", "uploader_id"}
        if ownership_fields and not any(field in code for field in ownership_fields):
            if "require_role" not in code and "get_current_user" not in code:
                return False, "owned entities require authenticated or role-restricted CRUD queries"
    if out_rel in {"frontend_templates/app.html", "frontend_templates/index.html"}:
        if "apiFetch" not in code and "function api(" not in code:
            return False, "application shell must include an authenticated API helper"
    if out_rel in {"frontend_templates/login.html", "frontend_templates/register.html"}:
        if "apiFetch" not in code and "fetch(" not in code:
            return False, "auth pages must include an API request helper"
    return True, ""


def _write_frontend_contract_page(out_dir: Path, out_rel: str) -> bool:
    markers = {
        "frontend_templates/entity_list.html": "const ENTITY_OVERRIDE = window.PAGE_ENTITY || '';",
        "frontend_templates/entity_form.html": "const SCHEMA_MAP = window.SCHEMA_MAP || {};",
    }
    marker = markers.get(out_rel)
    if not marker:
        return False
    content = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Loading workspace</title>
</head>
<body>
  <p>Loading application workspace...</p>
  <script>
    {marker}
    const access_token = localStorage.getItem('access_token') || '';
    async function apiFetch(path, options = {{}}) {{
      return fetch(path, {{
        ...options,
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': access_token ? 'Bearer ' + access_token : '',
          ...(options.headers || {{}})
        }}
      }});
    }}
    if (!access_token) {{
      location.href = '/ui/login?next=' + encodeURIComponent(location.pathname);
    }} else {{
      location.href = location.pathname;
    }}
  </script>
</body>
</html>
"""
    path = out_dir / out_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_invariant_db(out_dir: Path) -> bool:
    content = '''from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

_DEFAULT_DB = Path(__file__).resolve().parents[1] / "app.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB.as_posix()}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''
    path = out_dir / "app" / "db.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_invariant_deps(out_dir: Path) -> bool:
    content = '''from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import models
from app.auth import decode_access_token
from app.db import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.role or current_user.role.lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_role(*roles: str):
    allowed = {role.lower() for role in roles}

    def checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if not current_user.role or current_user.role.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {list(roles)}",
            )
        return current_user

    return checker
'''
    path = out_dir / "app" / "deps.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_invariant_auth_router(out_dir: Path, public_role: str = "Customer") -> bool:
    content = f'''from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import create_access_token, hash_password, verify_password
from app.deps import get_current_user, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
PUBLIC_REGISTER_ROLE = {public_role!r}


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(body: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=body.email,
        password_hash=hash_password(body.password),
        role=PUBLIC_REGISTER_ROLE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({{"sub": str(user.id), "role": user.role}})
    return {{"access_token": token, "token_type": "bearer"}}


@router.post("/login/form", response_model=schemas.Token)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({{"sub": str(user.id), "role": user.role}})
    return {{"access_token": token, "token_type": "bearer"}}


@router.get("/me", response_model=schemas.UserRead)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
'''
    path = out_dir / "app" / "routers" / "auth.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_invariant_auth(out_dir: Path) -> bool:
    content = '''from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "change_me_in_production_please")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
'''
    path = out_dir / "app" / "auth.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_forced_source_file(
    out_dir: Path,
    out_rel: str,
    project_data: dict,
    theme: dict,
    validator: Callable[[str], bool],
    log: Callable[[str], None],
) -> bool:
    wrote = False
    if out_rel == "app/db.py":
        wrote = _write_invariant_db(out_dir)
    elif out_rel == "app/auth.py":
        wrote = _write_invariant_auth(out_dir)
    elif out_rel == "app/deps.py":
        wrote = _write_invariant_deps(out_dir)
    elif out_rel == "app/routers/auth.py":
        wrote = _write_invariant_auth_router(out_dir, _default_public_role(project_data))
    elif out_rel in {"app/models.py", "app/schemas.py", "app/routers/generic_crud.py", "app/main.py", "seed.py"}:
        wrote = render_deterministic_file(out_dir, out_rel, project_data, theme, log)
    elif out_rel in {"frontend_templates/index.html", "frontend_templates/login.html", "frontend_templates/register.html", "frontend_templates/app.html"}:
        _write_frontend(out_dir, project_data, theme, log)
        wrote = True
    elif out_rel in {"frontend_templates/entity_list.html", "frontend_templates/entity_form.html"}:
        wrote = _write_frontend_contract_page(out_dir, out_rel)

    if not wrote:
        return False

    path = out_dir / out_rel
    code = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    valid = validator(code)
    contract_ok, contract_error = _validate_source_contract(code, out_rel, project_data)
    if valid and contract_ok:
        log(f"[deterministic] Wrote guaranteed source for {out_rel}")
        return True
    detail = f": {contract_error}" if contract_error else ""
    log(f"[error] Deterministic source failed validation for {out_rel}{detail}")
    return False


# ---------------------------------------------------------------------------
# Infrastructure files â€” served via Jinja2 templates (stable, correct)
# ---------------------------------------------------------------------------
_INFRA_TEMPLATES = {
    "fastapi_app/app/db.py.j2":               "app/db.py",
    "fastapi_app/app/auth.py.j2":             "app/auth.py",
    "fastapi_app/app/deps.py.j2":             "app/deps.py",
    "fastapi_app/routers/__init__.py.j2":     "app/routers/__init__.py",
    "fastapi_app/routers/auth.py.j2":         "app/routers/auth.py",
    "fastapi_app/requirements.txt.j2":        "requirements.txt",
    "fastapi_app/.env.example.j2":            ".env.example",
}

_OPTIONAL_TEMPLATES = {
    "fastapi_app/alembic.ini.j2":         "alembic.ini",
    "fastapi_app/docker-compose.yml.j2":  "docker-compose.yml",
    "fastapi_app/README.md.j2":           "README.md",
}

# Fallback templates for LLM-generated files (used if LLM fails)
_FALLBACK_TEMPLATES = {
    "app/models.py":                        "fastapi_app/app/models.py.j2",
    "app/schemas.py":                       "fastapi_app/app/schemas.py.j2",
    "app/main.py":                          "fastapi_app/app/main.py.j2",
    "app/routers/generic_crud.py":          "fastapi_app/routers/generic_crud.py.j2",
    "seed.py":                              "fastapi_app/seed.py.j2",
    "frontend_templates/base.html.j2":        "fastapi_app/frontend_templates/base.html.j2",
    "frontend_templates/login.html.j2":       "fastapi_app/frontend_templates/login.html.j2",
    "frontend_templates/register.html.j2":    "fastapi_app/frontend_templates/register.html.j2",
    "frontend_templates/dashboard.html.j2":   "fastapi_app/frontend_templates/dashboard.html.j2",
    "frontend_templates/entity_list.html.j2": "fastapi_app/frontend_templates/entity_list.html.j2",
    "frontend_templates/entity_form.html.j2": "fastapi_app/frontend_templates/entity_form.html.j2",
}


def _render_jinja_fallback(
    env: Environment,
    jinja_ctx: dict,
    out_dir: Path,
    out_rel: str,
    _log: Callable[[str], None],
) -> bool:
    """Render out_rel from deterministic writer or Jinja fallback template."""
    from generated_apps.generator.deterministic_backend import DETERMINISTIC_BACKEND_FILES

    if out_rel in DETERMINISTIC_BACKEND_FILES:
        project_data = {
            "cleaned_spec": jinja_ctx.get("cleaned_spec", {}),
            "architecture": jinja_ctx.get("architecture", {}),
            "data_model": jinja_ctx.get("data_model", {}),
            "requirements": jinja_ctx.get("requirements", {}),
            "user_stories": jinja_ctx.get("user_stories", {}),
            "ui_selection": jinja_ctx.get("ui_selection", {}),
        }
        if render_deterministic_file(out_dir, out_rel, project_data, jinja_ctx.get("theme"), _log):
            _log(f"[fallback] Deterministic writer used for {out_rel}")
            return True
        _log(f"[error] Deterministic writer failed for {out_rel}")
        return False

    tpl_key = _FALLBACK_TEMPLATES.get(out_rel)
    if not tpl_key:
        return False
    try:
        tpl = env.get_template(tpl_key)
        rendered = tpl.render(**jinja_ctx)
        out_path = out_dir / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        _log(f"[fallback] Jinja2 fallback used for {out_rel}")
        return True
    except Exception as fb_err:
        _log(f"[error] Fallback failed for {out_rel}: {fb_err}")
        return False


def _ensure_planned_files_exist(
    out_dir: Path,
    plan: list,
    env: Environment,
    jinja_ctx: dict,
    _log: Callable[[str], None],
) -> None:
    """After LLM generation, guarantee every planned file exists via Jinja fallback."""
    missing = []
    for spec in plan:
        out_rel = spec["output"]
        out_path = out_dir / out_rel
        if not out_path.exists() or out_path.stat().st_size < 40:
            missing.append(out_rel)
    if not missing:
        return
    _log(f"[guard] Filling {len(missing)} missing file(s) from templates: {', '.join(missing)}")
    for out_rel in missing:
        if not _render_jinja_fallback(env, jinja_ctx, out_dir, out_rel, _log):
            _log(f"[warn] Could not fallback {out_rel}")


# ---------------------------------------------------------------------------
# LLM generation plan â€” each entry defines one file
# ---------------------------------------------------------------------------
def _build_llm_plan(project_data: dict, theme: dict) -> list:
    """
    Returns a list of dicts, each describing one LLM-generated file.
    We keep the context payload small so llama3.1 8k window isn't exceeded.
    """
    from generated_apps.generator.codegen_prompts import (
        CODEGEN_MODELS_SYSTEM,
        CODEGEN_SCHEMAS_SYSTEM,
        CODEGEN_MAIN_SYSTEM,
        CODEGEN_CRUD_SYSTEM,
        CODEGEN_SEED_SYSTEM,
        CODEGEN_BASE_HTML_SYSTEM,
        CODEGEN_LOGIN_HTML_SYSTEM,
        CODEGEN_REGISTER_HTML_SYSTEM,
        CODEGEN_DASHBOARD_HTML_SYSTEM,
        CODEGEN_LIST_HTML_SYSTEM,
        CODEGEN_FORM_HTML_SYSTEM,
    )

    arch = project_data.get("architecture", {}) or {}
    dm   = project_data.get("data_model",   {}) or {}
    title = (project_data.get("cleaned_spec", {}) or {}).get("project_title") or "Generated App"

    # Trim architecture to save tokens (only what each file needs)
    arch_slim = {
        "pages":   arch.get("pages",   []),
        "roles":   arch.get("roles",   []),
        "layout":  arch.get("layout",  "topnav"),
        "endpoints": arch.get("endpoints", []),
    }

    return [
        # â”€â”€ Python backend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        {
            "output":   "app/models.py",
            "system":   CODEGEN_MODELS_SYSTEM,
            "context":  {"project_title": title, "data_model": dm},
            "type":     "python",
            "validate": _validate_python,
            "label":    "models.py (SQLAlchemy models)",
        },
        # schemas.py, main.py, generic_crud.py written deterministically in guard phase
        # â”€â”€ HTML frontend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        {
            "output":   "frontend_templates/base.html.j2",
            "system":   CODEGEN_BASE_HTML_SYSTEM,
            "context":  {"project_title": title, "theme": theme, "architecture": arch_slim},
            "type":     "html",
            "validate": _validate_html,
            "label":    "base.html.j2 (navigation + layout)",
        },
        {
            "output":   "frontend_templates/login.html.j2",
            "system":   CODEGEN_LOGIN_HTML_SYSTEM,
            "context":  {"project_title": title, "theme": theme},
            "type":     "html",
            "validate": _validate_html,
            "label":    "login.html.j2 (login page)",
        },
        {
            "output":   "frontend_templates/register.html.j2",
            "system":   CODEGEN_REGISTER_HTML_SYSTEM,
            "context":  {"project_title": title, "theme": theme},
            "type":     "html",
            "validate": _validate_html,
            "label":    "register.html.j2 (register page)",
        },
        {
            "output":   "frontend_templates/dashboard.html.j2",
            "system":   CODEGEN_DASHBOARD_HTML_SYSTEM,
            "context":  {"project_title": title, "theme": theme, "architecture": arch_slim, "data_model": dm},
            "type":     "html",
            "validate": _validate_html,
            "label":    "dashboard.html.j2 (main dashboard)",
        },
        {
            "output":   "frontend_templates/entity_list.html.j2",
            "system":   CODEGEN_LIST_HTML_SYSTEM,
            "context":  {"project_title": title, "theme": theme, "architecture": arch_slim, "data_model": dm},
            "type":     "html",
            "validate": _validate_html,
            "label":    "entity_list.html.j2 (data table)",
        },
        {
            "output":   "frontend_templates/entity_form.html.j2",
            "system":   CODEGEN_FORM_HTML_SYSTEM,
            "context":  {"project_title": title, "theme": theme, "architecture": arch_slim, "data_model": dm},
            "type":     "html",
            "validate": _validate_html,
            "label":    "entity_form.html.j2 (create/edit form)",
        },
    ]


# ---------------------------------------------------------------------------
# Post-process HTML: run Jinja2 rendering for HTML templates that use
# {% extends %} / {% block %} so the final file is flat HTML (no Jinja2).
# ---------------------------------------------------------------------------
def _render_html_with_jinja(
    html_source: str,
    file_name: str,
    context: dict,
    frontend_out_dir: Path,
) -> Optional[str]:
    """
    If the LLM wrote a child template ({% extends ... %}), we need to
    render it with Jinja2 so the output is flat HTML.
    Returns rendered string, or None if rendering fails.
    """
    if "{% extends" not in html_source:
        return html_source  # Already flat â€” no processing needed

    try:
        from jinja2 import DictLoader, Environment as JEnv
        # Build a mini env with the base template in memory
        base_path = frontend_out_dir / "base.html.j2"
        sources: dict[str, str] = {}
        if base_path.exists():
            sources["base.html.j2"] = base_path.read_text(encoding="utf-8")
        sources[file_name] = html_source

        env = JEnv(loader=DictLoader(sources), autoescape=False)
        env.filters["tojson"]  = lambda v, **kw: json.dumps(v, ensure_ascii=False)
        env.filters["pascal"]  = lambda v: "".join(
            (x[0].upper() + x[1:] if x else "") for x in re.split(r"[^a-zA-Z0-9]+", str(v))
        )
        env.filters["slugify"] = slugify

        tpl = env.get_template(file_name)
        return tpl.render(**context)
    except Exception as exc:
        print(f"[warn] Jinja2 render of {file_name} failed: {exc}")
        return None


# Replace the legacy partial/Jinja plan with a complete plain-source plan.
def _build_llm_plan(project_data: dict, theme: dict) -> list:
    from generated_apps.generator.codegen_prompts import (
        CODEGEN_AUTH_SYSTEM,
        CODEGEN_CRUD_SYSTEM,
        CODEGEN_DASHBOARD_HTML_SYSTEM,
        CODEGEN_DB_SYSTEM,
        CODEGEN_DEPS_SYSTEM,
        CODEGEN_FORM_HTML_SYSTEM,
        CODEGEN_LIST_HTML_SYSTEM,
        CODEGEN_LOGIN_HTML_SYSTEM,
        CODEGEN_MAIN_SYSTEM,
        CODEGEN_MODELS_SYSTEM,
        CODEGEN_REGISTER_HTML_SYSTEM,
        CODEGEN_ROUTER_AUTH_SYSTEM,
        CODEGEN_SCHEMAS_SYSTEM,
        CODEGEN_SEED_SYSTEM,
    )

    architecture = project_data.get("architecture", {}) or {}
    cleaned = project_data.get("cleaned_spec", {}) or {}
    title = cleaned.get("project_title") or "Generated App"
    common = {
        "project_title": title,
        "project_slug": slugify(title),
        "product_brief": cleaned,
        "requirements": project_data.get("requirements", {}) or {},
        "architecture": {
            "pages": architecture.get("pages", []),
            "roles": architecture.get("roles", []),
            "layout": architecture.get("layout", "topnav"),
            "endpoints": architecture.get("endpoints", []),
        },
        "data_model": project_data.get("data_model", {}) or {},
        "theme": theme,
        "source_policy": {
            "plain_source_only": True,
            "jinja_forbidden": True,
            "project_specific_implementation": True,
            "canonical_roles": architecture.get("roles") or ["Admin", "User"],
            "canonical_token_key": "access_token",
        },
    }

    def context(*keys: str) -> dict:
        value = {
            "project_title": common["project_title"],
            "project_slug": common["project_slug"],
            "source_policy": common["source_policy"],
        }
        for key in keys:
            value[key] = common[key]
        return value

    def python_file(output: str, system: str, label: str, *keys: str) -> dict:
        return {
            "output": output,
            "system": system,
            "context": context(*keys),
            "type": "python",
            "validate": _validate_python,
            "label": label,
        }

    def html_file(output: str, system: str, label: str, *keys: str) -> dict:
        return {
            "output": output,
            "system": system,
            "context": context(*keys),
            "type": "html",
            "validate": _validate_html,
            "label": label,
        }

    return [
        python_file("app/db.py", CODEGEN_DB_SYSTEM, "database infrastructure"),
        python_file("app/auth.py", CODEGEN_AUTH_SYSTEM, "JWT and password infrastructure"),
        python_file("app/deps.py", CODEGEN_DEPS_SYSTEM, "authentication dependencies", "data_model"),
        python_file(
            "app/routers/auth.py",
            CODEGEN_ROUTER_AUTH_SYSTEM,
            "authentication routes",
            "data_model",
        ),
        python_file("app/models.py", CODEGEN_MODELS_SYSTEM, "SQLAlchemy models", "data_model"),
        python_file("app/schemas.py", CODEGEN_SCHEMAS_SYSTEM, "Pydantic schemas", "data_model"),
        python_file(
            "app/routers/generic_crud.py",
            CODEGEN_CRUD_SYSTEM,
            "project CRUD routes",
            "data_model",
            "architecture",
        ),
        python_file(
            "app/main.py",
            CODEGEN_MAIN_SYSTEM,
            "application routes and dashboard statistics",
            "architecture",
            "data_model",
        ),
        python_file(
            "seed.py",
            CODEGEN_SEED_SYSTEM,
            "idempotent domain seed data",
            "data_model",
            "product_brief",
        ),
        html_file(
            "frontend_templates/login.html",
            CODEGEN_LOGIN_HTML_SYSTEM,
            "project login page",
            "theme",
        ),
        html_file(
            "frontend_templates/register.html",
            CODEGEN_REGISTER_HTML_SYSTEM,
            "project registration page",
            "theme",
        ),
        html_file(
            "frontend_templates/app.html",
            CODEGEN_DASHBOARD_HTML_SYSTEM,
            "domain-specific application dashboard",
            "theme",
            "architecture",
            "data_model",
            "product_brief",
        ),
        html_file(
            "frontend_templates/entity_list.html",
            CODEGEN_LIST_HTML_SYSTEM,
            "domain-specific entity list",
            "theme",
            "architecture",
            "data_model",
        ),
        html_file(
            "frontend_templates/entity_form.html",
            CODEGEN_FORM_HTML_SYSTEM,
            "schema-driven entity form",
            "theme",
            "architecture",
            "data_model",
        ),
    ]


# ---------------------------------------------------------------------------
# Deterministic app shell and validation guardrails
# ---------------------------------------------------------------------------
def _entity_class_name(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", str(name)))


def _resource_name(entity_name: str) -> str:
    return resource_path(entity_name)


def _contract_entity_dict(spec) -> dict:
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


def _infer_page_target(page: dict, entities: list[dict]) -> tuple[str, str]:
    text = f"{page.get('name', '')} {page.get('path', '')} {page.get('description', '')}".lower()
    explicit = page.get("target_entity")
    if explicit:
        return _entity_class_name(explicit), "form" if any(w in text for w in ["add", "new", "create", "borrow"]) else "list"

    if any(w in text for w in ["borrow", "loan", "history", "active loans", "top borrowers"]):
        for entity in entities:
            lowered = str(entity.get("name", "")).lower()
            if any(w in lowered for w in ["borrow", "loan"]):
                mode = "form" if any(w in text for w in ["borrow-book", "borrow book", "new", "add", "create"]) else "list"
                return _entity_class_name(entity.get("name")), mode

    if "stock" in text:
        for entity in entities:
            if "stock" in str(entity.get("name", "")).lower():
                return _entity_class_name(entity.get("name")), "list"

    best_entity = ""
    for entity in entities:
        name = str(entity.get("name", ""))
        words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", name)
        hay = " ".join(w.lower() for w in words) + " " + _resource_name(name)
        if any(word and word in text for word in hay.split()):
            best_entity = _entity_class_name(name)
            break

    if not best_entity and "borrow" in text:
        for entity in entities:
            if "borrow" in str(entity.get("name", "")).lower() or "loan" in str(entity.get("name", "")).lower():
                best_entity = _entity_class_name(entity.get("name"))
                break

    if not best_entity and entities:
        best_entity = _entity_class_name(entities[0].get("name"))

    mode = "dashboard"
    if any(w in text for w in ["add", "new", "create", "borrow"]):
        mode = "form"
    elif any(w in text for w in ["manage", "browse", "history", "active", "top", "list"]):
        mode = "list"
    elif any(w in text for w in ["stat", "dashboard", "analytics"]):
        mode = "dashboard"
    return best_entity, mode


def _write_main_routes(out_dir: Path, project_data: dict) -> None:
    from builder.data_model_guard import _is_ecommerce_spec

    arch = project_data.get("architecture", {}) or {}
    contract = build_app_contract(project_data)
    title = (project_data.get("cleaned_spec", {}) or {}).get("project_title") or "Generated App"
    api_prefix = contract.api_prefix
    entities = [entity for entity in contract.business_entities() if entity.ui_visible]
    entity_targets = [{"name": entity.raw_name} for entity in entities]

    product_ent = next(
        (e for e in entities if any(h in e.raw_name.lower() for h in ("product", "catalog", "item"))),
        None,
    )
    order_ent = next(
        (e for e in entities if any(h in e.raw_name.lower() for h in ("order", "purchase"))),
        None,
    )
    purchase_block = ""
    if product_ent and order_ent and _is_ecommerce_spec(project_data):
        pcls = product_ent.class_name
        ocls = order_ent.class_name
        ofields = {str(f.get("name", "")).lower(): f.get("name") for f in order_ent.fields}
        user_fk = ofields.get("user_id") or ofields.get("customer_id") or "user_id"
        product_fk = ofields.get("product_id", "product_id")
        qty_field = ofields.get("quantity", "quantity")
        total_field = ofields.get("total_cost") or ofields.get("total") or "total_cost"
        purchase_block = f'''

@app.post("{api_prefix}/store/purchase", tags=["store"])
def api_store_purchase(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Customer checkout — creates an order for the logged-in user."""
    from uuid import uuid4
    from fastapi import HTTPException

    if (current_user.role or "").lower() not in ("customer", "user"):
        raise HTTPException(status_code=403, detail="Only customers can purchase")

    product_id = body.get("product_id")
    quantity = max(1, int(body.get("quantity") or 1))
    if not product_id:
        raise HTTPException(status_code=400, detail="product_id is required")

    product = db.execute(
        select(models.{pcls}).where(models.{pcls}.id == product_id)
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    price = float(getattr(product, "price", 0) or 0)
    stock_attr = next(
        (a for a in ("stock_quantity", "stock", "quantity") if hasattr(product, a)),
        None,
    )
    if stock_attr:
        stock = int(getattr(product, stock_attr) or 0)
        if stock < quantity:
            raise HTTPException(status_code=400, detail="Not enough stock available")
        setattr(product, stock_attr, stock - quantity)

    total = round(price * quantity, 2)
    order_data = {{
        "id": str(uuid4()),
        {user_fk!r}: str(current_user.id),
        {product_fk!r}: str(product_id),
        {qty_field!r}: quantity,
        {total_field!r}: total,
    }}
    obj = models.{ocls}(**order_data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {{"ok": True, "order_id": str(obj.id), "total_cost": total, "message": "Purchase successful"}}
'''

    route_lines: list[str] = []
    for entity in entities:
        cls = entity.class_name
        res = entity.resource
        fn = re.sub(r"[^a-z0-9_]", "_", res.lower())
        route_lines.extend([
            f'@app.get("/ui/{res}", response_class=Response, include_in_schema=False)',
            f'def ui_list_{fn}(): return _app_html(entity="{cls}", mode="list")',
            "",
            f'@app.get("/ui/{res}/new", response_class=Response, include_in_schema=False)',
            f'def ui_new_{fn}(): return _app_html(entity="{cls}", mode="form")',
            "",
            f'@app.get("/ui/{res}/{{item_id}}/edit", response_class=Response, include_in_schema=False)',
            f'def ui_edit_{fn}(item_id: str): return _app_html(entity="{cls}", mode="form")',
            "",
        ])

    seen_paths = {"/", "/admin/dashboard", "/ui/login", "/ui/register"}
    for entity in entities:
        res = entity.resource
        seen_paths.update({f"/ui/{res}", f"/ui/{res}/new"})
    for idx, page in enumerate(arch.get("pages") or [], start=1):
        path = page.get("path")
        if not path or path in seen_paths or str(path).startswith("/ui/"):
            continue
        target, mode = _infer_page_target(page, entity_targets)
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(path).strip("/").replace("/", "_")) or f"page_{idx}"
        route_lines.extend([
            f'@app.get("{path}", response_class=Response, include_in_schema=False)',
            f'def ui_page_{idx}_{safe_name}(request: Request): return _app_html(entity="{target}", mode="{mode}", page_path="{path}")',
            "",
        ])
        seen_paths.add(path)

    stats_blocks: list[str] = []
    for entity in entities:
        cls = entity.class_name
        res = entity.resource
        roles = entity.read_roles
        stats_blocks.append(
            f"    if _role_ok(role, {roles!r}):\n"
            f"        try:\n"
            f"            stats[{res!r}] = int(db.execute(select(func.count()).select_from(models.{cls})).scalar_one() or 0)\n"
            f"        except Exception:\n"
            f"            stats[{res!r}] = None"
        )

    main_code = f'''from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import engine, Base
from app import models
from app.deps import get_current_user, get_db
from app.routers.auth import router as auth_router
from app.routers.generic_crud import router as crud_router

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend_templates"


def _serve_html(filename: str, inject: str = "") -> Response:
    path = _FRONTEND_DIR / filename
    if not path.exists():
        return JSONResponse({{"error": f"{{filename}} not found"}}, status_code=404)
    content = path.read_text(encoding="utf-8")
    if inject:
        content = content.replace("</head>", inject + "\\n</head>") if "</head>" in content else inject + content
    return Response(
        content=content,
        media_type="text/html",
        headers={{"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}},
    )


def _app_html(entity: str = "", mode: str = "dashboard", page_path: str = "") -> Response:
    inject = (
        "<script>"
        f"window.PAGE_ENTITY={{entity!r}};"
        f"window.PAGE_MODE={{mode!r}};"
        f"window.PAGE_PATH={{page_path!r}};"
        "</script>"
    )
    return _serve_html("app.html", inject)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title={title!r}, description="Auto-generated by AI Website Builder", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(crud_router)


@app.get("/health", tags=["health"])
def health():
    return {{"status": "ok", "project": {title!r}}}


@app.get("{api_prefix}", tags=["health"])
def api_root():
    return {{"project": {title!r}, "ui": "/", "docs": "/docs", "health": "/health"}}


def _role_ok(role: str, allowed: list[str]) -> bool:
    role = (role or "").lower()
    allowed = [a.lower() for a in allowed]
    if "any" in allowed:
        return True
    return role in allowed


@app.get("{api_prefix}/dashboard/stats", tags=["dashboard"])
def api_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    role = (current_user.role or "").lower()
    stats: dict = {{}}
{chr(10).join(stats_blocks) if stats_blocks else "    pass"}
    return stats


@app.get("/ui/login", response_class=Response, include_in_schema=False)
def ui_login(): return _serve_html("login.html")


@app.get("/ui/register", response_class=Response, include_in_schema=False)
def ui_register(): return _serve_html("register.html")


@app.get("/", response_class=Response, include_in_schema=False)
def ui_root(): return _app_html(mode="dashboard", page_path="/")


@app.get("/admin/dashboard", response_class=Response, include_in_schema=False)
def ui_admin(): return _app_html(mode="dashboard", page_path="/admin/dashboard")

{purchase_block}
{chr(10).join(route_lines)}
'''
    (out_dir / "app" / "main.py").write_text(main_code, encoding="utf-8")

def _project_text(project_data: dict) -> str:
    cleaned = project_data.get("cleaned_spec", {}) or {}
    prompt = cleaned.get("cleaned_prompt", {}) or {}
    values = [
        project_data.get("plain_text", ""),
        cleaned.get("project_title", ""),
        prompt.get("Goal", ""),
        " ".join(prompt.get("Roles") or []),
        " ".join(prompt.get("Constraints") or []),
        " ".join((project_data.get("architecture", {}) or {}).get("roles") or []),
    ]
    data = prompt.get("Data") or {}
    if isinstance(data, dict):
        values.extend(data.keys())
    dm = project_data.get("data_model", {}) or {}
    values.extend(str(e.get("name", "")) for e in dm.get("entities") or [])
    return " ".join(str(value or "") for value in values).lower()


def _frontend_visual_profile(project_data: dict, theme: dict) -> dict:
    text = _project_text(project_data)
    profiles = [
        (
            "school",
            ("school", "student", "teacher", "course", "assignment", "grade", "classroom"),
            {
                "brand_mark": "AC",
                "hero_kicker": "Learning workspace",
                "admin_headline": "Academic command center",
                "user_headline": "Your learning hub",
                "user_view": "cards",
                "admin_view": "table",
                "layout": "campus",
                "theme": {
                    "primary": "#2563eb",
                    "accent": "#f59e0b",
                    "secondary": "#7c3aed",
                    "bg": "#eff6ff",
                    "bg_alt": "#fff7ed",
                    "text": "#172554",
                    "text_muted": "#64748b",
                    "surface": "rgba(255,255,255,0.88)",
                    "surface_solid": "#ffffff",
                    "border": "rgba(37,99,235,0.18)",
                    "font_heading": "Space Grotesk",
                    "font_body": "Nunito",
                },
            },
        ),
        (
            "clinic",
            ("clinic", "doctor", "patient", "appointment", "medical", "health", "specialty"),
            {
                "brand_mark": "MD",
                "hero_kicker": "Care coordination",
                "admin_headline": "Clinic operations board",
                "user_headline": "Your care dashboard",
                "user_view": "timeline",
                "admin_view": "table",
                "layout": "care",
                "theme": {
                    "primary": "#0f766e",
                    "accent": "#38bdf8",
                    "secondary": "#14b8a6",
                    "bg": "#ecfeff",
                    "bg_alt": "#f0fdfa",
                    "text": "#134e4a",
                    "text_muted": "#5b7f7b",
                    "surface": "rgba(255,255,255,0.9)",
                    "surface_solid": "#ffffff",
                    "border": "rgba(15,118,110,0.18)",
                    "font_heading": "Manrope",
                    "font_body": "Inter",
                },
            },
        ),
        (
            "commerce",
            ("shop", "store", "commerce", "product", "order", "cart", "checkout", "inventory"),
            {
                "brand_mark": "ST",
                "hero_kicker": "Sales floor",
                "admin_headline": "Store control room",
                "user_headline": "Discover what is ready to buy",
                "user_view": "catalog",
                "admin_view": "table",
                "layout": "market",
                "theme": {
                    "primary": "#f97316",
                    "accent": "#ec4899",
                    "secondary": "#8b5cf6",
                    "bg": "#fff7ed",
                    "bg_alt": "#fdf2f8",
                    "text": "#431407",
                    "text_muted": "#7c2d12",
                    "surface": "rgba(255,255,255,0.9)",
                    "surface_solid": "#ffffff",
                    "border": "rgba(249,115,22,0.2)",
                    "font_heading": "Outfit",
                    "font_body": "Inter",
                },
            },
        ),
        (
            "property",
            ("property", "rental", "rent", "tenant", "landlord", "lease", "maintenance", "real estate"),
            {
                "brand_mark": "PR",
                "hero_kicker": "Property workspace",
                "admin_headline": "Portfolio operations",
                "user_headline": "Your rental home base",
                "user_view": "cards",
                "admin_view": "table",
                "layout": "estate",
                "theme": {
                    "primary": "#047857",
                    "accent": "#c2410c",
                    "secondary": "#0f766e",
                    "bg": "#f7fee7",
                    "bg_alt": "#ffedd5",
                    "text": "#14532d",
                    "text_muted": "#64748b",
                    "surface": "rgba(255,255,255,0.9)",
                    "surface_solid": "#ffffff",
                    "border": "rgba(4,120,87,0.2)",
                    "font_heading": "Plus Jakarta Sans",
                    "font_body": "Inter",
                },
            },
        ),
        (
            "workflow",
            ("task", "project", "kanban", "ticket", "issue", "workflow", "approval"),
            {
                "brand_mark": "WF",
                "hero_kicker": "Execution board",
                "admin_headline": "Workflow control center",
                "user_headline": "Focus on the next move",
                "user_view": "board",
                "admin_view": "board",
                "layout": "studio",
                "theme": {
                    "primary": "#7c3aed",
                    "accent": "#06b6d4",
                    "secondary": "#4f46e5",
                    "bg": "#f5f3ff",
                    "bg_alt": "#ecfeff",
                    "text": "#2e1065",
                    "text_muted": "#64748b",
                    "surface": "rgba(255,255,255,0.9)",
                    "surface_solid": "#ffffff",
                    "border": "rgba(124,58,237,0.2)",
                    "font_heading": "Sora",
                    "font_body": "Inter",
                },
            },
        ),
        (
            "finance",
            ("finance", "invoice", "payment", "expense", "budget", "transaction", "accounting"),
            {
                "brand_mark": "FN",
                "hero_kicker": "Financial cockpit",
                "admin_headline": "Revenue and controls",
                "user_headline": "Your money movement",
                "user_view": "ledger",
                "admin_view": "table",
                "layout": "ledger",
                "theme": {
                    "primary": "#16a34a",
                    "accent": "#0ea5e9",
                    "secondary": "#065f46",
                    "bg": "#f0fdf4",
                    "bg_alt": "#e0f2fe",
                    "text": "#052e16",
                    "text_muted": "#64748b",
                    "surface": "rgba(255,255,255,0.92)",
                    "surface_solid": "#ffffff",
                    "border": "rgba(22,163,74,0.18)",
                    "font_heading": "IBM Plex Sans",
                    "font_body": "Inter",
                },
            },
        ),
        (
            "restaurant",
            ("restaurant", "menu", "reservation", "table", "kitchen", "meal", "food"),
            {
                "brand_mark": "RS",
                "hero_kicker": "Dining room flow",
                "admin_headline": "Service operations",
                "user_headline": "A fresh place to order and reserve",
                "user_view": "catalog",
                "admin_view": "table",
                "layout": "bistro",
                "theme": {
                    "primary": "#dc2626",
                    "accent": "#facc15",
                    "secondary": "#fb923c",
                    "bg": "#fff7ed",
                    "bg_alt": "#fef9c3",
                    "text": "#450a0a",
                    "text_muted": "#854d0e",
                    "surface": "rgba(255,255,255,0.9)",
                    "surface_solid": "#ffffff",
                    "border": "rgba(220,38,38,0.18)",
                    "font_heading": "Playfair Display",
                    "font_body": "Inter",
                },
            },
        ),
        (
            "event",
            ("event", "ticket", "venue", "attendee", "booking", "speaker", "session"),
            {
                "brand_mark": "EV",
                "hero_kicker": "Live schedule",
                "admin_headline": "Event production desk",
                "user_headline": "Your event pass",
                "user_view": "timeline",
                "admin_view": "table",
                "layout": "stage",
                "theme": {
                    "primary": "#db2777",
                    "accent": "#f97316",
                    "secondary": "#7c3aed",
                    "bg": "#fdf2f8",
                    "bg_alt": "#fff7ed",
                    "text": "#500724",
                    "text_muted": "#831843",
                    "surface": "rgba(255,255,255,0.9)",
                    "surface_solid": "#ffffff",
                    "border": "rgba(219,39,119,0.18)",
                    "font_heading": "Bricolage Grotesque",
                    "font_body": "Inter",
                },
            },
        ),
    ]
    selected = None
    for domain, keywords, profile in profiles:
        if any(keyword in text for keyword in keywords):
            selected = {"domain": domain, **profile}
            break
    if selected is None:
        palettes = [
            ("nova", "#4f46e5", "#06b6d4", "#7c3aed", "Sora"),
            ("ember", "#ea580c", "#e11d48", "#7c2d12", "Outfit"),
            ("mint", "#0f766e", "#84cc16", "#155e75", "Manrope"),
            ("violet", "#8b5cf6", "#ec4899", "#312e81", "Space Grotesk"),
        ]
        idx = int(hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:2], 16) % len(palettes)
        domain, primary, accent, secondary, font = palettes[idx]
        selected = {
            "domain": domain,
            "brand_mark": domain[:2].upper(),
            "hero_kicker": "Custom workspace",
            "admin_headline": "Operations command center",
            "user_headline": "Your focused workspace",
            "user_view": "cards",
            "admin_view": "table",
            "layout": "custom",
            "theme": {
                "primary": primary,
                "accent": accent,
                "secondary": secondary,
                "bg": "#f8fafc",
                "bg_alt": "#eef2ff",
                "text": "#0f172a",
                "text_muted": "#64748b",
                "surface": "rgba(255,255,255,0.9)",
                "surface_solid": "#ffffff",
                "border": "rgba(15,23,42,0.14)",
                "font_heading": font,
                "font_body": "Inter",
            },
        }
    selected["theme"] = {**{k: v for k, v in (theme or {}).items() if v}, **selected["theme"]}
    selected["shell_class"] = f"domain-{selected['domain']} layout-{selected['layout']}"
    selected["empty_text"] = "Nothing here yet. Create the first record to bring this workspace to life."
    return selected


def _entity_icon(entity_name: str) -> str:
    name = str(entity_name or "").lower()
    if any(token in name for token in ("course", "assignment", "grade", "submission")):
        return "bi-mortarboard"
    if any(token in name for token in ("appointment", "doctor", "patient", "clinic")):
        return "bi-heart-pulse"
    if any(token in name for token in ("property", "lease", "rent", "maintenance")):
        return "bi-houses"
    if any(token in name for token in ("product", "order", "invoice", "payment")):
        return "bi-bag-check"
    if any(token in name for token in ("task", "ticket", "project", "workflow")):
        return "bi-kanban"
    if any(token in name for token in ("announcement", "comment", "message")):
        return "bi-megaphone"
    return "bi-grid-1x2"


def _entity_presentation(entity_name: str, kind: str, visual: dict) -> str:
    name = str(entity_name or "").lower()
    if kind == "catalog" or any(token in name for token in ("product", "property", "course", "menu", "service")):
        return "catalog"
    if any(token in name for token in ("appointment", "event", "schedule", "request", "comment", "announcement")):
        return "timeline"
    if any(token in name for token in ("task", "ticket", "assignment", "submission", "approval")):
        return "board"
    if any(token in name for token in ("payment", "invoice", "transaction", "expense")):
        return "ledger"
    return visual.get("user_view", "cards")


# ---------------------------------------------------------------------------
# Three-tier frontend router (Phase 1: scaffolding; only Tier A is implemented)
# ---------------------------------------------------------------------------
# Tiers:
#   "shell" (A) -> _write_frontend_shell (current, always works)
#   "app"   (B) -> bespoke dashboard layout            (Phase 2)
#   "site"  (C) -> bespoke public-site layout          (Phase 3)
#
# Selection order:
#   1. Explicit override in ui_selection (key "frontend_tier" or directive "ui: <tier>").
#   2. Spec-based classification (e-commerce / public-facing -> site; else app).
#   3. Safe default -> "shell".
# A master flag gates everything: when disabled, the router always returns "shell"
# so behavior is byte-for-byte identical to today.

FRONTEND_TIERS = ("shell", "app", "site")
# Phase 1: only the shell tier is actually implemented. As Tiers B/C are added in
# later phases, append their names here to let the router emit them.
IMPLEMENTED_FRONTEND_TIERS = {"shell"}


def _frontend_router_enabled(project_data: dict) -> bool:
    """Master feature flag. Off by default so nothing changes until explicitly enabled.

    Enable via ui_selection: {"frontend_router": true} or environment
    AIWB_FRONTEND_ROUTER=1. When off, the router always resolves to the shell.
    """
    ui_sel = project_data.get("ui_selection", {}) or {}
    if isinstance(ui_sel, dict) and ui_sel.get("frontend_router") is True:
        return True
    import os
    return os.environ.get("AIWB_FRONTEND_ROUTER", "").strip() in {"1", "true", "True", "yes"}


def _explicit_tier_hint(project_data: dict) -> str | None:
    """Read an explicit tier choice from ui_selection.

    Supports either {"frontend_tier": "site"} or a directive string like "ui: site"
    placed in ui_selection["directive"] or the plain prompt. Returns a valid tier
    name or None.
    """
    ui_sel = project_data.get("ui_selection", {}) or {}
    if isinstance(ui_sel, dict):
        explicit = str(ui_sel.get("frontend_tier", "")).strip().lower()
        if explicit in FRONTEND_TIERS:
            return explicit
        directive = str(ui_sel.get("directive", "")).strip().lower()
    else:
        directive = ""
    blob = directive + " " + str(project_data.get("plain_text", "")).lower()
    import re as _re
    match = _re.search(r"\bui\s*[:=]\s*(shell|app|site)\b", blob)
    if match:
        return match.group(1)
    return None


def _classify_frontend_tier(project_data: dict) -> str:
    """Spec-based tier classification (used only when no explicit hint is given).

    Heuristic, deterministic, no LLM:
      - e-commerce / storefront / public catalog signals -> "site"
      - otherwise (role-based internal tool, dashboard, CRUD) -> "app"
    """
    try:
        from builder.data_model_guard import _is_ecommerce_spec
        if _is_ecommerce_spec(project_data):
            return "site"
    except Exception:
        pass
    text = _project_text(project_data)
    site_signals = (
        "storefront", "public website", "landing page", "marketing",
        "catalog", "shop", "store", "ecommerce", "e-commerce", "booking site",
        "menu", "restaurant website", "portfolio",
    )
    if any(sig in text for sig in site_signals):
        return "site"
    return "app"


def _resolve_frontend_tier(project_data: dict, log) -> str:
    """Decide which tier to use, honoring the flag, explicit hint, then classification.

    Always returns a tier that is actually implemented; unimplemented selections
    degrade safely to "shell".
    """
    if not _frontend_router_enabled(project_data):
        return "shell"
    hint = _explicit_tier_hint(project_data)
    chosen = hint or _classify_frontend_tier(project_data)
    if chosen not in IMPLEMENTED_FRONTEND_TIERS:
        try:
            log(f"[frontend] tier '{chosen}' not implemented yet; using shell")
        except Exception:
            pass
        return "shell"
    return chosen


def _write_frontend(out_dir: Path, project_data: dict, theme: dict, log=None) -> None:
    """Entry point that routes to the chosen tier, with the shell as guaranteed fallback.

    Any error in tier selection or a bespoke tier falls back to _write_frontend_shell,
    so generation can never be broken by the router.
    """
    def _log(msg: str) -> None:
        if callable(log):
            try:
                log(msg)
            except Exception:
                pass

    try:
        tier = _resolve_frontend_tier(project_data, _log)
    except Exception as exc:
        _log(f"[frontend] tier resolution failed ({exc}); using shell")
        tier = "shell"

    if tier == "shell":
        _write_frontend_shell(out_dir, project_data, theme)
        return

    # Tiers B/C are added in later phases. Each will be wrapped in try/except and
    # fall back to the shell on any failure. Until then, this point is unreachable
    # because IMPLEMENTED_FRONTEND_TIERS only contains "shell".
    try:
        _write_bespoke_frontend(out_dir, project_data, theme, tier, _log)  # noqa: F821 (added in Phase 2/3)
    except Exception as exc:
        _log(f"[frontend] tier '{tier}' failed ({exc}); falling back to shell")
        _write_frontend_shell(out_dir, project_data, theme)


def _write_frontend_shell(out_dir: Path, project_data: dict, theme: dict) -> None:
    from builder.data_model_guard import _is_ecommerce_spec, entity_ui_kind

    dm = project_data.get("data_model", {}) or {}
    contract = build_app_contract(project_data)
    title = (project_data.get("cleaned_spec", {}) or {}).get("project_title") or "Generated App"
    store_purchase = _is_ecommerce_spec(project_data)
    public_role = contract.public_role.lower()
    public_account = contract.demo_accounts.get(contract.public_role) or {"email": "user@example.com", "password": "User1234!"}
    visual = _frontend_visual_profile(project_data, theme or {})
    theme = visual["theme"]
    entities = []
    for spec in contract.business_entities():
        if not spec.ui_visible:
            continue
        cls = spec.class_name
        read_roles = [str(role).lower() for role in spec.read_roles]
        write_roles = [str(role).lower() for role in spec.write_roles]
        kind = entity_ui_kind(spec.raw_name, dm)
        presentation = _entity_presentation(spec.raw_name, kind, visual)
        spaced_label = re.sub(r"(?<!^)(?=[A-Z])", " ", cls)
        entities.append({
            "name": cls,
            "resource": spec.resource,
            "label": spaced_label,
            "fields": [
                f for f in spec.fields
                if f.get("name") not in {"id", "created_at", "updated_at", "user_id", "owner_id", "customer_id", "created_by", "uploader_id"}
            ],
            "icon": _entity_icon(spec.raw_name),
            "presentation": presentation,
            "dashboard_roles": read_roles,
            "nav_roles": read_roles,
            "read_roles": read_roles,
            "write_roles": write_roles,
            "manage_label": f"Manage {spaced_label}s",
            "browse_label": f"Browse {spaced_label}s",
            "kind": kind,
        })

    nav = [
        {"label": "Dashboard", "path": "/", "entity": "", "mode": "dashboard", "roles": [public_role]},
        {"label": "Admin Dashboard", "path": "/admin/dashboard", "entity": "", "mode": "dashboard", "roles": ["admin"]},
    ]

    for entity in entities:
        res = entity["resource"]
        if "admin" in entity["nav_roles"]:
            nav.append({
                "label": entity["manage_label"],
                "path": f"/ui/{res}",
                "entity": entity["name"],
                "mode": "list",
                "roles": ["admin"],
            })
        for role in [r for r in entity["nav_roles"] if r != "admin"]:
            write_roles = [str(r).lower() for r in entity.get("write_roles", [])]
            nav.append({
                "label": entity["manage_label"] if role in write_roles else entity["browse_label"],
                "path": f"/ui/{res}",
                "entity": entity["name"],
                "mode": "list",
                "roles": [role],
            })

    payload = {
        "title": title,
        "api_prefix": contract.api_prefix,
        "theme": theme,
        "entities": entities,
        "nav": nav,
        "store_purchase": store_purchase,
        "visual": {k: v for k, v in visual.items() if k != "theme"},
    }
    ui_sel = project_data.get("ui_selection", {}) or {}
    bootstrap_cdn = ui_sel.get("bootstrap_css") or theme.get("bootstrap_css", "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css")
    primary_color = theme.get("primary", "#4f46e5")
    bg_color = theme.get("bg", "#f8fafc")
    bg_alt_color = theme.get("bg_alt", "#0f3460")
    text_color = theme.get("text", "#1e293b")
    surface_color = theme.get("surface", "#ffffff")
    surface_solid = theme.get("surface_solid", surface_color)
    border_color = theme.get("border", "rgba(255,255,255,0.16)")
    shadow_style = theme.get("shadow", "0 18px 48px rgba(0,0,0,0.22)")
    glow_style = theme.get("glow", f"0 0 28px {primary_color}40")
    accent_color = theme.get("accent", "#10b981")
    secondary_color = theme.get("secondary", "#7c3aed")
    font_heading = theme.get("font_heading", "Inter")
    font_body = theme.get("font_body", "Inter")
    shell_class = visual.get("shell_class", "domain-custom layout-custom")
    brand_mark = visual.get("brand_mark", "AI")
    
    app_html = f'''<!doctype html>
<html lang="en" data-bs-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link href="{bootstrap_cdn}" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family={font_heading.replace(' ', '+')}:wght@400;600;700;800&family={font_body.replace(' ', '+')}:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bs-primary: {primary_color};
  --bs-primary-rgb: {int(primary_color[1:3], 16)},{int(primary_color[3:5], 16)},{int(primary_color[5:7], 16)};
  --app-bg: {bg_color};
  --app-bg-alt: {bg_alt_color};
  --app-primary: {primary_color};
  --app-accent: {accent_color};
  --app-secondary: {secondary_color};
  --app-surface: {surface_color};
  --app-surface-solid: {surface_solid};
  --app-border: {border_color};
  --app-text: {text_color};
  --app-muted: {theme.get("text_muted", "rgba(255,255,255,0.72)")};
  --app-shadow: {shadow_style};
  --app-glow: {glow_style};
}}
* {{ box-sizing:border-box; }}
body {{
  font-family:'{font_body}',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  min-height:100vh;
  background:
    radial-gradient(circle at 12% 8%, {primary_color}26 0, transparent 26%),
    radial-gradient(circle at 82% 6%, {secondary_color}24 0, transparent 24%),
    linear-gradient(135deg,var(--app-bg) 0%,var(--app-bg-alt) 62%,#1a1a2e 100%);
  color:var(--app-text);
}}
body.domain-school {{ background:linear-gradient(135deg,#eff6ff 0%,#fff7ed 48%,#dbeafe 100%); }}
body.domain-clinic {{ background:linear-gradient(135deg,#ecfeff 0%,#f0fdfa 52%,#ccfbf1 100%); }}
body.domain-commerce {{ background:linear-gradient(135deg,#fff7ed 0%,#fdf2f8 50%,#ffedd5 100%); }}
body.domain-property {{ background:linear-gradient(135deg,#f7fee7 0%,#ffedd5 50%,#dcfce7 100%); }}
body.domain-workflow {{ background:linear-gradient(135deg,#f5f3ff 0%,#ecfeff 50%,#eef2ff 100%); }}
body.domain-finance {{ background:linear-gradient(135deg,#f0fdf4 0%,#e0f2fe 54%,#dcfce7 100%); }}
.shell {{ display:grid; grid-template-columns:280px 1fr; min-height:100vh; }}
.side {{
  position:sticky; top:0; height:100vh; color:white; padding:1.35rem 1rem;
  display:flex; flex-direction:column;
  background:linear-gradient(180deg,rgba(15,52,96,.92) 0%,rgba(26,26,46,.96) 100%);
  border-right:1px solid var(--app-border);
  box-shadow:12px 0 42px rgba(0,0,0,.22);
  backdrop-filter:blur(18px);
}}
.brand {{
  font-family:'{font_heading}',sans-serif; font-size:1.35rem; font-weight:800;
  margin-bottom:1.6rem; padding:.75rem .9rem; border-radius:14px;
  background:linear-gradient(135deg,{primary_color}24,{secondary_color}24);
  border:1px solid var(--app-border); box-shadow:var(--app-glow);
}}
.brand::before {{ content:"{brand_mark}"; display:inline-grid; place-items:center; width:2.25rem; height:2.25rem; margin-right:.65rem; border-radius:14px; background:linear-gradient(135deg,{primary_color},{accent_color}); color:#fff; font-size:.75rem; box-shadow:0 0 18px {primary_color}66; }}
.nav {{ flex:1; overflow:auto; padding-right:.2rem; }}
.nav a {{
  display:flex; align-items:center; gap:.75rem; color:rgba(255,255,255,.78); text-decoration:none;
  padding:.78rem .95rem; border-radius:12px; margin:.2rem 0; font-weight:600; font-size:.9rem;
  border:1px solid transparent; transition:transform .2s ease, background .2s ease, border-color .2s ease, color .2s ease, box-shadow .2s ease;
}}
.nav a:hover {{ background:rgba(255,255,255,.11); color:#fff; transform:translateX(3px); border-color:var(--app-border); }}
.nav a.active {{ background:linear-gradient(135deg,{primary_color}2b,{secondary_color}2e); color:#fff; border-color:{primary_color}88; box-shadow:var(--app-glow); }}
.side .mt-auto {{ border-top:1px solid var(--app-border); padding-top:1rem; }}
.workspace {{ min-width:0; display:flex; flex-direction:column; }}
.topbar {{
  position:sticky; top:0; z-index:10; min-height:76px; display:grid; grid-template-columns:1fr minmax(240px,420px) auto; gap:1rem; align-items:center;
  padding:1rem 1.5rem; background:var(--app-surface); border-bottom:1px solid var(--app-border); backdrop-filter:blur(18px);
}}
.crumbs {{ color:var(--app-muted); font-size:.86rem; }}
.crumbs strong {{ color:var(--app-text); }}
.top-search {{ width:100%; border:1px solid var(--app-border); border-radius:999px; padding:.72rem 1rem; background:rgba(255,255,255,.72); color:var(--app-text); outline:0; }}
.top-search::placeholder {{ color:var(--app-muted); }}
.top-actions {{ display:flex; align-items:center; gap:.6rem; justify-content:flex-end; }}
.icon-btn,.user-chip {{ border:1px solid var(--app-border); background:rgba(255,255,255,.72); color:var(--app-text); border-radius:999px; padding:.62rem .8rem; box-shadow:0 8px 20px rgba(0,0,0,.14); }}
main {{ padding:1.5rem; overflow-y:auto; }}
.top,.page-hdr {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; flex-wrap:wrap; gap:1rem; }}
.top h1,.page-hdr h1 {{ font-family:'{font_heading}',sans-serif; font-size:1.9rem; font-weight:800; margin:0; color:var(--app-text); }}
.top p,.page-hdr p {{ color:var(--app-muted); margin:0; font-size:.92rem; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:1rem; }}
.hero {{ position:relative; overflow:hidden; display:grid; grid-template-columns:1fr auto; gap:1rem; align-items:center; margin-bottom:1.35rem; padding:1.35rem; border-radius:24px; border:1px solid var(--app-border); background:linear-gradient(135deg,{primary_color}1f,{accent_color}22),var(--app-surface); box-shadow:var(--app-shadow); }}
.hero::after {{ content:""; position:absolute; inset:auto -12% -45% auto; width:340px; height:340px; border-radius:999px; background:radial-gradient(circle,{accent_color}44,transparent 64%); pointer-events:none; }}
.hero .kicker {{ display:inline-flex; color:var(--app-primary); text-transform:uppercase; letter-spacing:.12em; font-size:.72rem; font-weight:900; margin-bottom:.45rem; }}
.hero h1 {{ color:var(--app-text); font-family:'{font_heading}',sans-serif; font-size:clamp(2rem,4vw,3.5rem); line-height:1; margin:0 0 .6rem; }}
.hero p {{ color:var(--app-muted); max-width:62ch; margin:0; }}
.hero-mark {{ position:relative; z-index:1; display:grid; place-items:center; width:6.2rem; height:6.2rem; border-radius:2rem; font-weight:900; font-size:1.6rem; color:#fff; background:linear-gradient(135deg,{primary_color},{accent_color}); box-shadow:0 22px 60px {primary_color}44; }}
.dashboard-grid .card {{ min-height:150px; display:flex; flex-direction:column; justify-content:space-between; }}
.dash-icon {{ width:2.75rem; height:2.75rem; display:grid; place-items:center; border-radius:16px; color:#fff; background:linear-gradient(135deg,{primary_color},{secondary_color}); margin-bottom:.9rem; }}
.record-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(270px,1fr)); gap:1rem; }}
.record-card {{ position:relative; overflow:hidden; background:var(--app-surface); border:1px solid var(--app-border); border-radius:22px; padding:1.1rem; box-shadow:var(--app-shadow); }}
.record-card::before {{ content:""; position:absolute; inset:0 0 auto 0; height:5px; background:linear-gradient(90deg,{primary_color},{accent_color}); }}
.record-card h3 {{ margin:.25rem 0 .35rem; color:var(--app-text); font-family:'{font_heading}',sans-serif; font-size:1.15rem; }}
.record-card .meta {{ color:var(--app-muted); font-size:.86rem; min-height:1.2rem; }}
.record-fields {{ display:grid; gap:.55rem; margin:1rem 0; }}
.record-field {{ display:flex; justify-content:space-between; gap:1rem; padding:.58rem .7rem; border-radius:12px; background:rgba(255,255,255,.56); border:1px solid var(--app-border); }}
.record-field span:first-child {{ color:var(--app-muted); font-size:.76rem; text-transform:uppercase; letter-spacing:.06em; font-weight:800; }}
.record-field span:last-child {{ text-align:right; font-weight:700; }}
.pill {{ display:inline-flex; align-items:center; gap:.35rem; border-radius:999px; padding:.3rem .65rem; color:var(--app-primary); background:{primary_color}16; border:1px solid {primary_color}33; font-weight:800; font-size:.76rem; }}
.table-shell {{ overflow:auto; }}
.table-shell.admin-console {{ border-top:5px solid {primary_color}; }}
.empty-state {{ padding:2rem; text-align:center; color:var(--app-muted); border:1px dashed var(--app-border); border-radius:18px; background:var(--app-surface); }}
.card,.stat-card,.content-card {{
  background:var(--app-surface); color:var(--app-text); border-radius:16px; padding:1.25rem;
  box-shadow:var(--app-shadow); border:1px solid var(--app-border); backdrop-filter:blur(18px);
  transition:transform .22s ease, box-shadow .22s ease, border-color .22s ease;
}}
.card:hover,.stat-card:hover,.content-card:hover {{ transform:translateY(-3px); box-shadow:var(--app-shadow),var(--app-glow); border-color:{primary_color}66; }}
.card h2,.stat-card h3 {{ font-size:.86rem; text-transform:uppercase; letter-spacing:.04em; color:var(--app-muted); margin-bottom:.5rem; }}
.stat-card .value {{ font-size:2rem; font-weight:800; color:{primary_color}; }}
.btn,.btn-primary {{
  display:inline-flex; align-items:center; justify-content:center; gap:.45rem; border:0; border-radius:12px;
  padding:.72rem 1rem; background:linear-gradient(135deg,{primary_color},{accent_color}); color:#fff !important;
  text-decoration:none; font-weight:800; box-shadow:0 12px 26px {primary_color}33; transition:transform .18s ease, box-shadow .18s ease, filter .18s ease;
}}
.btn:hover,.btn-primary:hover {{ transform:translateY(-2px); filter:brightness(1.08); box-shadow:0 16px 34px {primary_color}4d; }}
.btn.secondary {{ background:rgba(255,255,255,.1); border:1px solid var(--app-border); box-shadow:none; }}
.btn.danger {{ background:linear-gradient(135deg,#ef4444,#f97316); }}
label {{ display:block; color:var(--app-muted); font-weight:700; margin:.9rem 0 .35rem; }}
input,select,textarea,.form-control {{
  width:100%; border:1px solid var(--app-border); border-radius:12px; padding:.78rem .9rem;
  background:rgba(255,255,255,.72); color:var(--app-text); outline:0; transition:border-color .18s ease, box-shadow .18s ease, background .18s ease;
}}
input:focus,select:focus,textarea:focus,.form-control:focus {{ border-color:{primary_color}; box-shadow:0 0 0 .22rem {primary_color}26; background:rgba(255,255,255,.92); }}
form .btn[type="submit"],form button[type="submit"] {{ margin-top:1rem; float:right; }}
table {{ width:100%; color:var(--app-text); border-collapse:separate; border-spacing:0 .55rem; }}
th {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.05em; color:var(--app-muted); border:0; }}
td {{ background:rgba(255,255,255,.06); border-top:1px solid var(--app-border); border-bottom:1px solid var(--app-border); padding:.78rem; }}
td:first-child {{ border-left:1px solid var(--app-border); border-radius:12px 0 0 12px; }}
td:last-child {{ border-right:1px solid var(--app-border); border-radius:0 12px 12px 0; }}
.actions {{ display:flex; gap:.5rem; justify-content:flex-end; flex-wrap:wrap; }}
.notice {{ position:fixed; right:1.5rem; bottom:1.5rem; z-index:1050; animation:slideIn .3s ease; background:var(--app-surface-solid); color:var(--app-text); border:1px solid var(--app-border); border-radius:12px; padding:.8rem 1rem; box-shadow:var(--app-shadow); }}
@keyframes slideIn {{ from {{ transform:translateY(100px); opacity:0; }} to {{ transform:translateY(0); opacity:1; }} }}
@media (max-width:900px) {{
  .shell {{ grid-template-columns:1fr; }}
  .side {{ position:relative; height:auto; }}
  .topbar {{ grid-template-columns:1fr; }}
  main {{ padding:1rem; }}
}}
</style>
<script>window.APP_CONFIG = {json.dumps(payload, ensure_ascii=False)};</script>
</head>
<body class="{shell_class}"><div class="shell"><aside class="side"><div class="brand">{title}</div><nav class="nav" id="nav"></nav><div class="mt-auto"><div class="small text-white-50 px-3 pb-2">Signed in as</div><div class="px-3 pb-3 fw-semibold" id="sideUser">User</div><a href="#" onclick="logout()" class="text-white-50 text-decoration-none small d-flex align-items-center gap-2 px-3 py-2"><i class="bi bi-box-arrow-right"></i> Sign Out</a></div></aside><div class="workspace"><header class="topbar"><div class="crumbs">Home / <strong id="crumbPage">Dashboard</strong></div><input class="top-search" id="globalSearch" placeholder="Search this workspace..." oninput="if(window.filterRows) filterRows()"><div class="top-actions"><button class="icon-btn" title="Notifications"><i class="bi bi-bell"></i></button><button class="user-chip" id="userMenu" title="User menu">Account</button></div></header><main><div id="app"></div></main></div></div><div id="notice" class="notice"></div>
<script>
const CFG = window.APP_CONFIG;
const API_PREFIX = CFG.api_prefix || '/api';
const token = () => localStorage.getItem('access_token') || '';
const user = () => JSON.parse(localStorage.getItem('current_user') || '{{}}');
const headers = () => token() ? {{'Content-Type':'application/json','Authorization':'Bearer '+token()}} : {{'Content-Type':'application/json'}};
function flash(msg) {{ const n=document.getElementById('notice'); n.textContent=msg; n.style.display='block'; setTimeout(()=>n.style.display='none',2600); }}
async function api(path, opts={{}}) {{ const r=await fetch(path, {{...opts, headers:{{...headers(), ...(opts.headers||{{}})}}}}); if(r.status===401) location.href='/ui/login?next='+encodeURIComponent(location.pathname); return r; }}
async function apiFetch(path, opts={{}}) {{ return api(path, opts); }}
const entityByName = Object.fromEntries(CFG.entities.map(e=>[e.name,e]));
function currentEntity() {{ return entityByName[window.PAGE_ENTITY] || CFG.entities[0]; }}
function roleAllowed(allowed, userRole) {{ const role=(userRole||'').toLowerCase(); const roles=(allowed||['any']).map(r=>String(r).toLowerCase()); if(roles.includes('any')) return true; return roles.includes(role); }}
function nav() {{ const currentUser=user(); const userRole=(currentUser.role||'').toLowerCase().trim(); const filteredNav=(CFG.nav||[]).filter(n=>roleAllowed(n.roles||[n.role||'any'], userRole)); const navHtml=filteredNav.map(n=>`<a class="${{location.pathname===n.path?'active':''}}" href="${{n.path}}">${{n.label}}</a>`).join(''); document.getElementById('nav').innerHTML=navHtml; const active=filteredNav.find(n=>location.pathname===n.path); const label=active?active.label:(userRole==='admin'?'Admin Dashboard':'Dashboard'); const sideUser=document.getElementById('sideUser'); const chip=document.getElementById('userMenu'); const crumb=document.getElementById('crumbPage'); if(sideUser) sideUser.textContent=currentUser.email||'User'; if(chip) chip.textContent=(currentUser.role||'User')+' ▾'; if(crumb) crumb.textContent=label; }}
function logout() {{ localStorage.removeItem('access_token'); localStorage.removeItem('current_user'); location.href='/ui/login'; }}
function titleCase(s) {{ return String(s||'').replace(/_/g,' ').replace(/\\b\\w/g,c=>c.toUpperCase()); }}
function formatApiError(payload, fallback='Request failed') {{
  if (!payload) return fallback;
  if (typeof payload === 'string') return payload;
  const d = payload.detail ?? payload.message ?? payload.error;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map(x => {{
    if (!x) return '';
    const loc = Array.isArray(x.loc) ? x.loc.filter(p=>p!=='body').join('.') : '';
    const msg = x.msg || x.message || JSON.stringify(x);
    return loc ? `${{loc}}: ${{msg}}` : msg;
  }}).filter(Boolean).join('; ') || fallback;
  if (typeof d === 'object') return JSON.stringify(d);
  return fallback;
}}
function fieldInput(f, value='') {{ const t=(f.type||'string').toLowerCase(); const name=f.name; const req=(f.required?'required':''); if(name.endsWith('_id')) return `<input id="f_${{name}}" value="${{value||''}}" placeholder="${{name}} UUID" ${{req}}>`; if(t.includes('int')||t.includes('decimal')||t.includes('float')||t.includes('number')) return `<input id="f_${{name}}" type="number" value="${{value??''}}" ${{req}}>`; if(t.includes('date')) return `<input id="f_${{name}}" type="date" value="${{String(value||'').slice(0,10)}}" ${{req}}>`; if(t.includes('bool')) return `<select id="f_${{name}}" ${{req}}><option value="">Select...</option><option value="false">No</option><option value="true" ${{value?'selected':''}}>Yes</option></select>`; if(t.includes('email')) return `<input id="f_${{name}}" type="email" value="${{value??''}}" ${{req}}>`; return `<input id="f_${{name}}" type="text" value="${{value??''}}" ${{req}}>`;  }}
async function purchaseProduct(productId, title) {{
  if (!CFG.store_purchase) {{ flash('Purchase is not enabled for this app'); return; }}
  const qtyStr = prompt('How many would you like to buy?', '1');
  if (qtyStr === null) return;
  const quantity = Math.max(1, parseInt(qtyStr, 10) || 1);
  try {{
    const r = await api(API_PREFIX + '/store/purchase', {{ method:'POST', body: JSON.stringify({{ product_id: productId, quantity }}), headers: {{'Content-Type':'application/json'}} }});
    let d = {{}};
    try {{ d = await r.json(); }} catch(_) {{}}
    if (!r.ok) {{ flash(formatApiError(d, 'Purchase failed ('+r.status+')')); return; }}
    flash(d.message || ('Purchased ' + (title || 'item') + ' successfully!'));
    const ordersPage = (CFG.entities||[]).find(x => x.kind === 'order');
    if (ordersPage) setTimeout(() => location.href = '/ui/' + ordersPage.resource, 1000);
  }} catch(err) {{ flash('Purchase error: ' + err.message); }}
}}
async function catalogListPage() {{
  const e = currentEntity();
  if (!e) {{ flash('Unknown catalog page'); return; }}
  try {{
    const r = await api(API_PREFIX + '/' + e.resource + '?limit=500');
    if (!r.ok) {{ flash('Failed to load products (' + r.status + ')'); return; }}
    const rows = await r.json();
    if (!Array.isArray(rows)) {{ flash('Invalid product data'); return; }}
    const cards = rows.map(p => {{
      const title = p.title || p.name || 'Product';
      const price = p.price != null ? p.price : '—';
      const stock = p.stock_quantity ?? p.stock ?? p.quantity;
      const stockTxt = stock != null ? `In stock: ${{stock}}` : '';
      const desc = (p.description || '').slice(0, 120);
      return `<div class="card"><h2>${{title}}</h2><p>${{desc}}</p><p style="font-size:1.4rem;font-weight:800;color:var(--app-primary)">$${{price}}</p><p class="small" style="color:var(--app-muted)">${{stockTxt}}</p><button class="btn" type="button" onclick="purchaseProduct('${{p.id}}', '${{String(title).replace(/'/g, '')}}')">Buy now</button></div>`;
    }}).join('');
    document.getElementById('app').innerHTML = `<div class="top"><div><h1>${{e.label}}s</h1><p>${{rows.length}} available — click Buy to purchase</p></div></div><div class="grid">${{cards || '<div class="card"><p>No products yet.</p></div>'}}</div>`;
  }} catch(err) {{ flash('Could not load products: ' + err.message); }}
}}
async function dashboard() {{ try {{ const userRole=(user().role||'').toLowerCase(); const visible=(CFG.entities||[]).filter(e=>roleAllowed(e.dashboard_roles||['admin'], userRole)); const r=await api(API_PREFIX + '/dashboard/stats'); if(!r.ok) {{ flash('Dashboard failed to load'); return; }} const stats=await r.json(); const cards=visible.map(e=>{{ const count=stats[e.resource]; if(count===undefined||count===null) return `<div class="card"><h2>${{e.label}}s</h2><p style="font-size:2rem;margin:0">—</p><a class="btn" href="/ui/${{e.resource}}">Open</a></div>`; return `<div class="card"><h2>${{e.label}}s</h2><p style="font-size:2rem;margin:0">${{count}}</p><a class="btn" href="/ui/${{e.resource}}">Open</a></div>`; }}); document.getElementById('app').innerHTML=`<div class="top"><div><h1>${{userRole==='admin'?'Admin Dashboard':'Dashboard'}}</h1><p>${{user().email||'Signed in user'}}</p></div></div><div class="grid">${{cards.join('')}}</div>`; }} catch(err) {{ flash('Dashboard error: '+err.message); }} }}
async function listPage() {{ const e=currentEntity(); if(!e||!e.resource) {{ flash('Unknown page — regenerate app shell'); return; }} const userRole=(user().role||'').toLowerCase(); const isAdmin=userRole==='admin'; const canWrite=roleAllowed(e.write_roles||['admin'], userRole); if(!isAdmin && e.kind==='catalog' && CFG.store_purchase) {{ return catalogListPage(); }} try {{ const r=await api(API_PREFIX + '/' + e.resource + '?limit=500'); if(!r.ok) {{ flash('Failed to load records ('+r.status+')'); return; }} const rows=await r.json(); if(!Array.isArray(rows)) {{ flash('Invalid data from server'); return; }} const fieldList=Array.isArray(e.fields)?e.fields:[]; const hideCols=['password_hash','password']; if(!isAdmin) hideCols.push('user_id','customer_id','product_id'); const keys=rows.length>0?Object.keys(rows[0]).filter(k=>!hideCols.includes(k)):fieldList.map(f=>f.name); window.__rows=rows; window.__keys=keys; window.__entity=e; window.__canWrite=canWrite; const bodyRows=rows.map(row=>rowHtml(row,e,keys,canWrite)).join(''); const emptyMsg=rows.length?'' : '<tr><td colspan="99" style="text-align:center;color:var(--app-muted)">No records yet</td></tr>'; const allowNew=canWrite; const newBtn=allowNew?`<a class="btn" href="/ui/${{e.resource}}/new">New ${{e.label}}</a>`:''; const actions=canWrite?'<th>Actions</th>':''; document.getElementById('app').innerHTML=`<div class="top"><div><h1>${{e.label}}s</h1><p>${{rows.length}} records</p></div>${{newBtn}}</div><div class="card"><input id="search" placeholder="Search..." oninput="filterRows()"></div><div class="card"><table><thead><tr>${{keys.map(k=>`<th>${{titleCase(k)}}</th>`).join('')}}${{actions}}</tr></thead><tbody id="rows">${{bodyRows||emptyMsg}}</tbody></table></div>`; }} catch(err) {{ flash('Records load failed: '+err.message); }} }}
function rowHtml(row, ent, keys, canWrite) {{ const e=ent||window.__entity; const cols=keys||window.__keys||[]; const writable=(canWrite!==undefined)?canWrite:!!window.__canWrite; if(!e||!cols.length) return ''; const cells=cols.map(k=>`<td>${{row[k]??''}}</td>`).join(''); if(!writable) return `<tr>${{cells}}</tr>`; return `<tr>${{cells}}<td class="actions"><a class="btn secondary" href="/ui/${{e.resource}}/${{row.id}}/edit">Edit</a><button class="btn danger" onclick="delRec('${{row.id}}')">Delete</button></td></tr>`; }}
function filterRows() {{ const local=document.getElementById('search'); const global=document.getElementById('globalSearch'); const q=((local&&local.value)||(global&&global.value)||'').toLowerCase(); if(!window.__rows||!document.getElementById('rows')) return; const e=window.__entity, keys=window.__keys, canWrite=window.__canWrite; document.getElementById('rows').innerHTML=window.__rows.filter(r=>JSON.stringify(r).toLowerCase().includes(q)).map(r=>rowHtml(r,e,keys,canWrite)).join('')||'<tr><td colspan="99" style="text-align:center;color:var(--app-muted)">No matching records</td></tr>'; }}
async function delRec(id) {{ if(!confirm('Delete this record?')) return; const e=currentEntity(); try {{ const r=await api(API_PREFIX + '/' + e.resource + '/' + id, {{method:'DELETE'}}); if(r.ok||r.status===204) {{ flash('Deleted successfully'); listPage(); }} else {{ const msg=await r.text(); flash('Delete failed: '+msg); }} }} catch(err) {{ flash('Delete error: '+err.message); }} }}
async function formPage() {{ const e=currentEntity(); if(!e) {{ flash('Unknown form'); return; }} const userRole=(user().role||'').toLowerCase(); if(!roleAllowed(e.write_roles||['admin'], userRole)) {{ flash('You do not have permission to save this record'); setTimeout(()=>location.href='/ui/'+e.resource,900); return; }} const parts=location.pathname.split('/').filter(Boolean); const isEdit=parts.at(-1)==='edit'; const id=isEdit?parts.at(-2):null; let data={{}}; if(isEdit) {{ try {{ const r=await api(API_PREFIX + '/' + e.resource + '/' + id); data=r.ok?await r.json():{{}}; }} catch(err) {{ flash('Failed to load record: '+err.message); }} }} const fieldList=Array.isArray(e.fields)?e.fields:[]; document.getElementById('app').innerHTML=`<div class="top"><div><h1>${{isEdit?'Edit':'Create'}} ${{e.label}}</h1></div><a class="btn secondary" href="/ui/${{e.resource}}">Back</a></div><div class="card"><form id="form">${{fieldList.map(f=>`<label>${{titleCase(f.name)}}</label>${{fieldInput(f,data[f.name]??'')}}`).join('')}}<br><br><button class="btn" type="submit" id="submitBtn">Save</button></form></div>`; setTimeout(()=>{{ const frm=document.getElementById('form'); if(frm) frm.onsubmit=async ev=>{{ ev.preventDefault(); const submitBtn=document.getElementById('submitBtn'); const originalText=submitBtn.textContent; submitBtn.disabled=true; submitBtn.textContent='Saving...'; try {{ const body={{}}; fieldList.forEach(f=>{{ const el=document.getElementById('f_'+f.name); if(el && el.value!==undefined && el.value!=='') {{ const v=el.value; body[f.name]=(el.type==='number')?Number(v):(el.type==='checkbox')?el.checked:v; }} }}); if(!Object.keys(body).length) {{ flash('Please fill in at least one field'); submitBtn.disabled=false; submitBtn.textContent=originalText; return; }} const r=await api(API_PREFIX + '/' + e.resource + (isEdit?'/'+id:''), {{method:isEdit?'PUT':'POST', body:JSON.stringify(body), headers:{{'Content-Type':'application/json'}} }}); if(r.ok) {{ flash('Saved successfully!'); setTimeout(()=>location.href='/ui/'+e.resource, 800); }} else {{ let errPayload={{}}; try {{ errPayload=await r.json(); }} catch(_) {{ errPayload={{detail:await r.text()}}; }} flash('Error: '+formatApiError(errPayload,'Save failed')); submitBtn.disabled=false; submitBtn.textContent=originalText; }} }} catch(error) {{ flash('Network error: '+error.message); submitBtn.disabled=false; submitBtn.textContent=originalText; }} }}; }}, 50); }}
const VIS = CFG.visual || {{}};
function esc(v) {{ const div=document.createElement('div'); div.textContent=String(v ?? ''); return div.innerHTML; }}
function cleanKeys(row,e,isAdmin) {{ const source=Object.keys(row||{{}}).length?Object.keys(row):((e.fields||[]).map(f=>f.name)); const hide=['password_hash','password']; if(!isAdmin) hide.push('user_id','customer_id','product_id','teacher_id','student_id','patient_id','tenant_id','landlord_id','owner_id'); return source.filter(k=>!hide.includes(k)); }}
function valueText(row,k) {{ const v=(row||{{}})[k]; if(v===null||v===undefined||v==='') return 'Empty'; return String(v).replace('T',' ').slice(0,96); }}
function entityPresentation(e,isAdmin) {{ if(isAdmin) return VIS.admin_view || 'table'; return e.presentation || VIS.user_view || 'cards'; }}
function heroHtml(userRole, visibleCount) {{ const admin=userRole==='admin'; const headline=admin?(VIS.admin_headline||'Admin command center'):(VIS.user_headline||'Your workspace'); const kicker=VIS.hero_kicker||'Workspace'; const roleName=userRole?titleCase(userRole):'User'; return `<section class="hero ${{admin?'admin':'user'}}"><div><span class="kicker">${{esc(kicker)}} / ${{esc(roleName)}}</span><h1>${{esc(headline)}}</h1><p>${{admin?'Manage every module with a focused, domain-aware control surface.':'A role-specific experience shaped for this application, not a generic admin table.'}} ${{visibleCount}} workspace modules are ready.</p></div><div class="hero-mark">${{esc(VIS.brand_mark||'AI')}}</div></section>`; }}
function dashboardCard(e, count) {{ const shown=(count===undefined||count===null)?'Ready':count; const label=(count===undefined||count===null)?'Open workspace':'Records tracked'; return `<div class="card"><div><div class="dash-icon"><i class="bi ${{e.icon||'bi-grid-1x2'}}"></i></div><h2>${{esc(e.label)}}s</h2><p class="small" style="color:var(--app-muted)">${{label}}</p></div><div><p style="font-size:2rem;margin:0;font-weight:900;color:var(--app-primary)">${{shown}}</p><a class="btn" href="/ui/${{e.resource}}">Open</a></div></div>`; }}
async function dashboard() {{ try {{ const userRole=(user().role||'').toLowerCase(); const visible=(CFG.entities||[]).filter(e=>roleAllowed(e.dashboard_roles||e.read_roles||['admin'], userRole)); const r=await api(API_PREFIX + '/dashboard/stats'); if(!r.ok) {{ flash('Dashboard failed to load'); return; }} const stats=await r.json(); const cards=visible.map(e=>dashboardCard(e, stats[e.resource])).join(''); document.getElementById('app').innerHTML=heroHtml(userRole, visible.length)+`<div class="grid dashboard-grid">${{cards||'<div class="empty-state">No dashboard modules are visible for this role yet.</div>'}}</div>`; }} catch(err) {{ flash('Dashboard error: '+err.message); }} }}
function tableHtml(rows,e,keys,canWrite,isAdmin) {{ const actions=canWrite?'<th>Actions</th>':''; const body=rows.map(row=>rowHtml(row,e,keys,canWrite)).join(''); const badge=isAdmin?'<span class="pill">Admin console</span>':'<span class="pill">Workspace list</span>'; return `<div class="card table-shell ${{isAdmin?'admin-console':''}}">${{badge}}<table><thead><tr>${{keys.map(k=>`<th>${{titleCase(k)}}</th>`).join('')}}${{actions}}</tr></thead><tbody id="rows">${{body}}</tbody></table></div>`; }}
function recordCardHtml(row,e,keys,canWrite,presentation) {{ const titleKey=keys.find(k=>/title|name|email|code|status/i.test(k))||keys[0]||'id'; const subtitleKey=keys.find(k=>k!==titleKey&&/description|message|address|date|status|role|city|reason/i.test(k))||keys.find(k=>k!==titleKey); const detailKeys=keys.filter(k=>![titleKey,subtitleKey,'id'].includes(k)).slice(0,4); const fields=detailKeys.map(k=>`<div class="record-field"><span>${{titleCase(k)}}</span><span>${{esc(valueText(row,k))}}</span></div>`).join(''); const actions=canWrite?`<div class="actions"><a class="btn secondary" href="/ui/${{e.resource}}/${{row.id}}/edit">Edit</a><button class="btn danger" onclick="delRec('${{row.id}}')">Delete</button></div>`:''; return `<article class="record-card ${{presentation}}"><span class="pill"><i class="bi ${{e.icon||'bi-grid-1x2'}}"></i> ${{esc(e.label)}}</span><h3>${{esc(valueText(row,titleKey))}}</h3><div class="meta">${{subtitleKey?esc(valueText(row,subtitleKey)):''}}</div><div class="record-fields">${{fields}}</div>${{actions}}</article>`; }}
function renderRecords(rows,e,keys,canWrite,presentation,isAdmin) {{ if(!rows.length) return `<div class="empty-state">${{esc(VIS.empty_text||'No records yet.')}}</div>`; if(presentation==='table') return tableHtml(rows,e,keys,canWrite,isAdmin); return `<div id="rows" class="record-grid ${{presentation}}">${{rows.map(row=>recordCardHtml(row,e,keys,canWrite,presentation)).join('')}}</div>`; }}
async function listPage() {{ const e=currentEntity(); if(!e||!e.resource) {{ flash('Unknown page - regenerate app shell'); return; }} const userRole=(user().role||'').toLowerCase(); const isAdmin=userRole==='admin'; const canWrite=roleAllowed(e.write_roles||['admin'], userRole); if(!isAdmin && e.kind==='catalog' && CFG.store_purchase) {{ return catalogListPage(); }} try {{ const r=await api(API_PREFIX + '/' + e.resource + '?limit=500'); if(!r.ok) {{ flash('Failed to load records ('+r.status+')'); return; }} const rows=await r.json(); if(!Array.isArray(rows)) {{ flash('Invalid data from server'); return; }} const presentation=entityPresentation(e,isAdmin); const keys=rows.length>0?cleanKeys(rows[0],e,isAdmin):cleanKeys({{}},e,isAdmin); window.__rows=rows; window.__keys=keys; window.__entity=e; window.__canWrite=canWrite; window.__presentation=presentation; window.__isAdmin=isAdmin; const newBtn=canWrite?`<a class="btn" href="/ui/${{e.resource}}/new">New ${{e.label}}</a>`:''; const intro=isAdmin?'Management view':'Designed for your role'; document.getElementById('app').innerHTML=`<div class="top"><div><span class="pill">${{esc(intro)}}</span><h1>${{esc(e.label)}}s</h1><p>${{rows.length}} records shown as ${{presentation}}</p></div>${{newBtn}}</div><div class="card"><input id="search" placeholder="Search ${{esc(e.label)}}s..." oninput="filterRows()"></div>${{renderRecords(rows,e,keys,canWrite,presentation,isAdmin)}}`; }} catch(err) {{ flash('Records load failed: '+err.message); }} }}
function rowHtml(row, ent, keys, canWrite) {{ const e=ent||window.__entity; const cols=keys||window.__keys||[]; const writable=(canWrite!==undefined)?canWrite:!!window.__canWrite; if(!e||!cols.length) return ''; const cells=cols.map(k=>`<td>${{esc(valueText(row,k))}}</td>`).join(''); if(!writable) return `<tr>${{cells}}</tr>`; return `<tr>${{cells}}<td class="actions"><a class="btn secondary" href="/ui/${{e.resource}}/${{row.id}}/edit">Edit</a><button class="btn danger" onclick="delRec('${{row.id}}')">Delete</button></td></tr>`; }}
function filterRows() {{ const local=document.getElementById('search'); const global=document.getElementById('globalSearch'); const q=((local&&local.value)||(global&&global.value)||'').toLowerCase(); if(!window.__rows||!window.__entity) return; const rows=window.__rows.filter(r=>JSON.stringify(r).toLowerCase().includes(q)); const container=document.getElementById('rows'); const e=window.__entity, keys=window.__keys, canWrite=window.__canWrite, presentation=window.__presentation, isAdmin=window.__isAdmin; if(presentation==='table'&&container) {{ container.innerHTML=rows.map(r=>rowHtml(r,e,keys,canWrite)).join('')||'<tr><td colspan="99" style="text-align:center;color:var(--app-muted)">No matching records</td></tr>'; return; }} const appGrid=document.querySelector('.record-grid'); if(appGrid) appGrid.innerHTML=rows.map(r=>recordCardHtml(r,e,keys,canWrite,presentation)).join('')||`<div class="empty-state">No matching records</div>`; }}
function guard() {{ if(!token()) {{ location.href='/ui/login?next='+encodeURIComponent(location.pathname); return; }} const role=(user().role||'').toLowerCase(); if(role==='admin'&&location.pathname==='/') {{ location.href='/admin/dashboard'; return; }} if(role!=='admin'&&location.pathname==='/admin/dashboard') {{ location.href='/'; return; }} }}
function start() {{ guard(); nav(); const mode=window.PAGE_MODE||'dashboard'; if(mode==='form') formPage(); else if(mode==='list') listPage(); else dashboard(); }}
start();
</script></body></html>'''

    login_html = f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Login - {title}</title>
<link href="{bootstrap_cdn}" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family={font_heading.replace(' ', '+')}:wght@400;600;700;800&family={font_body.replace(' ', '+')}:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
body{{font-family:'{font_body}',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,{primary_color}dd 0%,{primary_color}66 100%);padding:1rem;}}
.card{{border:0;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.2);width:min(420px,100%);}}
.card-body{{padding:2.5rem 2rem;}}
.brand{{font-family:'{font_heading}',sans-serif;font-size:1.5rem;font-weight:800;text-align:center;margin-bottom:0.25rem;color:{primary_color};}}
.sub{{text-align:center;color:var(--bs-secondary-color,#6c757d);margin-bottom:1.5rem;font-size:0.9rem;}}
.form-floating>.form-control:focus{{border-color:{primary_color};}}
.demo{{font-size:0.8rem;background:#f8f9fa;border-radius:8px;padding:0.75rem;margin:1rem 0;}}
</style>
</head>
<body>
<div class="card"><div class="card-body">
<div class="brand">{title}</div><p class="sub">Sign in to your account</p>
<form id="login">
<div class="form-floating mb-3"><input id="email" class="form-control" type="email" value="admin@example.com" placeholder="name@example.com" required><label for="email"><i class="bi bi-envelope me-2"></i>Email Address</label></div>
<div class="form-floating mb-3"><input id="password" class="form-control" type="password" value="Admin1234!" placeholder="Password" required><label for="password"><i class="bi bi-lock me-2"></i>Password</label></div>
<div class="demo"><strong><i class="bi bi-info-circle me-1"></i>Demo Credentials:</strong><br>
<span class="text-nowrap"><i class="bi bi-shield-check text-success me-1"></i>Admin:</span> admin@example.com / Admin1234!<br>
<span class="text-nowrap"><i class="bi bi-person text-primary me-1"></i>{contract.public_role}:</span> {public_account.get("email", "user@example.com")} / {public_account.get("password", "User1234!")}</div>
<button class="btn btn-primary w-100 py-2" type="submit"><i class="bi bi-box-arrow-in-right me-2"></i>Sign In</button>
<p class="text-center mt-3 mb-0"><a href="/ui/register" class="text-decoration-none small">Don't have an account? <strong>Create one</strong></a></p>
</form>
</div></div>
<script>
const access_token = localStorage.getItem('access_token') || '';
async function apiFetch(path, opts={{}}) {{ return fetch(path, opts); }}
document.getElementById('login').onsubmit=async e=>{{e.preventDefault();const btn=e.target.querySelector('button');const emailEl=document.getElementById('email');const passwordEl=document.getElementById('password');btn.disabled=true;btn.innerHTML='<span class="spinner-border spinner-border-sm me-2"></span>Signing in...';try{{const r=await apiFetch('{contract.api_prefix}/auth/login',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:emailEl.value,password:passwordEl.value}})}});const d=await r.json();if(!r.ok){{alert(d.detail||'Login failed');btn.disabled=false;btn.innerHTML='<i class="bi bi-box-arrow-in-right me-2"></i>Sign In';return}}localStorage.setItem('access_token',d.access_token);const me=await apiFetch('{contract.api_prefix}/auth/me',{{headers:{{Authorization:'Bearer '+d.access_token}}}});const userObj=me.ok?await me.json():{{email:emailEl.value,role:'{contract.public_role.lower()}'}};localStorage.setItem('current_user',JSON.stringify(userObj));const role=(userObj.role||'').toLowerCase();const landing=role==='admin'?'/admin/dashboard':'/';location.href=new URLSearchParams(location.search).get('next')||landing;}}catch(ex){{alert('Network error: '+ex.message);btn.disabled=false;btn.innerHTML='<i class="bi bi-box-arrow-in-right me-2"></i>Sign In';}}}}</script>
</body></html>'''
    register_html = f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Register - {title}</title>
<link href="{bootstrap_cdn}" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family={font_heading.replace(' ', '+')}:wght@400;600;700;800&family={font_body.replace(' ', '+')}:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
body{{font-family:'{font_body}',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,{primary_color}dd 0%,{primary_color}66 100%);padding:1rem;}}
.card{{border:0;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.2);width:min(460px,100%);}}
.card-body{{padding:2.5rem 2rem;}}
.brand{{font-family:'{font_heading}',sans-serif;font-size:1.5rem;font-weight:800;text-align:center;margin-bottom:0.25rem;color:{primary_color};}}
.sub{{text-align:center;color:var(--bs-secondary-color,#6c757d);margin-bottom:1.5rem;font-size:0.9rem;}}
.form-floating>.form-control:focus{{border-color:{primary_color};}}
.helper{{font-size:0.8rem;color:#6c757d;margin-top:0.25rem;}}
</style>
</head>
<body>
<div class="card"><div class="card-body">
<div class="brand">{title}</div><p class="sub">Create your account</p>
<form id="reg">
<div class="form-floating mb-3"><input id="name" class="form-control" type="text" placeholder="Full Name" required><label for="name"><i class="bi bi-person me-2"></i>Full Name</label></div>
<div class="form-floating mb-3"><input id="email" class="form-control" type="email" placeholder="name@example.com" required><label for="email"><i class="bi bi-envelope me-2"></i>Email Address</label></div>
<div class="form-floating mb-3"><input id="password" class="form-control" type="password" placeholder="Password" required><label for="password"><i class="bi bi-lock me-2"></i>Password</label></div>
<div class="helper mb-2"><i class="bi bi-info-circle me-1"></i>Min. 8 characters, use a strong password</div>
<div class="form-floating mb-3"><select id="role" class="form-select" required><option value="{contract.public_role}" selected>{contract.public_role} (Regular User)</option></select><label for="role"><i class="bi bi-person-badge me-2"></i>Account Type</label></div>
<button class="btn btn-primary w-100 py-2" type="submit"><i class="bi bi-person-plus me-2"></i>Create Account</button>
<p class="text-center mt-3 mb-0"><a href="/ui/login" class="text-decoration-none small">Already have an account? <strong>Sign in</strong></a></p>
</form>
</div></div>
<script>
const access_token = localStorage.getItem('access_token') || '';
async function apiFetch(path, opts={{}}) {{ return fetch(path, opts); }}
document.getElementById('reg').onsubmit=async e=>{{e.preventDefault();const btn=e.target.querySelector('button');const nameEl=document.getElementById('name');const emailEl=document.getElementById('email');const passwordEl=document.getElementById('password');const roleEl=document.getElementById('role');btn.disabled=true;btn.innerHTML='<span class="spinner-border spinner-border-sm me-2"></span>Creating account...';try{{const r=await apiFetch('{contract.api_prefix}/auth/register',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{full_name:nameEl.value,email:emailEl.value,password:passwordEl.value,role:roleEl.value||'{contract.public_role}'}})}});let created={{}};try{{created=await r.json();}}catch(_){{}}if(!r.ok){{alert(created.detail||'Account creation failed');btn.disabled=false;btn.innerHTML='<i class="bi bi-person-plus me-2"></i>Create Account';return}}const login=await apiFetch('{contract.api_prefix}/auth/login',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:emailEl.value,password:passwordEl.value}})}});const tokenPayload=await login.json();if(!login.ok||!tokenPayload.access_token){{alert('Account created. Please sign in.');location.href='/ui/login';return}}localStorage.setItem('access_token',tokenPayload.access_token);const me=await apiFetch('{contract.api_prefix}/auth/me',{{headers:{{Authorization:'Bearer '+tokenPayload.access_token}}}});const userObj=me.ok?await me.json():{{email:emailEl.value,role:'{contract.public_role.lower()}'}};localStorage.setItem('current_user',JSON.stringify(userObj));const role=(userObj.role||'').toLowerCase();location.href=role==='admin'?'/admin/dashboard':'/';}}catch(ex){{alert('Network error: '+ex.message);btn.disabled=false;btn.innerHTML='<i class="bi bi-person-plus me-2"></i>Create Account';}}}}</script>
</body></html>'''

    frontend_dir = out_dir / "frontend_templates"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    for old in frontend_dir.glob("*.j2"):
        old.unlink(missing_ok=True)
    # Some recovery/generation paths leave a placeholder index.html behind.
    # Keep it as the same authenticated shell so strict HTML validation passes.
    (frontend_dir / "index.html").write_text(app_html, encoding="utf-8")
    (frontend_dir / "app.html").write_text(app_html, encoding="utf-8")
    (frontend_dir / "login.html").write_text(login_html, encoding="utf-8")
    (frontend_dir / "register.html").write_text(register_html, encoding="utf-8")


def _write_deterministic_seed(out_dir: Path, project_data: dict) -> None:
    write_deterministic_seed(out_dir, project_data)


def _write_smoke_tests(out_dir: Path) -> None:
    tests_dir = out_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_code = '''import os
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smoke.db")

from app.main import app
import seed

seed.main()
seed.main()


client = TestClient(app)


def login():
    res = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "Admin1234!"})
    assert res.status_code == 200, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def test_health_and_auth_flow():
    assert client.get("/health").status_code == 200
    headers = login()
    assert client.get("/api/auth/me", headers=headers).status_code == 200


def test_backend_has_seeded_readable_resources():
    headers = login()
    spec = client.get("/openapi.json").json()
    list_paths = sorted(
        p for p, ops in spec["paths"].items()
        if p.startswith("/api/")
        and "{" not in p
        and p not in {
            "/api/auth/login",
            "/api/auth/login/form",
            "/api/auth/register",
            "/api/auth/me",
            "/api/dashboard/stats",
        }
        and "get" in ops
    )
    assert list_paths, "No resource API routes generated"
    non_empty = 0
    for path in list_paths:
        res = client.get(path, headers=headers)
        assert res.status_code == 200, f"{path}: {res.text}"
        assert isinstance(res.json(), list)
        non_empty += int(len(res.json()) > 0)
    assert non_empty > 0, "Seed data did not populate any resource"


def test_ui_routes_are_app_backed_and_not_jinja():
    for path in ["/", "/ui/login", "/ui/register"]:
        res = client.get(path)
        assert res.status_code == 200
        assert "{%" not in res.text and "{{" not in res.text and ".html.j2" not in res.text


def test_plain_ui_uses_one_auth_contract():
    login_page = client.get("/ui/login").text
    register_page = client.get("/ui/register").text
    app_page = client.get("/").text
    for page in (login_page, register_page, app_page):
        assert "access_token" in page
        assert "apiFetch" in page
        assert "localStorage.getItem('token')" not in page
    assert "/api/auth/me" in login_page
    assert "/api/auth/register" in register_page


def test_dashboard_stats_contract():
    res = client.get("/api/dashboard/stats", headers=login())
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), dict)
    assert all(isinstance(value, (int, float)) for value in res.json().values())
'''
    (tests_dir / "test_smoke.py").write_text(test_code, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------
def _generate_repo_internal(
    project_data: Dict[str, Any],
    generated_root: str,
    project_id: str,
    ask_llm_fn: Optional[Callable] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> GenerateResult:
    """
    Create a runnable FastAPI + SQLite repository as project-specific plain source.

    Every application Python and HTML file is generated by the LLM, validated, and
    retained. Template fallback and deterministic source overwrite are disabled.
    """

    def _log(msg: str):
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_msg = msg.encode(encoding, errors="replace").decode(encoding)
        print(safe_msg)
        if progress_callback:
            progress_callback(safe_msg)

    try:
        from builder.data_model_guard import normalize_data_model

        project_data, dm_fixes = normalize_data_model(project_data)
        for fix in dm_fixes:
            _log(f"[data_model] {fix}")
    except Exception as exc:
        _log(f"[warn] data_model normalize skipped: {exc}")

    cleaned      = project_data.get("cleaned_spec", {}) or {}
    title        = cleaned.get("project_title") or "Generated App"
    project_slug = slugify(title)

    out_dir = Path(generated_root) / project_id / "v1"

    out_dir.mkdir(parents=True, exist_ok=True)

    # â”€â”€ Locate templates dir â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if ask_llm_fn is None:
        raise ValueError(
            "From-scratch generation requires ask_llm_fn; template generation is disabled."
        )

    # â”€â”€ Build Jinja2 context (used for infrastructure files + fallbacks) â”€â”€â”€
    architecture = project_data.get("architecture", {}) or {}
    raw_theme    = architecture.get("theme", {}) or {}
    DEFAULT_THEME = {
        "primary":      "#4f46e5",
        "accent":       "#f59e0b",
        "bg":           "#0f0e17",
        "surface":      "#1a1a2e",
        "text":         "#fffffe",
        "text_muted":   "#a7a9be",
        "font_heading": "Outfit",
        "font_body":    "Inter",
        "vibe":         f"A clean, modern web application â€” {title}",
    }
    theme = {**DEFAULT_THEME, **raw_theme}

    # Override with UI_SELECTION theme if user explicitly chose one
    ui_sel = project_data.get("ui_selection", {}) or {}
    if ui_sel.get("theme_vars"):
        theme = {**theme, **ui_sel["theme_vars"]}

    jinja_ctx = {
        "project_title": title,
        "cleaned_spec":  project_data.get("cleaned_spec",  {}) or {},
        "requirements":  project_data.get("requirements",  {}) or {},
        "user_stories":  project_data.get("user_stories",  {}) or {},
        "architecture":  project_data.get("architecture",  {}) or {},
        "data_model":    project_data.get("data_model",    {}) or {},
        "project_slug":  project_slug,
        "project_id":    project_id,
        "theme":         theme,
    }

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # STEP 1 â€” Render stable infrastructure files via Jinja2 (always)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    _log("[infra] Writing package and dependency support files...")
    support_files = {
        "requirements.txt": (
            "fastapi>=0.110,<1\n"
            "uvicorn[standard]>=0.27,<1\n"
            "sqlalchemy>=2.0,<3\n"
            "pydantic[email]>=2.6,<3\n"
            "python-jose[cryptography]>=3.3,<4\n"
            "bcrypt>=4.1,<5\n"
            "python-dotenv>=1.0,<2\n"
            "python-multipart>=0.0.9,<1\n"
            "httpx>=0.27,<1\n"
            "pytest>=8,<9\n"
        ),
        ".env.example": (
            "DATABASE_URL=sqlite:///./app.db\n"
            "SECRET_KEY=replace-with-a-long-random-secret\n"
            "ALGORITHM=HS256\n"
            "ACCESS_TOKEN_EXPIRE_MINUTES=60\n"
        ),
        "README.md": (
            f"# {title}\n\n"
            "Generated from the product specification as plain source code.\n\n"
            "Run `python seed.py`, then `uvicorn app.main:app --reload`.\n"
        ),
    }
    for relative_path, content in support_files.items():
        path = out_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # â”€â”€ app/__init__.py (always empty, needed for Python package) â”€â”€â”€â”€â”€â”€â”€â”€â”€
    app_init = out_dir / "app" / "__init__.py"
    app_init.parent.mkdir(parents=True, exist_ok=True)
    if not app_init.exists():
        app_init.write_text('"""Generated app package"""\n', encoding="utf-8")

    # â”€â”€ routers/__init__.py â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (out_dir / "app" / "routers").mkdir(parents=True, exist_ok=True)
    (out_dir / "app" / "routers" / "__init__.py").write_text(
        '"""Generated route package."""\n',
        encoding="utf-8",
    )

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # STEP 2 â€” Generate business logic + HTML via LLM  (if ask_llm_fn given)
    #          otherwise fall back to Jinja2 templates
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    if ask_llm_fn:
        _log("[codegen] Starting guarded project-specific source generation...")
        frontend_out_dir = out_dir / "frontend_templates"
        frontend_out_dir.mkdir(parents=True, exist_ok=True)

        plan = _build_llm_plan(project_data, theme)

        for spec in plan:
            label     = spec["label"]
            out_rel   = spec["output"]
            system    = spec["system"]
            context   = spec["context"]
            validator = spec["validate"]
            ftype     = spec["type"]

            prefix = "[codegen]" if out_rel in FORCED_SOURCE_FILES else "[llm]"
            _log(f"{prefix} Generating {label} ...")

            existing_path = out_dir / out_rel
            if out_rel in FORCED_SOURCE_FILES:
                if _write_forced_source_file(
                    out_dir,
                    out_rel,
                    project_data,
                    theme,
                    validator,
                    _log,
                ):
                    continue
                raise RuntimeError(f"Deterministic source generation failed for {out_rel}")

            if existing_path.exists() and existing_path.stat().st_size >= 40:
                existing_code = existing_path.read_text(encoding="utf-8", errors="ignore")
                existing_valid = validator(existing_code)
                contract_ok = True
                contract_error = ""
                if existing_valid:
                    contract_ok, contract_error = _validate_source_contract(
                        existing_code,
                        out_rel,
                        project_data,
                    )
                if existing_valid and contract_ok:
                    _log(f"[resume] Reusing validated {out_rel}")
                    continue
                detail = f": {contract_error}" if contract_error else ""
                _log(f"[resume] Regenerating stale {out_rel}{detail}")

            if out_rel in {"app/main.py", "app/routers/generic_crud.py", "frontend_templates/app.html"}:
                if render_deterministic_file(out_dir, out_rel, project_data, theme, _log):
                    code = existing_path.read_text(encoding="utf-8", errors="ignore")
                    valid = validator(code)
                    contract_ok, contract_error = _validate_source_contract(
                        code,
                        out_rel,
                        project_data,
                    )
                    if valid and contract_ok:
                        _log(f"[deterministic] Replaced long LLM output with project-specific plain source for {out_rel}")
                        continue
                    detail = f": {contract_error}" if contract_error else ""
                    _log(f"[warn] Deterministic source failed validation for {out_rel}{detail}")

            if out_rel == "app/auth.py":
                if _write_invariant_auth(out_dir):
                    code = existing_path.read_text(encoding="utf-8", errors="ignore")
                    valid = validator(code)
                    contract_ok, contract_error = _validate_source_contract(
                        code,
                        out_rel,
                        project_data,
                    )
                    if valid and contract_ok:
                        _log("[deterministic] Wrote stable JWT source for app/auth.py")
                        continue
                    detail = f": {contract_error}" if contract_error else ""
                    _log(f"[warn] Stable auth source failed validation{detail}")

            if out_rel == "app/deps.py":
                if _write_invariant_deps(out_dir):
                    code = existing_path.read_text(encoding="utf-8", errors="ignore")
                    valid = validator(code)
                    contract_ok, contract_error = _validate_source_contract(
                        code,
                        out_rel,
                        project_data,
                    )
                    if valid and contract_ok:
                        _log("[deterministic] Wrote stable auth dependency source for app/deps.py")
                        continue
                    detail = f": {contract_error}" if contract_error else ""
                    _log(f"[warn] Stable deps source failed validation{detail}")

            if out_rel == "app/routers/auth.py":
                if _write_invariant_auth_router(out_dir):
                    code = existing_path.read_text(encoding="utf-8", errors="ignore")
                    valid = validator(code)
                    contract_ok, contract_error = _validate_source_contract(
                        code,
                        out_rel,
                        project_data,
                    )
                    if valid and contract_ok:
                        _log("[deterministic] Wrote stable auth router source for app/routers/auth.py")
                        continue
                    detail = f": {contract_error}" if contract_error else ""
                    _log(f"[warn] Stable auth router failed validation{detail}")

            if out_rel in {"frontend_templates/entity_list.html", "frontend_templates/entity_form.html"}:
                if _write_frontend_contract_page(out_dir, out_rel):
                    code = existing_path.read_text(encoding="utf-8", errors="ignore")
                    valid = validator(code)
                    contract_ok, contract_error = _validate_source_contract(
                        code,
                        out_rel,
                        project_data,
                    )
                    if valid and contract_ok:
                        _log(f"[deterministic] Wrote compatibility shell for {out_rel}")
                        continue
                    detail = f": {contract_error}" if contract_error else ""
                    _log(f"[warn] Compatibility shell failed validation for {out_rel}{detail}")

            if ftype == "html":
                predict_tokens = 4200
            elif out_rel in {"app/db.py", "app/auth.py", "app/deps.py"}:
                predict_tokens = 1400
            elif out_rel == "app/routers/auth.py":
                predict_tokens = 2200
            else:
                predict_tokens = 3400
            if out_rel in {"app/auth.py", "app/deps.py", "app/routers/auth.py"}:
                original_user_msg = (
                    f"Generate {out_rel} now. Follow the system instructions exactly. "
                    "Return only the complete raw Python file."
                )
            else:
                original_user_msg = json.dumps(context, ensure_ascii=False)
            user_msg = original_user_msg
            max_llm_attempts = 3
            written = False

            for attempt in range(1, max_llm_attempts + 1):
                raw = ""
                try:
                    raw = ask_llm_fn(
                        system=system,
                        user=user_msg,
                        num_predict=predict_tokens,
                    )
                except Exception as llm_err:
                    _log(f"[warn] LLM call failed for {out_rel} (attempt {attempt}/{max_llm_attempts}): {llm_err}")
                    if attempt >= max_llm_attempts:
                        break
                    continue

                code = _clean_llm_code(raw, ftype)

                if ftype == "python":
                    from builder.python_syntax import validate_python_syntax
                    ok_syntax, err_msg, err_line = validate_python_syntax(code, out_rel)
                    if not ok_syntax:
                        rejection = f"Python syntax error on line {err_line}: {err_msg}"
                        preview = raw[:160].replace("\r", " ").replace("\n", " ")
                        _log(
                            f"[warn] LLM syntax error in {out_rel} (attempt {attempt}/{max_llm_attempts}) "
                            f"line {err_line}: {err_msg}; output starts: {preview!r}"
                        )
                        user_msg = (
                            f"{original_user_msg}\n\n"
                            f"Your previous output was rejected: {rejection}. "
                            "Return the complete corrected file as raw source only."
                        )
                        continue

                valid = validator(code) if code else False
                contract_error = ""
                if valid:
                    valid, contract_error = _validate_source_contract(
                        code,
                        out_rel,
                        project_data,
                    )
                if valid:
                    out_path = out_dir / out_rel
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(code, encoding="utf-8")
                    _log(f"[llm] Wrote {out_rel} ({len(code)} chars)")
                    written = True
                    break
                detail = f": {contract_error}" if contract_error else ""
                _log(
                    f"[warn] LLM output invalid for {out_rel} "
                    f"(attempt {attempt}/{max_llm_attempts}){detail}"
                )
                rejection = contract_error or "the file was empty or failed its structural validator"
                user_msg = (
                    f"{original_user_msg}\n\n"
                    f"Your previous output was rejected: {rejection}. "
                    "Return the complete corrected file as raw source only and satisfy every system requirement."
                )

            if not written:
                raise RuntimeError(
                    f"From-scratch generation failed for {out_rel} after {max_llm_attempts} attempts"
                )

        missing = [
            spec["output"]
            for spec in plan
            if not (out_dir / spec["output"]).exists()
            or (out_dir / spec["output"]).stat().st_size < 40
        ]
        if missing:
            raise RuntimeError(f"Generated source files are missing: {', '.join(missing)}")

    else:
        raise AssertionError("ask_llm_fn must be available for plain-source generation")

    # â”€â”€â”€ Auto-copy .env.example â†’ .env â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _write_smoke_tests(out_dir)

    from builder.python_syntax import validate_project_python_files
    syntax_issues = validate_project_python_files(out_dir)
    if syntax_issues:
        for issue in syntax_issues:
            _log(f"[error] Syntax invalid in {issue.path}: {issue.message} (line {issue.lineno})")
        names = ", ".join(i.path for i in syntax_issues)
        raise RuntimeError(f"Generated app has Python syntax errors in: {names}")

    env_example = out_dir / ".env.example"
    env_file    = out_dir / ".env"
    if env_example.exists() and not env_file.exists():
        shutil.copy(env_example, env_file)

    # â”€â”€â”€ Save artifacts for traceability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    artifacts_dir = out_dir / "_builder_artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    (artifacts_dir / "project_data.json").write_text(
        json.dumps(project_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    generated_sources = {}
    for path in sorted(
        list((out_dir / "app").rglob("*.py"))
        + list((out_dir / "frontend_templates").glob("*.html"))
        + [out_dir / "seed.py"]
    ):
        if path.exists():
            generated_sources[path.relative_to(out_dir).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    (artifacts_dir / "generation_manifest.json").write_text(
        json.dumps(
            {
                "mode": "guarded_project_specific_plain_source",
                "project_id": project_id,
                "files": generated_sources,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    reqs = project_data.get("requirements", {})
    if reqs:
        (out_dir / "requirements.json").write_text(
            json.dumps(reqs, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    _log(f"[done] Repository generated at: {out_dir}")
    return GenerateResult(out_dir=str(out_dir), project_slug=project_slug)


# ---------------------------------------------------------------------------
# Public API â€” called by builder/app.py
# ---------------------------------------------------------------------------
def generate_repo(
    project_id: str,
    data: dict,
    ask_llm_fn: Optional[Callable] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Public API used by Streamlit app.py.

    Args:
        project_id:        Unique project identifier.
        data:              Full project_data dict from session state.
        ask_llm_fn:        Required callable matching signature:
                             ask_llm(system: str, user: str, num_predict: int) -> str
                           All application Python and HTML files are generated from
                           scratch by the LLM. None is rejected.
        progress_callback: Optional callable(str) for live progress logging.

    Returns:
        str: absolute path to the generated project directory.
    """
    # Ensure generated_apps package is importable (needed for codegen_prompts)
    _generator_dir = Path(__file__).resolve().parent
    _gen_apps_dir  = _generator_dir.parent
    for _p in [str(_gen_apps_dir), str(_generator_dir)]:
        if _p not in sys.path:
            sys.path.insert(0, _p)

    repo_root      = Path(__file__).resolve().parents[2]
    generated_root = repo_root / "generated_apps" / "projects"
    generated_root.mkdir(parents=True, exist_ok=True)

    result = _generate_repo_internal(
        project_data=data,
        generated_root=str(generated_root),
        project_id=project_id,
        ask_llm_fn=ask_llm_fn,
        progress_callback=progress_callback,
    )
    return result.out_dir

