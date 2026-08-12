from __future__ import annotations

import json
from pathlib import Path

from builder.app_contract import build_app_contract
from builder.data_model_guard import normalize_data_model


def _user_entity():
    return {
        "name": "User",
        "fields": [
            {"name": "id", "type": "uuid", "pk": True},
            {"name": "email", "type": "string"},
            {"name": "password_hash", "type": "string"},
            {"name": "role", "type": "string"},
        ],
    }


def _entity(contract, name):
    return next(entity for entity in contract.business_entities() if entity.raw_name == name)


def _capabilities(contract, role):
    role_key = role.lower()
    caps = set()
    for entity in contract.business_entities():
        if any(r.lower() == role_key for r in entity.read_roles):
            caps.add((entity.raw_name, "read"))
        if any(r.lower() == role_key for r in entity.write_roles):
            caps.add((entity.raw_name, "write"))
    return caps


def _normalized_contract(project_data):
    normalized, _actions = normalize_data_model(project_data)
    return build_app_contract(normalized), normalized


def task_manager_project():
    fixture = Path("generated_apps/projects/9673a4aa/v1/_builder_artifacts/project_data.json")
    if fixture.exists():
        return json.loads(fixture.read_text(encoding="utf-8"))
    return {
        "plain_text": "Build a simple task manager. Roles: User, Admin. Users create and manage their own tasks. Admin manages everything.",
        "cleaned_spec": {
            "project_title": "Simple Task Manager",
            "cleaned_prompt": {
                "Roles": ["User: Create and manage own tasks.", "Admin: Manage all tasks."],
            },
        },
        "architecture": {"roles": ["User", "Admin"]},
        "data_model": {
            "entities": [
                _user_entity(),
                {
                    "name": "Task",
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True},
                        {"name": "title", "type": "string"},
                        {"name": "status", "type": "string"},
                    ],
                },
            ],
            "relationships": [],
        },
    }


def hotel_project():
    return {
        "plain_text": "Build a hotel system. Roles: Guest, Receptionist, Admin. Guests create reservations for their own stays. Receptionists create and manage bookings. Guests browse rooms. Admin manages everything.",
        "cleaned_spec": {
            "project_title": "Hotel Booking",
            "cleaned_prompt": {
                "Roles": [
                    "Guest: Create their own reservations and browse rooms.",
                    "Receptionist: Manage bookings.",
                    "Admin: Manage everything.",
                ],
            },
        },
        "requirements": {
            "functional_requirements": [
                {"actor": "Guest", "shall": "The system shall allow Guest to create Reservation."},
                {"actor": "Receptionist", "shall": "The system shall allow Receptionist to write Bookings."},
            ]
        },
        "architecture": {"roles": ["Guest", "Receptionist", "Admin"]},
        "data_model": {
            "entities": [
                _user_entity(),
                {"name": "Room", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "number", "type": "string"}]},
                {"name": "Reservation", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "room_id", "type": "uuid"}]},
                {"name": "Booking", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "status", "type": "string"}]},
            ],
            "relationships": [],
        },
    }


def library_project():
    return {
        "plain_text": "Build a library system. Roles: Member, Librarian, Admin. Members borrow books by creating loans for their own account. Librarians add and manage books. Admin manages everything.",
        "cleaned_spec": {
            "project_title": "Library",
            "cleaned_prompt": {
                "Roles": [
                    "Member: Borrow books and view their own loans.",
                    "Librarian: Add and manage books.",
                    "Admin: Manage everything.",
                ],
            },
        },
        "requirements": {
            "functional_requirements": [
                {"actor": "Member", "shall": "The system shall allow Member to borrow Book by creating Loan."},
                {"actor": "Librarian", "shall": "The system shall allow Librarian to manage Books."},
            ]
        },
        "user_stories": {
            "stories": [
                {"role": "Member", "story": "As a Member I want to borrow a book so that I can create a loan."},
                {"role": "Librarian", "story": "As a Librarian I want to add books so that I can manage the catalog."},
            ]
        },
        "architecture": {"roles": ["Member", "Librarian", "Admin"]},
        "data_model": {
            "entities": [
                _user_entity(),
                {"name": "Book", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "title", "type": "string"}]},
                {"name": "Loan", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "book_id", "type": "uuid"}]},
            ],
            "relationships": [],
        },
    }


def test_task_user_can_write_and_owns_tasks():
    contract, normalized = _normalized_contract(task_manager_project())
    task = _entity(contract, "Task")
    fields = {field["name"] for field in task.fields}

    assert "User" in task.write_roles
    assert "user_id" in fields
    assert task.scope_fields == ["user_id"]
    assert any(
        rel.get("from") == "Task" and rel.get("to") == "User" and rel.get("fk_field") == "user_id"
        for rel in normalized["data_model"]["relationships"]
    )


def test_hotel_guest_and_receptionist_primary_writes_are_preserved():
    contract, _normalized = _normalized_contract(hotel_project())

    assert "Guest" in _entity(contract, "Reservation").write_roles
    assert "Receptionist" in _entity(contract, "Booking").write_roles
    assert "Guest" not in _entity(contract, "Room").write_roles
    assert "user_id" in {field["name"] for field in _entity(contract, "Reservation").fields}


def test_library_member_borrows_loan_but_does_not_manage_book_catalog():
    contract, _normalized = _normalized_contract(library_project())

    assert "Member" in _entity(contract, "Loan").write_roles
    assert "Librarian" in _entity(contract, "Book").write_roles
    assert "Member" not in _entity(contract, "Book").write_roles
    assert "user_id" in {field["name"] for field in _entity(contract, "Loan").fields}
    assert _capabilities(contract, "Member") != _capabilities(contract, "Librarian")
    assert _capabilities(contract, "Member")
    assert _capabilities(contract, "Librarian")
