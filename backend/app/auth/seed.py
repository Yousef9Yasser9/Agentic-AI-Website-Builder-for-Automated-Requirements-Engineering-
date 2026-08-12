from __future__ import annotations

import logging
import os

from backend.app.auth.database import SessionLocal
from backend.app.auth.models import User
from backend.app.auth.security import hash_password

logger = logging.getLogger("ai-builder.auth")


def seed_first_admin() -> None:
    """Create the first admin from env vars when no admin exists yet."""
    email = os.getenv("FIRST_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("FIRST_ADMIN_PASSWORD", "").strip()
    full_name = os.getenv("FIRST_ADMIN_FULL_NAME", "Platform Admin").strip()

    if not email or not password:
        return

    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == "admin").first():
            return

        user = db.query(User).filter(User.email == email).first()
        if user:
            user.full_name = full_name
            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_verified = True
            user.is_active = True
        else:
            db.add(
                User(
                    full_name=full_name,
                    email=email,
                    password_hash=hash_password(password),
                    role="admin",
                    is_verified=True,
                    is_active=True,
                )
            )
        db.commit()
        logger.warning("[AUTH] First admin account ready for: %s", email)
        print(f"\n{'=' * 60}\n[AUTH] First admin ready: {email}\n{'=' * 60}\n")
    except Exception as exc:
        db.rollback()
        logger.error("Failed to seed first admin: %s", exc)
    finally:
        db.close()
