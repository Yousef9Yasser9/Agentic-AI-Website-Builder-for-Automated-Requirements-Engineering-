"""
Build a focused runtime test plan from project artifacts.

Scope:
  - Page loading
  - Buttons / forms / navigation
  - Database CRUD
  - Role-based access and dashboards
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from builder.app_contract import build_app_contract, field_type_map


@dataclass
class PageTestCase:
    path: str
    name: str
    expected_in_body: List[str] = field(default_factory=list)
    allow_redirect: bool = False


@dataclass
class ActionTestCase:
    test_id: str
    category: str  # ui_action
    name: str
    method: str
    path: str
    json_body: Optional[Dict[str, Any]] = None
    form_data: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    expected_status: int = 200
    follow_redirect: bool = True
    expect_json_key: Optional[str] = None
    navigate_from: Optional[str] = None
    link_href: Optional[str] = None


@dataclass
class DatabaseTestCase:
    test_id: str
    name: str
    resource: str
    entity_class: str
    operation: str  # init, list, create, read, update, delete
    sample_payload: Dict[str, Any] = field(default_factory=dict)
    fk_refs: Dict[str, str] = field(default_factory=dict)


@dataclass
class RoleTestCase:
    test_id: str
    name: str
    email: str
    password: str
    role: str
    expected_landing: str
    allowed_nav_paths: List[str] = field(default_factory=list)
    forbidden_nav_paths: List[str] = field(default_factory=list)
    dashboard_stats_keys: List[str] = field(default_factory=list)
    forbidden_api_paths: List[str] = field(default_factory=list)


@dataclass
class RuntimeTestPlan:
    pages: List[PageTestCase] = field(default_factory=list)
    actions: List[ActionTestCase] = field(default_factory=list)
    database: List[DatabaseTestCase] = field(default_factory=list)
    roles: List[RoleTestCase] = field(default_factory=list)

    @property
    def total_tests(self) -> int:
        return len(self.pages) + len(self.actions) + len(self.database) + len(self.roles)


def _non_user_entities(data_model: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        e for e in (data_model.get("entities") or [])
        if str(e.get("name", "")).lower() != "user"
    ]


def _fk_refs_for_entity(
    entity: Any,
    relationships: List[Dict[str, Any]],
    entities: List[Any],
) -> Dict[str, str]:
    entity_name = entity.class_name
    entity_names = {
        item.class_name for item in entities
    }
    resources_by_class = {item.class_name: item.resource for item in entities}
    refs: Dict[str, str] = {}
    for rel in relationships:
        rel_from = "".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", str(rel.get("from", ""))))
        rel_to = "".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", str(rel.get("to", ""))))
        fk_field = str(rel.get("fk_field") or "")
        if rel_from == entity_name and rel_to and fk_field:
            if rel_to == "User" or rel_to not in entity_names:
                refs[fk_field] = "__current_user__"
            else:
                refs[fk_field] = resources_by_class[rel_to]
    return refs


def _default_sample_payload(entity: Any, fk_refs: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    import uuid as _uuid

    payload: Dict[str, Any] = {}
    fk_refs = fk_refs or {}
    for f in entity.fields:
        fname = str(f.get("name", ""))
        if fname.lower() in ("id", "password_hash", "created_at", "updated_at"):
            continue
        fmap = field_type_map(f)
        ftype = str(fmap["pydantic"]).lower()
        if fname in fk_refs:
            payload[fname] = "__FK__"
        elif fname.endswith("_id") or ftype == "uuid":
            payload[fname] = str(_uuid.uuid4())
        elif "int" in ftype or ftype in ("integer", "number"):
            payload[fname] = 1
        elif "float" in ftype or "decimal" in ftype:
            payload[fname] = 9.99
        elif "bool" in ftype:
            payload[fname] = True
        elif "date" in ftype:
            payload[fname] = "2026-01-01"
        else:
            payload[fname] = f"runtime_test_{fname}"
    return payload


def build_runtime_test_plan(project_data: Dict[str, Any]) -> RuntimeTestPlan:
    """Derive page, UI action, and database tests from requirements artifacts."""
    arch = project_data.get("architecture", {}) or {}
    dm = project_data.get("data_model", {}) or {}
    contract = build_app_contract(project_data)
    entities = contract.business_entities()
    visible_entities = [entity for entity in entities if entity.ui_visible]
    admin_account = contract.demo_accounts.get("Admin") or contract.demo_accounts.get("admin") or {
        "email": "admin@example.com",
        "password": "Admin1234!",
    }
    public_account = contract.demo_accounts.get(contract.public_role) or {
        "email": "user@example.com",
        "password": "User1234!",
    }
    plan = RuntimeTestPlan()

    seen_pages: set[str] = set()

    def add_page(path: str, name: str, markers: Optional[List[str]] = None) -> None:
        if not path or path in seen_pages:
            return
        seen_pages.add(path)
        plan.pages.append(
            PageTestCase(
                path=path,
                name=name,
                expected_in_body=markers or [],
            )
        )

    add_page("/", "Dashboard", ["window.APP_CONFIG", "<html"])
    add_page("/admin/dashboard", "Admin dashboard", ["window.APP_CONFIG", "<html"])
    add_page("/ui/login", "Login page", ["login", "<form", "email"])
    add_page("/ui/register", "Register page", ["register", "<form", "email"])

    for entity in visible_entities:
        add_page(f"/ui/{entity.resource}", f"{entity.raw_name} list", ["APP_CONFIG", "<html"])
        add_page(f"/ui/{entity.resource}/new", f"New {entity.raw_name}", ["APP_CONFIG", "<html"])

    for page in arch.get("pages") or []:
        path = page.get("path")
        if not path or path in seen_pages or str(path).startswith("/ui/"):
            continue
        if path in ("/", "/admin/dashboard"):
            continue
        title = page.get("name") or path
        add_page(path, title, ["<html"])

    plan.actions.append(
        ActionTestCase(
            test_id="action_health",
            category="ui_action",
            name="Health endpoint",
            method="GET",
            path="/health",
            expected_status=200,
        )
    )

    plan.actions.append(
        ActionTestCase(
            test_id="action_login_api",
            category="ui_action",
            name="Login API",
            method="POST",
            path=f"{contract.api_prefix}/auth/login",
            json_body={"email": admin_account["email"], "password": admin_account["password"]},
            expected_status=200,
            expect_json_key="access_token",
        )
    )

    plan.actions.append(
        ActionTestCase(
            test_id="action_register_page_form",
            category="ui_action",
            name="Register page has submit hook",
            method="GET",
            path="/ui/register",
            expected_status=200,
        )
    )

    plan.actions.append(
        ActionTestCase(
            test_id="action_login_page_form",
            category="ui_action",
            name="Login page has submit hook",
            method="GET",
            path="/ui/login",
            expected_status=200,
        )
    )

    for entity in visible_entities:
        res = entity.resource
        cls = entity.class_name
        plan.actions.append(
            ActionTestCase(
                test_id=f"action_nav_list_{res}",
                category="ui_action",
                name=f"Navigate to {cls} list UI",
                method="GET",
                path=f"/ui/{res}",
                expected_status=200,
                navigate_from="/",
            )
        )
        plan.actions.append(
            ActionTestCase(
                test_id=f"action_nav_new_{res}",
                category="ui_action",
                name=f"Navigate to new {cls} form",
                method="GET",
                path=f"/ui/{res}/new",
                expected_status=200,
            )
        )

    plan.database.append(
        DatabaseTestCase(
            test_id="db_init_metadata",
            name="Database tables created",
            resource="",
            entity_class="",
            operation="init",
        )
    )

    plan.database.append(
        DatabaseTestCase(
            test_id="db_auth_me",
            name="Authenticated read /api/auth/me",
            resource="auth",
            entity_class="User",
            operation="me",
        )
    )

    for entity in entities:
        res = entity.resource
        cls = entity.class_name
        fk_refs = _fk_refs_for_entity(entity, dm.get("relationships") or [], entities)
        sample = _default_sample_payload(entity, fk_refs)

        plan.database.extend([
            DatabaseTestCase(
                test_id=f"db_list_{res}",
                name=f"List {cls} records",
                resource=res,
                entity_class=cls,
                operation="list",
            ),
            DatabaseTestCase(
                test_id=f"db_create_{res}",
                name=f"Create {cls} record",
                resource=res,
                entity_class=cls,
                operation="create",
                sample_payload=sample,
                fk_refs=fk_refs,
            ),
            DatabaseTestCase(
                test_id=f"db_read_{res}",
                name=f"Read {cls} record by id",
                resource=res,
                entity_class=cls,
                operation="read",
            ),
            DatabaseTestCase(
                test_id=f"db_update_{res}",
                name=f"Update {cls} record",
                resource=res,
                entity_class=cls,
                operation="update",
                sample_payload=sample,
                fk_refs=fk_refs,
            ),
            DatabaseTestCase(
                test_id=f"db_delete_{res}",
                name=f"Delete {cls} record",
                resource=res,
                entity_class=cls,
                operation="delete",
            ),
        ])

    plan.actions.append(
        ActionTestCase(
            test_id="action_dashboard_stats",
            category="ui_action",
            name="Dashboard stats API returns counts",
            method="GET",
            path=f"{contract.api_prefix}/dashboard/stats",
            expected_status=200,
            expect_json_key=None,
        )
    )

    # Role-based tests when auth roles exist
    arch_roles = [str(r).lower() for r in contract.roles]
    has_admin = "admin" in arch_roles
    primary_normal_role = contract.public_role.lower()
    has_customer = bool(primary_normal_role)

    admin_only_paths: List[str] = []
    customer_paths: List[str] = []
    admin_stats: List[str] = []
    customer_stats: List[str] = []

    for entity in visible_entities:
        res = entity.resource
        read_roles = {str(role).lower() for role in entity.read_roles}
        if "admin" in read_roles:
            admin_only_paths.append(f"/ui/{res}")
        if primary_normal_role in read_roles:
            customer_paths.append(f"/ui/{res}")
        if "admin" in read_roles:
            admin_stats.append(res)
        if primary_normal_role in read_roles:
            customer_stats.append(res)

    if has_admin:
        plan.roles.append(
            RoleTestCase(
                test_id="role_admin",
                name="Admin role access",
                email=admin_account["email"],
                password=admin_account["password"],
                role="admin",
                expected_landing="/admin/dashboard",
                allowed_nav_paths=["/admin/dashboard"] + admin_only_paths + customer_paths,
                forbidden_nav_paths=[],
                dashboard_stats_keys=admin_stats,
                forbidden_api_paths=[],
            )
        )

    if has_customer:
        forbidden = []
        forbidden_api = []
        for entity in entities:
            res = entity.resource
            read_roles = {str(role).lower() for role in entity.read_roles}
            if "admin" in read_roles and primary_normal_role not in read_roles:
                if entity.ui_visible:
                    forbidden.append(f"/ui/{res}")
                forbidden_api.append(f"{contract.api_prefix}/{res}")
        plan.roles.append(
            RoleTestCase(
                test_id="role_customer",
                name=f"{contract.public_role} role access",
                email=public_account["email"],
                password=public_account["password"],
                role=primary_normal_role,
                expected_landing="/",
                allowed_nav_paths=["/"] + customer_paths,
                forbidden_nav_paths=["/admin/dashboard"] + forbidden,
                dashboard_stats_keys=customer_stats,
                forbidden_api_paths=forbidden_api,
            )
        )

    return plan


def load_project_data(project_dir: str) -> Dict[str, Any]:
    from pathlib import Path
    import json

    artifacts = Path(project_dir) / "_builder_artifacts" / "project_data.json"
    if artifacts.exists():
        return json.loads(artifacts.read_text(encoding="utf-8"))
    req = Path(project_dir) / "requirements.json"
    if req.exists():
        return {"requirements": json.loads(req.read_text(encoding="utf-8"))}
    return {}
