from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.auth.deps import get_current_user
from backend.app.auth.models import User
from backend.app.routes.helpers import route_handle, with_project_access
from backend.app.schemas.project_schema import CodeGenerationRequest, RegenerateStageRequest
from backend.app.services import builder_service as service

router = APIRouter(prefix="/api/projects/{project_id}", tags=["generation"])


@router.post("/generate/code")
def generate_code(project_id: str, payload: CodeGenerationRequest, current_user: User = Depends(get_current_user)):
    return route_handle(
        lambda: with_project_access(
            project_id,
            current_user,
            lambda: service.generate_code(project_id, payload.model_dump()),
        )
    )


@router.post("/recover/regenerate-stage")
def recover_regenerate_stage(
    project_id: str,
    payload: RegenerateStageRequest,
    current_user: User = Depends(get_current_user),
):
    return route_handle(
        lambda: with_project_access(
            project_id,
            current_user,
            lambda: service.regenerate_stage_and_recascade(project_id, payload.stage, payload.reason),
        )
    )


@router.get("/logs")
def get_logs(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.get_logs(project_id)))
