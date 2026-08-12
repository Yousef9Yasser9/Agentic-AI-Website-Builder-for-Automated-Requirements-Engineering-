from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.auth.database import get_db
from backend.app.auth.deps import get_current_user_public
from backend.app.auth.schemas import (
    AuthTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    ResendOtpRequest,
    UserPublic,
    VerifyOtpRequest,
)
from backend.app.auth.service import (
    AuthError,
    forgot_password,
    login_user,
    register_user,
    resend_otp,
    reset_password,
    verify_otp,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _handle(call):
    try:
        return call()
    except AuthError as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@router.post("/register", response_model=MessageResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    result = _handle(lambda: register_user(db, payload))
    if isinstance(result, JSONResponse):
        return result
    return result


@router.post("/verify-otp")
def verify_otp_route(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    result = _handle(lambda: verify_otp(db, payload))
    if isinstance(result, JSONResponse):
        return result
    return result


@router.post("/resend-otp", response_model=MessageResponse)
def resend_otp_route(payload: ResendOtpRequest, db: Session = Depends(get_db)):
    result = _handle(lambda: resend_otp(db, payload))
    if isinstance(result, JSONResponse):
        return result
    return result


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    result = _handle(lambda: login_user(db, payload))
    if isinstance(result, JSONResponse):
        return result
    return result


@router.post("/logout", response_model=MessageResponse)
def logout():
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(get_current_user_public)):
    return current_user


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password_route(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    result = _handle(lambda: forgot_password(db, payload))
    if isinstance(result, JSONResponse):
        return result
    return result


@router.post("/reset-password", response_model=MessageResponse)
def reset_password_route(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    result = _handle(lambda: reset_password(db, payload))
    if isinstance(result, JSONResponse):
        return result
    return result
