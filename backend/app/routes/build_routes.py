from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.auth.deps import get_current_user
from backend.app.auth.models import User
from backend.app.routes.helpers import route_handle, with_project_access
from backend.app.services import builder_service as service

router = APIRouter(prefix="/api/projects/{project_id}", tags=["build-preview"])


@router.post("/build")
def build_project(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.build_generated_app(project_id)))


@router.post("/start-server")
def start_server(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.start_server(project_id)))


@router.post("/stop-server")
def stop_server(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.stop_server(project_id)))


@router.get("/server-status")
def server_status(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.server_status(project_id)))
