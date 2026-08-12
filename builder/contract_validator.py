"""
Validate consistency between generated frontend, backend routes, API, and APP_CONFIG.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from builder.app_contract import build_app_contract


HTTP_METHODS = ("get", "post", "put", "patch", "delete")


@dataclass
class ContractIssue:
    category: str
    message: str
    file: str = ""
    severity: str = "error"


@dataclass
class ContractReport:
    ok: bool
    issues: List[ContractIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [
                {"category": i.category, "message": i.message, "file": i.file, "severity": i.severity}
                for i in self.issues
            ],
        }


class EngineContractError(RuntimeError):
    """Raised when generated source disagrees with the AppContract before TDD."""

    def __init__(self, report: Dict[str, Any]):
        self.report = report
        super().__init__(_format_engine_contract_error(report))

    def to_dict(self) -> Dict[str, Any]:
        return self.report


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _normalize_route(path: str) -> str:
    clean = re.sub(r"//+", "/", str(path or "").strip())
    if not clean.startswith("/"):
        clean = "/" + clean
    if len(clean) > 1:
        clean = clean.rstrip("/")
    return clean


def _join_route(prefix: str, path: str) -> str:
    if not prefix:
        return _normalize_route(path)
    if not path or path == "/":
        return _normalize_route(prefix)
    return _normalize_route(f"{prefix.rstrip('/')}/{path.lstrip('/')}")


def _router_prefix(source: str) -> str:
    match = re.search(r"APIRouter\s*\([^)]*prefix\s*=\s*[rubfRUBF]*['\"]([^'\"]+)['\"]", source, re.DOTALL)
    return _normalize_route(match.group(1)) if match else ""


def parse_exposed_routes(project_dir: str | Path) -> List[str]:
    """Statically parse generated FastAPI decorators from main.py and routers."""
    root = Path(project_dir)
    files = [root / "app" / "main.py"]
    routers_dir = root / "app" / "routers"
    if routers_dir.exists():
        files.extend(sorted(routers_dir.glob("*.py")))

    routes: Set[str] = set()
    decorator = re.compile(
        r"@(app|router)\.(" + "|".join(HTTP_METHODS) + r")\s*\(\s*"
        r"(?:path\s*=\s*)?(?:[rubfRUBF]*)?['\"]([^'\"]+)['\"]",
        re.IGNORECASE,
    )
    for path in files:
        source = _read_text(path)
        if not source:
            continue
        prefix = _router_prefix(source)
        for match in decorator.finditer(source):
            owner = match.group(1).lower()
            route_path = match.group(3)
            route = _join_route(prefix if owner == "router" else "", route_path)
            if route.startswith(("/api", "/ui")):
                routes.add(route)
    return sorted(routes)


def _expected_preflight_routes(project_data: Dict[str, Any]) -> List[str]:
    contract = build_app_contract(project_data)
    expected = set(contract.api_paths())
    expected.update(contract.ui_paths())
    for ui_path in contract.ui_paths():
        expected.add(f"{ui_path}/new")
    expected.update(
        {
            f"{contract.api_prefix}/auth/register",
            f"{contract.api_prefix}/auth/login",
            f"{contract.api_prefix}/auth/login/form",
            f"{contract.api_prefix}/auth/me",
            f"{contract.api_prefix}/dashboard/stats",
            "/ui/login",
            "/ui/register",
        }
    )
    return sorted(_normalize_route(route) for route in expected)


def _class_names(source: str) -> Set[str]:
    return set(re.findall(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b", source, re.MULTILINE))


def run_engine_contract_preflight(
    project_dir: str | Path,
    project_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fast static coherence check between AppContract and generated source.

    This intentionally avoids importing the generated app, starting a server, or
    invoking pytest. It catches engine/contract drift before self-healing starts.
    """
    root = Path(project_dir)
    if project_data is None:
        artifacts = root / "_builder_artifacts" / "project_data.json"
        project_data = json.loads(artifacts.read_text(encoding="utf-8")) if artifacts.exists() else {}
    project_data = project_data or {}
    contract = build_app_contract(project_data)

    exposed_routes = parse_exposed_routes(root)
    expected_routes = _expected_preflight_routes(project_data)
    exposed_set = set(exposed_routes)
    missing_routes = sorted(route for route in expected_routes if route not in exposed_set)

    models_source = _read_text(root / "app" / "models.py")
    schemas_source = _read_text(root / "app" / "schemas.py")
    seed_source = _read_text(root / "seed.py")
    model_classes = _class_names(models_source)
    schema_classes = _class_names(schemas_source)

    missing_models: List[str] = []
    missing_schemas: Dict[str, List[str]] = {}
    for entity in contract.business_entities():
        if entity.class_name not in model_classes:
            missing_models.append(entity.class_name)
        required_schema_classes = [
            f"{entity.class_name}Create",
            f"{entity.class_name}Update",
            f"{entity.class_name}Read",
        ]
        absent = [name for name in required_schema_classes if name not in schema_classes]
        if absent:
            missing_schemas[entity.class_name] = absent

    public_account = contract.demo_accounts.get(contract.public_role) or {}
    public_email = public_account.get("email", "")
    public_password = public_account.get("password", "")
    missing_demo_account: List[str] = []
    if public_email and public_email not in seed_source:
        missing_demo_account.append(f"{contract.public_role} email {public_email}")
    if public_password and public_password not in seed_source:
        missing_demo_account.append(f"{contract.public_role} password")

    report: Dict[str, Any] = {
        "ok": not (missing_routes or missing_models or missing_schemas or missing_demo_account),
        "type": "EngineContractError",
        "api_prefix": contract.api_prefix,
        "missing_routes": missing_routes,
        "missing_models": sorted(missing_models),
        "missing_schemas": missing_schemas,
        "missing_demo_account": missing_demo_account,
        "expected_routes": expected_routes,
        "exposed_routes": exposed_routes,
        "exposed_sample": exposed_routes[:20],
        "message": "",
    }
    report["message"] = _format_engine_contract_error(report) if not report["ok"] else "Engine contract pre-flight passed."
    return report


