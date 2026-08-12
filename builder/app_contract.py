"""Canonical application contract derived from project_data.

This module centralizes the facts that generated backends, frontends, tests,
and validators currently infer separately. It intentionally captures existing
rules without changing generator behavior yet.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List

from builder.data_model_guard import should_expose_entity_in_ui
from generated_apps.generator.engine_rules import infer_entity_access, normalize_field_type


API_PREFIX = "/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin1234!"
CUSTOMER_EMAIL = "user@example.com"
CUSTOMER_PASSWORD = "User1234!"

_PUBLIC_ROLE_PREFERENCE = ("Patient", "Customer", "Client", "Student", "User")
_PUBLIC_DEMO_ROLES = {
    "attendee",
    "customer",
    "client",
    "guest",
    "patient",
    "student",
    "tenant",
    "member",
    "user",
}
_ROLE_EMAILS = {
    "admin": ADMIN_EMAIL,
    "staff": "staff@example.com",
    "mechanic": "mechanic@example.com",
    "receptionist": "receptionist@example.com",
    "manager": "manager@example.com",
    "doctor": "doctor@example.com",
    "teacher": "teacher@example.com",
}
_ROLE_PASSWORDS = {
    "admin": ADMIN_PASSWORD,
    "staff": "Staff1234!",
    "mechanic": "Mechanic1234!",
    "receptionist": "Receptionist1234!",
    "manager": "Manager1234!",
    "doctor": "Doctor1234!",
    "teacher": "Teacher1234!",
}


@dataclass
class EntitySpec:
    raw_name: str
    class_name: str
    resource: str
    fields: List[Dict[str, Any]]
    read_roles: List[str]
    write_roles: List[str]
    scope_fields: List[str]
    ui_visible: bool
    is_user_entity: bool


@dataclass
class AppContract:
    api_prefix: str
    roles: List[str]
    public_role: str
    entities: List[EntitySpec]
    demo_accounts: Dict[str, Dict[str, str]]

    def business_entities(self) -> List[EntitySpec]:
        return [entity for entity in self.entities if not entity.is_user_entity]

    def api_paths(self) -> List[str]:
        return [f"{self.api_prefix}/{entity.resource}" for entity in self.business_entities()]

    def ui_paths(self) -> List[str]:
        return [f"/ui/{entity.resource}" for entity in self.business_entities() if entity.ui_visible]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        clean = str(value or "").strip()
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(clean)
    return result


def _project_roles(project_data: Dict[str, Any]) -> List[str]:
    roles = []
    for role in (project_data.get("architecture", {}) or {}).get("roles") or []:
        value = str(role or "").strip()
        if value:
            roles.append(value)
    return _dedupe(roles) or ["User", "Admin"]


def _default_public_role(project_data: Dict[str, Any]) -> str:
    roles = _project_roles(project_data)
    for preferred in _PUBLIC_ROLE_PREFERENCE:
        if any(role.lower() == preferred.lower() for role in roles):
            return preferred
    return next((role for role in roles if role.lower() != "admin"), "User")


def _entity_class_name(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", str(name)))


def resource_path(entity_name: str) -> str:
    """Return the current canonical resource segment for /api and /ui paths."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", str(entity_name)).strip("_").lower() + "s"


def _access_context(project_data: Dict[str, Any]) -> Dict[str, Any]:
    architecture = project_data.get("architecture", {}) or {}
    return {
        **architecture,
        "plain_text": project_data.get("plain_text", ""),
        "cleaned_spec": project_data.get("cleaned_spec", {}) or {},
        "requirements": project_data.get("requirements", {}) or {},
        "user_stories": project_data.get("user_stories", {}) or {},
        "data_model": project_data.get("data_model", {}) or {},
    }


def _scope_fields(access: Dict[str, Any]) -> List[str]:
    scope = access.get("role_scope_fields") or {}
    if isinstance(scope, dict):
        fields: List[str] = []
        for values in scope.values():
            if isinstance(values, (list, tuple, set)):
                fields.extend(str(value) for value in values)
            elif values:
                fields.append(str(values))
        return sorted({field for field in fields if field})
    return _dedupe(str(field) for field in scope)


