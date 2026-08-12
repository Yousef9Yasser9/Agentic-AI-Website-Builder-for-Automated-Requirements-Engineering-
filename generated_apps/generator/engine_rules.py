"""
Shared rules for role-based access and entity classification in generated apps.
Used by repo_generator, contract_validator, and runtime test planning.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

ADMIN_ENTITY_HINTS = ("admin", "setting", "config", "permission")
CATALOG_ENTITY_HINTS = ("product", "catalog", "item", "book", "course", "menu", "service", "inventory")
ORDER_ENTITY_HINTS = ("order", "purchase", "cart")
OWNER_FIELD_NAMES = ("user_id", "owner_id", "created_by", "customer_id", "uploader_id")
OWNED_ENTITY_HINTS = ("task", "reservation", "booking", "loan", "order", "ticket", "submission")
SHARED_CATALOG_NAMES = ("room", "book", "event")
SHADOW_PROFILE_NAMES = frozenset({"customer", "admin", "staff", "employee"})

READ_VERBS = (
    "view",
    "browse",
    "see",
    "list",
    "read",
    "track",
    "history",
    "schedule",
    "assigned",
    "own",
    "enrolled",
)
WRITE_VERBS = (
    "manage",
    "create",
    "add",
    "update",
    "edit",
    "delete",
    "remove",
    "post",
    "grade",
    "submit",
    "book",
    "borrow",
    "place",
    "buy",
    "purchase",
    "reserve",
    "scan",
    "mark",
    "cancel",
    "approve",
    "assign",
)

ENTITY_ALIASES = {
    "course": ("course", "courses", "class", "classes", "enrolled course", "enrolled courses"),
    "enrollment": ("enrollment", "enrollments", "enroll", "enrolled", "register for course", "registered course"),
    "assignment": ("assignment", "assignments", "homework", "task", "tasks"),
    "submission": ("submission", "submissions", "submit assignment", "submitted work", "submitted works", "work"),
    "announcement": ("announcement", "announcements", "notice", "notices", "message", "messages"),
    "grade": ("grade", "grades", "grading", "score", "scores", "feedback"),
    "appointment": ("appointment", "appointments", "booking", "bookings", "schedule"),
    "task": ("task", "tasks", "todo", "todos", "to do", "to dos"),
    "reservation": ("reservation", "reservations", "booking", "bookings", "book a room", "room booking"),
    "booking": ("booking", "bookings", "reservation", "reservations", "book a room", "room booking"),
    "loan": ("loan", "loans", "borrow", "borrowing", "borrowed book", "borrowed books", "book loan", "book loans"),
    "order": ("order", "orders", "purchase", "purchases", "place order", "placed order"),
    "ticket": ("ticket", "tickets", "entry pass", "entry passes"),
    "submission": ("submission", "submissions", "submit", "submitted work", "submitted works"),
    "payment": ("payment", "payments", "invoice", "invoices"),
    "invoice": ("invoice", "invoices", "payment", "payments", "bill", "bills"),
    "servicetype": ("service type", "service types", "service", "services"),
    "workshopbay": ("workshop bay", "workshop bays", "bay", "bays"),
    "doctorprofile": ("doctor profile", "doctor profiles", "doctor", "doctors"),
    "specialty": ("specialty", "specialties", "speciality", "specialities"),
}


def _singular_token(value: Any) -> str:
    token = _norm_token(value)
    if token.endswith("ies"):
        return token[:-3] + "y"
    if token.endswith("es"):
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _norm_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
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


def _arch_roles(architecture: Dict[str, Any] | None) -> List[str]:
    roles = []
    for role in (architecture or {}).get("roles") or ["Admin", "User"]:
        clean = str(role or "").strip()
        if clean:
            roles.append(clean)
    if not any(role.lower() == "admin" for role in roles):
        roles.append("Admin")
    return _dedupe(roles)


def _role_label(architecture: Dict[str, Any] | None, role_lower: str) -> str:
    for role in _arch_roles(architecture):
        if role.lower() == role_lower:
            return role
    return role_lower[:1].upper() + role_lower[1:]


def _known_role_key(architecture: Dict[str, Any] | None, value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    for role in _arch_roles(architecture):
        role_key = role.lower()
        if text == role_key:
            return role_key
        if re.search(rf"\b{re.escape(role_key)}\b", text):
            return role_key
    return ""


def _entity_aliases(entity_name: str) -> List[str]:
    raw = str(entity_name or "").strip()
    name = raw.lower()
    token = _norm_token(raw)
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", raw).lower()
    values = {name, spaced, name + "s", spaced + "s", token}
    values.update(ENTITY_ALIASES.get(token, ()))
    values.update(ENTITY_ALIASES.get(name, ()))
    return sorted(v for v in values if v)


def _context_entity_tokens(architecture: Dict[str, Any] | None, current_entity_name: str) -> set[str]:
    tokens: set[str] = set()
    current = _singular_token(current_entity_name)
    dm = (architecture or {}).get("data_model") or {}
    for entity in dm.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        token = _singular_token(entity.get("name"))
        if token and token != current:
            tokens.add(token)
    return tokens


def _entity_aliases_for_context(entity_name: str, architecture: Dict[str, Any] | None = None) -> List[str]:
    other_entity_tokens = _context_entity_tokens(architecture, entity_name)
    if not other_entity_tokens:
        return _entity_aliases(entity_name)
    aliases: List[str] = []
    for alias in _entity_aliases(entity_name):
        alias_token = _singular_token(alias)
        if alias_token in other_entity_tokens:
            continue
        aliases.append(alias)
    return aliases


def _mentions_entity(entity_name: str, text: str) -> bool:
    return _mentions_entity_context(entity_name, text, None)


def _mentions_entity_context(entity_name: str, text: str, architecture: Dict[str, Any] | None = None) -> bool:
    haystack = str(text or "").lower()
    compact = _norm_token(haystack)
    for alias in _entity_aliases_for_context(entity_name, architecture):
        alias_text = alias.lower()
        if " " in alias_text:
            if alias_text in haystack:
                return True
        elif re.search(rf"\b{re.escape(alias_text)}s?\b", haystack):
            return True
        elif alias_text and alias_text in compact:
            return True
    return False


def _has_any(text: str, verbs: Iterable[str]) -> bool:
    haystack = str(text or "").lower()
    return any(re.search(rf"\b{re.escape(verb)}\w*\b", haystack) for verb in verbs)


def _action_verbs_in(text: str, verbs: Iterable[str]) -> List[str]:
    haystack = str(text or "").lower()
    return [
        verb
        for verb in verbs
        if re.search(rf"\b{re.escape(verb)}\w*\b", haystack)
    ]


def _is_shared_catalog_entity(entity_name: str) -> bool:
    token = _singular_token(entity_name)
    name = str(entity_name or "").lower()
    if token in SHARED_CATALOG_NAMES or token in CATALOG_ENTITY_HINTS:
        return True
    return any(
        hint in name
        for hint in CATALOG_ENTITY_HINTS
        if hint not in {"book", "item", "menu", "course"}
    )


def _transaction_verb_targets_catalog(entity_name: str, text: str, verbs: Iterable[str]) -> bool:
    """Prevent "Member borrows books" from granting write access to Book.

    Transaction verbs create personal records such as Loan, Reservation, Ticket,
    or Order; they do not mutate shared catalogs like Book, Room, or Event.
    """
    if not _is_shared_catalog_entity(entity_name):
        return False
    verb_set = {str(verb).lower() for verb in verbs}
    transaction_verbs = {"borrow", "book", "place", "buy", "purchase", "order", "scan", "mark", "reserve"}
    management_verbs = {"manage", "create", "add", "update", "edit", "delete", "remove", "approve", "assign"}
    if verb_set & management_verbs and not (verb_set & (transaction_verbs - {"book"})):
        return False
    if not (verb_set & transaction_verbs):
        return False
    entity_token = _singular_token(entity_name)
    if entity_token in {"book", "room", "event", "product", "item", "menu", "course"}:
        return True
    return bool(re.search(r"\b(borrow|book|place|buy|purchase|order|scan|mark)\w*\b", str(text or "").lower()))


def _verb_targets_entity(
    entity_name: str,
    text: str,
    verbs: Iterable[str],
    architecture: Dict[str, Any] | None = None,
) -> bool:
    haystack = str(text or "").lower()
    aliases = [alias for alias in _entity_aliases_for_context(entity_name, architecture) if alias and _norm_token(alias)]
    boundary_verbs = [v for v in READ_VERBS if v not in {"own", "assigned", "enrolled"}]
    read_boundary = re.compile(r"\b(" + "|".join(re.escape(v) + r"\w*" for v in boundary_verbs) + r")\b")
    for verb in verbs:
        verb_re = rf"\b{re.escape(str(verb).lower())}\w*\b"
        for alias in aliases:
            alias_text = alias.lower()
            if " " in alias_text:
                alias_re = re.escape(alias_text)
            else:
                alias_re = rf"\b{re.escape(alias_text)}s?\b"
            forward = re.search(rf"{verb_re}((?:\s+\w+){{0,6}})\s+{alias_re}", haystack)
            if forward and not read_boundary.search(forward.group(1)):
                return True
            backward = re.search(rf"{alias_re}((?:\s+\w+){{0,4}})\s+{verb_re}", haystack)
            if backward and not read_boundary.search(backward.group(1)):
                return True
    return False


def _flatten_text(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        chunks: List[str] = []
        for item in value.values():
            chunks.extend(_flatten_text(item))
        return chunks
    if isinstance(value, (list, tuple, set)):
        chunks = []
        for item in value:
            chunks.extend(_flatten_text(item))
        return chunks
    return [str(value)]


def _split_text_records(text: str) -> List[str]:
    parts = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|[\r\n;]+", str(text or ""))
        if part and part.strip()
    ]
    return parts or ([str(text)] if str(text or "").strip() else [])


def _text_records(architecture: Dict[str, Any] | None) -> List[Dict[str, str]]:
    arch = architecture or {}
    records: List[Dict[str, str]] = []

    for key in ("plain_text", "prompt", "description", "srs_document"):
        for text in _flatten_text(arch.get(key)):
            records.extend({"text": part, "role": ""} for part in _split_text_records(text))

    cleaned = arch.get("cleaned_spec") or {}
    cleaned_prompt = cleaned.get("cleaned_prompt") or {}
    for key in ("Goal", "Constraints", "Notes"):
        for text in _flatten_text(cleaned_prompt.get(key)):
            records.extend({"text": part, "role": ""} for part in _split_text_records(text))

    for line in cleaned_prompt.get("Roles") or []:
        text = str(line or "")
        role_name, sep, rest = text.partition(":")
        role_key = _known_role_key(arch, role_name) if sep else ""
        records.extend({"text": part, "role": role_key} for part in _split_text_records(rest if sep else text))

    features = cleaned_prompt.get("Features") or {}
    if isinstance(features, dict):
        for label, items in features.items():
            role_key = _known_role_key(arch, label)
            for text in _flatten_text(items):
                records.extend({"text": part, "role": role_key} for part in _split_text_records(text))
    else:
        for text in _flatten_text(features):
            records.extend({"text": part, "role": ""} for part in _split_text_records(text))

    reqs = arch.get("requirements") or {}
    if isinstance(reqs, dict):
        for item in reqs.get("functional_requirements") or []:
            if not isinstance(item, dict):
                continue
            text = " ".join(str(item.get(k) or "") for k in ("shall", "title", "description", "desc"))
            role_key = _known_role_key(arch, item.get("actor") or item.get("role"))
            records.extend({"text": part, "role": role_key} for part in _split_text_records(text))

    stories = arch.get("user_stories") or {}
    if isinstance(stories, dict):
        for item in stories.get("stories") or []:
            if not isinstance(item, dict):
                continue
            text_parts = [str(item.get(k) or "") for k in ("story", "title", "description", "desc")]
            text_parts.extend(str(x) for x in item.get("acceptance_criteria") or [])
            role_key = _known_role_key(arch, item.get("role") or item.get("actor"))
            for text in text_parts:
                records.extend({"text": part, "role": role_key} for part in _split_text_records(text))

    return [record for record in records if record.get("text")]


def _roles_mentioned_in_text(text: str, architecture: Dict[str, Any] | None) -> List[str]:
    haystack = str(text or "").lower()
    matched: List[str] = []
    for role in _arch_roles(architecture):
        key = role.lower()
        variants = {key, key + "s"}
        if key.endswith("y"):
            variants.add(key[:-1] + "ies")
        if any(re.search(rf"\b{re.escape(v)}\b", haystack) for v in variants):
            matched.append(key)
    return _dedupe(matched)


def _prompt_roles(entity_name: str, architecture: Dict[str, Any] | None, write: bool) -> List[str]:
    roles: List[str] = []
    for record in _text_records(architecture):
        text = record["text"]
        if not _mentions_entity_context(entity_name, text, architecture):
            continue
        verbs = _action_verbs_in(text, WRITE_VERBS if write else (*READ_VERBS, *WRITE_VERBS))
        if not verbs:
            continue
        if write and not _verb_targets_entity(entity_name, text, verbs, architecture):
            continue
        if write and _transaction_verb_targets_catalog(entity_name, text, verbs):
            continue
        role_keys = [record.get("role") or ""]
        if not role_keys[0]:
            role_keys = _roles_mentioned_in_text(text, architecture)
        for role_key in role_keys:
            if role_key and role_key != "admin":
                roles.append(_role_label(architecture, role_key))
    return roles


def entity_is_owned(entity: Dict[str, Any], architecture: Dict[str, Any] | None = None) -> bool:
    entity_name = str(entity.get("name") or "")
    token = _singular_token(entity_name)
    if token in SHARED_CATALOG_NAMES:
        return False
    if token in OWNED_ENTITY_HINTS:
        return True
    fields = [str(f.get("name") or "").lower() for f in entity.get("fields") or [] if isinstance(f, dict)]
    if set(fields) & set(OWNER_FIELD_NAMES):
        return not _is_shared_catalog_entity(entity_name)
    for record in _text_records(architecture):
        text = record["text"]
        if not _mentions_entity_context(entity_name, text, architecture):
            continue
        if re.search(r"\b(their own|own|my|mine|personal|submitted|borrowed|placed|booked)\b", text.lower()):
            return not _is_shared_catalog_entity(entity_name)
    return False


def _role_features(architecture: Dict[str, Any] | None) -> Dict[str, List[str]]:
    arch = architecture or {}
    candidates = (
        arch.get("role_features"),
        (arch.get("cleaned_spec") or {}).get("role_features"),
        ((arch.get("cleaned_spec") or {}).get("cleaned_prompt") or {}).get("Features"),
        ((arch.get("cleaned_spec") or {}).get("cleaned_prompt") or {}).get("features"),
    )
    features: Dict[str, List[str]] = {}
    for candidate in candidates:
        if isinstance(candidate, dict):
            for role, items in candidate.items():
                role_key = _known_role_key(arch, role)
                if not role_key:
                    continue
                if isinstance(items, list):
                    features.setdefault(role_key, []).extend(str(item) for item in items)
                elif items:
                    features.setdefault(role_key, []).append(str(items))
    for line in ((arch.get("cleaned_spec") or {}).get("cleaned_prompt") or {}).get("Roles") or []:
        match = re.match(r"\s*([^:]+):\s*(.+)", str(line))
        if match:
            role_key = _known_role_key(arch, match.group(1))
            if not role_key:
                continue
            actions = [
                action.strip()
                for action in re.split(r",|\band\b", match.group(2).strip())
                if action.strip()
            ]
            features.setdefault(role_key, []).extend(actions or [match.group(2).strip()])
    return features


def _page_roles(entity_name: str, architecture: Dict[str, Any] | None, write: bool) -> List[str]:
    roles: List[str] = []
    for page in (architecture or {}).get("pages") or (architecture or {}).get("main_pages") or []:
        if not isinstance(page, dict):
            continue
        target = page.get("target_entity") or page.get("entity")
        text = " ".join(
            str(page.get(key) or "") for key in ("name", "path", "desc", "description", "purpose")
        )
        if target and _norm_token(target) != _norm_token(entity_name):
            if not _mentions_entity_context(entity_name, text, architecture):
                continue
        elif not _mentions_entity_context(entity_name, text, architecture):
            continue
        if write:
            verbs = _action_verbs_in(text, WRITE_VERBS)
            path_is_new = str(page.get("path") or "").lower().endswith("/new")
            if verbs and _transaction_verb_targets_catalog(entity_name, text, verbs):
                continue
            if not path_is_new and not (verbs and _verb_targets_entity(entity_name, text, verbs, architecture)):
                continue
        raw_roles = page.get("role_access") or page.get("roles") or []
        roles.extend(str(role) for role in raw_roles)
    return roles


def _endpoint_roles(entity_name: str, architecture: Dict[str, Any] | None, write: bool) -> List[str]:
    roles: List[str] = []
    for endpoint in (architecture or {}).get("endpoints") or (architecture or {}).get("backend_routes") or []:
        if not isinstance(endpoint, dict):
            continue
        method = str(endpoint.get("method") or "GET").upper()
        is_write = method in {"POST", "PUT", "PATCH", "DELETE"}
        if is_write != write:
            continue
        text = " ".join(
            str(endpoint.get(key) or "") for key in ("path", "name", "desc", "description", "purpose")
        )
        if not _mentions_entity_context(entity_name, text, architecture):
            continue
        roles.extend(str(role) for role in endpoint.get("role_access") or endpoint.get("roles") or [])
    return roles


def _feature_roles(entity_name: str, architecture: Dict[str, Any] | None, write: bool) -> List[str]:
    roles: List[str] = []
    for role, items in _role_features(architecture).items():
        if role in {"admin"}:
            continue
        for item in items:
            text = str(item)
            if not _mentions_entity_context(entity_name, text, architecture):
                continue
            if write:
                if _norm_token(entity_name) == "assignment" and re.search(r"\bsubmit\w*\s+assignments?\b", text.lower()):
                    continue
                if _norm_token(entity_name) == "grade" and re.search(r"\b(view|see|check|read)\w*\s+grades?\b", text.lower()):
                    continue
                verbs = _action_verbs_in(text, WRITE_VERBS)
                if (
                    verbs
                    and _verb_targets_entity(entity_name, text, verbs, architecture)
                    and not _transaction_verb_targets_catalog(entity_name, text, verbs)
                ):
                    roles.append(_role_label(architecture, role))
            elif _has_any(text, READ_VERBS) or _has_any(text, WRITE_VERBS):
                roles.append(_role_label(architecture, role))
    return roles


def _requirement_roles(entity_name: str, architecture: Dict[str, Any] | None, write: bool) -> List[str]:
    roles: List[str] = []
    arch = architecture or {}
    items: List[Dict[str, Any]] = []
    reqs = arch.get("requirements") or {}
    if isinstance(reqs, dict):
        items.extend(reqs.get("functional_requirements") or [])
    stories = arch.get("user_stories") or {}
    if isinstance(stories, dict):
        items.extend(stories.get("stories") or [])
    for item in items:
        if not isinstance(item, dict):
            continue
        role_key = _known_role_key(arch, item.get("actor") or item.get("role"))
        if not role_key or role_key == "admin":
            continue
        text = " ".join(
            str(item.get(key) or "")
            for key in ("shall", "story", "title", "description", "desc")
        )
        if not _mentions_entity_context(entity_name, text, arch):
            continue
        if write:
            verbs = _action_verbs_in(text, WRITE_VERBS)
            if (
                verbs
                and _verb_targets_entity(entity_name, text, verbs, arch)
                and not _transaction_verb_targets_catalog(entity_name, text, verbs)
            ):
                roles.append(_role_label(arch, role_key))
        elif _has_any(text, READ_VERBS) or _has_any(text, WRITE_VERBS):
            roles.append(_role_label(arch, role_key))
    return roles


def _field_roles(entity: Dict[str, Any], architecture: Dict[str, Any] | None) -> Dict[str, List[str]]:
    entity_role_key = _norm_token(entity.get("name", ""))
    fields = [str(f.get("name") or "").lower() for f in entity.get("fields") or [] if isinstance(f, dict)]
    result: Dict[str, List[str]] = {}
    for role in _arch_roles(architecture):
        role_lower = role.lower()
        if role_lower in {"admin"}:
            continue
        matches = []
        for field in fields:
            if field in {role_lower, f"{role_lower}_id", f"{role_lower}_user_id"}:
                matches.append(field)
            elif field == "user_id" and entity_role_key == _norm_token(role_lower):
                matches.append(field)
        if matches:
            result[role] = _dedupe(matches)
    return result


def infer_entity_access(entity: Dict[str, Any], architecture: Dict[str, Any] | None = None) -> Dict[str, Any]:
    entity_name = str(entity.get("name") or "")
    base = classify_entity(entity_name, architecture)
    roles = _arch_roles(architecture)
    admin_label = next((role for role in roles if role.lower() == "admin"), "Admin")

    read_roles = [admin_label]
    read_roles.extend(_role_label(architecture, role) for role in base.get("nav_roles", []) if role != "admin")
    read_roles.extend(_page_roles(entity_name, architecture, write=False))
    read_roles.extend(_feature_roles(entity_name, architecture, write=False))
    read_roles.extend(_requirement_roles(entity_name, architecture, write=False))
    read_roles.extend(_prompt_roles(entity_name, architecture, write=False))

    write_roles = [admin_label]
    write_roles.extend(_page_roles(entity_name, architecture, write=True))
    write_roles.extend(_feature_roles(entity_name, architecture, write=True))
    write_roles.extend(_requirement_roles(entity_name, architecture, write=True))
    write_roles.extend(_prompt_roles(entity_name, architecture, write=True))

    role_scope_fields = _field_roles(entity, architecture)
    for role in role_scope_fields:
        read_roles.append(role)
        write_roles.append(role)
    valid = {role.lower(): role for role in roles}
    def keep_known(values: Iterable[str]) -> List[str]:
        kept = []
        for value in values:
            role = valid.get(str(value or "").lower())
            if role:
                kept.append(role)
        return _dedupe(kept)

    read_roles = keep_known(read_roles)
    write_roles = keep_known(write_roles)
    for role in write_roles:
        if role.lower() != "admin":
            read_roles.append(role)
    read_roles = keep_known(read_roles)
    if not read_roles:
        read_roles = [admin_label]
    if not write_roles:
        write_roles = [admin_label]

    if entity_is_owned(entity, architecture):
        fields = [str(f.get("name") or "").lower() for f in entity.get("fields") or [] if isinstance(f, dict)]
        scope_field = next((field for field in OWNER_FIELD_NAMES if field in fields), "")
        if scope_field:
            for role in read_roles:
                if role.lower() != "admin":
                    role_scope_fields.setdefault(role, [])
                    if scope_field not in role_scope_fields[role]:
                        role_scope_fields[role].append(scope_field)

    return {
        **base,
        "read_roles": read_roles,
        "write_roles": write_roles,
        "role_scope_fields": role_scope_fields,
    }


def classify_entity(entity_name: str, architecture: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Return role visibility rules for an entity.

    nav_roles / dashboard_roles use normalized lowercase roles from architecture.
    """
    name = str(entity_name or "").lower()
    arch_roles = [str(r).lower() for r in _arch_roles(architecture)]
    has_admin = "admin" in arch_roles
    non_admin_roles = [r for r in arch_roles if r != "admin"]
    primary_user_role = (
        "patient" if "patient" in non_admin_roles
        else "guest" if "guest" in non_admin_roles
        else "tenant" if "tenant" in non_admin_roles
        else "student" if "student" in non_admin_roles
        else "employee" if "employee" in non_admin_roles
        else "member" if "member" in non_admin_roles
        else "customer" if "customer" in non_admin_roles
        else non_admin_roles[0] if non_admin_roles
        else ""
    )
    explicit_roles = []
    for role in (
        _page_roles(entity_name, architecture, write=False)
        + _feature_roles(entity_name, architecture, write=False)
        + _requirement_roles(entity_name, architecture, write=False)
        + _page_roles(entity_name, architecture, write=True)
        + _feature_roles(entity_name, architecture, write=True)
        + _requirement_roles(entity_name, architecture, write=True)
    ):
        role_key = _known_role_key(architecture, role)
        if role_key and role_key != "admin":
            explicit_roles.append(role_key)

    def with_explicit(base_roles: List[str]) -> List[str]:
        known = set(arch_roles)
        return _dedupe([role for role in [*base_roles, *explicit_roles] if role in known])

    if name == "user" or (name.endswith("user") and name not in ("customer",)):
        return {
            "nav_roles": with_explicit(["admin"]),
            "dashboard_roles": with_explicit(["admin"]),
            "manage_label": "Manage Users",
            "browse_label": "Users",
        }

    if name in SHADOW_PROFILE_NAMES:
        return {
            "nav_roles": with_explicit(["admin"]),
            "dashboard_roles": with_explicit(["admin"]),
            "manage_label": f"Manage {entity_name}s",
            "browse_label": f"{entity_name}s",
        }

    if any(h in name for h in ADMIN_ENTITY_HINTS):
        return {
            "nav_roles": with_explicit(["admin"]),
            "dashboard_roles": with_explicit(["admin"]),
            "manage_label": f"Manage {entity_name}s",
            "browse_label": f"{entity_name}s",
        }

    if _is_shared_catalog_entity(entity_name):
        nav = ["admin"]
        dash = ["admin"]
        if primary_user_role:
            nav.append(primary_user_role)
            dash.append(primary_user_role)
        return {
            "nav_roles": with_explicit(nav),
            "dashboard_roles": with_explicit(dash),
            "manage_label": f"Manage {entity_name}s",
            "browse_label": f"Browse {entity_name}s",
        }

    if any(h in name for h in ORDER_ENTITY_HINTS):
        nav = ["admin"]
        dash = ["admin"]
        if primary_user_role:
            nav.append(primary_user_role)
            dash.append(primary_user_role)
        return {
            "nav_roles": with_explicit(nav),
            "dashboard_roles": with_explicit(dash),
            "manage_label": f"Manage {entity_name}s",
            "browse_label": f"My {entity_name}s",
        }

    # Default: management data is admin-only unless app has no customer role
    nav = ["admin"]
    dash = ["admin"]
    if not has_admin and primary_user_role:
        nav = [primary_user_role]
        dash = [primary_user_role]
    return {
        "nav_roles": with_explicit(nav),
        "dashboard_roles": with_explicit(dash),
        "manage_label": f"Manage {entity_name}s",
        "browse_label": f"Browse {entity_name}s",
    }


def role_can_access(allowed: List[str], user_role: str) -> bool:
    role = (user_role or "").lower().strip()
    allowed_norm = [a.lower() for a in allowed]
    if "any" in allowed_norm:
        return True
    return role in allowed_norm


def login_redirect_for_role(user_role: str) -> str:
    if (user_role or "").lower().strip() == "admin":
        return "/admin/dashboard"
    return "/"


def normalize_field_type(field_name: str, field_type: str) -> str:
    """Align data-model field types with sensible SQLAlchemy/Pydantic types."""
    name = (field_name or "").lower()
    ftype = (field_type or "string").lower()
    if ftype in ("integer", "number"):
        return "int"
    if ftype in ("float", "double"):
        return "decimal"
    if name in ("quantity", "count", "stock", "qty", "amount", "age", "year") and ftype in ("string", "text"):
        return "int"
    if name in ("price", "total_cost", "cost", "total", "rate", "fee") and ftype in ("string", "text"):
        return "decimal"
    if name.endswith("_id") and ftype in ("string", "text"):
        return "uuid"
    return ftype
