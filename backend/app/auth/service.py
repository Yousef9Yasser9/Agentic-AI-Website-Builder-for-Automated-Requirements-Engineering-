from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.auth.config import OTP_EXPIRE_MINUTES, OTP_MAX_ATTEMPTS
from backend.app.auth.email_service import send_otp_email, smtp_configured
from backend.app.auth.models import User, VerificationOTP
from backend.app.auth.schemas import (
    AuthTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResendOtpRequest,
    UserPublic,
    VerifyOtpRequest,
)
from backend.app.auth.security import (
    create_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    verify_otp as verify_otp_hash,
    verify_password,
)


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def user_to_public(user: User) -> UserPublic:
    return UserPublic.model_validate(user)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _issue_token(user: User) -> AuthTokenResponse:
    token = create_access_token(str(user.id))
    return AuthTokenResponse(access_token=token, user=user_to_public(user))


def _create_otp_record(
    db: Session,
    *,
    email: str,
    purpose: str,
    user_id: int | None,
) -> str:
    plain_otp = generate_otp()
    record = VerificationOTP(
        user_id=user_id,
        email=email,
        otp_hash=hash_otp(plain_otp),
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
        attempts=0,
    )
    db.add(record)
    db.commit()
    send_otp_email(email, plain_otp, purpose)
    return plain_otp


def _otp_message(message: str, otp: str) -> dict:
    response = {"message": message}
    if not smtp_configured():
        response["dev_otp"] = otp
    return response


def register_user(db: Session, payload: RegisterRequest) -> dict:
    email = _normalize_email(payload.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        if existing.is_verified:
            raise AuthError("An account with this email already exists.", 409)
        existing.full_name = payload.full_name.strip()
        existing.password_hash = hash_password(payload.password)
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        otp = _create_otp_record(db, email=email, purpose="register_verification", user_id=existing.id)
        return _otp_message("Account updated. Verification code sent to your email.", otp)

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="user",
        is_verified=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    otp = _create_otp_record(db, email=email, purpose="register_verification", user_id=user.id)
    return _otp_message("Registration successful. Please verify your email with the OTP sent.", otp)


def verify_otp(db: Session, payload: VerifyOtpRequest) -> AuthTokenResponse | dict:
    email = _normalize_email(payload.email)
    otp_value = payload.otp.strip()
    if not otp_value.isdigit():
        raise AuthError("OTP must be numeric.")

    record = (
        db.query(VerificationOTP)
        .filter(
            VerificationOTP.email == email,
            VerificationOTP.purpose == payload.purpose,
            VerificationOTP.used_at.is_(None),
        )
        .order_by(desc(VerificationOTP.created_at))
        .first()
    )
    if not record:
        raise AuthError("No active verification code found. Please request a new one.", 404)

    now = datetime.now(timezone.utc)
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        raise AuthError("Verification code has expired. Please request a new one.", 400)

    if record.attempts >= OTP_MAX_ATTEMPTS:
        raise AuthError("Too many failed attempts. Please request a new code.", 429)

    if not verify_otp_hash(otp_value, record.otp_hash):
        record.attempts += 1
        db.commit()
        raise AuthError("Invalid verification code.", 400)

    record.used_at = now
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise AuthError("User not found.", 404)

    if payload.purpose == "register_verification":
        user.is_verified = True
        db.commit()
        db.refresh(user)
        return _issue_token(user)

    db.commit()
    return {"message": "OTP verified. You may now reset your password."}


def resend_otp(db: Session, payload: ResendOtpRequest) -> dict:
    email = _normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise AuthError("If an account exists, a new code has been sent.", 200)

    if payload.purpose == "register_verification" and user.is_verified:
        raise AuthError("This account is already verified.", 400)

    otp = _create_otp_record(db, email=email, purpose=payload.purpose, user_id=user.id)
    return _otp_message("A new verification code has been sent.", otp)


def login_user(db: Session, payload: LoginRequest) -> AuthTokenResponse:
    email = _normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise AuthError("Invalid email or password.", 401)

    if not user.is_verified:
        raise AuthError("Please verify your email before logging in.", 403)

    if not user.is_active:
        raise AuthError("Your account has been disabled. Contact support.", 403)

    return _issue_token(user)


def forgot_password(db: Session, payload: ForgotPasswordRequest) -> dict:
    email = _normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if user and user.is_verified and user.is_active:
        _create_otp_record(db, email=email, purpose="password_reset", user_id=user.id)
    return {"message": "If an account exists, a password reset code has been sent."}


def reset_password(db: Session, payload: ResetPasswordRequest) -> dict:
    email = _normalize_email(payload.email)
    otp_value = payload.otp.strip()
    if not otp_value.isdigit():
        raise AuthError("OTP must be numeric.")

    record = (
        db.query(VerificationOTP)
        .filter(
            VerificationOTP.email == email,
            VerificationOTP.purpose == "password_reset",
            VerificationOTP.used_at.is_(None),
        )
        .order_by(desc(VerificationOTP.created_at))
        .first()
    )
    if not record:
        raise AuthError("No active reset code found. Please request a new one.", 404)

    now = datetime.now(timezone.utc)
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        raise AuthError("Reset code has expired. Please request a new one.", 400)

    if record.attempts >= OTP_MAX_ATTEMPTS:
        raise AuthError("Too many failed attempts. Please request a new code.", 429)

    if not verify_otp_hash(otp_value, record.otp_hash):
        record.attempts += 1
        db.commit()
        raise AuthError("Invalid reset code.", 400)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise AuthError("User not found.", 404)

    record.used_at = now
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password reset successful. You can now log in."}


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()
