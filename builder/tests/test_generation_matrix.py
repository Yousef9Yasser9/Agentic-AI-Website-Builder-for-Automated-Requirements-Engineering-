from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from builder.app_contract import build_app_contract
from builder.contract_validator import parse_exposed_routes, run_engine_contract_preflight
from builder.runtime_test_generator import write_runtime_focused_tests
from generated_apps.generator.deterministic_backend import apply_deterministic_guard
from generated_apps.generator.repo_generator import (
    _default_public_role,
    _write_invariant_auth,
    _write_invariant_auth_router,
    _write_invariant_db,
    _write_invariant_deps,
)


REQUIRED_PARSE_FILES = (
    "app/main.py",
    "app/schemas.py",
    "app/models.py",
    "app/routers/generic_crud.py",
    "seed.py",
)


def _user_entity() -> dict:
    return {
        "name": "User",
        "fields": [
            {"name": "id", "type": "uuid", "pk": True},
            {"name": "email", "type": "string"},
            {"name": "role", "type": "string"},
        ],
    }


def _project(title: str, roles: list[str], entities: list[dict], relationships: list[dict] | None = None) -> dict:
    role_lines = [f"{role}: use the application features for their role" for role in roles]
    return {
        "plain_text": f"{title}. Users can manage and view their own relevant records.",
        "cleaned_spec": {
            "project_title": title,
            "cleaned_prompt": {
                "Goal": f"Build {title}",
                "Roles": role_lines,
                "Features": [
                    "Role-based dashboards",
                    "Authenticated CRUD",
                    "Users can view their own scoped records",
                ],
            },
        },
        "requirements": {
            "functional_requirements": [
                {"actor": role, "shall": "work with their relevant records"}
                for role in roles
            ]
        },
        "user_stories": {
            "stories": [
                {"actor": role, "story": "I want to access my role-specific records"}
                for role in roles
            ]
        },
        "architecture": {
            "roles": roles,
            "pages": [],
            "endpoints": [],
        },
        "data_model": {
            "entities": [_user_entity(), *entities],
            "relationships": relationships or [],
        },
        "ui_selection": {"theme_vars": {}},
    }


