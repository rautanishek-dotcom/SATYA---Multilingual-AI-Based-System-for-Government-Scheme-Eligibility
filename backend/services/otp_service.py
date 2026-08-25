"""
SATYA – OTP Service

Handles the full OTP lifecycle: generation, secure hashing, MongoDB storage,
validation, expiry, rate-limiting, and audit logging.

OTP rules:
  • 6-digit numeric code (via ``secrets``)
  • Hashed with bcrypt before storage
  • Expires after 5 minutes
  • Max 5 verification attempts per OTP
  • Max 3 resend requests per (user, purpose) session
  • Deleted after successful verification
  • Expired OTPs cleaned up on every operation
"""

import datetime
import logging
import secrets

import bcrypt
from bson import ObjectId

from database import get_db
from vault.audit import AuditLogger

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_VERIFY_ATTEMPTS = 5
MAX_RESEND_COUNT = 3


# ── Helpers ────────────────────────────────────────────────────────────────

def _collection():
    """Return the ``email_otps`` MongoDB collection."""
    db = get_db()
    if db is None:
        return None
    return db.email_otps


def _hash_otp(plain_otp: str) -> bytes:
    """Return a bcrypt hash of the plain OTP string."""
    return bcrypt.hashpw(plain_otp.encode("utf-8"), bcrypt.gensalt())


def _check_otp(plain_otp: str, otp_hash) -> bool:
    """Verify *plain_otp* against the stored bcrypt *otp_hash*."""
    if isinstance(otp_hash, str):
        otp_hash = otp_hash.encode("utf-8")
    try:
        return bcrypt.checkpw(plain_otp.encode("utf-8"), otp_hash)
    except Exception:
        return False


def _cleanup_expired():
    """Delete all OTP records that have passed their expiry time."""
    col = _collection()
    if col is None:
        return
    try:
        result = col.delete_many({"expires_at": {"$lt": datetime.datetime.utcnow()}})
        if result.deleted_count:
            logger.info("[OTP] Cleaned up %d expired OTP(s)", result.deleted_count)
    except Exception as exc:
        logger.warning("[OTP] Expired cleanup failed: %s", exc)


# ── Public API ─────────────────────────────────────────────────────────────

def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    # secrets.randbelow gives [0, 10**6), left-pad with zeros
    code = secrets.randbelow(10 ** OTP_LENGTH)
    return str(code).zfill(OTP_LENGTH)


def create_otp(
    user_id: str,
    email: str,
    purpose: str,
    document_id: str = None,
    ip_address: str = "",
    user_agent: str = "",
) -> dict:
    """
    Generate a new OTP, store its hash in MongoDB, and return the result.

    Returns a dict with keys: ``success``, ``otp`` (plain, for the caller to
    send via email), ``message``, and ``expires_at``.
    """
    _cleanup_expired()
    col = _collection()
    if col is None:
        return {"success": False, "message": "Database unavailable"}

    # Rate-limit: check how many active (non-expired, non-verified) OTPs exist
    # for this user + purpose. We track resend_count on the latest record.
    existing = col.find_one(
        {
            "user_id": str(user_id),
            "purpose": purpose,
            "verified": False,
            "expires_at": {"$gt": datetime.datetime.utcnow()},
        },
        sort=[("created_at", -1)],
    )

    if existing and existing.get("resend_count", 0) >= MAX_RESEND_COUNT:
        return {
            "success": False,
            "message": f"Maximum resend limit ({MAX_RESEND_COUNT}) reached. Please try again later.",
        }

    # Invalidate any previous OTPs for same user + purpose
    col.delete_many({
        "user_id": str(user_id),
        "purpose": purpose,
        "verified": False,
    })

    plain_otp = generate_otp()
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)

    resend_count = (existing.get("resend_count", 0) + 1) if existing else 0

    record = {
        "user_id": str(user_id),
        "email": email,
        "otp_hash": _hash_otp(plain_otp),
        "purpose": purpose,
        "document_id": str(document_id) if document_id else None,
        "created_at": now,
        "expires_at": expires_at,
        "verified": False,
        "attempt_count": 0,
        "resend_count": resend_count,
    }

    try:
        col.insert_one(record)
    except Exception as exc:
        logger.error("[OTP] Failed to store OTP: %s", exc)
        return {"success": False, "message": "Failed to generate OTP"}

    # Audit
    AuditLogger.record("otp_generated", user_id, {
        "email": email,
        "purpose": purpose,
        "document_id": str(document_id) if document_id else None,
        "resend_count": resend_count,
        "expires_at": expires_at.isoformat(),
        "ip_address": ip_address,
        "user_agent": user_agent,
    })

    logger.info("[OTP] Generated for user=%s purpose=%s resend=%d", user_id, purpose, resend_count)

    return {
        "success": True,
        "otp": plain_otp,
        "message": "OTP generated successfully",
        "expires_at": expires_at.isoformat(),
        "resend_count": resend_count,
        "resends_remaining": MAX_RESEND_COUNT - resend_count,
    }


