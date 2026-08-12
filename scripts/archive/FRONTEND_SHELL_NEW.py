# This contains the COMPLETE NEW _write_frontend_shell function
# Copy this and replace the old function in repo_generator.py

def _write_frontend_shell(out_dir: Path, project_data: dict, theme: dict) -> None:
    """Generate modern, role-aware, production-ready frontend shell"""
    arch = project_data.get("architecture", {}) or {}
    dm = project_data.get("data_model", {}) or {}
    title = (project_data.get("cleaned_spec", {}) or {}).get("project_title") or "Generated App"
    
    # Build entities list
    entities = []
    for entity in dm.get("entities") or []:
        if str(entity.get("name", "")).lower() == "user":
            continue
        cls = _entity_class_name(entity.get("name", "Record"))
        entities.append({
            "name": cls,
            "resource": _resource_name(entity.get("name", "record")),
            "label": re.sub(r"(?<!^)(?=[A-Z])", " ", cls),
            "fields": [f for f in entity.get("fields", []) if f.get("name") not in {"id", "created_at", "updated_at"}],
        })

    # Build navigation with role metadata
    nav = [
        {"label": "🏠 Dashboard", "path": "/", "role": "any", "entity": "", "mode": "dashboard"}
    ]
    
    # Add entity management (admin/all users)
    for entity in entities:
        nav.append({
            "label": f"📋 {entity['label']}s",
            "path": f"/ui/{entity['resource']}",
            "role": "any",  # All logged-in users can access
            "entity": entity["name"],
            "mode": "list"
        })
    
    # Add admin section
    nav.append({
        "label": "⚙️ Admin Panel",
        "path": "/admin/dashboard",
        "role": "admin",
        "entity": "",
        "mode": "dashboard"
    })

    payload = {
        "title": title,
        "theme": theme,
        "entities": entities,
        "nav": nav,
    }