def _fixtures() -> list[tuple[str, dict]]:
    return [
        (
            "event_ticketing",
            _project(
                "Event Ticketing",
                ["Attendee", "Organizer", "Usher", "Admin"],
                [
                    {
                        "name": "Event",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "title", "type": "string"},
                            {"name": "date", "type": "date"},
                            {"name": "venue", "type": "string"},
                            {"name": "organizer_id", "type": "uuid"},
                        ],
                    },
                    {
                        "name": "Ticket",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "event_id", "type": "uuid"},
                            {"name": "user_id", "type": "uuid"},
                            {"name": "seat", "type": "string"},
                        ],
                    },
                    {
                        "name": "Attendance",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "ticket_id", "type": "uuid"},
                            {"name": "usher_id", "type": "uuid"},
                            {"name": "checked_in_at", "type": "datetime"},
                        ],
                    },
                ],
                [
                    {"from": "Ticket", "to": "Event", "type": "many-to-one", "fk_field": "event_id"},
                    {"from": "Ticket", "to": "User", "type": "many-to-one", "fk_field": "user_id"},
                    {"from": "Attendance", "to": "Ticket", "type": "many-to-one", "fk_field": "ticket_id"},
                ],
            ),
        ),
        (
            "food_delivery",
            _project(
                "Food Delivery",
                ["Customer", "Driver", "Restaurant Owner", "Admin"],
                [
                    {
                        "name": "Restaurant",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "name", "type": "string"},
                            {"name": "owner_id", "type": "uuid"},
                        ],
                    },
                    {
                        "name": "Menu Item",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "restaurant_id", "type": "uuid"},
                            {"name": "name", "type": "string"},
                            {"name": "price", "type": "decimal"},
                        ],
                    },
                    {
                        "name": "Order",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "customer_id", "type": "uuid"},
                            {"name": "restaurant_id", "type": "uuid"},
                            {"name": "delivery_date", "type": "date"},
                            {"name": "status", "type": "string"},
                        ],
                    },
                    {
                        "name": "Delivery",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "order_id", "type": "uuid"},
                            {"name": "driver_id", "type": "uuid"},
                            {"name": "status", "type": "string"},
                        ],
                    },
                ],
                [
                    {"from": "Menu Item", "to": "Restaurant", "type": "many-to-one", "fk_field": "restaurant_id"},
                    {"from": "Order", "to": "User", "type": "many-to-one", "fk_field": "customer_id"},
                    {"from": "Delivery", "to": "Order", "type": "many-to-one", "fk_field": "order_id"},
                ],
            ),
        ),
        (
            "clinic_booking",
            _project(
                "Clinic Booking",
                ["Patient", "Doctor", "Admin"],
                [
                    {
                        "name": "Appointment",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "patient_id", "type": "uuid"},
                            {"name": "doctor_id", "type": "uuid"},
                            {"name": "date", "type": "date"},
                            {"name": "reason", "type": "text"},
                        ],
                    },
                    {
                        "name": "Prescription",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "appointment_id", "type": "uuid"},
                            {"name": "patient_id", "type": "uuid"},
                            {"name": "notes", "type": "text"},
                        ],
                    },
                ],
                [
                    {"from": "Appointment", "to": "User", "type": "many-to-one", "fk_field": "patient_id"},
                    {"from": "Prescription", "to": "Appointment", "type": "many-to-one", "fk_field": "appointment_id"},
                ],
            ),
        ),
        (
            "hotel_booking",
            _project(
                "Hotel Booking",
                ["Guest", "Staff", "Admin"],
                [
                    {
                        "name": "Room",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "number", "type": "string"},
                            {"name": "room_type", "type": "string"},
                            {"name": "price", "type": "decimal"},
                        ],
                    },
                    {
                        "name": "Booking",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "guest_id", "type": "uuid"},
                            {"name": "room_id", "type": "uuid"},
                            {"name": "check_in_date", "type": "date"},
                            {"name": "check_out_date", "type": "date"},
                        ],
                    },
                    {
                        "name": "Payment",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "booking_id", "type": "uuid"},
                            {"name": "amount", "type": "decimal"},
                            {"name": "status", "type": "string"},
                        ],
                    },
                ],
                [
                    {"from": "Booking", "to": "User", "type": "many-to-one", "fk_field": "guest_id"},
                    {"from": "Booking", "to": "Room", "type": "many-to-one", "fk_field": "room_id"},
                    {"from": "Payment", "to": "Booking", "type": "many-to-one", "fk_field": "booking_id"},
                ],
            ),
        ),
        (
            "school_lms",
            _project(
                "School LMS",
                ["Student", "Teacher", "Admin"],
                [
                    {
                        "name": "Course",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "title", "type": "string"},
                            {"name": "teacher_id", "type": "uuid"},
                        ],
                    },
                    {
                        "name": "Enrollment",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "student_id", "type": "uuid"},
                            {"name": "course_id", "type": "uuid"},
                            {"name": "date", "type": "date"},
                        ],
                    },
                    {
                        "name": "Assignment",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "course_id", "type": "uuid"},
                            {"name": "due_date", "type": "date"},
                            {"name": "title", "type": "string"},
                        ],
                    },
                    {
                        "name": "Submission",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "assignment_id", "type": "uuid"},
                            {"name": "student_id", "type": "uuid"},
                            {"name": "content", "type": "text"},
                        ],
                    },
                ],
                [
                    {"from": "Enrollment", "to": "User", "type": "many-to-one", "fk_field": "student_id"},
                    {"from": "Enrollment", "to": "Course", "type": "many-to-one", "fk_field": "course_id"},
                    {"from": "Assignment", "to": "Course", "type": "many-to-one", "fk_field": "course_id"},
                    {"from": "Submission", "to": "Assignment", "type": "many-to-one", "fk_field": "assignment_id"},
                ],
            ),
        ),
        (
            "simple_ecommerce",
            _project(
                "Simple E-commerce",
                ["Customer", "Seller", "Admin"],
                [
                    {
                        "name": "Product",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "seller_id", "type": "uuid"},
                            {"name": "name", "type": "string"},
                            {"name": "price", "type": "decimal"},
                            {"name": "stock_quantity", "type": "integer"},
                        ],
                    },
                    {
                        "name": "Cart Item",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "user_id", "type": "uuid"},
                            {"name": "product_id", "type": "uuid"},
                            {"name": "quantity", "type": "integer"},
                        ],
                    },
                    {
                        "name": "Order",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "customer_id", "type": "uuid"},
                            {"name": "date", "type": "date"},
                            {"name": "total", "type": "decimal"},
                        ],
                    },
                ],
                [
                    {"from": "Product", "to": "User", "type": "many-to-one", "fk_field": "seller_id"},
                    {"from": "Cart Item", "to": "User", "type": "many-to-one", "fk_field": "user_id"},
                    {"from": "Cart Item", "to": "Product", "type": "many-to-one", "fk_field": "product_id"},
                    {"from": "Order", "to": "User", "type": "many-to-one", "fk_field": "customer_id"},
                ],
            ),
        ),
    ]


