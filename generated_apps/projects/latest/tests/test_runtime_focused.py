"""
Auto-generated runtime validation tests (pages, UI actions, database, roles).
DO NOT weaken assertions — failures indicate real broken behavior.
"""
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
import pytest
import httpx
from sqlalchemy import inspect

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_runtime.db")

PAGES = [{'path': '/', 'name': 'Dashboard', 'expected': ['window.APP_CONFIG', '<html']}, {'path': '/admin/dashboard', 'name': 'Admin dashboard', 'expected': ['window.APP_CONFIG', '<html']}, {'path': '/ui/login', 'name': 'Login page', 'expected': ['login', '<form', 'email']}, {'path': '/ui/register', 'name': 'Register page', 'expected': ['register', '<form', 'email']}, {'path': '/ui/notes', 'name': 'Note list', 'expected': ['APP_CONFIG', '<html']}, {'path': '/ui/notes/new', 'name': 'New Note', 'expected': ['APP_CONFIG', '<html']}, {'path': '/ui/roles', 'name': 'Role list', 'expected': ['APP_CONFIG', '<html']}, {'path': '/ui/roles/new', 'name': 'New Role', 'expected': ['APP_CONFIG', '<html']}, {'path': '/notes', 'name': 'Note List', 'expected': ['<html']}, {'path': '/notes/new', 'name': 'Create Note', 'expected': ['<html']}, {'path': '/notes/view/edit', 'name': 'Edit Note', 'expected': ['<html']}, {'path': '/notes/view/delete', 'name': 'Delete Note', 'expected': ['<html']}, {'path': '/shared-notes', 'name': 'Shared Notes', 'expected': ['<html']}, {'path': '/users', 'name': 'Manage User Accounts', 'expected': ['<html']}, {'path': '/admin/roles', 'name': 'Assign Roles to Users', 'expected': ['<html']}]
ACTIONS = [{'id': 'action_health', 'name': 'Health endpoint', 'method': 'GET', 'path': '/health', 'json': None, 'status': 200, 'key': None, 'nav_from': None}, {'id': 'action_login_api', 'name': 'Login API', 'method': 'POST', 'path': '/api/auth/login', 'json': {'email': 'admin@example.com', 'password': 'Admin1234!'}, 'status': 200, 'key': 'access_token', 'nav_from': None}, {'id': 'action_register_page_form', 'name': 'Register page has submit hook', 'method': 'GET', 'path': '/ui/register', 'json': None, 'status': 200, 'key': None, 'nav_from': None}, {'id': 'action_login_page_form', 'name': 'Login page has submit hook', 'method': 'GET', 'path': '/ui/login', 'json': None, 'status': 200, 'key': None, 'nav_from': None}, {'id': 'action_nav_list_notes', 'name': 'Navigate to Note list UI', 'method': 'GET', 'path': '/ui/notes', 'json': None, 'status': 200, 'key': None, 'nav_from': '/'}, {'id': 'action_nav_new_notes', 'name': 'Navigate to new Note form', 'method': 'GET', 'path': '/ui/notes/new', 'json': None, 'status': 200, 'key': None, 'nav_from': None}, {'id': 'action_nav_list_roles', 'name': 'Navigate to Role list UI', 'method': 'GET', 'path': '/ui/roles', 'json': None, 'status': 200, 'key': None, 'nav_from': '/'}, {'id': 'action_nav_new_roles', 'name': 'Navigate to new Role form', 'method': 'GET', 'path': '/ui/roles/new', 'json': None, 'status': 200, 'key': None, 'nav_from': None}, {'id': 'action_dashboard_stats', 'name': 'Dashboard stats API returns counts', 'method': 'GET', 'path': '/api/dashboard/stats', 'json': None, 'status': 200, 'key': None, 'nav_from': None}]
DB_CASES = [{'id': 'db_init_metadata', 'name': 'Database tables created', 'resource': '', 'entity': '', 'op': 'init', 'payload': {}, 'fk_refs': {}}, {'id': 'db_auth_me', 'name': 'Authenticated read /api/auth/me', 'resource': 'auth', 'entity': 'User', 'op': 'me', 'payload': {}, 'fk_refs': {}}, {'id': 'db_list_notes', 'name': 'List Note records', 'resource': 'notes', 'entity': 'Note', 'op': 'list', 'payload': {}, 'fk_refs': {}}, {'id': 'db_create_notes', 'name': 'Create Note record', 'resource': 'notes', 'entity': 'Note', 'op': 'create', 'payload': {'title': 'runtime_test_title', 'content': 'runtime_test_content', 'user_id': '__FK__'}, 'fk_refs': {'user_id': '__current_user__'}}, {'id': 'db_read_notes', 'name': 'Read Note record by id', 'resource': 'notes', 'entity': 'Note', 'op': 'read', 'payload': {}, 'fk_refs': {}}, {'id': 'db_update_notes', 'name': 'Update Note record', 'resource': 'notes', 'entity': 'Note', 'op': 'update', 'payload': {'title': 'runtime_test_title', 'content': 'runtime_test_content', 'user_id': '__FK__'}, 'fk_refs': {'user_id': '__current_user__'}}, {'id': 'db_delete_notes', 'name': 'Delete Note record', 'resource': 'notes', 'entity': 'Note', 'op': 'delete', 'payload': {}, 'fk_refs': {}}, {'id': 'db_list_roles', 'name': 'List Role records', 'resource': 'roles', 'entity': 'Role', 'op': 'list', 'payload': {}, 'fk_refs': {}}, {'id': 'db_create_roles', 'name': 'Create Role record', 'resource': 'roles', 'entity': 'Role', 'op': 'create', 'payload': {'role_name': 'runtime_test_role_name'}, 'fk_refs': {'role_id': '__current_user__'}}, {'id': 'db_read_roles', 'name': 'Read Role record by id', 'resource': 'roles', 'entity': 'Role', 'op': 'read', 'payload': {}, 'fk_refs': {}}, {'id': 'db_update_roles', 'name': 'Update Role record', 'resource': 'roles', 'entity': 'Role', 'op': 'update', 'payload': {'role_name': 'runtime_test_role_name'}, 'fk_refs': {'role_id': '__current_user__'}}, {'id': 'db_delete_roles', 'name': 'Delete Role record', 'resource': 'roles', 'entity': 'Role', 'op': 'delete', 'payload': {}, 'fk_refs': {}}]
ROLE_CASES = [{'id': 'role_admin', 'name': 'Admin role access', 'email': 'admin@example.com', 'password': 'Admin1234!', 'role': 'admin', 'landing': '/admin/dashboard', 'allowed': ['/admin/dashboard', '/ui/notes', '/ui/roles', '/ui/notes', '/ui/roles'], 'forbidden': [], 'stats': ['notes', 'roles'], 'forbidden_api': []}, {'id': 'role_customer', 'name': 'User role access', 'email': 'user@example.com', 'password': 'User1234!', 'role': 'user', 'landing': '/', 'allowed': ['/', '/ui/notes', '/ui/roles'], 'forbidden': ['/admin/dashboard'], 'stats': ['notes', 'roles'], 'forbidden_api': []}]
PUBLIC_ROLE = 'user'
PUBLIC_ROLE_LOWER = PUBLIC_ROLE.lower()
OWNED_RESOURCES = [{'resource': 'notes', 'owner_field': 'user_id'}]

