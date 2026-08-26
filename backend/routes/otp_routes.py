"""
SATYA – OTP API Routes

Endpoints:
  POST /api/otp/send   — Generate OTP and email it to the user's registered address
  POST /api/otp/verify  — Verify a user-submitted OTP code
  POST /api/otp/resend  — Resend (regenerate) OTP to the same email
"""

import logging

from flask import Blueprint, request, jsonify, session
from bson import ObjectId

from database import get_db
from routes.auth import token_required
from services.otp_service import create_otp, verify_otp, get_resend_info, get_verification_status, SHARED_VERIFICATION_PURPOSE
from services.email_service import send_otp_email

logger = logging.getLogger(__name__)
otp_bp = Blueprint("otp", __name__)

VALID_PURPOSES = {"document_verification", "eligibility_check"}


def _client_meta():
    """Extract IP address and User-Agent from the current request."""
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ua = request.headers.get("User-Agent", "")
    return ip, ua


def _user_email(current_user_id):
    db = get_db()
    if db is None:
        return None, None, ("Database unavailable", 500)
    user = db.users.find_one({"_id": ObjectId(current_user_id)})
    if not user:
        return None, None, ("User not found", 404)
    user_email = user.get("email")
    if not user_email:
        return None, None, ("No email address registered for this account", 400)
    return user_email, db, None


# ── POST /api/otp/send ────────────────────────────────────────────────────

@otp_bp.route("/send", methods=["POST"])
@token_required
def send_otp(current_user_id, current_user_role):
    """
    Generate a 6-digit OTP and send it to the logged-in user's registered email.

    Body JSON:
      - purpose: "document_verification" | "eligibility_check"  (required)
      - document_id: string  (optional, for document_verification)
    """
    data = request.get_json(silent=True) or {}
    purpose = data.get("purpose", "")
    document_id = data.get("document_id")

    if purpose not in VALID_PURPOSES:
        return jsonify({"error": f"Invalid purpose. Must be one of: {', '.join(VALID_PURPOSES)}"}), 400

    user_email, db, email_error = _user_email(current_user_id)
    if email_error:
        message, status_code = email_error
        return jsonify({"error": message}), status_code

    # A verified vault OTP belongs to the current Flask login session. Do not
    # reuse the short-lived MongoDB record after that session has ended.
    vault_verified = session.get("document_vault_verified_user_id") == str(current_user_id)
    if purpose == "document_verification" and not vault_verified:
        db.email_otps.delete_many({
            "user_id": str(current_user_id),
            "purpose": SHARED_VERIFICATION_PURPOSE,
            "verified": True,
        })

    ip, ua = _client_meta()

    # Generate OTP
    result = create_otp(
        user_id=current_user_id,
        email=user_email,
        purpose=purpose,
        document_id=document_id,
        ip_address=ip,
        user_agent=ua,
    )

    if not result.get("success"):
        status_code = 429
        if result.get("message") == "A valid OTP verification session already exists":
            status_code = 200
        return jsonify({
            "error": result.get("message", "Failed to generate OTP"),
            "already_verified": result.get("already_verified", False),
            "already_pending": result.get("already_pending", False),
            "resend_count": result.get("resend_count", 0),
            "resends_remaining": result.get("resends_remaining", 0),
            "expires_at": result.get("expires_at"),
        }), status_code

    if result.get("already_verified"):
        return jsonify({
            "message": result.get("message"),
            "already_verified": True,
            "verified": True,
            "expires_at": result.get("expires_at"),
            "resend_count": result.get("resend_count", 0),
            "resends_remaining": result.get("resends_remaining", 0),
        }), 200

    if result.get("already_pending"):
        return jsonify({
            "message": result.get("message"),
            "already_pending": True,
            "verified": False,
            "expires_at": result.get("expires_at"),
            "resend_count": result.get("resend_count", 0),
            "resends_remaining": result.get("resends_remaining", 0),
        }), 200

    # Send email
    plain_otp = result.pop("otp")  # remove plain OTP from response
    email_sent = send_otp_email(user_email, plain_otp, purpose)

    if not email_sent:
        # Rollback the OTP creation to avoid incrementing the rate limit for a failed send
        db.email_otps.delete_one({"user_id": str(current_user_id), "purpose": purpose, "verified": False})
        return jsonify({
            "error": "Failed to send OTP email. Please check your email configuration and try again."
        }), 500

    # Mask the email for the response (e.g. r***l@gmail.com)
    parts = user_email.split("@")
    local = parts[0]
    if len(local) > 2:
        masked = local[0] + "*" * (len(local) - 2) + local[-1]
    else:
        masked = local[0] + "*"
    masked_email = f"{masked}@{parts[1]}" if len(parts) == 2 else user_email

    return jsonify({
        "message": f"OTP sent to {masked_email}",
        "masked_email": masked_email,
        "expires_at": result.get("expires_at"),
        "resend_count": result.get("resend_count", 0),
        "resends_remaining": result.get("resends_remaining", 3),
        "verified": False,
    }), 200


# ── POST /api/otp/verify ──────────────────────────────────────────────────

