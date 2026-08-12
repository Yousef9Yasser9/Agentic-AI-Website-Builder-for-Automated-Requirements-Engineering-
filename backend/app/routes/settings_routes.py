from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.auth.deps import require_admin
from backend.app.auth.models import User
from backend.app.schemas.project_schema import ModelSettings
from backend.app.services import builder_service as service

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings/models")
def get_model_settings(current_user: User = Depends(require_admin)):
    del current_user
    return service.load_settings()


@router.put("/settings/models")
def update_model_settings(payload: ModelSettings, current_user: User = Depends(require_admin)):
    del current_user
    return service.save_settings(payload.model_dump())


@router.get("/ollama/status")
def get_ollama_status(current_user: User = Depends(require_admin)):
    del current_user
    return service.ollama_status()