ERROR_MARKERS = (
    "error loading",
    "internal server error",
    "failed to fetch",
    "cannot get",
    "traceback",
)

BASE_URL = os.environ.get("RUNTIME_TEST_BASE_URL", "").rstrip("/")
USE_LIVE = bool(BASE_URL)
API_PREFIX = '/api'


@pytest.fixture(scope="module", autouse=True)
def seeded_database():
    project_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "seed.py"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=120,
        env=os.environ.copy(),
    )
    assert result.returncode == 0, (
        "seed.py failed before runtime tests: "
        + (result.stdout + result.stderr)[-1200:]
    )


@pytest.fixture(scope="module")
def client():
    if USE_LIVE:
        timeout = httpx.Timeout(30.0, connect=10.0)
        with httpx.Client(base_url=BASE_URL, timeout=timeout, follow_redirects=True) as c:
            yield c
    else:
        from fastapi.testclient import TestClient
        from app.main import app
        import seed
        try:
            if hasattr(seed, "main"):
                seed.main()
            elif hasattr(seed, "seed"):
                seed.seed()
            else:
                pytest.fail("seed.py must define main() or seed()")
        except Exception as exc:
            pytest.fail(f"seed.py failed — app cannot start for runtime tests: {exc}")
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def _assert_not_server_error(res, context: str):
    assert res.status_code != 500, f"{context}: Internal Server Error — {res.text[:800]}"
    assert res.status_code != 404, f"{context}: Not Found for {getattr(res, 'url', '')}"


