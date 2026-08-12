from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.auth.deps import require_admin
from backend.app.auth.models import User
from backend.app.schemas.project_schema import CleanupRequest
from backend.app.services import builder_service as service

router = APIRouter(prefix="/api/system", tags=["system"])


def _handle(call):
    try:
        return call()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/size-report")
def size_report(current_user: User = Depends(require_admin)):
    del current_user
    return _handle(service.size_report)


@router.post("/cleanup")
def cleanup(payload: CleanupRequest, current_user: User = Depends(require_admin)):
    del current_user
    return _handle(lambda: service.cleanup_system(payload.keep_apps, payload.keep_checkpoints))
