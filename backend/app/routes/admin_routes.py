from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.auth.database import get_db
from backend.app.auth.deps import require_admin
from backend.app.auth.models import User
from backend.app.auth.schemas import AdminStatsResponse, AdminUserUpdate, UserPublic
from backend.app.auth.service import user_to_public
from backend.app.services import builder_service as service

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _handle(call):
    try:
        return call()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stats", response_model=AdminStatsResponse)
def admin_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del admin
    users = db.query(User).all()
    projects = service.list_all_project_summaries()
    generated = [p for p in projects if (p.get("project_data") or {}).get("repo_path")]
    running = sum(1 for p in generated if service.is_server_running(p["project_id"]))
    ollama = service.ollama_status()
    warnings: list[str] = []
    if not ollama.get("online"):
        warnings.append("Ollama is offline")
    if ollama.get("ram_warning"):
        warnings.append("High RAM usage detected")

    recent_users = (
        db.query(User).order_by(desc(User.created_at)).limit(5).all()
    )
    return AdminStatsResponse(
        total_users=len(users),
        verified_users=sum(1 for u in users if u.is_verified),
        disabled_users=sum(1 for u in users if not u.is_active),
        total_projects=len(projects),
        total_generated_apps=len(generated),
        active_running_apps=running,
        ollama_online=bool(ollama.get("online")),
        recent_users=[user_to_public(u) for u in recent_users],
        recent_projects=projects[:5],
        system_warnings=warnings,
    )


@router.get("/users", response_model=list[UserPublic])
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    del admin
    users = db.query(User).order_by(desc(User.created_at)).all()
    return [user_to_public(u) for u in users]


@router.patch("/users/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        if payload.role is not None and payload.role != admin.role:
            raise HTTPException(status_code=400, detail="You cannot change your own role.")
        if payload.is_active is False:
            raise HTTPException(status_code=400, detail="You cannot disable your own account.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user_to_public(user)


@router.get("/projects")
def admin_projects(admin: User = Depends(require_admin)):
    del admin
    return _handle(service.list_all_project_summaries_enriched)


@router.get("/generated-apps")
def admin_generated_apps(admin: User = Depends(require_admin)):
    del admin
    return _handle(service.list_generated_apps_admin)


@router.get("/system/health")
def admin_system_health(admin: User = Depends(require_admin)):
    del admin
    return _handle(service.get_system_health)


@router.get("/logs")
def admin_logs(admin: User = Depends(require_admin)):
    del admin
    return _handle(service.get_all_logs)


@router.post("/models/test")
def test_model_connection(admin: User = Depends(require_admin)):
    del admin
    return _handle(service.ollama_status)