def assert_engine_contract_preflight(
    project_dir: str | Path,
    project_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = run_engine_contract_preflight(project_dir, project_data)
    if not report.get("ok"):
        raise EngineContractError(report)
    return report


def _format_engine_contract_error(report: Dict[str, Any]) -> str:
    lines = [
        "EngineContractError: routes/classes the tests will call are not exposed by the app:",
    ]
    if report.get("missing_routes"):
        lines.append(f"  missing routes: {report['missing_routes']}")
    if report.get("missing_models"):
        lines.append(f"  missing model classes: {report['missing_models']}")
    if report.get("missing_schemas"):
        lines.append(f"  missing schema classes: {report['missing_schemas']}")
    if report.get("missing_demo_account"):
        lines.append(f"  missing demo account seed data: {report['missing_demo_account']}")
    lines.append(f"  expected api prefix: {report.get('api_prefix')}")
    lines.append(f"  exposed sample: {report.get('exposed_sample', [])}")
    lines.append("  => engine bug (generator/contract mismatch), NOT an app bug. Self-healing skipped.")
    return "\n".join(lines)


# Plain-source contract for standalone generated apps.
def validate_generated_app_contract(
    project_dir: str | Path,
    project_data: Optional[Dict[str, Any]] = None,
) -> ContractReport:
    root = Path(project_dir)
    issues: List[ContractIssue] = []
    if project_data is None:
        artifacts = root / "_builder_artifacts" / "project_data.json"
        project_data = json.loads(artifacts.read_text(encoding="utf-8")) if artifacts.exists() else {}
    contract = build_app_contract(project_data)
    entities = contract.business_entities()

    source = {
        rel: _read_text(root / rel)
        for rel in (
            "app/main.py",
            "app/deps.py",
            "app/routers/auth.py",
            "app/routers/generic_crud.py",
            "seed.py",
            "frontend_templates/index.html",
            "frontend_templates/app.html",
            "frontend_templates/login.html",
            "frontend_templates/register.html",
            "frontend_templates/entity_list.html",
            "frontend_templates/entity_form.html",
        )
    }
    for rel, content in source.items():
        if not content:
            issues.append(ContractIssue("files", f"Missing or empty source file: {rel}", rel))

    main_py = source["app/main.py"]
    auth_py = source["app/routers/auth.py"]
    crud_py = source["app/routers/generic_crud.py"]
    deps_py = source["app/deps.py"]
    seed_py = source["seed.py"]

    for route in ("/health", f"{contract.api_prefix}/dashboard/stats"):
        if route not in main_py:
            issues.append(ContractIssue("routes", f"Missing guaranteed route {route}", "app/main.py"))
    for route in ("/register", "/login", "/login/form", "/me"):
        if route not in auth_py:
            issues.append(ContractIssue("auth", f"Missing authentication route {route}", "app/routers/auth.py"))
    if "PUBLIC_REGISTER_ROLE" not in auth_py:
        issues.append(
            ContractIssue(
                "auth",
                "Public registration must force the configured public role",
                "app/routers/auth.py",
            )
        )
    if ".lower()" not in deps_py:
        issues.append(ContractIssue("roles", "Role checks must normalize casing", "app/deps.py"))
    if "drop_all" in seed_py:
        issues.append(ContractIssue("seed", "Seed script may not drop application data", "seed.py"))

    for entity in entities:
        resource = entity.resource
        api_path = f"{contract.api_prefix}/{resource}"
        if api_path not in crud_py and f'"/{resource}"' not in crud_py and f"'/{resource}'" not in crud_py:
            issues.append(
                ContractIssue(
                    "api",
                    f"Missing CRUD routes for {entity.raw_name}",
                    "app/routers/generic_crud.py",
                )
            )
        if entity.ui_visible and f"/ui/{resource}" not in main_py:
            issues.append(
                ContractIssue(
                    "routes",
                    f"Missing UI list route /ui/{resource}",
                    "app/main.py",
                )
            )

    ownership_fields = {
        field.get("name")
        for entity in entities
        for field in entity.fields
    } & {"user_id", "owner_id", "created_by", "customer_id", "uploader_id"}
    if ownership_fields and not any(field in crud_py for field in ownership_fields):
        issues.append(
            ContractIssue(
                "authorization",
                "Owned entities are not scoped in CRUD queries",
                "app/routers/generic_crud.py",
            )
        )

    for rel, content in source.items():
        if not rel.endswith(".html") or not content:
            continue
        if any(marker in content for marker in ("{{", "{%", "{#")):
            issues.append(ContractIssue("frontend", "Jinja syntax is forbidden", rel))
        if "access_token" not in content or "apiFetch" not in content:
            issues.append(ContractIssue("frontend", "Canonical auth helpers are missing", rel))

    errors = [issue for issue in issues if issue.severity == "error"]
    return ContractReport(ok=not errors, issues=issues)


def repair_contract_issues(project_dir: str | Path, project_data: Dict[str, Any]) -> List[str]:
    """Contract repairs are handled by the project-aware healer, never a template."""
    return []
