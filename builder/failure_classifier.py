"""Classify generated-app failures for targeted pipeline recovery."""

from __future__ import annotations

import re
from typing import Any, Dict, List


RESERVED_FIELD_NAMES = {"date", "time", "datetime", "id", "type", "list", "dict", "json"}
OWNER_FIELD_NAMES = {"user_id", "owner_id", "created_by", "customer_id", "uploader_id"}


def _entity_names(project_data: Dict[str, Any]) -> set[str]:
    data_model = project_data.get("data_model") or {}
    return {
        str(entity.get("name", "")).strip()
        for entity in data_model.get("entities", []) or []
        if str(entity.get("name", "")).strip()
    }


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _words(value: str) -> List[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    return re.findall(r"[a-z0-9]+", spaced.lower())


def _plural(value: str) -> str:
    if not value:
        return value
    if value.endswith("y") and len(value) > 1 and value[-2] not in "aeiou":
        return value[:-1] + "ies"
    if value.endswith(("s", "x", "ch", "sh")):
        return value + "es"
    return value + "s"


def _entity_aliases(entity: str) -> set[str]:
    words = _words(entity)
    compact = _compact(entity)
    aliases = {compact}
    if words:
        phrase = " ".join(words)
        slug = "-".join(words)
        aliases.update({phrase, slug, _plural(compact), _plural(slug)})
        last = words[-1]
        aliases.update({last, _plural(last)})
    return {alias for alias in aliases if alias}


def _blob_mentions_entity(blob: str, entity: str) -> bool:
    lower_blob = str(blob or "").lower()
    compact_blob = _compact(blob)
    for alias in _entity_aliases(entity):
        if " " in alias or "-" in alias:
            if alias in lower_blob:
                return True
            if _compact(alias) in compact_blob:
                return True
        elif alias in compact_blob:
            return True
    return False


def _declared_role_names(project_data: Dict[str, Any]) -> set[str]:
    """Roles declared by this app, plus a small generic safety net."""
    roles: set[str] = set()
    arch = project_data.get("architecture") or {}
    for role in arch.get("roles") or []:
        name = str(role).strip().lower()
        if name:
            roles.add(name)
    cleaned = (project_data.get("cleaned_spec") or {}).get("cleaned_prompt") or {}
    for role_line in cleaned.get("Roles") or []:
        name = str(role_line).partition(":")[0].strip().lower()
        if name:
            roles.add(name)
    roles.update(
        {
            "technician",
            "tenant",
            "patient",
            "doctor",
            "customer",
            "staff",
            "student",
            "teacher",
            "admin",
            "manager",
            "user",
        }
    )
    return roles


def _seg_variants(segment: str) -> set[str]:
    """Compact singular/plural variants of a path segment for robust matching."""
    c = _compact(segment)
    variants = {c}
    if c.endswith("ies"):
        variants.add(c[:-3] + "y")
    if c.endswith("es"):
        variants.add(c[:-2])
    if c.endswith("s"):
        variants.add(c[:-1])
    variants.add(c + "s")
    return {v for v in variants if v}


def _resource_segment(path: str) -> str:
    parts = [part for part in str(path or "").strip("/").split("/") if part and not part.startswith("{")]
    while parts and (parts[0] == "api" or re.fullmatch(r"v\d+", parts[0])):
        parts.pop(0)
    return parts[0] if parts else ""


def _field_names(project_data: Dict[str, Any]) -> set[str]:
    data_model = project_data.get("data_model") or {}
    fields: set[str] = set()
    for entity in data_model.get("entities", []) or []:
        for field in entity.get("fields", []) or []:
            name = str(field.get("name", "")).strip().lower()
            if name:
                fields.add(name)
    return fields


def _entities(project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    data_model = project_data.get("data_model") or {}
    return list(data_model.get("entities") or [])


def _entity_class_name(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", str(name or "")))


def _resource_name(entity_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", str(entity_name)).strip("_").lower() + "s"


def _reserved_field_collisions(project_data: Dict[str, Any]) -> List[Dict[str, str]]:
    collisions: List[Dict[str, str]] = []
    for entity in _entities(project_data):
        entity_name = str(entity.get("name", "")).strip()
        if not entity_name:
            continue
        for field in entity.get("fields") or []:
            field_name = str(field.get("name", "")).strip()
            field_key = field_name.lower()
            if field_key not in RESERVED_FIELD_NAMES:
                continue
            if field_key == "id" and field.get("pk"):
                continue
            collisions.append({"entity": entity_name, "field": field_name})
    return collisions


def _looks_like_reserved_field_failure(output: str) -> bool:
    lower = output.lower()
    if not any(marker in lower for marker in ("pydantic", "sqlalchemy", "field name", "column", "attribute", "typeerror")):
        return False
    if not any(re.search(rf"['\"`]?\b{re.escape(name)}\b['\"`]?", lower) for name in RESERVED_FIELD_NAMES):
        return False
    return any(
        marker in lower
        for marker in (
            "shadow",
            "reserved",
            "builtin",
            "built-in",
            "not a valid",
            "non-annotated",
            "no validator found",
            "is not defined",
            "expected annotation",
            "field",
            "column",
        )
    )


def _ownerless_scope_entities(project_data: Dict[str, Any]) -> List[str]:
    likely: List[str] = []
    text = " ".join(
        [
            str(project_data.get("plain_text", "")),
            str((project_data.get("cleaned_spec") or {}).get("cleaned_prompt", "")),
            str(project_data.get("requirements", "")),
            str(project_data.get("user_stories", "")),
        ]
    ).lower()
    wants_ownership = any(
        marker in text
        for marker in (
            "own ",
            "their ",
            "my ",
            "customer order",
            "customer can",
            "user-scoped",
            "per-user",
            "ownership",
        )
    )
    for entity in _entities(project_data):
        name = str(entity.get("name", "")).strip()
        if name.lower() == "user":
            continue
        field_names = {str(field.get("name", "")).lower() for field in entity.get("fields") or []}
        if field_names & OWNER_FIELD_NAMES:
            continue
        lower_name = name.lower()
        if wants_ownership or any(hint in lower_name for hint in ("order", "booking", "reservation", "ticket", "cart", "delivery")):
            likely.append(name)
    return likely


def _looks_like_scope_failure(output: str) -> bool:
    lower = output.lower()
    return any(
        marker in lower
        for marker in (
            "test_database_customer_lists_are_ownership_scoped",
            "ownership scoped",
            "ownership-scoped",
            "owner_field",
            "scope field",
            "user-scoped",
            "customer can see another",
            "another user's",
            "own records",
            "not scoped",
        )
    )


def _missing_fk_targets(project_data: Dict[str, Any], output: str) -> List[str]:
    entities = {_entity_class_name(name).lower() for name in _entity_names(project_data)}
    resources = {_resource_name(name).lower(): _entity_class_name(name) for name in _entity_names(project_data)}
    missing: set[str] = set()
    data_model = project_data.get("data_model") or {}
    for rel in data_model.get("relationships") or []:
        target = str(rel.get("to") or "").strip()
        if target and _entity_class_name(target).lower() not in entities:
            missing.add(_entity_class_name(target) or target)

    for match in re.finditer(r"(?:parent resource|resource|table|entity)\s+['\"`]?([A-Za-z][A-Za-z0-9_-]+)['\"`]?", output, re.IGNORECASE):
        token = match.group(1)
        compact = _compact(token)
        if compact and compact not in {_compact(resource) for resource in resources} and compact not in entities:
            missing.add(_entity_class_name(token) or token)
    return sorted(missing)


def _looks_like_missing_fk_failure(output: str) -> bool:
    lower = output.lower()
    return any(
        marker in lower
        for marker in (
            "could not load parent resource",
            "noreferencedtableerror",
            "foreign key",
            "referenced table",
            "referenced by tests",
            "missing parent",
            "no such table",
        )
    )


def classify_failure(
    project_data: Dict[str, Any],
    last_test_output: str,
    total_cycles: int,
) -> Dict[str, Any]:
    """
    Decide whether a failed generated app looks like a code bug or an upstream
    architecture/data-model problem.
    """
    architecture = project_data.get("architecture") or {}
    endpoints = architecture.get("endpoints") or []
    entities = _entity_names(project_data)
    roles = _declared_role_names(project_data)
    fields = _field_names(project_data)
    output = last_test_output or ""
    evidence: List[str] = []

    reserved_collisions = _reserved_field_collisions(project_data)
    if reserved_collisions and _looks_like_reserved_field_failure(output):
        names = [f"{item['entity']}.{item['field']}" for item in reserved_collisions]
        return {
            "category": "DATA_MODEL_GAP",
            "confidence": 0.9,
            "reason": (
                "A generated model/schema field collides with a Python/Pydantic/SQLAlchemy "
                "reserved type or builtin; rename or alias reserved field."
            ),
            "fix_hint": "rename or alias reserved field",
            "suggested_stage_to_regenerate": "DATA_MODEL",
            "evidence": names[:5],
            "deterministic_fixes": [
                {
                    "kind": "reserved_field_alias",
                    "fields": reserved_collisions,
                }
            ],
        }

    if _looks_like_scope_failure(output):
        ownerless = _ownerless_scope_entities(project_data)
        return {
            "category": "DATA_MODEL_GAP",
            "confidence": 0.86,
            "reason": (
                "Ownership/scoping validation failed and the data model lacks an owner/user/customer "
                "scope field for one or more user-owned entities."
            ),
            "fix_hint": "add owner/user/customer scope field",
            "suggested_stage_to_regenerate": "DATA_MODEL",
            "evidence": ownerless[:5] or ["ownership scope failure"],
            "deterministic_fixes": [
                {
                    "kind": "missing_scope_field",
                    "entities": ownerless,
                }
            ],
        }

    missing_fk_targets = _missing_fk_targets(project_data, output)
    if missing_fk_targets and _looks_like_missing_fk_failure(output):
        return {
            "category": "DATA_MODEL_GAP",
            "confidence": 0.84,
            "reason": (
                "A test or relationship references an FK target entity that is absent from the data model."
            ),
            "fix_hint": "add missing FK target entity or repoint the FK to User when it is a role",
            "suggested_stage_to_regenerate": "DATA_MODEL",
            "evidence": missing_fk_targets[:5],
            "deterministic_fixes": [
                {
                    "kind": "missing_fk_target",
                    "targets": missing_fk_targets,
                }
            ],
        }

    missing_model_lines: List[str] = []
    for line in output.splitlines():
        lower = line.lower()
        if any(
            marker in lower
            for marker in (
                "no such table",
                "no such column",
                "could not assemble any primary key",
                "has no property",
                "attributeerror",
                "keyerror",
                "does not exist",
                "foreign key",
            )
        ):
            cleaned = line.strip()
            if cleaned:
                evidence.append(cleaned[:220])
                missing_model_lines.append(cleaned)

    if any("primary key" in line.lower() for line in missing_model_lines):
        return {
            "category": "DATA_MODEL_GAP",
            "confidence": 0.9,
            "reason": "The generated app failed because one or more data-model entities do not have a usable primary key.",
            "suggested_stage_to_regenerate": "DATA_MODEL",
            "evidence": evidence[:5],
        }

    if any(
        ("no such table" in line.lower()) or ("no such column" in line.lower())
        for line in missing_model_lines
    ):
        return {
            "category": "DATA_MODEL_GAP",
            "confidence": 0.82,
            "reason": (
                "The runtime database schema is missing a table or column required by "
                "the generated data model."
            ),
            "suggested_stage_to_regenerate": "DATA_MODEL",
            "evidence": evidence[:5],
        }

    if len(missing_model_lines) >= 2:
        return {
            "category": "DATA_MODEL_GAP",
            "confidence": 0.75,
            "reason": (
                f"{len(missing_model_lines)} failure lines reference missing tables, columns, "
                "attributes, or relationships. The data model likely does not support what "
                "the generated code or architecture expects."
            ),
            "suggested_stage_to_regenerate": "DATA_MODEL",
            "evidence": evidence[:5],
        }

    orphan_endpoints = []
    for endpoint in endpoints:
        path = str(endpoint.get("path", "")).lower()
        desc = str(endpoint.get("desc", endpoint.get("purpose", ""))).lower()
        blob = f"{path} {desc}"
        if path in {"", "/", "/health", "/api/health"}:
            continue
        if path.startswith(("/api/auth", "/auth")):
            continue
        # If this endpoint is already backed by a real entity, it is fine.
        if any(entity and _blob_mentions_entity(blob, entity) for entity in entities):
            continue
        # An endpoint whose resource is a declared role is served by User + role,
        # not a missing entity. Do not treat it as an orphan.
        seg_variants = _seg_variants(_resource_segment(path))
        compact_roles = {_compact(role) for role in roles}
        compact_role_plurals = {_compact(_plural(role)) for role in roles}
        if seg_variants & compact_roles or seg_variants & compact_role_plurals:
            continue
        orphan_endpoints.append(endpoint)

    # Convergence guard: if ARCHITECTURE was already regenerated once for this
    # project, do not request it again. The mismatch is structural and another
    # LLM pass often reproduces it.
    options = project_data.get("generation_options") or {}
    recovery_chain = [str(s).upper() for s in (options.get("_auto_recovery_chain") or [])]
    architecture_already_retried = "ARCHITECTURE" in recovery_chain

    if (
        len(orphan_endpoints) >= 3
        and total_cycles >= 2
        and not architecture_already_retried
    ):
        return {
            "category": "ARCHITECTURE_MISMATCH",
            "confidence": 0.65,
            "reason": (
                f"{len(orphan_endpoints)} architecture endpoints do not map to any "
                "entity or known role in the data model. Regenerating architecture "
                "should bring routes and supported data back into alignment."
            ),
            "suggested_stage_to_regenerate": "ARCHITECTURE",
            "evidence": [
                f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"
                for endpoint in orphan_endpoints[:5]
            ],
        }

    requested_entities = set()
    text = " ".join(
        [
            str(project_data.get("plain_text", "")),
            str((project_data.get("cleaned_spec") or {}).get("cleaned_prompt", "")),
        ]
    )
    match = re.search(r"entities\s*:\s*([^\n]+)", text, flags=re.IGNORECASE)
    if match:
        requested_entities = {
            re.sub(r"[^a-z0-9]+", "", item.strip().lower())
            for item in match.group(1).split(",")
            if item.strip()
        }
    normalized_entities = {_compact(entity) for entity in entities}
    missing_requested = sorted(requested_entities - normalized_entities)
    if missing_requested:
        return {
            "category": "DATA_MODEL_GAP",
            "confidence": 0.8,
            "reason": (
                "The prompt requested entities that are missing from the data model: "
                + ", ".join(missing_requested)
            ),
            "suggested_stage_to_regenerate": "DATA_MODEL",
            "evidence": missing_requested[:5],
        }

    if fields and "id" not in fields:
        return {
            "category": "DATA_MODEL_GAP",
            "confidence": 0.7,
            "reason": "The data model does not expose standard id fields for generated CRUD.",
            "suggested_stage_to_regenerate": "DATA_MODEL",
            "evidence": ["Missing id fields"],
        }

    return {
        "category": "CODE_BUG",
        "confidence": 0.5,
        "reason": "No clear architecture/data-model mismatch was detected. This looks like a code-level failure.",
        "suggested_stage_to_regenerate": None,
        "evidence": evidence[:3],
    }