@otp_bp.route("/verify", methods=["POST"])
@token_required
def verify_otp_route(current_user_id, current_user_role):
    """
    Verify a user-submitted OTP code.

    Body JSON:
      - otp_code: string (required, 6 digits)
      - purpose: "document_verification" | "eligibility_check"  (required)
      - document_id: string  (optional)
    """
    data = request.get_json(silent=True) or {}
    otp_code = (data.get("otp_code") or "").strip()
    purpose = data.get("purpose", "")
    document_id = data.get("document_id")

    if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
        return jsonify({"error": "Please enter a valid 6-digit OTP"}), 400

    if purpose not in VALID_PURPOSES:
        return jsonify({"error": f"Invalid purpose. Must be one of: {', '.join(VALID_PURPOSES)}"}), 400

    ip, ua = _client_meta()

    result = verify_otp(
        user_id=current_user_id,
        otp_code=otp_code,
        purpose=purpose,
        document_id=document_id,
        ip_address=ip,
        user_agent=ua,
    )

    if result.get("success"):
        if purpose == "document_verification":
            session["document_vault_verified_user_id"] = str(current_user_id)
        return jsonify({
            "message": result["message"],
            "verified": True,
            "already_verified": result.get("already_verified", False),
            "expires_at": result.get("expires_at"),
        }), 200
    else:
        status_code = 400
        if "attempt" in result.get("message", "").lower():
            status_code = 429
        return jsonify({
            "error": result["message"],
            "verified": False,
            "attempts_remaining": result.get("attempts_remaining"),
        }), status_code


# ── GET /api/otp/status ───────────────────────────────────────────────────

@otp_bp.route("/status", methods=["GET"])
@token_required
def otp_status(current_user_id, current_user_role):
    """
    Return the shared OTP session state for the logged-in user.
    Query params:
      - purpose: "document_verification" | "eligibility_check"  (optional, defaults to shared session)
      - document_id: string (optional)
    """
    purpose = request.args.get("purpose", "")
    document_id = request.args.get("document_id")

    if purpose and purpose not in VALID_PURPOSES:
        return jsonify({"error": f"Invalid purpose. Must be one of: {', '.join(VALID_PURPOSES)}"}), 400

    is_verified_in_session = (
        purpose == "document_verification"
        and session.get("document_vault_verified_user_id") == str(current_user_id)
    )
    if is_verified_in_session:
        return jsonify({
            "success": True,
            "active": True,
            "verified": True,
            "status": "verified"
        }), 200

    if purpose == "document_verification":
        return jsonify({
            "success": True,
            "active": False,
            "verified": False,
            "status": "none",
            "resend_count": 0,
            "resends_remaining": 3,
        }), 200

    result = get_verification_status(current_user_id, purpose or "document_verification", document_id=document_id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Failed to fetch OTP status")}), 500
    return jsonify(result), 200


# ── POST /api/otp/resend ──────────────────────────────────────────────────

@otp_bp.route("/resend", methods=["POST"])
@token_required
def resend_otp(current_user_id, current_user_role):
    """
    Resend (regenerate) an OTP to the user's registered email.
    Invalidates any previous OTP for the same purpose.

    Body JSON:
      - purpose: "document_verification" | "eligibility_check"  (required)
      - document_id: string  (optional)
    """
    data = request.get_json(silent=True) or {}
    purpose = data.get("purpose", "")
    document_id = data.get("document_id")

    if purpose not in VALID_PURPOSES:
        return jsonify({"error": f"Invalid purpose. Must be one of: {', '.join(VALID_PURPOSES)}"}), 400

    # Check resend limit before doing anything
    info = get_resend_info(current_user_id, purpose)
    if info["resends_remaining"] <= 0:
        return jsonify({
            "error": "Maximum resend limit reached. Please try again later.",
            "resend_count": info["resend_count"],
            "resends_remaining": 0,
        }), 429

    user_email, db, email_error = _user_email(current_user_id)
    if email_error:
        message, status_code = email_error
        return jsonify({"error": message}), status_code

    ip, ua = _client_meta()

    result = create_otp(
        user_id=current_user_id,
        email=user_email,
        purpose=purpose,
        document_id=document_id,
        ip_address=ip,
        user_agent=ua,
        force_new=True,
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Failed to resend OTP")}), 429

    if result.get("already_verified"):
        return jsonify({
            "message": result.get("message"),
            "already_verified": True,
            "resend_count": result.get("resend_count", 0),
            "resends_remaining": result.get("resends_remaining", 0),
            "expires_at": result.get("expires_at"),
        }), 200

    plain_otp = result.pop("otp")
    email_sent = send_otp_email(user_email, plain_otp, purpose)

    if not email_sent:
        # Rollback the OTP creation
        db.email_otps.delete_one({"user_id": str(current_user_id), "purpose": purpose, "verified": False})
        return jsonify({"error": "Failed to send OTP email"}), 500

    return jsonify({
        "message": "New OTP sent to your registered email",
        "resend_count": result.get("resend_count", 0),
        "resends_remaining": result.get("resends_remaining", 0),
        "expires_at": result.get("expires_at"),
    }), 200