def _assert_no_error_markers(body: str, context: str):
    lower = (body or "").lower()
    visible_markers = (
        'style="color:red;">error loading',
        ">error loading</p>",
        "internal server error",
        "failed to fetch",
    )
    for marker in visible_markers:
        if marker in lower:
            assert False, f"{context}: page contains error marker {marker!r}"


def _login(client, email: str, password: str) -> dict:
    res = client.post(f"{API_PREFIX}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        res = client.post(
            f"{API_PREFIX}/auth/login/form",
            data={"username": email, "password": password},
        )
    assert res.status_code == 200, f"Login failed for {email}: {res.status_code} {res.text[:400]}"
    token = res.json().get("access_token")
    assert token, "No access_token in login response"
    return {"Authorization": f"Bearer {token}"}


def _payload_for_case(client, case, headers):
    payload = dict(case.get("payload") or {})
    for field, resource in (case.get("fk_refs") or {}).items():
        if resource == "__current_user__":
            me = client.get(f"{API_PREFIX}/auth/me", headers=headers)
            _assert_not_server_error(me, f"Current user FK {field} for {case['name']}")
            assert me.status_code == 200, me.text[:400]
            payload[field] = me.json()["id"]
            continue
        res = client.get(f"{API_PREFIX}/{resource}", headers=headers)
        _assert_not_server_error(res, f"FK parent list {resource} for {case['name']}")
        assert res.status_code == 200, (
            f"Cannot resolve FK {field} from {API_PREFIX}/{resource}: {res.status_code} {res.text[:400]}"
        )
        rows = res.json()
        assert isinstance(rows, list) and rows, (
            f"No seeded parent rows in {API_PREFIX}/{resource} for FK {field}"
        )
        payload[field] = rows[0]["id"]
    return payload


@pytest.fixture(scope="module")
def auth_headers(client):
    return _login(client, 'admin@example.com', 'Admin1234!')


@pytest.mark.page_load
@pytest.mark.parametrize("page", PAGES, ids=[p["name"] for p in PAGES])
def test_page_loads(client, page):
    res = client.get(page["path"])
    _assert_not_server_error(res, page["name"])
    assert 200 <= res.status_code < 400, (
        f"{page['name']} ({page['path']}): expected success, got {res.status_code}"
    )
    body = res.text
    assert "<html" in body.lower() or "<!doctype" in body.lower(), (
        f"{page['path']} did not return HTML"
    )
    for marker in page.get("expected") or []:
        assert marker.lower() in body.lower(), (
            f"{page['path']} missing expected content: {marker!r}"
        )
    if page["path"] in ("/", "/admin/dashboard"):
        assert 'style="color:red;">error loading' not in body.lower(), (
            f"{page['path']} dashboard shows visible Error loading state"
        )


@pytest.mark.ui_action
def test_dashboard_stats_no_errors(client, auth_headers):
    res = client.get(f"{API_PREFIX}/dashboard/stats", headers=auth_headers)
    if res.status_code == 404:
        pytest.skip("Dashboard statistics are not used by this generated UI")
    _assert_not_server_error(res, "Dashboard stats API")
    assert res.status_code == 200, res.text[:400]
    data = res.json()
    assert isinstance(data, dict), "Dashboard stats must return JSON object"
    for key, val in data.items():
        assert val is not None, f"Dashboard stat {key} is null/error"
        if isinstance(val, (int, float)):
            assert val >= 0, f"Dashboard stat {key} invalid: {val}"


@pytest.mark.ui_action
@pytest.mark.parametrize("action", ACTIONS, ids=[a["id"] for a in ACTIONS])
def test_ui_action(client, action, auth_headers):
    method = action["method"].upper()
    path = action["path"]
    headers = dict(auth_headers) if path.startswith(API_PREFIX + "/") and path != f"{API_PREFIX}/auth/login" else {}
    kwargs = {}
    if action.get("json"):
        kwargs["json"] = action["json"]
    res = client.request(method, path, headers=headers, **kwargs)
    _assert_not_server_error(res, action["name"])
    expected = action.get("status", 200)
    assert res.status_code == expected, (
        f"{action['name']}: expected {expected}, got {res.status_code} — {res.text[:500]}"
    )
    if action.get("key"):
        data = res.json()
        assert action["key"] in data, f"{action['name']}: missing {action['key']}"

    nav_from = action.get("nav_from")
    if nav_from:
        home = client.get(nav_from, headers=headers)
        _assert_not_server_error(home, f"Navigation source {nav_from}")
        target = client.get(path, headers=headers)
        _assert_not_server_error(target, action["name"])
        assert target.status_code == 200

    if path == "/ui/register":
        assert f"{API_PREFIX}/auth/register" in res.text and "<form" in res.text.lower()
    if path == "/ui/login":
        assert f"{API_PREFIX}/auth/login" in res.text and "<form" in res.text.lower()


