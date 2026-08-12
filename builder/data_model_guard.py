"""
Normalize LLM-produced data models before codegen.

Fixes common e-commerce mistakes: duplicate Customer/Admin tables beside User,
missing product stock, and Order FKs pointing at profile tables instead of User.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Set, Tuple

from generated_apps.generator.engine_rules import entity_is_owned


SHADOW_PROFILE_NAMES = frozenset({"customer", "admin", "staff", "employee"})
CATALOG_HINTS = ("product", "catalog", "item", "menu", "book", "course")
ORDER_HINTS = ("order", "purchase", "cart")
OWNER_FIELD_NAMES = ("user_id", "owner_id", "created_by", "customer_id", "uploader_id")
SHARED_CATALOG_NAMES = frozenset({"room", "book", "event"})
RESERVED_FIELD_NAMES = frozenset({"date", "time", "datetime", "id", "type", "list", "dict", "json"})


def _has_user_entity(entities: List[Dict[str, Any]]) -> bool:
    return any(str(e.get("name", "")).lower() == "user" for e in entities)


def _is_ecommerce_spec(project_data: Dict[str, Any]) -> bool:
    text = " ".join(
        [
            str((project_data.get("cleaned_spec") or {}).get("project_title", "")),
            str(project_data.get("plain_text", "")),
            str((project_data.get("cleaned_spec") or {}).get("cleaned_prompt", "")),
        ]
    ).lower()
    if any(w in text for w in ("e-commerce", "ecommerce", "online store", "web shop", "webstore")):
        return True
    feats = (project_data.get("cleaned_spec") or {}).get("cleaned_prompt", {}) or {}
    if isinstance(feats, dict):
        blob = str(feats.get("Features", "")) + str(feats.get("Goal", ""))
        if any(w in blob.lower() for w in ("cart", "checkout", "purchase", "browse product", "store")):
            return True
    dm = project_data.get("data_model") or {}
    names = {str(e.get("name", "")).lower() for e in dm.get("entities") or []}
    return "product" in names and ("order" in names or any("order" in n for n in names))


def entity_ui_kind(entity_name: str, data_model: Dict[str, Any] | None = None) -> str:
    """catalog | order | profile_shadow | standard"""
    name = str(entity_name or "").lower()
    token = _norm_token(entity_name)
    entities = (data_model or {}).get("entities") or []
    if name in SHADOW_PROFILE_NAMES and _has_user_entity(entities):
        return "profile_shadow"
    if token in {"reservation", "booking", "loan", "ticket", "submission", "task"}:
        return "standard"
    if _has_catalog_hint(entity_name):
        return "catalog"
    if any(h in name for h in ORDER_HINTS):
        return "order"
    return "standard"


def should_expose_entity_in_ui(entity_name: str, data_model: Dict[str, Any] | None = None) -> bool:
    """Expose every generated business entity except the canonical auth User.

    Runtime tests, CRUD generation, dashboard stats, and APP_CONFIG are all
    derived from non-User entities. Hiding profile-shadow entities here leaves
    valid CRUD routes without matching UI routes or dashboard counts.
    """
    if str(entity_name or "").lower() == "user":
        return False
    return True


def _norm_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _singular_token(text: str) -> str:
    token = _norm_token(text)
    if token.endswith("ies"):
        return token[:-3] + "y"
    if token.endswith("es"):
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _has_catalog_hint(entity_name: str) -> bool:
    name = str(entity_name or "").lower()
    token = _singular_token(entity_name)
    if token in CATALOG_HINTS:
        return True
    return any(
        hint in name
        for hint in CATALOG_HINTS
        if hint not in {"book", "item", "menu", "course"}
    )


def _entity_path_tokens(entity_names: Set[str]) -> Set[str]:
    """Compact tokens a real entity could appear as in a path."""
    tokens: Set[str] = set()
    for name in entity_names:
        compact = _norm_token(name)
        if compact:
            tokens.add(compact)
            tokens.add(compact + "s")
    return tokens


def _seg_token_variants(segment: str) -> Set[str]:
    c = _norm_token(segment)
    variants = {c}
    if c.endswith("ies"):
        variants.add(c[:-3] + "y")
    if c.endswith("es"):
        variants.add(c[:-2])
    if c.endswith("s"):
        variants.add(c[:-1])
    variants.add(c + "s")
    return {v for v in variants if v}


def _class_name(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", str(name or "")))


def _field_names_for_entity(entity: Dict[str, Any]) -> Set[str]:
    return {str(field.get("name", "")).lower() for field in entity.get("fields") or []}


def _safe_reserved_alias(entity_name: str, field_name: str, existing: Set[str]) -> str:
    entity_token = re.sub(r"[^a-z0-9]+", "_", str(entity_name or "record").lower()).strip("_") or "record"
    field_token = re.sub(r"[^a-z0-9]+", "_", str(field_name or "field").lower()).strip("_") or "field"
    if field_token == "id":
        candidate = f"{entity_token}_external_id"
    else:
        candidate = f"{entity_token}_{field_token}"
    base = candidate
    suffix = 2
    while candidate.lower() in existing:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _rename_field(entity: Dict[str, Any], old_name: str, new_name: str) -> bool:
    changed = False
    for field in entity.get("fields") or []:
        if str(field.get("name", "")).lower() == old_name.lower():
            field["source_name"] = field.get("source_name") or field.get("name")
            field["name"] = new_name
            changed = True
    return changed


def _ensure_user_scope_field(entity: Dict[str, Any]) -> bool:
    fields = entity.setdefault("fields", [])
    names = _field_names_for_entity(entity)
    if names & set(OWNER_FIELD_NAMES):
        return False
    fields.append({"name": "user_id", "type": "uuid", "required": False, "nullable": True})
    return True


def _access_context(project_data: Dict[str, Any]) -> Dict[str, Any]:
    arch = project_data.get("architecture", {}) or {}
    return {
        **arch,
        "plain_text": project_data.get("plain_text", ""),
        "cleaned_spec": project_data.get("cleaned_spec", {}) or {},
        "requirements": project_data.get("requirements", {}) or {},
        "user_stories": project_data.get("user_stories", {}) or {},
        "data_model": project_data.get("data_model", {}) or {},
    }


def _should_inject_user_scope(entity: Dict[str, Any], project_data: Dict[str, Any]) -> bool:
    name = str(entity.get("name", ""))
    token = _norm_token(name)
    if not name or name.lower() == "user" or token in SHARED_CATALOG_NAMES:
        return False
    return entity_is_owned(entity, _access_context(project_data))


def _ensure_relationship(relationships: List[Dict[str, Any]], from_entity: str, to_entity: str, fk_field: str) -> bool:
    for rel in relationships:
        if (
            str(rel.get("from", "")).lower() == str(from_entity).lower()
            and str(rel.get("to", "")).lower() == str(to_entity).lower()
            and str(rel.get("fk_field", "")).lower() == str(fk_field).lower()
        ):
            return False
    relationships.append({"from": from_entity, "to": to_entity, "type": "many-to-one", "fk_field": fk_field})
    return True


def _reconcile_architecture_endpoints(
    pd: Dict[str, Any], role_names: Set[str], entity_names: Set[str]
) -> List[str]:
    """Safely repoint stale per-role endpoints to /users.

    Repoints only when the resource segment is not backed by an entity and
    matches a declared role. Unknown segments are left untouched and reported.
    """
    actions: List[str] = []
    arch = pd.get("architecture")
    if not isinstance(arch, dict):
        return actions
    endpoints = arch.get("endpoints")
    if not isinstance(endpoints, list):
        return actions

    system_segments = {"auth", "health", "dashboard", "users", "me", "login", "register", "stats"}
    entity_tokens = _entity_path_tokens(entity_names)
    role_tokens: Set[str] = set()
    for role in role_names:
        c = _norm_token(role)
        if not c:
            continue
        role_tokens.add(c)
        role_tokens.add(c + "s")
        if c.endswith("y"):
            role_tokens.add(c[:-1] + "ies")

    for ep in endpoints:
        path = str(ep.get("path", ""))
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        while parts and (parts[0].lower() == "api" or re.fullmatch(r"v\d+", parts[0].lower())):
            parts.pop(0)
        if not parts:
            continue
        seg = parts[0]
        variants = _seg_token_variants(seg)
        if _norm_token(seg) in system_segments:
            continue
        if variants & entity_tokens:
            continue
        if not (variants & role_tokens):
            actions.append(f"endpoint {path} not entity-backed and not a known role; left unchanged (review)")
            continue
        new_path = re.sub(
            r"(/api(?:/v\d+)?/)[^/{]+",
            lambda m: m.group(1) + "users",
            path,
            count=1,
        )
        if new_path == path and path.startswith("/"):
            new_path = re.sub(r"^/[^/{]+", "/users", path, count=1)
        if new_path != path:
            ep["path"] = new_path
            actions.append(f"endpoint {path} repointed to {new_path} (role served by User)")
    return actions


def recover_data_model_from_failure(
    project_data: Dict[str, Any],
    diagnosis: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Apply deterministic DATA_MODEL fixes requested by failure classification."""
    actions: List[str] = []
    pd = copy.deepcopy(project_data)
    diagnosis = diagnosis or {}
    dm = pd.get("data_model")
    if not isinstance(dm, dict):
        return pd, actions

    entities: List[Dict[str, Any]] = list(dm.get("entities") or [])
    relationships: List[Dict[str, Any]] = list(dm.get("relationships") or [])
    if not entities:
        return pd, actions

    fixes = diagnosis.get("deterministic_fixes") or []
    fix_kinds = {str(fix.get("kind") or "") for fix in fixes if isinstance(fix, dict)}
    entity_by_class = {_class_name(entity.get("name")): entity for entity in entities}
    entity_names = {str(entity.get("name", "")) for entity in entities}
    entity_names_lower = {name.lower() for name in entity_names}
    has_user = any(name.lower() == "user" for name in entity_names)

    if "reserved_field_alias" in fix_kinds:
        requested = {
            (str(item.get("entity") or ""), str(item.get("field") or "").lower())
            for fix in fixes
            if fix.get("kind") == "reserved_field_alias"
            for item in (fix.get("fields") or [])
            if isinstance(item, dict)
        }
        for entity in entities:
            entity_name = str(entity.get("name", "Record"))
            existing = _field_names_for_entity(entity)
            for field in entity.get("fields") or []:
                old_name = str(field.get("name", ""))
                old_key = old_name.lower()
                if old_key not in RESERVED_FIELD_NAMES:
                    continue
                if old_key == "id" and field.get("pk"):
                    continue
                if requested and (entity_name, old_key) not in requested and (_class_name(entity_name), old_key) not in requested:
                    continue
                new_name = _safe_reserved_alias(entity_name, old_name, existing)
                if _rename_field(entity, old_name, new_name):
                    existing.discard(old_key)
                    existing.add(new_name.lower())
                    for rel in relationships:
                        if str(rel.get("from", "")).lower() == entity_name.lower() and str(rel.get("fk_field", "")).lower() == old_key:
                            rel["fk_field"] = new_name
                    actions.append(f"{entity_name}: renamed reserved field {old_name} to {new_name}")

    if "missing_scope_field" in fix_kinds and has_user:
        requested_entities = {
            str(name)
            for fix in fixes
            if fix.get("kind") == "missing_scope_field"
            for name in (fix.get("entities") or [])
        }
        for entity in entities:
            entity_name = str(entity.get("name", ""))
            if entity_name.lower() == "user":
                continue
            should_fix = (
                not requested_entities
                or entity_name in requested_entities
                or _class_name(entity_name) in requested_entities
                or any(hint in entity_name.lower() for hint in ORDER_HINTS)
            )
            if should_fix and _ensure_user_scope_field(entity):
                _ensure_relationship(relationships, entity_name, "User", "user_id")
                actions.append(f"{entity_name}: added user_id ownership scope field")

    if "missing_fk_target" in fix_kinds:
        requested_targets = {
            str(target)
            for fix in fixes
            if fix.get("kind") == "missing_fk_target"
            for target in (fix.get("targets") or [])
            if str(target or "").strip()
        }
        for rel in list(relationships):
            target = str(rel.get("to") or "").strip()
            if not target or target.lower() in entity_names_lower:
                continue
            if requested_targets and target not in requested_targets and _class_name(target) not in requested_targets:
                continue
            if target.lower() in {"customer", "admin", "staff", "employee"} and has_user:
                rel["to"] = "User"
                actions.append(f"{rel.get('from')}: FK target {target} repointed to User")
                continue
            entities.append(
                {
                    "name": _class_name(target) or target,
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True, "nullable": False},
                        {"name": "name", "type": "string", "required": False},
                    ],
                }
            )
            entity_names_lower.add(target.lower())
            actions.append(f"{target}: added minimal entity for missing FK target")

    dm["entities"] = entities
    dm["relationships"] = relationships
    pd["data_model"] = dm
    if actions:
        pd, normalization_actions = normalize_data_model(pd)
        actions.extend(normalization_actions)
    return pd, actions


