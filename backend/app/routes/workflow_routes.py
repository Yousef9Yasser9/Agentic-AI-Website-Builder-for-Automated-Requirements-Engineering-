from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.auth.deps import get_current_user
from backend.app.auth.models import User
from backend.app.routes.helpers import route_handle, with_project_access
from backend.app.schemas.project_schema import UiSelectionRequest
from backend.app.services import builder_service as service

router = APIRouter(prefix="/api/projects/{project_id}", tags=["workflow"])


@router.post("/generate/cleaned-spec")
def generate_cleaned_spec(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.generate_cleaned_spec(project_id)))


@router.post("/generate/requirements")
def generate_requirements(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.generate_requirements(project_id)))


@router.post("/generate/user-stories")
def generate_user_stories(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.generate_user_stories(project_id)))


@router.post("/generate/architecture")
def generate_architecture(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.generate_architecture(project_id)))


@router.post("/generate/data-model")
def generate_data_model(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.generate_data_model(project_id)))


@router.post("/generate/srs")
def generate_srs(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.generate_srs(project_id)))


@router.post("/ui-selection")
def save_ui_selection(project_id: str, payload: UiSelectionRequest, current_user: User = Depends(get_current_user)):
    return route_handle(
        lambda: with_project_access(
            project_id,
            current_user,
            lambda: service.save_ui_selection(project_id, payload.model_dump()),
        )
    )


@router.post("/generate/post-analysis")
def generate_post_analysis(project_id: str, current_user: User = Depends(get_current_user)):
    return route_handle(lambda: with_project_access(project_id, current_user, lambda: service.generate_post_analysis(project_id)))
