from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "change_me_to_a_long_random_secret_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR / '.tmp' / 'builder_auth.db'}")

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip() or SMTP_USER
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() in {"1", "true", "yes"}

FIRST_ADMIN_EMAIL = os.getenv("FIRST_ADMIN_EMAIL", "").strip()
FIRST_ADMIN_PASSWORD = os.getenv("FIRST_ADMIN_PASSWORD", "").strip()
FIRST_ADMIN_FULL_NAME = os.getenv("FIRST_ADMIN_FULL_NAME", "Platform Admin").strip()