def normalize_data_model(project_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Return a copy of project_data with a cleaned data_model.
    """
    actions: List[str] = []
    pd = copy.deepcopy(project_data)
    dm = pd.get("data_model")
    if not isinstance(dm, dict):
        return pd, actions

    entities: List[Dict[str, Any]] = list(dm.get("entities") or [])
    relationships: List[Dict[str, Any]] = list(dm.get("relationships") or [])
    if not entities:
        return pd, actions

    is_store = _is_ecommerce_spec(pd)
    has_user = _has_user_entity(entities)
    entity_names = {str(ent.get("name", "")) for ent in entities}
    role_names: Set[str] = set()
    arch = pd.get("architecture") or {}
    for role in arch.get("roles") or []:
        role_names.add(str(role).strip().lower())
    cleaned_prompt = (pd.get("cleaned_spec") or {}).get("cleaned_prompt") or {}
    for role_line in cleaned_prompt.get("Roles") or []:
        role_name = str(role_line).partition(":")[0].strip().lower()
        if role_name:
            role_names.add(role_name)

    # Drop shadow profile entities when User already handles auth/roles
    if has_user and is_store:
        keep: List[Dict[str, Any]] = []
        removed: Set[str] = set()
        for ent in entities:
            n = str(ent.get("name", "")).lower()
            if n in SHADOW_PROFILE_NAMES:
                removed.add(ent.get("name", ""))
                continue
            keep.append(ent)
        if removed:
            entities = keep
            actions.append(f"Removed profile tables (use User.role): {', '.join(sorted(removed))}")
            relationships = [
                r
                for r in relationships
                if r.get("from") not in removed and r.get("to") not in removed
            ]
            # Point Order.customer_id at User instead of Customer
            for ent in entities:
                if not any(h in str(ent.get("name", "")).lower() for h in ORDER_HINTS):
                    continue
                fields = ent.get("fields") or []
                for f in fields:
                    if str(f.get("name", "")).lower() == "customer_id":
                        f["name"] = "user_id"
                        actions.append(f"{ent.get('name')}: customer_id renamed to user_id (FK → User)")
                rels = []
                for r in relationships:
                    if r.get("from") == ent.get("name") and str(r.get("fk_field", "")).lower() == "customer_id":
                        r = {**r, "to": "User", "fk_field": "user_id"}
                    rels.append(r)
                relationships = rels

    # Ensure Product has stock for e-commerce
    for ent in entities:
        fields = ent.setdefault("fields", [])
        id_field = None
        for field in fields:
            if str(field.get("name", "")).lower() == "id":
                id_field = field
                break
        if id_field is None:
            fields.insert(0, {"name": "id", "type": "uuid", "pk": True, "nullable": False})
            actions.append(f"{ent.get('name')}: added id primary key")
        else:
            if not id_field.get("pk"):
                id_field["pk"] = True
                actions.append(f"{ent.get('name')}: marked id as primary key")
            id_field["nullable"] = False
            if str(id_field.get("type", "")).lower() in {"", "int", "integer"}:
                id_field["type"] = "uuid"

    # Ensure personal/owned records can be created by their acting role and
    # scoped to the signed-in user at runtime.
    if has_user:
        for ent in entities:
            entity_name = str(ent.get("name", ""))
            if _should_inject_user_scope(ent, pd) and _ensure_user_scope_field(ent):
                _ensure_relationship(relationships, entity_name, "User", "user_id")
                actions.append(f"{entity_name}: added user_id ownership scope field")

    # Ensure Product has stock for e-commerce
    for ent in entities:
        if not _has_catalog_hint(str(ent.get("name", ""))):
            continue
        field_names = {str(f.get("name", "")).lower() for f in ent.get("fields") or []}
        if not any(n in field_names for n in ("stock_quantity", "stock", "quantity", "inventory")):
            ent.setdefault("fields", []).append(
                {"name": "stock_quantity", "type": "integer", "required": False}
            )
            actions.append(f"{ent.get('name')}: added stock_quantity field")

    if has_user:
        normalized_relationships: List[Dict[str, Any]] = []
        for rel in relationships:
            target = str(rel.get("to") or "")
            target_key = target.strip().lower()
            if target and target not in entity_names and target_key in role_names:
                rel = {**rel, "to": "User"}
                actions.append(
                    f"{rel.get('from')}: {rel.get('fk_field')} now targets User because {target} is a login role"
                )
            normalized_relationships.append(rel)
        relationships = normalized_relationships

    dm["entities"] = entities
    dm["relationships"] = relationships
    try:
        final_entity_names = {str(e.get("name", "")) for e in entities}
        actions.extend(_reconcile_architecture_endpoints(pd, role_names, final_entity_names))
    except Exception as exc:  # never let reconciliation break the build
        actions.append(f"endpoint reconciliation skipped: {exc}")
    pd["data_model"] = dm
    return pd, actions