@pytest.mark.role_based
@pytest.mark.parametrize("role_case", ROLE_CASES, ids=[r["id"] for r in ROLE_CASES])
def test_role_access(client, role_case):
    headers = _login(client, role_case["email"], role_case["password"])

    me = client.get(f"{API_PREFIX}/auth/me", headers=headers)
    assert me.status_code == 200, me.text[:300]
    role = (me.json().get("role") or "").lower()
    assert role == role_case["role"], f"Expected role {role_case['role']}, got {role}"

    landing = client.get(role_case["landing"], headers=headers)
    _assert_not_server_error(landing, f"{role_case['name']} landing")
    assert landing.status_code == 200
    _assert_no_error_markers(landing.text, role_case["name"])

    stats = client.get(f"{API_PREFIX}/dashboard/stats", headers=headers)
    assert stats.status_code == 200, stats.text[:400]
    stats_data = stats.json()
    for key in role_case.get("stats") or []:
        assert key in stats_data, f"{role_case['role']} missing dashboard stat {key}"
        assert stats_data[key] is not None, f"Dashboard stat {key} failed for {role_case['role']}"

    for path in role_case.get("allowed") or []:
        res = client.get(path, headers=headers)
        _assert_not_server_error(res, f"{role_case['role']} allowed {path}")
        assert res.status_code == 200, f"{role_case['role']} cannot access {path}: {res.status_code}"

    for path in role_case.get("forbidden") or []:
        if path in (role_case.get("allowed") or []):
            continue
        res = client.get(path, headers=headers)
        assert res.status_code in (200, 403, 302, 307, 401), (
            f"{role_case['role']} forbidden page {path} crashed: {res.status_code}"
        )
        if res.status_code == 200:
            body = res.text.lower()
            cfg_match = re.search(r"window\.APP_CONFIG\s*=\s*(\{.*?\});", res.text, re.DOTALL)
            if cfg_match and role_case["role"] != "admin":
                try:
                    cfg = json.loads(cfg_match.group(1))
                    def _role_ok(allowed, role):
                        allowed = [str(a).lower() for a in (allowed or ['any'])]
                        if 'any' in allowed: return True
                        if role == 'admin' and 'admin' in allowed: return True
                        return role in allowed
                    nav_items = [n for n in (cfg.get("nav") or []) if _role_ok(n.get('roles') or [n.get('role') or 'any'], role_case["role"])]
                    nav_paths = [n.get("path") for n in nav_items]
                    assert path not in nav_paths, (
                        f"Customer UI exposes forbidden nav path {path}"
                    )
                except json.JSONDecodeError:
                    pass

    for api_path in role_case.get("forbidden_api") or []:
        res = client.get(api_path, headers=headers)
        assert res.status_code in (200, 403, 401), (
            f"{role_case['role']} forbidden API {api_path} returned {res.status_code}"
        )
        if res.status_code == 200 and role_case["role"] != "admin":
            data = res.json()
            if isinstance(data, list) and api_path.endswith(("admins", "customers")):
                pytest.fail(f"Customer can list admin-only resource {api_path}")


@pytest.mark.database
def test_database_init(client):
    if USE_LIVE:
        res = client.get("/health")
        assert res.status_code == 200
        return
    from app.db import engine, Base
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    tables = inspect(engine).get_table_names()
    assert tables, "No database tables were created"
    assert "users" in [t.lower() for t in tables], "users table missing"


@pytest.mark.database
def test_database_auth_me(client, auth_headers):
    res = client.get(f"{API_PREFIX}/auth/me", headers=auth_headers)
    _assert_not_server_error(res, "auth me")
    assert res.status_code == 200, res.text[:300]
    data = res.json()
    assert data.get("email"), "auth/me returned no email"


@pytest.mark.database
def test_database_form_login_compatibility(client):
    res = client.post(
        f"{API_PREFIX}/auth/login/form",
        data={"username": 'user@example.com', "password": 'User1234!'},
    )
    assert res.status_code == 200, res.text[:400]
    assert res.json().get("access_token")


