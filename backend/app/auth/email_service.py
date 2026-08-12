from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from backend.app.auth.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_TLS, SMTP_USER

logger = logging.getLogger("ai-builder.auth")


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM)


def send_otp_email(to_email: str, otp: str, purpose: str) -> None:
    subject_map = {
        "register_verification": "Verify your AI Website Builder account",
        "password_reset": "Reset your AI Website Builder password",
    }
    subject = subject_map.get(purpose, "Your verification code")
    body = (
        f"Your verification code is: {otp}\n\n"
        f"This code expires in a few minutes. If you did not request this, you can ignore this email."
    )

    if not smtp_configured():
        logger.warning(
            "[AUTH OTP - DEV ONLY] email=%s purpose=%s otp=%s (SMTP not configured)",
            to_email,
            purpose,
            otp,
        )
        print(f"\n{'=' * 60}\n[DEV OTP] {to_email} | {purpose} | OTP: {otp}\n{'=' * 60}\n")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_TLS:
            server.starttls()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)
