"""Normalize LLM-produced architecture before downstream generation."""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Tuple


def _canonical_role(value: Any) -> str | None:
    role = str(value or "").strip().lower()
    if role in {"system", "the system", "application", "platform"}:
        return None
    if "admin" in role:
        return "Admin"
    if "staff" in role or "back-office" in role or "operator" in role:
        return "Staff"
    if "manager" in role:
        return "Manager"
    if "agent" in role or "realtor" in role:
        return "Agent"
    if "tenant" in role or "renter" in role:
        return "Tenant"
    if "employee" in role:
        return "Employee"
    if "guest" in role or "visitor" in role:
        return "Guest"
    if "member" in role:
        return "Member"
    if "doctor" in role or "physician" in role:
        return "Doctor"
    if "patient" in role:
        return "Patient"
    if "student" in role:
        return "Student"
    if "teacher" in role or "professor" in role:
        return "Teacher"
    if "customer" in role or "buyer" in role:
        return "Customer"
    if "client" in role:
        return "Client"
    if any(token in role for token in ("user", "public")):
        return "User"
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", str(value or "")).strip()
    if cleaned:
        return "".join(part[:1].upper() + part[1:].lower() for part in cleaned.split())
    return None


def _add_role(roles: List[str], value: Any) -> None:
    role = _canonical_role(value)
    if role and role not in roles:
        roles.append(role)


def _page_role_hint(page: Dict[str, Any], known_roles: List[str]) -> str | None:
    text = " ".join(str(page.get(key) or "") for key in ("name", "desc")).lower()
    if not text:
        return None
    for role in known_roles:
        if role == "Admin":
            continue
        if re.search(rf"\b{re.escape(role.lower())}\b", text):
            return role
    if re.search(r"\badmin\b", text):
        return "Admin"
    return None


def _clean_path(value: Any) -> str:
    path = str(value or "/").strip()
    if not path.startswith("/"):
        path = f"/{path}"
    path = re.sub(r"/\{[^/{}]+\}", "/view", path)
    path = re.sub(r"/+", "/", path)
    return path.rstrip("/") or "/"


def _clean_api_path(value: Any) -> str:
    path = str(value or "/").strip()
    if not path.startswith("/"):
        path = f"/{path}"
    path = re.sub(r"/+", "/", path)
    return path.rstrip("/") or "/"


def _path_for_role(path: str, role: str) -> str:
    if role == "Admin":
        if path == "/":
            return "/admin/dashboard"
        return path if path.startswith("/admin/") else f"/admin{path}"
    if path == "/admin":
        return "/"
    if path.startswith("/admin/"):
        return path[len("/admin") :] or "/"
    return path


def _entity_slug(entity: Any) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(entity or "").strip().lower()).strip("-")
    if not value:
        return ""
    if value.endswith("y") and not value.endswith(("ay", "ey", "oy")):
        return f"{value[:-1]}ies"
    if value.endswith("s"):
        return value
    return f"{value}s"