@pytest.mark.role_based
def test_role_public_registration_cannot_create_admin(client):
    email = f"role-check-{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": email,
            "password": "ValidPass123!",
            "full_name": "Role Check",
            "role": "Admin",
        },
    )
    assert res.status_code in (200, 201), res.text[:400]
    assert (res.json().get("role") or "").lower() == PUBLIC_ROLE_LOWER
    headers = _login(client, email, "ValidPass123!")
    me = client.get(f"{API_PREFIX}/auth/me", headers=headers)
    assert me.status_code == 200, me.text[:300]
    assert (me.json().get("role") or "").lower() == PUBLIC_ROLE_LOWER


@pytest.mark.database
def test_seed_is_idempotent(client, auth_headers):
    resources = sorted({
        case["resource"]
        for case in DB_CASES
        if case["op"] == "list" and case.get("resource")
    })
    before = {}
    for resource in resources:
        res = client.get(f"{API_PREFIX}/{resource}", headers=auth_headers)
        assert res.status_code == 200, res.text[:300]
        before[resource] = len(res.json())
    project_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "seed.py"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=120,
        env=os.environ.copy(),
    )
    assert result.returncode == 0, (result.stdout + result.stderr)[-1000:]
    for resource, count in before.items():
        res = client.get(f"{API_PREFIX}/{resource}", headers=auth_headers)
        assert res.status_code == 200, res.text[:300]
        assert len(res.json()) == count, f"seed.py duplicated {resource} rows"


@pytest.mark.database
@pytest.mark.role_based
def test_database_customer_lists_are_ownership_scoped(client):
    if not OWNED_RESOURCES:
        pytest.skip("No customer-owned entities in this project")
    headers = _login(client, 'user@example.com', 'User1234!')
    me = client.get(f"{API_PREFIX}/auth/me", headers=headers)
    assert me.status_code == 200, me.text[:300]
    customer_id = str(me.json()["id"])
    for item in OWNED_RESOURCES:
        res = client.get(f"{API_PREFIX}/{item['resource']}", headers=headers)
        assert res.status_code == 200, res.text[:400]
        rows = res.json()
        assert isinstance(rows, list)
        for row in rows:
            assert str(row.get(item["owner_field"])) == customer_id, (
                f"Customer can see another user's {item['resource']} row"
            )


@pytest.mark.database
@pytest.mark.parametrize("case", [c for c in DB_CASES if c["op"] not in ("init", "me")], ids=[c["id"] for c in DB_CASES if c["op"] not in ("init", "me")])
def test_database_crud(client, case, auth_headers):
    resource = case["resource"]
    op = case["op"]
    headers = auth_headers
    api = f"{API_PREFIX}/{resource}"

    if op == "list":
        res = client.get(api, headers=headers)
        _assert_not_server_error(res, case["name"])
        assert res.status_code == 200, res.text[:400]
        assert isinstance(res.json(), list), "List endpoint must return JSON array"
        return

    if op == "create":
        payload = _payload_for_case(client, case, headers)
        payload["id"] = str(uuid.uuid4())
        res = client.post(api, headers=headers, json=payload)
        _assert_not_server_error(res, case["name"])
        assert res.status_code in (200, 201), f"Create failed: {res.status_code} {res.text[:400]}"
        created = res.json()
        assert created.get("id"), "Created record missing id"
        return

    list_res = client.get(api, headers=headers)
    assert list_res.status_code == 200
    rows = list_res.json()
    if not rows and op in ("read", "update", "delete"):
        payload = _payload_for_case(client, case, headers)
        payload["id"] = str(uuid.uuid4())
        cr = client.post(api, headers=headers, json=payload)
        assert cr.status_code in (200, 201), f"Could not seed row: {cr.text[:300]}"
        record_id = cr.json()["id"]
    elif rows:
        record_id = rows[0]["id"]
    else:
        pytest.fail(f"No records for {resource} to test {op}")

    if op == "read":
        res = client.get(f"{api}/{record_id}", headers=headers)
        _assert_not_server_error(res, case["name"])
        assert res.status_code == 200
        assert res.json().get("id") == record_id
    elif op == "update":
        payload = _payload_for_case(client, case, headers)
        payload.pop("id", None)
        res = client.put(f"{api}/{record_id}", headers=headers, json=payload)
        _assert_not_server_error(res, case["name"])
        assert res.status_code == 200, res.text[:400]
    elif op == "delete":
        res = client.delete(f"{api}/{record_id}", headers=headers)
        _assert_not_server_error(res, case["name"])
        assert res.status_code in (200, 204), res.text[:400]
