from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from backend.app.auth.deps import get_current_user
from backend.app.auth.models import User
from backend.app.schemas.project_schema import PlainTextRequest, ProjectCreate, ProjectSave, StageUpdate
from backend.app.services import builder_service as service

router = APIRouter(prefix="/api/projects", tags=["projects"])


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


def _is_admin(user: User) -> bool:
    return user.role == "admin"


@router.get("")
def list_projects(current_user: User = Depends(get_current_user)):
    return service.list_project_summaries(
        user_id=current_user.id,
        is_admin=_is_admin(current_user),
    )


@router.post("")
def create_project(payload: ProjectCreate, current_user: User = Depends(get_current_user)):
    return _handle(lambda: service.create_project(payload.plain_text, user_id=current_user.id))


@router.get("/{project_id}")
def get_project(project_id: str, current_user: User = Depends(get_current_user)):
    return _handle(
        lambda: service.get_project(project_id, user_id=current_user.id, is_admin=_is_admin(current_user))
    )


@router.delete("/{project_id}")
def delete_project(project_id: str, current_user: User = Depends(get_current_user)):
    return _handle(
        lambda: (
            service.assert_project_access(project_id, current_user.id, _is_admin(current_user)),
            service.delete_project(project_id),
        )[1]
    )


@router.post("/{project_id}/load")
def load_project(project_id: str, current_user: User = Depends(get_current_user)):
    return _handle(
        lambda: service.get_project(project_id, user_id=current_user.id, is_admin=_is_admin(current_user))
    )


@router.post("/{project_id}/save")
def save_project(project_id: str, payload: ProjectSave, current_user: User = Depends(get_current_user)):
    def _save():
        service.assert_project_access(project_id, current_user.id, _is_admin(current_user))
        return service.save_project(project_id, payload.project_data, payload.stage)

    return _handle(_save)


@router.get("/{project_id}/state")
def get_state(project_id: str, current_user: User = Depends(get_current_user)):
    return _handle(
        lambda: service.get_project(project_id, user_id=current_user.id, is_admin=_is_admin(current_user))
    )


@router.post("/{project_id}/stage")
def update_stage(project_id: str, payload: StageUpdate, current_user: User = Depends(get_current_user)):
    def _update():
        service.assert_project_access(project_id, current_user.id, _is_admin(current_user))
        return service.update_stage(project_id, payload.stage)

    return _handle(_update)


@router.post("/{project_id}/plain-text")
def update_plain_text(project_id: str, payload: PlainTextRequest, current_user: User = Depends(get_current_user)):
    def _update():
        service.assert_project_access(project_id, current_user.id, _is_admin(current_user))
        return service.update_plain_text(project_id, payload.plain_text)

    return _handle(_update)


@router.get("/{project_id}/artifact/{artifact_name}")
def download_artifact(project_id: str, artifact_name: str, current_user: User = Depends(get_current_user)):
    def _path():
        service.assert_project_access(project_id, current_user.id, _is_admin(current_user))
        return service.artifact_path(project_id, artifact_name)

    path = _handle(_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return FileResponse(path)
