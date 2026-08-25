"""
SATYA – Email Service (Flask-Mail + Gmail SMTP)

Provides a professional HTML email sender for OTP delivery.
All credentials are read from environment variables – nothing is hardcoded.
"""

import logging
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask
from flask_mail import Mail, Message

logger = logging.getLogger(__name__)

# Module-level Mail instance – initialised via ``init_mail(app)``
mail = Mail()

MAIL_BACKEND_ENV = "MAIL_BACKEND"
MAIL_BACKEND_SMTP = "smtp"
MAIL_BACKEND_CONSOLE = "console"
MAIL_BACKEND_FILE = "file"
MAIL_BACKEND_DRY_RUN = "dry_run"


def _get_mail_backend() -> str:
    return (os.getenv(MAIL_BACKEND_ENV, MAIL_BACKEND_SMTP) or MAIL_BACKEND_SMTP).strip().lower()


def init_mail(app: Flask) -> None:
    """Configure Flask-Mail from environment variables and bind to *app*."""
    backend = _get_mail_backend()
    app.config["SATYA_MAIL_BACKEND"] = backend
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
    app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "yes")
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"])
    app.config["MAIL_SUPPRESS_SEND"] = backend in {MAIL_BACKEND_CONSOLE, MAIL_BACKEND_FILE, MAIL_BACKEND_DRY_RUN}
    app.config["MAIL_DEBUG"] = backend != MAIL_BACKEND_SMTP

    mail.init_app(app)
    logger.info(
        "[EMAIL] Flask-Mail initialised (backend=%s, server=%s, port=%s)",
        backend,
        app.config["MAIL_SERVER"],
        app.config["MAIL_PORT"],
    )


# ── HTML email template ────────────────────────────────────────────────────

def _build_otp_html(otp_code: str, purpose_label: str) -> str:
    """Return a responsive HTML email body with the OTP prominently displayed."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SATYA Verification Code</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;padding:32px 16px;">
<tr><td align="center">
<table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,#1e3a8a,#2563eb);padding:32px 24px;text-align:center;">
      <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:800;letter-spacing:1px;">
        🛡️ SATYA
      </h1>
      <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">
        Multilingual AI-Based Government Scheme Eligibility System
      </p>
    </td>
  </tr>

  <!-- Body -->
  <tr>
    <td style="padding:32px 28px 24px;">
      <p style="margin:0 0 8px;color:#334155;font-size:16px;">Hello,</p>
      <p style="margin:0 0 24px;color:#475569;font-size:14px;line-height:1.6;">
        Your One-Time Password (OTP) for <strong>{purpose_label}</strong> is:
      </p>

      <!-- OTP Box -->
      <div style="text-align:center;margin:0 0 24px;">
        <div style="display:inline-block;background:linear-gradient(135deg,#eff6ff,#dbeafe);border:2px solid #2563eb;border-radius:12px;padding:18px 40px;letter-spacing:12px;font-size:36px;font-weight:900;color:#1e3a8a;">
          {otp_code}
        </div>
      </div>

      <p style="margin:0 0 6px;color:#475569;font-size:13px;text-align:center;">
        ⏱ This verification code is valid for <strong>5 minutes</strong>.
      </p>
      <p style="margin:0 0 24px;color:#94a3b8;font-size:12px;text-align:center;">
        If you did not request this verification, please ignore this email.
      </p>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="background:#f8fafc;padding:20px 28px;border-top:1px solid #e2e8f0;text-align:center;">
      <p style="margin:0;color:#94a3b8;font-size:12px;">
        Regards,<br><strong>SATYA Team</strong>
      </p>
      <p style="margin:8px 0 0;color:#cbd5e1;font-size:11px;">
        This is an automated message. Please do not reply.
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Public API ─────────────────────────────────────────────────────────────

PURPOSE_LABELS = {
    "document_verification": "Document Verification",
    "eligibility_check": "Eligibility Check",
}


def _write_mock_email(recipient_email: str, subject: str, plain_body: str, html_body: str, purpose: str, backend: str) -> Path:
    output_dir = Path(os.getenv("MAIL_OUTPUT_DIR", os.path.join("temp_uploads", "mock_mail")))
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    payload = {
        "backend": backend,
        "recipient_email": recipient_email,
        "subject": subject,
        "purpose": purpose,
        "plain_body": plain_body,
        "html_body": html_body,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path = output_dir / f"otp_{timestamp}_{os.getpid()}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _send_mock_email(recipient_email: str, subject: str, plain_body: str, html_body: str, purpose: str, backend: str) -> bool:
    if backend == MAIL_BACKEND_CONSOLE:
        logger.info(
            "[EMAIL][MOCK] to=%s subject=%s purpose=%s body=%s",
            recipient_email,
            subject,
            purpose,
            plain_body,
        )
        return True
    if backend == MAIL_BACKEND_FILE:
        path = _write_mock_email(recipient_email, subject, plain_body, html_body, purpose, backend)
        logger.info("[EMAIL][MOCK] wrote email payload to %s", path)
        return True
    if backend == MAIL_BACKEND_DRY_RUN:
        logger.info("[EMAIL][MOCK] dry-run send to=%s subject=%s purpose=%s", recipient_email, subject, purpose)
        return True
    return False


def send_otp_email(recipient_email: str, otp_code: str, purpose: str = "document_verification") -> bool:
    """
    Send a styled OTP email to *recipient_email*.

    Returns ``True`` on success, ``False`` on failure.
    All errors are logged but never propagated to the caller.
    """
    purpose_label = PURPOSE_LABELS.get(purpose, "Verification")
    subject = "SATYA Verification Code"

    html_body = _build_otp_html(otp_code, purpose_label)
    plain_body = (
        f"Hello,\n\n"
        f"Your One-Time Password (OTP) for {purpose_label} is: {otp_code}\n\n"
        f"This verification code is valid for 5 minutes.\n"
        f"If you did not request this verification, please ignore this email.\n\n"
        f"Regards,\nSATYA Team"
    )

    try:
        backend = _get_mail_backend()
        if backend != MAIL_BACKEND_SMTP:
            return _send_mock_email(recipient_email, subject, plain_body, html_body, purpose, backend)
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=plain_body,
            html=html_body,
        )
        mail.send(msg)
        logger.info("[EMAIL] OTP email sent to %s (purpose=%s)", recipient_email, purpose)
        return True
    except Exception as exc:
        logger.error("[EMAIL] Failed to send OTP to %s: %s", recipient_email, exc)
        return False