def _render_project(tmp_path: Path, slug: str, project_data: dict) -> Path:
    out_dir = tmp_path / slug
    (out_dir / "app" / "routers").mkdir(parents=True)
    (out_dir / "app" / "__init__.py").write_text('"""Generated app package."""\n', encoding="utf-8")
    (out_dir / "app" / "routers" / "__init__.py").write_text('"""Generated routers."""\n', encoding="utf-8")
    _write_invariant_db(out_dir)
    _write_invariant_auth(out_dir)
    _write_invariant_deps(out_dir)
    _write_invariant_auth_router(out_dir, _default_public_role(project_data))
    apply_deterministic_guard(out_dir, project_data)
    write_runtime_focused_tests(str(out_dir), project_data)
    artifacts = out_dir / "_builder_artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "project_data.json").write_text(json.dumps(project_data, indent=2), encoding="utf-8")
    return out_dir


def _assert_python_parses(out_dir: Path) -> None:
    for rel in REQUIRED_PARSE_FILES:
        path = out_dir / rel
        assert path.exists(), f"Missing generated file: {rel}"
        ast.parse(path.read_text(encoding="utf-8"), filename=rel)


def _assert_contract_prefix_only(out_dir: Path, api_prefix: str) -> None:
    for rel in REQUIRED_PARSE_FILES:
        source = (out_dir / rel).read_text(encoding="utf-8")
        assert "/api/v1" not in source, f"{rel} leaked /api/v1"
    assert api_prefix == "/api"


def _has_runtime_dependencies() -> bool:
    return all(
        importlib.util.find_spec(name) is not None
        for name in ("fastapi", "pytest", "httpx", "sqlalchemy", "pydantic")
    )


def _local_tmp_dir(slug: str) -> Path:
    root = Path.cwd() / ".pytest-run-tmp-generation-matrix"
    root.mkdir(exist_ok=True)
    safe_slug = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in slug)
    out_dir = root / f"{safe_slug}-{uuid.uuid4().hex[:10]}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    return out_dir


@pytest.mark.parametrize("slug,project_data", _fixtures(), ids=[slug for slug, _ in _fixtures()])
def test_generation_matrix_contract_coherence(slug: str, project_data: dict):
    contract = build_app_contract(project_data)
    tmp_path = _local_tmp_dir(slug)
    try:
        out_dir = _render_project(tmp_path, slug, project_data)

        _assert_python_parses(out_dir)
        _assert_contract_prefix_only(out_dir, contract.api_prefix)

        report = run_engine_contract_preflight(out_dir, project_data)
        assert report["ok"], report["message"]
        assert set(report["expected_routes"]).issubset(set(report["exposed_routes"]))
        assert set(contract.api_paths()).issubset(set(report["exposed_routes"]))
        assert set(contract.ui_paths()).issubset(set(report["exposed_routes"]))
        assert set(parse_exposed_routes(out_dir)) == set(report["exposed_routes"])

        seed_py = (out_dir / "seed.py").read_text(encoding="utf-8")
        public_account = contract.demo_accounts[contract.public_role]
        assert public_account["email"] in seed_py
        assert public_account["password"] in seed_py
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.mark.parametrize(
    "slug,project_data",
    [item for item in _fixtures() if item[0] in {"event_ticketing", "food_delivery"}],
    ids=["event_ticketing", "food_delivery"],
)
def test_generation_matrix_runtime_smoke_for_representative_domains(slug: str, project_data: dict):
    if not _has_runtime_dependencies():
        pytest.skip("Runtime dependencies are not installed in this environment")

    tmp_path = _local_tmp_dir(f"runtime-{slug}")
    try:
        out_dir = _render_project(tmp_path, slug, project_data)
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["TMP"] = str(tmp_path / "tmp")
        env["TEMP"] = str(tmp_path / "tmp")
        env["TMPDIR"] = str(tmp_path / "tmp")
        Path(env["TMP"]).mkdir(exist_ok=True)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_runtime_focused.py", "-q", "-p", "no:cacheprovider"],
            cwd=out_dir,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        assert result.returncode == 0, (result.stdout + "\n" + result.stderr)[-4000:]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
