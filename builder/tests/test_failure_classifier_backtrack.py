from __future__ import annotations

from builder.failure_classifier import classify_failure


def _project_data() -> dict:
    return {
        "plain_text": "Customers can view their own orders and bookings.",
        "cleaned_spec": {
            "cleaned_prompt": {
                "Roles": ["Admin: manage everything", "Customer: view their own orders"],
            }
        },
        "architecture": {"roles": ["Admin", "Customer"]},
        "requirements": {
            "functional_requirements": [
                {"actor": "Customer", "shall": "view only their own orders"},
            ]
        },
        "data_model": {
            "entities": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True},
                        {"name": "email", "type": "string"},
                        {"name": "role", "type": "string"},
                    ],
                },
                {
                    "name": "Order",
                    "fields": [
                        {"name": "id", "type": "uuid", "pk": True},
                        {"name": "date", "type": "string"},
                        {"name": "type", "type": "string"},
                    ],
                },
            ],
            "relationships": [],
        },
    }


def test_pydantic_reserved_field_error_backtracks_to_data_model():
    output = """
    pydantic.errors.PydanticUserError: Field name "date" shadows an attribute in parent "BaseModel";
    use a different field name with an alias.
    """

    diagnosis = classify_failure(_project_data(), output, total_cycles=1)

    assert diagnosis["category"] == "DATA_MODEL_GAP"
    assert diagnosis["suggested_stage_to_regenerate"] == "DATA_MODEL"
    assert diagnosis["fix_hint"] == "rename or alias reserved field"
    assert diagnosis["deterministic_fixes"][0]["kind"] == "reserved_field_alias"


def test_ownership_scope_failure_backtracks_to_data_model():
    output = """
    FAILED tests/test_runtime_focused.py::test_database_customer_lists_are_ownership_scoped
    AssertionError: Customer can see another user's orders row; entity is not ownership scoped.
    """

    diagnosis = classify_failure(_project_data(), output, total_cycles=3)

    assert diagnosis["category"] == "DATA_MODEL_GAP"
    assert diagnosis["suggested_stage_to_regenerate"] == "DATA_MODEL"
    assert diagnosis["fix_hint"] == "add owner/user/customer scope field"
    assert diagnosis["deterministic_fixes"][0]["kind"] == "missing_scope_field"


def test_plain_assertion_remains_code_bug():
    output = """
    FAILED tests/test_runtime_focused.py::test_dashboard_stats_no_errors
    AssertionError: expected 200, got 500
    """

    diagnosis = classify_failure(_project_data(), output, total_cycles=1)

    assert diagnosis["category"] == "CODE_BUG"
    assert diagnosis["suggested_stage_to_regenerate"] is None


def test_missing_fk_target_backtracks_to_data_model():
    project_data = _project_data()
    project_data["data_model"]["entities"][1]["fields"].append(
        {"name": "restaurant_id", "type": "uuid"}
    )
    project_data["data_model"]["relationships"] = [
        {"from": "Order", "to": "Restaurant", "fk_field": "restaurant_id"}
    ]
    output = """
    sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column
    'orders.restaurant_id' could not find table 'restaurants'
    """

    diagnosis = classify_failure(project_data, output, total_cycles=1)

    assert diagnosis["category"] == "DATA_MODEL_GAP"
    assert diagnosis["suggested_stage_to_regenerate"] == "DATA_MODEL"
    assert diagnosis["deterministic_fixes"][0]["kind"] == "missing_fk_target"
