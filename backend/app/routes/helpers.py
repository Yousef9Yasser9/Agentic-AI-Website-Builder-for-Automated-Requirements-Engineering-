from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from backend.app.auth.models import User
from backend.app.services import builder_service as service


def route_handle(call: Callable[[], Any]):
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


def with_project_access(project_id: str, user: User, fn: Callable[[], Any]):
    service.assert_project_access(project_id, user.id, user.role == "admin")
    return fn()
