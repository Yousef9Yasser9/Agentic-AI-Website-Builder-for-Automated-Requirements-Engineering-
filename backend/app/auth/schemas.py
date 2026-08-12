from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: Literal["user", "admin"]
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=8)
    purpose: Literal["register_verification", "password_reset"] = "register_verification"


class ResendOtpRequest(BaseModel):
    email: EmailStr
    purpose: Literal["register_verification", "password_reset"] = "register_verification"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=8)
    new_password: str = Field(min_length=8, max_length=128)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class MessageResponse(BaseModel):
    message: str
    dev_otp: str | None = None


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    role: Literal["user", "admin"] | None = None


class AdminStatsResponse(BaseModel):
    total_users: int
    verified_users: int
    disabled_users: int
    total_projects: int
    total_generated_apps: int
    active_running_apps: int
    ollama_online: bool
    recent_users: list[UserPublic]
    recent_projects: list[dict]
    system_warnings: list[str]
