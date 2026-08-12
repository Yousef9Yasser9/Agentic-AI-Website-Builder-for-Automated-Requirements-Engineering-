"""
Engine unit tests for the AI Website Builder.

These tests lock in the behavior of the builder's decision logic — the parts
that decide HOW an app is generated and recovered, independent of any LLM call.
They run fast, need no Ollama, no network, and no database.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (ROOT, os.path.join(ROOT, "builder")):
    if path not in sys.path:
        sys.path.insert(0, path)

import failure_classifier as fc  # noqa: E402
import data_model_guard as dmg  # noqa: E402
import architecture_guard as ag  # noqa: E402


def _maintenance_project(with_role_routes: bool = True):
    endpoints = [
        {"method": "GET", "path": "/api/v1/maintenance-requests", "desc": "list requests"},
        {"method": "GET", "path": "/api/v1/invoices", "desc": "list invoices"},
    ]
    if with_role_routes:
        endpoints += [
            {"method": "GET", "path": "/api/technicians", "desc": "list technicians"},
            {"method": "GET", "path": "/api/tenants", "desc": "list tenants"},
            {"method": "POST", "path": "/api/technicians", "desc": "create technician"},
        ]
    return {
        "cleaned_spec": {"cleaned_prompt": {"Roles": ["Tenant: renter", "Technician: fixer", "Admin: manager"]}},
        "architecture": {"roles": ["Tenant", "Technician", "Admin"], "endpoints": endpoints},
        "data_model": {
            "entities": [
                {"name": "User", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "role", "type": "string"}]},
                {"name": "MaintenanceRequest", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "assigned_technician_id", "type": "uuid"}]},
                {"name": "Invoice", "fields": [{"name": "id", "type": "uuid", "pk": True}]},
            ],
            "relationships": [],
        },
    }


def _store_project():
    return {
        "cleaned_spec": {"cleaned_prompt": {"Roles": ["Customer: buyer", "Admin: staff"]}},
        "architecture": {"roles": ["Customer", "Admin"], "endpoints": []},
        "data_model": {
            "entities": [
                {"name": "User", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "role", "type": "string"}]},
                {"name": "Customer", "fields": [{"name": "id", "type": "uuid", "pk": True}]},
                {"name": "Product", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "price", "type": "float"}]},
                {"name": "Order", "fields": [{"name": "id", "type": "uuid", "pk": True}, {"name": "customer_id", "type": "uuid"}]},
            ],
            "relationships": [{"from": "Order", "to": "Customer", "type": "many-to-one", "fk_field": "customer_id"}],
        },
    }


class TestFailureClassifier:
    def test_primary_key_error_routes_to_data_model(self):
        pd = _maintenance_project()
        result = fc.classify_failure(pd, "sqlalchemy could not assemble any primary key", total_cycles=2)
        assert result["category"] == "DATA_MODEL_GAP"
        assert result["suggested_stage_to_regenerate"] == "DATA_MODEL"

    def test_missing_table_error_routes_to_data_model(self):
        pd = _maintenance_project()
        out = "OperationalError: no such table: appointments\nno such column: foo"
        result = fc.classify_failure(pd, out, total_cycles=2)
        assert result["category"] == "DATA_MODEL_GAP"
        assert result["suggested_stage_to_regenerate"] == "DATA_MODEL"

    def test_role_endpoints_are_not_orphans(self):
        pd = _maintenance_project(with_role_routes=True)
        result = fc.classify_failure(pd, "runtime test failed: 404", total_cycles=2)
        assert result["suggested_stage_to_regenerate"] != "ARCHITECTURE"

    def test_convergence_guard_prevents_second_architecture_pass(self):
        pd = _maintenance_project(with_role_routes=True)
        pd["generation_options"] = {"_auto_recovery_chain": ["ARCHITECTURE"]}
        result = fc.classify_failure(pd, "runtime test failed", total_cycles=3)
        assert result["suggested_stage_to_regenerate"] != "ARCHITECTURE"

    def test_genuine_code_bug_does_not_trigger_upstream_recovery(self):
        pd = _maintenance_project(with_role_routes=False)
        result = fc.classify_failure(pd, "IndentationError in app/main.py line 42", total_cycles=1)
        assert result["category"] != "ARCHITECTURE_MISMATCH"

    def test_classifier_returns_required_keys(self):
        pd = _maintenance_project()
        result = fc.classify_failure(pd, "some failure", total_cycles=1)
        for key in ("category", "confidence", "reason", "suggested_stage_to_regenerate", "evidence"):
            assert key in result
        assert 0.0 <= result["confidence"] <= 1.0


class TestDataModelGuard:
    def test_redundant_customer_table_merged_into_user(self):
        out, actions = dmg.normalize_data_model(_store_project())
        names = [e["name"] for e in out["data_model"]["entities"]]
        assert "Customer" not in names
        assert "User" in names

    def test_order_fk_repointed_to_user(self):
        out, actions = dmg.normalize_data_model(_store_project())
        order = next(e for e in out["data_model"]["entities"] if e["name"] == "Order")
        field_names = {f["name"] for f in order["fields"]}
        assert "user_id" in field_names

    def test_product_gets_stock_field(self):
        out, actions = dmg.normalize_data_model(_store_project())
        product = next(e for e in out["data_model"]["entities"] if e["name"] == "Product")
        field_names = {f["name"].lower() for f in product["fields"]}
        assert any(n in field_names for n in ("stock_quantity", "stock", "quantity", "inventory"))

    def test_every_entity_keeps_a_primary_key(self):
        out, _ = dmg.normalize_data_model(_store_project())
        for entity in out["data_model"]["entities"]:
            assert any(f.get("pk") for f in entity["fields"])

    def test_normalize_is_nondestructive_to_input(self):
        pd = _store_project()
        original = len(pd["data_model"]["entities"])
        dmg.normalize_data_model(pd)
        assert len(pd["data_model"]["entities"]) == original

    def test_actions_are_human_readable_strings(self):
        _, actions = dmg.normalize_data_model(_store_project())
        assert isinstance(actions, list)
        assert all(isinstance(a, str) for a in actions)


class TestDomainDetection:
    def test_ecommerce_spec_detected(self):
        assert dmg._is_ecommerce_spec(_store_project()) is True

    def test_non_ecommerce_spec_not_flagged(self):
        assert dmg._is_ecommerce_spec(_maintenance_project()) is False

    def test_product_classified_as_catalog(self):
        out, _ = dmg.normalize_data_model(_store_project())
        assert dmg.entity_ui_kind("Product", out["data_model"]) == "catalog"

    def test_user_entity_hidden_from_generic_ui(self):
        assert dmg.should_expose_entity_in_ui("User") is False


class TestArchitectureGuard:
    def test_normalize_returns_dict_and_actions(self):
        out, actions = ag.normalize_architecture(_maintenance_project())
        assert isinstance(out, dict)
        assert isinstance(actions, list)

    def test_paths_have_leading_slash(self):
        pd = {
            "architecture": {
                "roles": ["Admin"],
                "pages": [{"name": "Dash", "path": "dashboard", "role_access": ["Admin"], "target_entity": None}],
                "endpoints": [{"method": "GET", "path": "api/v1/items", "role_access": ["Admin"]}],
            }
        }
        out, _ = ag.normalize_architecture(pd)
        for page in out["architecture"].get("pages", []):
            assert str(page.get("path", "/")).startswith("/")


class TestFrontendShellGuard:
    def test_deterministic_guard_repairs_placeholder_index_html(self):
        project_data = {
            "cleaned_spec": {"project_title": "Inventory Portal"},
            "architecture": {"roles": ["Customer", "Admin"], "pages": [], "endpoints": []},
            "requirements": {},
            "user_stories": {},
            "ui_selection": {},
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
                        "name": "Product",
                        "fields": [
                            {"name": "id", "type": "uuid", "pk": True},
                            {"name": "name", "type": "string"},
                            {"name": "price", "type": "float"},
                        ],
                    },
                ],
                "relationships": [],
            },
        }
        work_dir = Path(ROOT) / ".engine-test-workspace" / "frontend-index-contract"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        frontend_dir = work_dir / "frontend_templates"
        frontend_dir.mkdir(parents=True)
        (frontend_dir / "index.html").write_text(
            "<!doctype html><html><body>Basic placeholder</body></html>",
            encoding="utf-8",
        )

        from backend.app.services.builder_service import validate_before_serve
        from generated_apps.generator.deterministic_backend import apply_deterministic_guard
        from generated_apps.generator.repo_generator import (
            _default_public_role,
            _write_frontend_contract_page,
            _write_invariant_auth,
            _write_invariant_auth_router,
            _write_invariant_db,
            _write_invariant_deps,
        )

        try:
            written = apply_deterministic_guard(work_dir, project_data, theme={})
            _write_invariant_db(work_dir)
            _write_invariant_auth(work_dir)
            _write_invariant_deps(work_dir)
            _write_invariant_auth_router(work_dir, _default_public_role(project_data))
            _write_frontend_contract_page(work_dir, "frontend_templates/entity_list.html")
            _write_frontend_contract_page(work_dir, "frontend_templates/entity_form.html")
            (work_dir / "app" / "__init__.py").write_text('"""Generated app package."""\n', encoding="utf-8")
            (work_dir / "app" / "routers" / "__init__.py").write_text('"""Generated route package."""\n', encoding="utf-8")
            (work_dir / "requirements.txt").write_text("fastapi\nsqlalchemy\n", encoding="utf-8")
            (work_dir / ".env.example").write_text("DATABASE_URL=sqlite:///./app.db\n", encoding="utf-8")

            index_html = (frontend_dir / "index.html").read_text(encoding="utf-8")
            assert "frontend_templates/index.html" in written
            assert "access_token" in index_html
            assert "apiFetch" in index_html
            assert "/api/dashboard/stats" in index_html
            assert validate_before_serve(str(work_dir)) == []
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


class TestEndpointReconciler:
    @pytest.mark.skipif(
        not hasattr(dmg, "_reconcile_architecture_endpoints"),
        reason="Layer-3 reconciler not applied yet",
    )
    def test_reconciler_keeps_entities_repoints_roles_skips_unknown(self):
        pd = {
            "architecture": {
                "roles": ["Mechanic", "Customer", "Admin"],
                "endpoints": [
                    {"method": "GET", "path": "/api/v1/service-types"},
                    {"method": "GET", "path": "/api/mechanics"},
                    {"method": "GET", "path": "/api/widgets"},
                ],
            }
        }
        roles = {"mechanic", "customer", "admin"}
        entities = {"User", "Vehicle", "ServiceType", "Appointment", "Invoice"}
        dmg._reconcile_architecture_endpoints(pd, roles, entities)
        paths = [e["path"] for e in pd["architecture"]["endpoints"]]
        assert "/api/v1/service-types" in paths
        assert "/api/users" in paths
        assert "/api/widgets" in paths


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
