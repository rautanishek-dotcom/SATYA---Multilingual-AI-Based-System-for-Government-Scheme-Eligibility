"""
SATYA – Email Service (Flask-Mail + Gmail SMTP)

Provides a professional HTML email sender for OTP delivery.
All credentials are read from environment variables – nothing is hardcoded.
"""

import logging
import json
import os
import re
from email.utils import make_msgid, parseaddr
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Module-level Mail instance – initialised via ``init_mail(app)``
mail = Mail()

MAIL_BACKEND_ENV = "MAIL_BACKEND"
MAIL_BACKEND_SMTP = "smtp"
MAIL_BACKEND_CONSOLE = "console"
MAIL_BACKEND_FILE = "file"
MAIL_BACKEND_DRY_RUN = "dry_run"
_PLACEHOLDER_ENV_VALUES = {
    "yourgmail@gmail.com",
    "your_google_app_password",
    "satya <yourgmail@gmail.com>",
}


def _load_backend_env() -> None:
    """Load environment files without overwriting already injected secrets."""
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = Path(__file__).resolve().parents[1]
    for env_file in (repo_root / ".env", backend_dir / ".env"):
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)
    load_dotenv(override=False)


def _normalize_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered in _PLACEHOLDER_ENV_VALUES:
        return None
    for placeholder in _PLACEHOLDER_ENV_VALUES:
        if placeholder in lowered:
            return None
    return cleaned


def _get_env_value(key: str, default: str | None = None) -> str | None:
    return _normalize_env_value(os.getenv(key)) or default


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


def _safe_email_hint(email: str | None) -> str:
    if not email or "@" not in email:
        return "unavailable"
    local, domain = email.split("@", 1)
    if not local:
        return f"*@{domain}"
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def _safe_sender_hint(sender: str | None) -> str:
    return _safe_email_hint(sender)


def _extract_email_address(value: str | None) -> str | None:
    if not value:
        return None
    _, address = parseaddr(value)
    address = address.strip()
    return address or None


def _sanitize_error_message(message: str) -> str:
    text = message or ""
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email>", text)
    text = re.sub(r"\b\d{6}\b", "<otp>", text)
    return text


def _log_mail_diagnostics(backend: str, recipient_email: str | None = None) -> None:
    username = _get_env_value("MAIL_USERNAME", "") or ""
    server = _get_env_value("MAIL_SERVER", "smtp.gmail.com") or "smtp.gmail.com"
    port = int(_get_env_value("MAIL_PORT", "587"))
    tls_enabled = _as_bool(_get_env_value("MAIL_USE_TLS", "True"), True)
    ssl_enabled = _as_bool(_get_env_value("MAIL_USE_SSL", "False"), False)
    password_configured = bool(_normalize_env_value(os.getenv("MAIL_PASSWORD")))
    sender = _extract_email_address(_get_env_value("MAIL_DEFAULT_SENDER", username) or username)
    sender_configured = bool(_normalize_env_value(sender))
    recipient_configured = bool(_normalize_env_value(recipient_email))
    logger.info(
        "[EMAIL][SMTP_DIAG] backend=%s server=%s port=%s tls=%s ssl=%s username_configured=%s password_configured=%s sender_configured=%s sender_hint=%s recipient_configured=%s recipient_hint=%s",
        backend,
        server,
        port,
        tls_enabled,
        ssl_enabled,
        bool(username),
        password_configured,
        sender_configured,
        _safe_sender_hint(sender),
        recipient_configured,
        _safe_email_hint(recipient_email),
    )


def _get_mail_backend() -> str:
    return (os.getenv(MAIL_BACKEND_ENV, MAIL_BACKEND_SMTP) or MAIL_BACKEND_SMTP).strip().lower()


def init_mail(app: Flask) -> None:
    """Configure Flask-Mail from environment variables and bind to *app*."""
    _load_backend_env()
    backend = _get_mail_backend()
    app.config["SATYA_MAIL_BACKEND"] = backend
    app.config["MAIL_SERVER"] = _get_env_value("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(_get_env_value("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = (_get_env_value("MAIL_USE_TLS", "True") or "True").lower() in ("true", "1", "yes")
    app.config["MAIL_USE_SSL"] = (_get_env_value("MAIL_USE_SSL", "False") or "False").lower() in ("true", "1", "yes")
    app.config["MAIL_USERNAME"] = _get_env_value("MAIL_USERNAME", "") or ""
    app.config["MAIL_PASSWORD"] = _get_env_value("MAIL_PASSWORD", "") or ""
    app.config["MAIL_DEFAULT_SENDER"] = _get_env_value("MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"]) or app.config["MAIL_USERNAME"]
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
    subject = os.getenv("SATYA_TEST_SUBJECT", "SATYA Verification Code").strip() or "SATYA Verification Code"

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
        _log_mail_diagnostics(backend, recipient_email)
        sender = _extract_email_address(_get_env_value("MAIL_DEFAULT_SENDER", _get_env_value("MAIL_USERNAME", "")))
        message_id = make_msgid(domain=(sender.split("@", 1)[1] if sender and "@" in sender else None))
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=plain_body,
            html=html_body,
        )
        logger.info(
            "[EMAIL][SMTP_TRACE] from_hint=%s to_hint=%s reply_to_hint=%s recipients=%s message_id=%s subject=%s",
            _safe_sender_hint(sender),
            _safe_email_hint(recipient_email),
            _safe_sender_hint(sender),
            [_safe_email_hint(addr) for addr in msg.recipients],
            message_id,
            subject,
        )
        mail.send(msg)
        logger.info(
            "[EMAIL] OTP email accepted for delivery (purpose=%s, recipient_hint=%s, message_id=%s)",
            purpose,
            _safe_email_hint(recipient_email),
            message_id,
        )
        return True
    except Exception as exc:
        logger.error(
            "[EMAIL] Failed to send OTP (type=%s, message=%s)",
            exc.__class__.__name__,
            _sanitize_error_message(str(exc)),
        )
        return False
