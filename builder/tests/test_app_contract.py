from __future__ import annotations

import importlib

import pytest

from builder.app_contract import build_app_contract, field_type_map, resource_path


def _user_entity():
    return {
        "name": "User",
        "fields": [
            {"name": "id", "type": "uuid", "pk": True},
            {"name": "email", "type": "string"},
            {"name": "role", "type": "string"},
        ],
    }


def event_ticketing_project():
    return {
        "cleaned_spec": {"project_title": "Event Ticketing"},
        "architecture": {"roles": ["Admin", "Attendee"]},
        "data_model": {
            "entities": [
                _user_entity(),
                {
                    "name": "Event",
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True},
                        {"name": "title", "type": "string"},
                        {"name": "date", "type": "date"},
                    ],
                },
                {
                    "name": "Ticket",
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True},
                        {"name": "event_id", "type": "uuid"},
                        {"name": "user_id", "type": "uuid"},
                    ],
                },
            ],
            "relationships": [],
        },
    }


def food_delivery_project():
    return {
        "cleaned_spec": {"project_title": "Food Delivery"},
        "architecture": {"roles": ["Customer", "Admin"]},
        "requirements": {
            "functional_requirements": [
                {"actor": "Customer", "shall": "browse menu items and create orders"}
            ]
        },
        "data_model": {
            "entities": [
                _user_entity(),
                {"name": "Customer", "fields": [{"name": "id", "type": "uuid", "pk": True}]},
                {
                    "name": "Menu Item",
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True},
                        {"name": "name", "type": "string"},
                        {"name": "price", "type": "decimal"},
                    ],
                },
                {
                    "name": "Order",
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True},
                        {"name": "customer_id", "type": "uuid"},
                    ],
                },
            ],
            "relationships": [],
        },
    }


def clinic_project():
    return {
        "cleaned_spec": {"project_title": "Clinic Booking"},
        "architecture": {"roles": ["Patient", "Doctor", "Admin"]},
        "user_stories": {
            "stories": [
                {"role": "Patient", "story": "As a Patient I can view my appointments"},
                {"role": "Doctor", "story": "As a Doctor I can manage appointments"},
            ]
        },
        "data_model": {
            "entities": [
                _user_entity(),
                {"name": "Patient", "fields": [{"name": "id", "type": "uuid", "pk": True}]},
                {
                    "name": "Appointment",
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True},
                        {"name": "patient_id", "type": "uuid"},
                        {"name": "date", "type": "date"},
                    ],
                },
            ],
            "relationships": [],
        },
    }


@pytest.mark.parametrize(
    "project_factory",
    [event_ticketing_project, food_delivery_project, clinic_project],
)
def test_contract_core_invariants(project_factory):
    contract = build_app_contract(project_factory())
    resources = [entity.resource for entity in contract.business_entities()]

    assert contract.api_prefix == "/api"
    assert all("/v1" not in path for path in contract.api_paths())
    assert all(resources)
    assert len(resources) == len(set(resources))
    assert contract.public_role.lower() != "admin"
    assert contract.demo_accounts[contract.public_role]["email"]
    assert contract.demo_accounts[contract.public_role]["password"]


def test_business_entities_exclude_user_but_keep_profile_and_spaced_entities():
    contract = build_app_contract(food_delivery_project())
    business_names = [entity.raw_name for entity in contract.business_entities()]

    assert "User" not in business_names
    assert "Customer" in business_names
    assert "Menu Item" in business_names
    assert any(entity.is_user_entity for entity in contract.entities)
    assert "/api/menu_items" in contract.api_paths()
    assert "/ui/customers" in contract.ui_paths()
    assert resource_path("Menu Item") == "menu_items"


def test_date_field_uses_alias_types_not_bare_date_name():
    mapped = field_type_map({"name": "date", "type": "date"})
    inferred = field_type_map({"name": "date"})

    assert mapped["python"] == "Date"
    assert mapped["pydantic"] == "Date"
    assert mapped["sqlalchemy"] == "Date"
    assert inferred["python"] in {"Date", "DateTime"}
    assert inferred["python"] is not None


def test_imports_cleanly_next_to_builder_and_generator_packages():
    builder_contract = importlib.import_module("builder.app_contract")
    generator_rules = importlib.import_module("generated_apps.generator.engine_rules")

    assert builder_contract.build_app_contract is build_app_contract
    assert hasattr(generator_rules, "infer_entity_access")
