"""
Generate strict runtime-focused pytest suite for a generated FastAPI app.
"""

from __future__ import annotations

import textwrap
import re
from pathlib import Path
from typing import Any, Dict

from builder.app_contract import build_app_contract
from builder.runtime_test_plan import RuntimeTestPlan, build_runtime_test_plan


def write_runtime_focused_tests(project_dir: str, project_data: Dict[str, Any]) -> Path:
    """Write tests/test_runtime_focused.py and return its path."""
    plan = build_runtime_test_plan(project_data)
    tests_dir = Path(project_dir) / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "__init__.py").touch()
    (tests_dir / "conftest.py").write_text(
        textwrap.dedent(
            """\
            import pytest

            def pytest_configure(config):
                config.addinivalue_line("markers", "page_load: HTTP page load validation")
                config.addinivalue_line("markers", "ui_action: buttons, forms, and navigation")
                config.addinivalue_line("markers", "database: database CRUD and schema checks")
                config.addinivalue_line("markers", "role_based: role dashboards and access control")
            """
        ),
        encoding="utf-8",
    )

    pages_literal = repr(
        [{"path": p.path, "name": p.name, "expected": p.expected_in_body} for p in plan.pages]
    )
    actions_literal = repr(
        [
            {
                "id": a.test_id,
                "name": a.name,
                "method": a.method,
                "path": a.path,
                "json": a.json_body,
                "status": a.expected_status,
                "key": a.expect_json_key,
                "nav_from": a.navigate_from,
            }
            for a in plan.actions
        ]
    )
    db_literal = repr(
        [
            {
                "id": d.test_id,
                "name": d.name,
                "resource": d.resource,
                "entity": d.entity_class,
                "op": d.operation,
                "payload": d.sample_payload,
                "fk_refs": d.fk_refs,
            }
            for d in plan.database
        ]
    )

    roles_literal = repr(
        [
            {
                "id": r.test_id,
                "name": r.name,
                "email": r.email,
                "password": r.password,
                "role": r.role,
                "landing": r.expected_landing,
                "allowed": r.allowed_nav_paths,
                "forbidden": r.forbidden_nav_paths,
                "stats": r.dashboard_stats_keys,
                "forbidden_api": r.forbidden_api_paths,
            }
            for r in plan.roles
        ]
    )
    contract = build_app_contract(project_data)
    admin_account = contract.demo_accounts.get("Admin") or contract.demo_accounts.get("admin") or {
        "email": "admin@example.com",
        "password": "Admin1234!",
    }
    public_account = contract.demo_accounts.get(contract.public_role) or {
        "email": "user@example.com",
        "password": "User1234!",
    }
    public_role = next((r.role for r in plan.roles if r.test_id == "role_customer"), contract.public_role)
    public_role_literal = repr(public_role)
    public_role_lower = public_role.lower()
    api_prefix_literal = repr(contract.api_prefix)
    admin_email_literal = repr(admin_account["email"])
    admin_password_literal = repr(admin_account["password"])
    public_email_literal = repr(public_account["email"])
    public_password_literal = repr(public_account["password"])
    owned_resources = []
    for entity in contract.business_entities():
        readable_roles = {str(role).lower() for role in entity.read_roles}
        if public_role_lower not in readable_roles:
            continue
        fields = {field.get("name") for field in entity.fields}
        owner_field = next(
            (
                field
                for field in ("user_id", "owner_id", "created_by", "customer_id", "uploader_id")
                if field in fields
            ),
            None,
        )
        if owner_field:
            if owner_field not in set(entity.scope_fields):
                continue
            owned_resources.append({"resource": entity.resource, "owner_field": owner_field})
    owned_literal = repr(owned_resources)

    code = textwrap.dedent(
        f'''\
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

        PAGES = {pages_literal}
        ACTIONS = {actions_literal}
        DB_CASES = {db_literal}
        ROLE_CASES = {roles_literal}
        PUBLIC_ROLE = {public_role_literal}
        PUBLIC_ROLE_LOWER = PUBLIC_ROLE.lower()
        OWNED_RESOURCES = {owned_literal}

        ERROR_MARKERS = (
            "error loading",
            "internal server error",
            "failed to fetch",
            "cannot get",
            "traceback",
        )

        BASE_URL = os.environ.get("RUNTIME_TEST_BASE_URL", "").rstrip("/")
        USE_LIVE = bool(BASE_URL)
        API_PREFIX = {api_prefix_literal}


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
                    pytest.fail(f"seed.py failed — app cannot start for runtime tests: {{exc}}")
                with TestClient(app, raise_server_exceptions=False) as c:
                    yield c


        def _assert_not_server_error(res, context: str):
            assert res.status_code != 500, f"{{context}}: Internal Server Error — {{res.text[:800]}}"
            assert res.status_code != 404, f"{{context}}: Not Found for {{getattr(res, 'url', '')}}"


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
                    assert False, f"{{context}}: page contains error marker {{marker!r}}"


        def _login(client, email: str, password: str) -> dict:
            res = client.post(f"{{API_PREFIX}}/auth/login", json={{"email": email, "password": password}})
            if res.status_code != 200:
                res = client.post(
                    f"{{API_PREFIX}}/auth/login/form",
                    data={{"username": email, "password": password}},
                )
            assert res.status_code == 200, f"Login failed for {{email}}: {{res.status_code}} {{res.text[:400]}}"
            token = res.json().get("access_token")
            assert token, "No access_token in login response"
            return {{"Authorization": f"Bearer {{token}}"}}


        def _payload_for_case(client, case, headers):
            payload = dict(case.get("payload") or {{}})
            for field, resource in (case.get("fk_refs") or {{}}).items():
                if resource == "__current_user__":
                    me = client.get(f"{{API_PREFIX}}/auth/me", headers=headers)
                    _assert_not_server_error(me, f"Current user FK {{field}} for {{case['name']}}")
                    assert me.status_code == 200, me.text[:400]
                    payload[field] = me.json()["id"]
                    continue
                res = client.get(f"{{API_PREFIX}}/{{resource}}", headers=headers)
                _assert_not_server_error(res, f"FK parent list {{resource}} for {{case['name']}}")
                assert res.status_code == 200, (
                    f"Cannot resolve FK {{field}} from {{API_PREFIX}}/{{resource}}: {{res.status_code}} {{res.text[:400]}}"
                )
                rows = res.json()
                assert isinstance(rows, list) and rows, (
                    f"No seeded parent rows in {{API_PREFIX}}/{{resource}} for FK {{field}}"
                )
                payload[field] = rows[0]["id"]
            return payload


        @pytest.fixture(scope="module")
        def auth_headers(client):
            return _login(client, {admin_email_literal}, {admin_password_literal})


        @pytest.mark.page_load
        @pytest.mark.parametrize("page", PAGES, ids=[p["name"] for p in PAGES])
        def test_page_loads(client, page):
            res = client.get(page["path"])
            _assert_not_server_error(res, page["name"])
            assert 200 <= res.status_code < 400, (
                f"{{page['name']}} ({{page['path']}}): expected success, got {{res.status_code}}"
            )
            body = res.text
            assert "<html" in body.lower() or "<!doctype" in body.lower(), (
                f"{{page['path']}} did not return HTML"
            )
            for marker in page.get("expected") or []:
                assert marker.lower() in body.lower(), (
                    f"{{page['path']}} missing expected content: {{marker!r}}"
                )
            if page["path"] in ("/", "/admin/dashboard"):
                assert 'style="color:red;">error loading' not in body.lower(), (
                    f"{{page['path']}} dashboard shows visible Error loading state"
                )


        @pytest.mark.ui_action
        def test_dashboard_stats_no_errors(client, auth_headers):
            res = client.get(f"{{API_PREFIX}}/dashboard/stats", headers=auth_headers)
            if res.status_code == 404:
                pytest.skip("Dashboard statistics are not used by this generated UI")
            _assert_not_server_error(res, "Dashboard stats API")
            assert res.status_code == 200, res.text[:400]
            data = res.json()
            assert isinstance(data, dict), "Dashboard stats must return JSON object"
            for key, val in data.items():
                assert val is not None, f"Dashboard stat {{key}} is null/error"
                if isinstance(val, (int, float)):
                    assert val >= 0, f"Dashboard stat {{key}} invalid: {{val}}"


        @pytest.mark.ui_action
        @pytest.mark.parametrize("action", ACTIONS, ids=[a["id"] for a in ACTIONS])
        def test_ui_action(client, action, auth_headers):
            method = action["method"].upper()
            path = action["path"]
            headers = dict(auth_headers) if path.startswith(API_PREFIX + "/") and path != f"{{API_PREFIX}}/auth/login" else {{}}
            kwargs = {{}}
            if action.get("json"):
                kwargs["json"] = action["json"]
            res = client.request(method, path, headers=headers, **kwargs)
            _assert_not_server_error(res, action["name"])
            expected = action.get("status", 200)
            assert res.status_code == expected, (
                f"{{action['name']}}: expected {{expected}}, got {{res.status_code}} — {{res.text[:500]}}"
            )
            if action.get("key"):
                data = res.json()
                assert action["key"] in data, f"{{action['name']}}: missing {{action['key']}}"

            nav_from = action.get("nav_from")
            if nav_from:
                home = client.get(nav_from, headers=headers)
                _assert_not_server_error(home, f"Navigation source {{nav_from}}")
                target = client.get(path, headers=headers)
                _assert_not_server_error(target, action["name"])
                assert target.status_code == 200

            if path == "/ui/register":
                assert f"{{API_PREFIX}}/auth/register" in res.text and "<form" in res.text.lower()
            if path == "/ui/login":
                assert f"{{API_PREFIX}}/auth/login" in res.text and "<form" in res.text.lower()


        @pytest.mark.role_based
        @pytest.mark.parametrize("role_case", ROLE_CASES, ids=[r["id"] for r in ROLE_CASES])
        def test_role_access(client, role_case):
            headers = _login(client, role_case["email"], role_case["password"])

            me = client.get(f"{{API_PREFIX}}/auth/me", headers=headers)
            assert me.status_code == 200, me.text[:300]
            role = (me.json().get("role") or "").lower()
            assert role == role_case["role"], f"Expected role {{role_case['role']}}, got {{role}}"

            landing = client.get(role_case["landing"], headers=headers)
            _assert_not_server_error(landing, f"{{role_case['name']}} landing")
            assert landing.status_code == 200
            _assert_no_error_markers(landing.text, role_case["name"])

            stats = client.get(f"{{API_PREFIX}}/dashboard/stats", headers=headers)
            assert stats.status_code == 200, stats.text[:400]
            stats_data = stats.json()
            for key in role_case.get("stats") or []:
                assert key in stats_data, f"{{role_case['role']}} missing dashboard stat {{key}}"
                assert stats_data[key] is not None, f"Dashboard stat {{key}} failed for {{role_case['role']}}"

            for path in role_case.get("allowed") or []:
                res = client.get(path, headers=headers)
                _assert_not_server_error(res, f"{{role_case['role']}} allowed {{path}}")
                assert res.status_code == 200, f"{{role_case['role']}} cannot access {{path}}: {{res.status_code}}"

            for path in role_case.get("forbidden") or []:
                if path in (role_case.get("allowed") or []):
                    continue
                res = client.get(path, headers=headers)
                assert res.status_code in (200, 403, 302, 307, 401), (
                    f"{{role_case['role']}} forbidden page {{path}} crashed: {{res.status_code}}"
                )
                if res.status_code == 200:
                    body = res.text.lower()
                    cfg_match = re.search(r"window\\.APP_CONFIG\\s*=\\s*(\\{{.*?\\}});", res.text, re.DOTALL)
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
                                f"Customer UI exposes forbidden nav path {{path}}"
                            )
                        except json.JSONDecodeError:
                            pass

            for api_path in role_case.get("forbidden_api") or []:
                res = client.get(api_path, headers=headers)
                assert res.status_code in (200, 403, 401), (
                    f"{{role_case['role']}} forbidden API {{api_path}} returned {{res.status_code}}"
                )
                if res.status_code == 200 and role_case["role"] != "admin":
                    data = res.json()
                    if isinstance(data, list) and api_path.endswith(("admins", "customers")):
                        pytest.fail(f"Customer can list admin-only resource {{api_path}}")


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
            res = client.get(f"{{API_PREFIX}}/auth/me", headers=auth_headers)
            _assert_not_server_error(res, "auth me")
            assert res.status_code == 200, res.text[:300]
            data = res.json()
            assert data.get("email"), "auth/me returned no email"


        @pytest.mark.database
        def test_database_form_login_compatibility(client):
            res = client.post(
                f"{{API_PREFIX}}/auth/login/form",
                data={{"username": {public_email_literal}, "password": {public_password_literal}}},
            )
            assert res.status_code == 200, res.text[:400]
            assert res.json().get("access_token")


        @pytest.mark.role_based
        def test_role_public_registration_cannot_create_admin(client):
            email = f"role-check-{{uuid.uuid4().hex[:10]}}@example.com"
            res = client.post(
                f"{{API_PREFIX}}/auth/register",
                json={{
                    "email": email,
                    "password": "ValidPass123!",
                    "full_name": "Role Check",
                    "role": "Admin",
                }},
            )
            assert res.status_code in (200, 201), res.text[:400]
            assert (res.json().get("role") or "").lower() == PUBLIC_ROLE_LOWER
            headers = _login(client, email, "ValidPass123!")
            me = client.get(f"{{API_PREFIX}}/auth/me", headers=headers)
            assert me.status_code == 200, me.text[:300]
            assert (me.json().get("role") or "").lower() == PUBLIC_ROLE_LOWER


        @pytest.mark.database
        def test_seed_is_idempotent(client, auth_headers):
            resources = sorted({{
                case["resource"]
                for case in DB_CASES
                if case["op"] == "list" and case.get("resource")
            }})
            before = {{}}
            for resource in resources:
                res = client.get(f"{{API_PREFIX}}/{{resource}}", headers=auth_headers)
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
                res = client.get(f"{{API_PREFIX}}/{{resource}}", headers=auth_headers)
                assert res.status_code == 200, res.text[:300]
                assert len(res.json()) == count, f"seed.py duplicated {{resource}} rows"


        @pytest.mark.database
        @pytest.mark.role_based
        def test_database_customer_lists_are_ownership_scoped(client):
            if not OWNED_RESOURCES:
                pytest.skip("No customer-owned entities in this project")
            headers = _login(client, {public_email_literal}, {public_password_literal})
            me = client.get(f"{{API_PREFIX}}/auth/me", headers=headers)
            assert me.status_code == 200, me.text[:300]
            customer_id = str(me.json()["id"])
            for item in OWNED_RESOURCES:
                res = client.get(f"{{API_PREFIX}}/{{item['resource']}}", headers=headers)
                assert res.status_code == 200, res.text[:400]
                rows = res.json()
                assert isinstance(rows, list)
                for row in rows:
                    assert str(row.get(item["owner_field"])) == customer_id, (
                        f"Customer can see another user's {{item['resource']}} row"
                    )


        @pytest.mark.database
        @pytest.mark.parametrize("case", [c for c in DB_CASES if c["op"] not in ("init", "me")], ids=[c["id"] for c in DB_CASES if c["op"] not in ("init", "me")])
        def test_database_crud(client, case, auth_headers):
            resource = case["resource"]
            op = case["op"]
            headers = auth_headers
            api = f"{{API_PREFIX}}/{{resource}}"

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
                assert res.status_code in (200, 201), f"Create failed: {{res.status_code}} {{res.text[:400]}}"
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
                assert cr.status_code in (200, 201), f"Could not seed row: {{cr.text[:300]}}"
                record_id = cr.json()["id"]
            elif rows:
                record_id = rows[0]["id"]
            else:
                pytest.fail(f"No records for {{resource}} to test {{op}}")

            if op == "read":
                res = client.get(f"{{api}}/{{record_id}}", headers=headers)
                _assert_not_server_error(res, case["name"])
                assert res.status_code == 200
                assert res.json().get("id") == record_id
            elif op == "update":
                payload = _payload_for_case(client, case, headers)
                payload.pop("id", None)
                res = client.put(f"{{api}}/{{record_id}}", headers=headers, json=payload)
                _assert_not_server_error(res, case["name"])
                assert res.status_code == 200, res.text[:400]
            elif op == "delete":
                res = client.delete(f"{{api}}/{{record_id}}", headers=headers)
                _assert_not_server_error(res, case["name"])
                assert res.status_code in (200, 204), res.text[:400]
        '''
    )

    out = tests_dir / "test_runtime_focused.py"
    out.write_text(code, encoding="utf-8")
    return out