def _normalize_field(field: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(field or {})
    name = str(normalized.get("name", "")).strip()
    normalized["name"] = name
    normalized["type"] = _normalized_field_type(normalized)
    type_map = field_type_map(normalized)
    normalized["type_map"] = type_map
    normalized["python_type"] = type_map["python"]
    normalized["pydantic_type"] = type_map["pydantic"]
    normalized["sqlalchemy_type"] = type_map["sqlalchemy"]
    return normalized


def _normalized_field_type(field: Dict[str, Any]) -> str:
    name = str(field.get("name", ""))
    raw_type = str(field.get("type", "string") or "string")
    normalized = normalize_field_type(name, raw_type).lower()
    if normalized == "bool":
        return "boolean"
    if name.lower() == "date" and normalized in {"string", "text"}:
        return "date"
    return normalized


def _demo_account_for_role(role: str) -> Dict[str, str]:
    role_key = str(role or "").strip().lower()
    if role_key in _PUBLIC_DEMO_ROLES:
        return {"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
    email = _ROLE_EMAILS.get(role_key) or f"{re.sub(r'[^a-z0-9]+', '', role_key) or 'user'}@example.com"
    password = _ROLE_PASSWORDS.get(role_key) or CUSTOMER_PASSWORD
    return {"email": email, "password": password}


def _demo_accounts(roles: List[str], public_role: str) -> Dict[str, Dict[str, str]]:
    accounts = {role: _demo_account_for_role(role) for role in roles}
    if public_role not in accounts:
        accounts[public_role] = _demo_account_for_role(public_role)
    return accounts


def build_app_contract(project_data: Dict[str, Any]) -> AppContract:
    project_data = project_data or {}
    roles = _project_roles(project_data)
    public_role = _default_public_role(project_data)
    data_model = project_data.get("data_model", {}) or {}
    access_context = _access_context(project_data)
    entities: List[EntitySpec] = []

    for entity in data_model.get("entities") or []:
        raw_name = str(entity.get("name", "")).strip()
        is_user = raw_name.lower() == "user"
        access = infer_entity_access(entity, access_context)
        fields = [_normalize_field(field) for field in entity.get("fields") or []]
        entities.append(
            EntitySpec(
                raw_name=raw_name,
                class_name=_entity_class_name(raw_name),
                resource=resource_path(raw_name),
                fields=fields,
                read_roles=list(access.get("read_roles") or []),
                write_roles=list(access.get("write_roles") or []),
                scope_fields=_scope_fields(access),
                ui_visible=bool(should_expose_entity_in_ui(raw_name, data_model)),
                is_user_entity=is_user,
            )
        )

    return AppContract(
        api_prefix=API_PREFIX,
        roles=roles,
        public_role=public_role,
        entities=entities,
        demo_accounts=_demo_accounts(roles, public_role),
    )


def field_type_map(field: Dict[str, Any]) -> Dict[str, str]:
    """Return canonical Python/Pydantic/SQLAlchemy type names for a data field."""
    normalized = _normalized_field_type(field or {})
    if normalized == "uuid" or (field or {}).get("pk"):
        return {"python": "UUID", "pydantic": "UUID", "sqlalchemy": "GUID"}
    if normalized == "text":
        return {"python": "str", "pydantic": "str", "sqlalchemy": "Text"}
    if normalized == "int":
        return {"python": "int", "pydantic": "int", "sqlalchemy": "Integer"}
    if normalized == "float":
        return {"python": "float", "pydantic": "float", "sqlalchemy": "Float"}
    if normalized == "decimal":
        return {"python": "float", "pydantic": "float", "sqlalchemy": "Numeric(12, 2)"}
    if normalized == "boolean":
        return {"python": "bool", "pydantic": "bool", "sqlalchemy": "Boolean"}
    if normalized == "datetime":
        return {"python": "DateTime", "pydantic": "DateTime", "sqlalchemy": "DateTime"}
    if normalized == "date":
        return {"python": "Date", "pydantic": "Date", "sqlalchemy": "Date"}
    return {"python": "str", "pydantic": "str", "sqlalchemy": "String(255)"}


__all__ = [
    "API_PREFIX",
    "AppContract",
    "EntitySpec",
    "build_app_contract",
    "field_type_map",
    "resource_path",
]