def verify_otp(
    user_id: str,
    otp_code: str,
    purpose: str,
    document_id: str = None,
    ip_address: str = "",
    user_agent: str = "",
) -> dict:
    """
    Verify a user-submitted OTP code.

    Returns a dict with ``success``, ``message``, and optionally
    ``attempts_remaining``.
    """
    _cleanup_expired()
    col = _collection()
    if col is None:
        return {"success": False, "message": "Database unavailable"}

    # Find the latest active OTP for this user + purpose
    query = {
        "user_id": str(user_id),
        "purpose": purpose,
        "verified": False,
        "expires_at": {"$gt": datetime.datetime.utcnow()},
    }
    if document_id:
        query["document_id"] = str(document_id)

    record = col.find_one(query, sort=[("created_at", -1)])

    if not record:
        AuditLogger.record("otp_verify_failed", user_id, {
            "reason": "no_active_otp",
            "purpose": purpose,
            "ip_address": ip_address,
            "user_agent": user_agent,
        })
        return {"success": False, "message": "No active OTP found. Please request a new one."}

    # Check attempt limit
    attempt_count = record.get("attempt_count", 0)
    if attempt_count >= MAX_VERIFY_ATTEMPTS:
        # Invalidate this OTP
        col.delete_one({"_id": record["_id"]})
        AuditLogger.record("otp_blocked", user_id, {
            "reason": "max_attempts_exceeded",
            "purpose": purpose,
            "attempt_count": attempt_count,
            "ip_address": ip_address,
            "user_agent": user_agent,
        })
        return {
            "success": False,
            "message": f"Maximum verification attempts ({MAX_VERIFY_ATTEMPTS}) exceeded. Please request a new OTP.",
        }

    # Increment attempt counter
    col.update_one(
        {"_id": record["_id"]},
        {"$inc": {"attempt_count": 1}},
    )

    # Verify the OTP hash
    if _check_otp(otp_code, record["otp_hash"]):
        # Success – mark as verified, then delete
        col.delete_one({"_id": record["_id"]})
        AuditLogger.record("otp_verified", user_id, {
            "purpose": purpose,
            "document_id": record.get("document_id"),
            "attempts_used": attempt_count + 1,
            "ip_address": ip_address,
            "user_agent": user_agent,
        })
        logger.info("[OTP] Verified for user=%s purpose=%s (attempts=%d)", user_id, purpose, attempt_count + 1)
        return {"success": True, "message": "OTP verified successfully"}
    else:
        remaining = MAX_VERIFY_ATTEMPTS - (attempt_count + 1)
        AuditLogger.record("otp_verify_failed", user_id, {
            "reason": "invalid_code",
            "purpose": purpose,
            "attempt_count": attempt_count + 1,
            "attempts_remaining": remaining,
            "ip_address": ip_address,
            "user_agent": user_agent,
        })
        return {
            "success": False,
            "message": f"Invalid OTP. {remaining} attempt(s) remaining.",
            "attempts_remaining": remaining,
        }


def get_resend_info(user_id: str, purpose: str) -> dict:
    """Return resend count info for the current OTP session."""
    col = _collection()
    if col is None:
        return {"resend_count": 0, "resends_remaining": MAX_RESEND_COUNT}

    record = col.find_one(
        {
            "user_id": str(user_id),
            "purpose": purpose,
            "verified": False,
            "expires_at": {"$gt": datetime.datetime.utcnow()},
        },
        sort=[("created_at", -1)],
    )

    count = record.get("resend_count", 0) if record else 0
    return {
        "resend_count": count,
        "resends_remaining": max(0, MAX_RESEND_COUNT - count),
    }