def normalize_architecture(project_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Return a copy with canonical roles, role-separated pages, and secured writes."""
    normalized = copy.deepcopy(project_data)
    architecture = normalized.get("architecture")
    if not isinstance(architecture, dict):
        return normalized, []

    fixes: List[str] = []
    stack = architecture.setdefault("stack", {})
    if isinstance(stack, dict) and stack.get("db") != "SQLite":
        stack["db"] = "SQLite"
        fixes.append("Aligned database stack with the generated SQLite runtime")

    normalized_roles: List[str] = []
    for raw_role in architecture.get("roles") or []:
        _add_role(normalized_roles, raw_role)
    for story in architecture.get("stories_min") or []:
        if isinstance(story, dict):
            _add_role(normalized_roles, story.get("role"))
    for feature in architecture.get("features") or []:
        if isinstance(feature, dict):
            for raw_role in feature.get("roles") or []:
                _add_role(normalized_roles, raw_role)
    for raw_page in architecture.get("pages") or []:
        if not isinstance(raw_page, dict):
            continue
        for raw_role in raw_page.get("role_access") or []:
            _add_role(normalized_roles, raw_role)
        page_text = " ".join(str(raw_page.get(key) or "") for key in ("name", "desc"))
        for token in ("Guest", "Staff", "Manager", "Agent", "Tenant", "Employee", "Member", "Doctor", "Patient", "Student", "Teacher", "Customer", "Client"):
            if re.search(rf"\b{token.lower()}\b", page_text.lower()):
                _add_role(normalized_roles, token)
    if "Admin" not in normalized_roles:
        normalized_roles.append("Admin")
    if not any(role != "Admin" for role in normalized_roles):
        normalized_roles.insert(0, "User")
    architecture["roles"] = normalized_roles

    pages: List[Dict[str, Any]] = []
    seen_pages = set()
    for raw_page in architecture.get("pages") or []:
        if not isinstance(raw_page, dict):
            continue
        original_path = str(raw_page.get("path") or "/")
        clean_path = _clean_path(original_path)
        raw_roles = raw_page.get("role_access") or []
        roles = []
        for value in raw_roles:
            role = _canonical_role(value)
            if role and role not in roles:
                roles.append(role)
        hinted_role = _page_role_hint(raw_page, normalized_roles)
        if hinted_role and hinted_role != "Admin" and roles == ["Admin"]:
            roles = [hinted_role]
            fixes.append(f"Recovered {hinted_role} access for page {str(raw_page.get('name') or clean_path)!r}")
        if not roles:
            roles = ["Admin" if clean_path.startswith("/admin") else next((r for r in normalized_roles if r != "Admin"), "User")]

        for role in roles:
            page = copy.deepcopy(raw_page)
            page["role_access"] = [role]
            page["path"] = _path_for_role(clean_path, role)
            if role == "Admin" and len(roles) > 1:
                name = str(page.get("name") or "Page")
                page["name"] = name if name.lower().startswith("admin") else f"Admin {name}"
            key = (page["path"], role)
            if key not in seen_pages:
                seen_pages.add(key)
                pages.append(page)

        if len(roles) > 1:
            fixes.append(f"Split shared page {original_path!r} into role-specific pages")
        if clean_path != original_path:
            fixes.append(f"Removed path variables from UI page {original_path!r}")

    architecture["pages"] = pages
    page_roles = {role for page in pages for role in page.get("role_access") or []}
    for role in normalized_roles:
        if role == "Admin" or role in page_roles:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-") or "user"
        path = "/" if not any(page.get("path") == "/" for page in pages) else f"/{slug}/dashboard"
        pages.append(
            {
                "name": f"{role} Dashboard",
                "path": path,
                "role_access": [role],
                "target_entity": None,
                "desc": f"Role-specific dashboard for {role}",
            }
        )
        fixes.append(f"Added missing {role} dashboard page")

    admin_entities = {
        _entity_slug(page.get("target_entity"))
        for page in pages
        if page.get("role_access") == ["Admin"] and page.get("target_entity")
    }
    non_admin_write_entities = {
        _entity_slug(page.get("target_entity"))
        for page in pages
        if page.get("target_entity")
        and page.get("role_access") != ["Admin"]
        and any(
            token in str(page.get("name") or page.get("path") or page.get("desc") or "").lower()
            for token in ("manage", "create", "add", "edit", "update", "post", "submit", "grade")
        )
    }
    endpoints: List[Dict[str, Any]] = []
    for raw_endpoint in architecture.get("endpoints") or []:
        if not isinstance(raw_endpoint, dict):
            continue
        endpoint = copy.deepcopy(raw_endpoint)
        endpoint["path"] = _clean_api_path(endpoint.get("path"))
        method = str(endpoint.get("method") or "GET").upper()
        endpoint["method"] = method
        roles = []
        for value in endpoint.get("role_access") or []:
            role = _canonical_role(value)
            if role and role not in roles:
                roles.append(role)
        endpoint_text = str(endpoint.get("desc") or "").lower()
        for role in normalized_roles:
            if role != "Admin" and re.search(rf"\b{re.escape(role.lower())}\b", endpoint_text) and roles == ["Admin"]:
                roles = [role]
                fixes.append(f"Recovered {role} access for {method} {endpoint['path']}")
                break
        if not roles:
            roles = ["Admin"] if "/admin/" in endpoint["path"] else [next((r for r in normalized_roles if r != "Admin"), "User")]
        if any(role != "Admin" for role in roles) and endpoint["path"].startswith("/admin/"):
            endpoint["path"] = endpoint["path"][len("/admin") :] or "/"

        path_parts = {part for part in endpoint["path"].lower().split("/") if part}
        explicit_non_admin = any(role != "Admin" for role in roles)
        admin_write = method in {"POST", "PUT", "PATCH", "DELETE"} and bool(
            path_parts & admin_entities
        ) and not bool(
            path_parts & non_admin_write_entities
        )
        description = str(endpoint.get("desc") or "").lower()
        explicitly_admin = any(
            token in description for token in ("admin only", "administrator only")
        )
        if (admin_write and not explicit_non_admin) or explicitly_admin or ("/admin/" in endpoint["path"] and roles == ["Admin"]):
            if roles != ["Admin"]:
                fixes.append(
                    f"Restricted {method} {endpoint['path']} to Admin"
                )
            roles = ["Admin"]
        endpoint["role_access"] = roles
        endpoints.append(endpoint)

    architecture["endpoints"] = endpoints
    normalized["architecture"] = architecture
    return normalized, fixes
