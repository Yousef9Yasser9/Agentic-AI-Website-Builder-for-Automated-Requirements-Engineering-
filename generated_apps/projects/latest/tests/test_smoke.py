import os
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
