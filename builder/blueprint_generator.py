"""
blueprint_generator.py
======================
Generates a custom project blueprint and file manifest before code generation.
This ensures every generated web app is unique and tailored to the specific requirements.
"""

import json
from typing import Any, Dict, List, Optional


def generate_project_blueprint(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a comprehensive project blueprint based on planning artifacts.
    
    Args:
        project_data: Complete project data including cleaned_spec, requirements,
                     user_stories, architecture, data_model, ui_selection
    
    Returns:
        Blueprint dictionary containing technology stack, folder structure,
        pages, routes, database schema, and test plan
    """
    cleaned_spec = project_data.get("cleaned_spec", {}) or {}
    requirements = project_data.get("requirements", {}) or {}
    user_stories = project_data.get("user_stories", {}) or {}
    architecture = project_data.get("architecture", {}) or {}
    data_model = project_data.get("data_model", {}) or {}
    ui_selection = project_data.get("ui_selection", {}) or {}
    
    project_title = cleaned_spec.get("project_title", "Generated Web App")
    
    # Extract technology stack from architecture
    stack_info = architecture.get("stack", {}) or {}
    backend = stack_info.get("backend", "FastAPI")
    database = stack_info.get("db", "SQLite")
    orm = stack_info.get("orm", "SQLAlchemy")
    auth = stack_info.get("auth", "JWT")
    frontend = stack_info.get("frontend", "Plain HTML+CSS+JavaScript")
    
    # Determine UI framework from selection
    ui_framework = ui_selection.get("framework", "Bootstrap")
    ui_layout = ui_selection.get("layout", "topnav")
    
    # Extract roles
    roles = architecture.get("roles", ["User", "Admin"])
    
    # Extract pages
    pages = architecture.get("pages", [])
    
    # Extract API endpoints
    endpoints = architecture.get("endpoints", [])
    
    # Extract entities
    entities = data_model.get("entities", [])
    relationships = data_model.get("relationships", [])
    
    # Build folder structure
    folder_structure = _generate_folder_structure(backend, frontend)
    
    # Build main pages list
    main_pages = _extract_main_pages(pages)
    
    # Build backend routes
    backend_routes = _extract_backend_routes(endpoints, entities)
    
    # Build database tables
    database_tables = _extract_database_tables(entities, relationships)
    
    # Build models/entities
    models_entities = _extract_models(entities)
    
    # Build forms and validation
    forms_validation = _extract_forms(entities, pages)
    
    # Build frontend/UI structure
    frontend_structure = _extract_frontend_structure(pages, ui_layout, ui_framework)
    
    # Build test plan
    test_plan = _generate_test_plan(requirements, user_stories, entities, endpoints)
    
    # Build run commands
    run_commands = _generate_run_commands(backend, database)
    
    blueprint = {
        "project_title": project_title,
        "technology_stack": {
            "backend": backend,
            "database": database,
            "orm": orm,
            "auth": auth,
            "frontend": frontend,
            "ui_framework": ui_framework,
            "ui_layout": ui_layout
        },
        "roles": roles,
        "folder_structure": folder_structure,
        "main_pages": main_pages,
        "backend_routes": backend_routes,
        "database_tables": database_tables,
        "models_entities": models_entities,
        "forms_validation": forms_validation,
        "frontend_structure": frontend_structure,
        "test_plan": test_plan,
        "run_commands": run_commands
    }
    
    return blueprint


def generate_file_manifest(
    project_data: Dict[str, Any],
    blueprint: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a file manifest listing all files to be created.
    
    Args:
        project_data: Complete project data
        blueprint: Project blueprint from generate_project_blueprint
    
    Returns:
        File manifest as valid JSON
    """
    cleaned_spec = project_data.get("cleaned_spec", {}) or {}
    project_title = cleaned_spec.get("project_title", "Generated Web App")
    
    # Determine project name slug
    import re
    project_slug = re.sub(r'[^a-z0-9]+', '_', project_title.lower()).strip('_')
    
    stack = blueprint.get("technology_stack", {})
    backend = stack.get("backend", "FastAPI")
    database = stack.get("database", "SQLite")
    ui_framework = stack.get("ui_framework", "Bootstrap")
    
    stack_description = f"{backend} + {database} + {ui_framework}"
    
    # Build file list
    files = []
    
    # Backend files
    files.append({
        "path": "app/__init__.py",
        "purpose": "Python package marker for app module"
    })
    files.append({
        "path": "app/main.py",
        "purpose": "Main FastAPI application entry point with routes"
    })
    files.append({
        "path": "app/models.py",
        "purpose": "SQLAlchemy database models"
    })
    files.append({
        "path": "app/schemas.py",
        "purpose": "Pydantic schemas for request/response validation"
    })
    files.append({
        "path": "app/db.py",
        "purpose": "Database connection and session management"
    })
    files.append({
        "path": "app/auth.py",
        "purpose": "Authentication utilities (JWT, password hashing)"
    })
    files.append({
        "path": "app/deps.py",
        "purpose": "FastAPI dependencies (auth, role checks)"
    })
    
    # Router files
    files.append({
        "path": "app/routers/__init__.py",
        "purpose": "Python package marker for routers module"
    })
    files.append({
        "path": "app/routers/auth.py",
        "purpose": "Authentication routes (login, register, me)"
    })
    files.append({
        "path": "app/routers/generic_crud.py",
        "purpose": "Generic CRUD operations for all entities"
    })
    
    # Plain frontend source files
    entities = blueprint.get("models_entities", [])
    pages = blueprint.get("main_pages", [])
    
    files.append({
        "path": "frontend_templates/app.html",
        "purpose": "Main application dashboard and navigation"
    })
    files.append({
        "path": "frontend_templates/login.html",
        "purpose": "User login page"
    })
    files.append({
        "path": "frontend_templates/register.html",
        "purpose": "User registration page"
    })
    files.append({
        "path": "frontend_templates/entity_list.html",
        "purpose": "Generic entity list/table view"
    })
    files.append({
        "path": "frontend_templates/entity_form.html",
        "purpose": "Generic entity create/edit form"
    })
    
    # Configuration files
    files.append({
        "path": "requirements.txt",
        "purpose": "Python dependencies"
    })
    files.append({
        "path": ".env.example",
        "purpose": "Environment variables template"
    })
    files.append({
        "path": ".env",
        "purpose": "Environment variables (auto-generated from .env.example)"
    })
    
    # Database seeding
    files.append({
        "path": "seed.py",
        "purpose": "Database seeding script with sample data"
    })
    
    # Testing
    files.append({
        "path": "tests/__init__.py",
        "purpose": "Python package marker for tests module"
    })
    files.append({
        "path": "tests/test_app.py",
        "purpose": "TDD test suite for the application"
    })
    
    # Documentation
    files.append({
        "path": "README.md",
        "purpose": "Project documentation and run instructions"
    })
    
    # Optional files
    files.append({
        "path": "alembic.ini",
        "purpose": "Alembic database migration configuration (optional)"
    })
    files.append({
        "path": "docker-compose.yml",
        "purpose": "Docker compose configuration (optional)"
    })
    
    # Artifacts
    files.append({
        "path": "_builder_artifacts/project_data.json",
        "purpose": "Complete project planning data for traceability"
    })
    files.append({
        "path": "_builder_artifacts/blueprint.json",
        "purpose": "Project blueprint used for generation"
    })
    files.append({
        "path": "_builder_artifacts/manifest.json",
        "purpose": "This file manifest"
    })
    
    manifest = {
        "project_name": project_slug,
        "project_title": project_title,
        "stack": stack_description,
        "description": cleaned_spec.get("cleaned_prompt", {}).get("Goal", "Auto-generated web application"),
        "total_files": len(files),
        "files": files
    }
    
    return manifest


# Helper functions

def _generate_folder_structure(backend: str, frontend: str) -> List[str]:
    """Generate folder structure based on stack."""
    folders = [
        "app/",
        "app/routers/",
        "frontend_templates/",
        "tests/",
        "_builder_artifacts/"
    ]
    
    if backend == "FastAPI":
        folders.extend([
            "alembic/",
            "alembic/versions/"
        ])
    
    return sorted(folders)


def _extract_main_pages(pages: List[Dict]) -> List[Dict]:
    """Extract main pages from architecture."""
    main_pages = []
    for page in pages:
        main_pages.append({
            "name": page.get("name", "Unknown"),
            "path": page.get("path", "/"),
            "roles": page.get("role_access", []),
            "description": page.get("desc", "")
        })
    return main_pages


def _extract_backend_routes(endpoints: List[Dict], entities: List[Dict]) -> List[Dict]:
    """Extract backend API routes."""
    routes = []
    
    # Add auth routes
    routes.extend([
        {"method": "POST", "path": "/api/auth/register", "purpose": "User registration"},
        {"method": "POST", "path": "/api/auth/login", "purpose": "User login"},
        {"method": "GET", "path": "/api/auth/me", "purpose": "Get current user"}
    ])
    
    # Add CRUD routes for each entity
    for entity in entities:
        entity_name = entity.get("name", "Entity")
        resource = entity_name.lower().replace(" ", "_") + "s"
        
        routes.extend([
            {"method": "GET", "path": f"/api/{resource}", "purpose": f"List all {entity_name}"},
            {"method": "POST", "path": f"/api/{resource}", "purpose": f"Create {entity_name}"},
            {"method": "GET", "path": f"/api/{resource}/{{id}}", "purpose": f"Get {entity_name} by ID"},
            {"method": "PUT", "path": f"/api/{resource}/{{id}}", "purpose": f"Update {entity_name}"},
            {"method": "DELETE", "path": f"/api/{resource}/{{id}}", "purpose": f"Delete {entity_name}"}
        ])
    
    # Add custom endpoints from architecture
    for endpoint in endpoints:
        routes.append({
            "method": endpoint.get("method", "GET"),
            "path": endpoint.get("path", "/"),
            "purpose": endpoint.get("desc", "")
        })
    
    return routes


def _extract_database_tables(entities: List[Dict], relationships: List[Dict]) -> List[Dict]:
    """Extract database table definitions."""
    tables = []
    
    for entity in entities:
        entity_name = entity.get("name", "Entity")
        table_name = entity_name.lower().replace(" ", "_") + "s"
        
        fields = entity.get("fields", [])
        field_list = []
        
        for field in fields:
            is_pk = bool(field.get("pk") or field.get("primary_key") or field.get("name") == "id")
            field_list.append({
                "name": field.get("name", "field"),
                "type": field.get("type", "string"),
                "nullable": False if is_pk else field.get("nullable", True),
                "unique": field.get("unique", False),
                "primary_key": is_pk
            })
        
        tables.append({
            "entity": entity_name,
            "table_name": table_name,
            "fields": field_list
        })
    
    return tables


def _extract_models(entities: List[Dict]) -> List[str]:
    """Extract model/entity names."""
    return [entity.get("name", "Entity") for entity in entities]


def _extract_forms(entities: List[Dict], pages: List[Dict]) -> List[Dict]:
    """Extract forms and validation requirements."""
    forms = []
    
    # Registration form
    forms.append({
        "name": "RegistrationForm",
        "fields": ["email", "password", "full_name"],
        "validation": ["email format", "password min 6 chars"]
    })
    
    # Login form
    forms.append({
        "name": "LoginForm",
        "fields": ["email", "password"],
        "validation": ["email format", "required fields"]
    })
    
    # Entity forms
    for entity in entities:
        if entity.get("name") != "User":
            entity_name = entity.get("name", "Entity")
            fields = [f.get("name") for f in entity.get("fields", []) 
                     if not f.get("pk") and f.get("name") not in ["created_at", "updated_at"]]
            
            forms.append({
                "name": f"{entity_name}Form",
                "fields": fields,
                "validation": ["required fields", "type validation"]
            })
    
    return forms


def _extract_frontend_structure(pages: List[Dict], layout: str, framework: str) -> Dict:
    """Extract frontend structure."""
    return {
        "layout_type": layout,
        "ui_framework": framework,
        "pages": [p.get("name") for p in pages],
        "components": [
            "Navigation",
            "Sidebar" if layout == "sidebar" else "TopNav",
            "DataTable",
            "Form",
            "Modal",
            "Flash Messages"
        ]
    }


def _generate_test_plan(
    requirements: Dict,
    user_stories: Dict,
    entities: List[Dict],
    endpoints: List[Dict]
) -> Dict:
    """Generate test plan based on requirements and user stories."""
    test_categories = []
    
    # Health check tests
    test_categories.append({
        "category": "Health & Smoke Tests",
        "tests": [
            "test_health_endpoint",
            "test_app_starts_successfully"
        ]
    })
    
    # Authentication tests
    test_categories.append({
        "category": "Authentication Tests",
        "tests": [
            "test_user_registration",
            "test_user_login",
            "test_protected_route_requires_auth",
            "test_invalid_credentials_rejected"
        ]
    })
    
    # CRUD tests for entities
    for entity in entities:
        if entity.get("name") != "User":
            entity_name = entity.get("name", "Entity")
            test_categories.append({
                "category": f"{entity_name} CRUD Tests",
                "tests": [
                    f"test_list_{entity_name.lower()}",
                    f"test_create_{entity_name.lower()}",
                    f"test_get_{entity_name.lower()}",
                    f"test_update_{entity_name.lower()}",
                    f"test_delete_{entity_name.lower()}_requires_admin"
                ]
            })
    
    # User story tests
    stories = user_stories.get("stories", [])
    if stories:
        story_tests = []
        for story in stories[:5]:  # Limit to first 5 stories
            story_id = story.get("id", "US1")
            story_tests.append(f"test_user_story_{story_id.lower()}")
        
        test_categories.append({
            "category": "User Story Tests",
            "tests": story_tests
        })
    
    return {
        "test_framework": "pytest",
        "test_categories": test_categories,
        "total_estimated_tests": sum(len(cat["tests"]) for cat in test_categories)
    }


def _generate_run_commands(backend: str, database: str) -> Dict:
    """Generate run commands for the project."""
    commands = {
        "setup": [
            "python -m venv .venv",
            ".venv\\Scripts\\activate" if backend == "FastAPI" else "source .venv/bin/activate",
            "pip install -r requirements.txt",
            "copy .env.example .env"
        ],
        "seed_database": [
            "python seed.py"
        ],
        "run_development": [
            "uvicorn app.main:app --reload --port 8000"
        ],
        "run_tests": [
            "pytest tests/ -v"
        ],
        "run_production": [
            "uvicorn app.main:app --host 0.0.0.0 --port 8000"
        ]
    }
    
    return commands
