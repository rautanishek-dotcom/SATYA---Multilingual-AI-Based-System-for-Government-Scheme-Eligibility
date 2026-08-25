from flask import Blueprint, request, jsonify, send_file
import logging
import os
import time
import datetime
import bcrypt
import tempfile
import uuid

from bson import ObjectId

from database import get_db
from vault.audit import AuditLogger
from vault.document_manager import DocumentManager
from vault.document_vault import DocumentVault
from vault.identity_matcher import get_user_identity
from vault.policy import RESET_COOLDOWN_HOURS
from vault.security import SecurityManager
from vault.verification_orchestrator import VerificationOrchestrator, sanitize_for_json
from document_intelligence.orchestrator import DocumentIntelligenceOrchestrator
from services.otp_service import verify_otp


logger = logging.getLogger(__name__)
vault_bp = Blueprint("vault", __name__)
manager = DocumentManager()
orchestrator = VerificationOrchestrator()
extractor = DocumentIntelligenceOrchestrator()

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def _get_user_id():
    return request.form.get("user_id") or request.args.get("user_id") or (request.get_json(silent=True) or {}).get("user_id")


def _scalar(value, default=""):
    if isinstance(value, dict):
        if "value" in value:
            value = value.get("value")
        elif "Value" in value:
            value = value.get("Value")
    if value is None or value == "":
        return default
    return value


def _serialize_identity(user, identity_profile):
    identity_profile = identity_profile or {}
    identity_locked = bool(user.get("identity_locked", False))
    verified_at = _scalar(identity_profile.get("verifiedAt") or identity_profile.get("verified_at", ""))
    return {
        "user_id": str(user.get("_id")),
        "full_name": _scalar(identity_profile.get("fullName") or identity_profile.get("full_name") or user.get("name", "")),
        "dob": _scalar(identity_profile.get("dob", "")),
        "gender": _scalar(identity_profile.get("gender", "")),
        "masked_aadhaar": _scalar(identity_profile.get("maskedAadhaar") or identity_profile.get("masked_aadhaar", "")),
        "aadhaar_reference_id": _scalar(identity_profile.get("aadhaarReferenceId") or identity_profile.get("aadhaar_reference_id", "")),
        "identity_locked": identity_locked,
        "verification_status": _scalar(identity_profile.get("verificationStatus") or identity_profile.get("verification_status", "Verified" if identity_locked else "")),
        "confidence": float(_scalar(identity_profile.get("confidence", 0), 0) or 0),
        "verified_at": verified_at,
        "last_reset_at": user.get("identity_reset_meta", {}).get("last_reset_at"),
        "document_type": _scalar(identity_profile.get("documentType") or identity_profile.get("document_type", "")),
        "verification_method": _scalar(identity_profile.get("verificationMethod") or identity_profile.get("verification_method", "")),
    }


@vault_bp.route("/upload", methods=["POST"])
def upload_document():
    content_type = request.content_type or ""
    files_info = {
        name: {
            "filename": f.filename,
            "content_type": getattr(f, "content_type", None) or getattr(f, "mimetype", None),
            "content_length": getattr(f, "content_length", None),
        }
        for name, f in request.files.items()
    }
    logger.info("Received upload request: content_type=%s, request_files=%s", content_type, files_info)

    if not content_type.lower().startswith("multipart/form-data"):
        logger.warning("Upload rejected: missing multipart/form-data")
        return jsonify({"error": "Missing multipart/form-data"}), 400

    user_id = _get_user_id()
    if not user_id:
        logger.warning("Upload rejected: missing user_id")
        return jsonify({"error": "Missing file or user_id"}), 400

    file = request.files.get("file")
    if not file:
        logger.warning("Upload rejected: no file received in request.files")
        return jsonify({"error": "No file was received"}), 400

    file_mimetype = getattr(file, "content_type", None) or getattr(file, "mimetype", None)
    file_size = getattr(file, "content_length", None)
    logger.info(
        "Upload file details: filename=%s, mimetype=%s, content_length=%s",
        file.filename,
        file_mimetype,
        file_size,
    )

    try:
        result = manager.process_upload(user_id=user_id, file_storage=file)
    except Exception as e:
        logger.exception("Upload processing failed: %s", e)
        result = {"status": "FAILED", "error": str(e)}

    status_code = 200
    result_status = result.get("status", "")
    if result_status in ["FAILED", "REJECTED"]:
        status_code = 400
    if result_status in ["CONFIRMATION_REQUIRED", "AWAITING_REVIEW", "STORED"]:
        status_code = 200
    return jsonify(sanitize_for_json(result)), status_code


@vault_bp.route("/<document_type>", methods=["POST"])
def verify_specific_document(document_type):
    engine_map = {
        "verify-offline-ekyc": "aadhaar_ekyc",
        "verify-ocr": "aadhaar_ocr",
        "verify-income": "income_verifier",
        "verify-caste": "caste_verifier",
        "verify-ration": "ration_verifier",
        "verify-disability": "disability_verifier",
    }

    engine = engine_map.get(document_type)
    if not engine:
        return jsonify({"error": "Invalid verification route"}), 404

    user_id = _get_user_id()
    file = request.files.get("file")
    share_code = request.form.get("share_code")

    if not file or not user_id:
        return jsonify({"error": "Missing file or user_id"}), 400

    path = os.path.join(UPLOAD_FOLDER, f"VAULT_{int(time.time())}_{file.filename}")
    file.save(path)

    try:
        result = orchestrator.process_document(
            user_id=user_id,
            file_path=path,
            original_filename=file.filename,
            share_code=share_code,
            force_engine=engine,
        )
    finally:
        SecurityManager.secure_cleanup([path])

    return jsonify(sanitize_for_json(result)), 200


@vault_bp.route("/extract", methods=["POST"])
def extract_document_fields():
    user_id = _get_user_id()
    file = request.files.get("file")
    share_code = request.form.get("share_code")
    force_engine = request.form.get("force_engine")

    if not file or not user_id:
        return jsonify({"error": "Missing file or user_id"}), 400

    path = os.path.join(UPLOAD_FOLDER, f"VAULT_{int(time.time())}_{file.filename}")
    file.save(path)

    try:
        result = extractor.infer(
            user_id=user_id,
            file_path=path,
            original_filename=file.filename,
            share_code=share_code,
            force_engine=force_engine,
        )
    finally:
        SecurityManager.secure_cleanup([path])

    return jsonify(sanitize_for_json(result)), 200


@vault_bp.route("/status/<verification_id>", methods=["GET"])
def get_verification_status(verification_id):
    doc = DocumentVault.get_document_by_id(verification_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"status": doc.get("verification_status")}), 200


@vault_bp.route("/identity", methods=["GET"])
def get_identity_lock():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    user, identity_profile = get_user_identity(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db = get_db()
    doc_count = 0
    if db is not None:
        doc_count = db.vault_documents.count_documents({"user_id": str(user_id)})

    reset_meta = user.get("identity_reset_meta", {}) or {}
    last_reset_at = reset_meta.get("last_reset_at")
    last_reset_dt = None
    if last_reset_at:
        try:
            last_reset_dt = datetime.datetime.fromisoformat(str(last_reset_at))
        except Exception:
            last_reset_dt = None
    next_allowed = None
    reset_available = True
    if last_reset_dt:
        next_allowed = last_reset_dt + datetime.timedelta(hours=RESET_COOLDOWN_HOURS)
        reset_available = datetime.datetime.utcnow() >= next_allowed

    return jsonify({
        "identityLocked": bool(user.get("identity_locked", False)),
        "identityProfile": sanitize_for_json(_serialize_identity(user, identity_profile)),
        "documentCount": doc_count,
        "resetAvailable": reset_available,
        "lastResetAt": last_reset_dt.isoformat() if last_reset_dt else sanitize_for_json(last_reset_at),
        "nextResetAllowedAt": next_allowed.isoformat() if next_allowed else None,
    }), 200


@vault_bp.route("/", methods=["GET"])
def get_vault():
    user_id = request.args.get("user_id")
    query = request.args.get("q", "")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    docs = DocumentVault.search_documents(user_id, query) if query else DocumentVault.get_user_vault(user_id)

    user, identity_profile = get_user_identity(user_id)
    identity_locked = bool(user.get("identity_locked", False)) if user else False

    return jsonify({
        "documents": sanitize_for_json(docs),
        "identity_locked": identity_locked,
        "identity_profile": sanitize_for_json(_serialize_identity(user, identity_profile)) if user else {},
    }), 200


@vault_bp.route("/documents", methods=["GET"])
def list_documents():
    user_id = request.args.get("user_id")
    query = request.args.get("q", "")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    docs = DocumentVault.search_documents(user_id, query) if query else DocumentVault.get_user_vault(user_id)
    return jsonify({"documents": sanitize_for_json(docs), "query": query}), 200


@vault_bp.route("/document/<document_id>", methods=["GET"])
def get_document(document_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    doc = DocumentVault.get_document_by_id(document_id, user_id=user_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    return jsonify({"document": sanitize_for_json(doc)}), 200


@vault_bp.route("/search", methods=["GET"])
def search_vault():
    user_id = request.args.get("user_id")
    query = request.args.get("q", "")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    docs = DocumentVault.search_documents(user_id, query)
    return jsonify({"documents": sanitize_for_json(docs), "query": query}), 200


@vault_bp.route("/identity/reset", methods=["POST"])
def reset_identity_lock():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or request.args.get("user_id")
    password = data.get("password", "")
    reason = data.get("reason", "User Requested")
    device = data.get("device", request.headers.get("User-Agent", "unknown"))
    ip_address = data.get("ipAddress") or request.headers.get("X-Forwarded-For") or request.remote_addr

    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    if not password:
        return jsonify({"error": "Password required for identity reset"}), 400

    db = get_db()
    if db is None:
        return jsonify({"error": "Database not available"}), 500

    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    reset_meta = user.get("identity_reset_meta", {}) or {}
    last_reset_at = reset_meta.get("last_reset_at")
    if last_reset_at:
        try:
            last_reset_dt = datetime.datetime.fromisoformat(str(last_reset_at))
            if datetime.datetime.utcnow() < last_reset_dt + datetime.timedelta(hours=RESET_COOLDOWN_HOURS):
                return jsonify({
                    "error": f"Identity reset is only allowed once every {RESET_COOLDOWN_HOURS} hours",
                }), 429
        except Exception:
            pass

    stored_password = user.get("password")
    if isinstance(stored_password, str):
        stored_password = stored_password.encode("utf-8")
    if not stored_password or not bcrypt.checkpw(password.encode("utf-8"), stored_password):
        return jsonify({"error": "Authentication failed"}), 401

    deleted_docs = DocumentVault.purge_user_vault(user_id)
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "identity_locked": False,
                "identity_profile": {},
                "aadhaar_verified": False,
                "identity_reset_meta": {
                    "last_reset_at": datetime.datetime.utcnow().isoformat(),
                    "last_reason": reason,
                },
                "updated_at": datetime.datetime.utcnow(),
            },
            "$unset": {
                "aadhaar_verified_at": "",
                "aadhaar_reference_id": "",
                "identity_reset_pending": "",
                "identity_reset_token": "",
            },
        },
    )

    reset_event = {
        "action": "Identity Reset",
        "userId": str(user_id),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "ipAddress": ip_address,
        "device": device,
        "reason": reason,
        "deletedDocuments": deleted_docs,
    }
    AuditLogger.record("identity_reset", user_id, reset_event)
    AuditLogger.record("identity_reset_notification_queued", user_id, {
        "channels": ["email", "sms"],
        "reason": reason,
    })

    return jsonify({
        "message": "Identity successfully reset. Please verify your Aadhaar again to continue using the SATYA AI Document Vault.",
        "identityLocked": False,
        "deletedDocuments": deleted_docs,
        "resetEvent": reset_event,
    }), 200


@vault_bp.route("/document/<document_id>", methods=["DELETE"])
def delete_document(document_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    success = DocumentVault.delete_document(user_id, document_id)
    if success:
        return jsonify({"message": "Document deleted"}), 200
    return jsonify({"error": "Document not found"}), 404


@vault_bp.route("/<document_id>", methods=["DELETE"])
def delete_document_alias(document_id):
    return delete_document(document_id)

@vault_bp.route("/download/<document_id>", methods=["GET"])
def download_document(document_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id parameter"}), 400
    try:
        doc = DocumentVault.get_document_by_id(document_id, user_id=user_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        storage_path = doc.get("storage_path")
        file_name = doc.get("document_name", "document")
        if not storage_path or not os.path.exists(storage_path):
            return jsonify({"error": "File not found on server"}), 404
        temp_dir = os.path.join(tempfile.gettempdir(), "vault_downloads")
        os.makedirs(temp_dir, exist_ok=True)
        decrypted_path = os.path.join(temp_dir, f"decrypted_{uuid.uuid4().hex}_{os.path.basename(storage_path)}")
        SecurityManager.decrypt_file(storage_path, decrypted_path)
        return send_file(decrypted_path, as_attachment=True, download_name=file_name)
    except Exception as e:
        logger.error(f"Error in download_document: {e}")
        return jsonify({"error": "Internal server error"}), 500



@vault_bp.route("/preview/<document_id>", methods=["GET"])
def preview_document(document_id):
    from flask import after_this_request
    import tempfile
    import uuid
    import os
    
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
        
    doc = DocumentVault.get_document_by_id(document_id, user_id=user_id)
    if not doc or not doc.get("storage_path") or not os.path.exists(doc["storage_path"]):
        return jsonify({"error": "File not found"}), 404
        
    decrypted_path = None
    try:
        temp_dir = os.path.join(tempfile.gettempdir(), "vault_previews")
        os.makedirs(temp_dir, exist_ok=True)
        decrypted_path = os.path.join(temp_dir, f"preview_{uuid.uuid4().hex}_{os.path.basename(doc['storage_path'])}")
        SecurityManager.decrypt_file(doc["storage_path"], decrypted_path)
        
        mimetype = "application/pdf" if doc.get("file_type") == "pdf" else f"image/{doc.get('file_type', 'jpeg')}"
        response = send_file(decrypted_path, mimetype=mimetype)
        
        @after_this_request
        def cleanup(res):
            try:
                if decrypted_path and os.path.exists(decrypted_path):
                    os.remove(decrypted_path)
            except Exception:
                pass
            return res
            
        return response
    except Exception as e:
        logger.error(f"Error in preview_document: {e}")
        # Ensure cleanup on failure as well
        try:
            if decrypted_path and os.path.exists(decrypted_path):
                os.remove(decrypted_path)
        except Exception:
            pass
        return jsonify({"error": "Internal server error"}), 500

@vault_bp.route("/thumbnail/<document_id>", methods=["GET"])
def thumbnail_document(document_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
        
    doc = DocumentVault.get_document_by_id(document_id, user_id=user_id)
    if not doc or not doc.get("thumbnail_path") or not os.path.exists(doc["thumbnail_path"]):
        return jsonify({"error": "File not found"}), 404
        
    return send_file(doc["thumbnail_path"], mimetype="image/png")

@vault_bp.route("/stats", methods=["GET"])
def vault_stats():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    stats = DocumentVault.get_dashboard_stats(user_id)
    return jsonify(stats), 200


# ══════════════════════════════════════════════════════════════════════════════
# NEW: POST /api/vault/confirm_review_with_otp
# ══════════════════════════════════════════════════════════════════════════════

@vault_bp.route("/confirm_review_with_otp", methods=["POST"])
def confirm_review_with_otp():
    """
    Accept the user's reviewed/corrected metadata for a document, but only
    after validating the OTP sent to their email.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    document_id = data.get("document_id")
    verified_fields = data.get("verified_data", {})
    corrections = data.get("corrections", [])
    otp_code = data.get("otp_code")

    if not user_id or not document_id:
        return jsonify({"error": "user_id and document_id are required"}), 400
        
    if not otp_code:
        return jsonify({"error": "OTP is required"}), 400

    # 1. Verify OTP first
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ua = request.headers.get("User-Agent", "")
    
    otp_result = verify_otp(
        user_id=user_id,
        otp_code=otp_code,
        purpose="document_verification",
        document_id=document_id,
        ip_address=ip,
        user_agent=ua
    )
    
    if not otp_result.get("success"):
        status_code = 400
        if "attempt" in otp_result.get("message", "").lower():
            status_code = 429
        return jsonify({
            "error": otp_result.get("message"),
            "verified": False
        }), status_code

    # 2. Proceed with document review confirmation
    doc = DocumentVault.get_document_by_id(document_id, user_id=user_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    db = get_db()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 500

    # Record individual corrections in the audit trail
    for correction in corrections:
        AuditLogger.record_correction(
            user_id=user_id,
            document_id=document_id,
            field_name=correction.get("field", ""),
            ocr_value=correction.get("ocr_value", ""),
            corrected_value=correction.get("corrected_value", ""),
            reason=correction.get("reason", ""),
        )

    AuditLogger.record_review(
        user_id=user_id,
        document_id=document_id,
        decision="confirmed_with_otp",
        corrections=corrections,
    )

    # Determine final document_status based on confidence
    confidence = float(doc.get("confidence", 0))
    if confidence >= 80.0:
        final_status = "Accepted"
    else:
        final_status = "Rejected"

    now = datetime.datetime.utcnow()
    update_fields = {
        "verified_data": verified_fields,
        "document_status": final_status,
        "identity_status": "Verified" if final_status == "Accepted" else "Unverified",
        "verification_status": final_status,
        "review_timestamp": now,
        "verification_timestamp": now,
        "updated_at": now,
    }

    if verified_fields:
        update_fields["metadata"] = verified_fields

    from bson import ObjectId as _OID
    db.vault_documents.update_one(
        {"_id": _OID(document_id), "user_id": str(user_id)},
        {"$set": update_fields}
    )

    # Invalidate eligibility cache for this user
    try:
        from routes.eligibility_routes import _ELIGIBILITY_CACHE
        keys_to_remove = [k for k in _ELIGIBILITY_CACHE if k.startswith(f"{user_id}:")]
        for k in keys_to_remove:
            del _ELIGIBILITY_CACHE[k]
    except Exception:
        pass

    logger.info("[REVIEW] Document %s confirmed with OTP by user %s -> %s", document_id, user_id, final_status)

    return jsonify({
        "message": f"Document review and OTP verified. Status: {final_status}",
        "document_id": document_id,
        "document_status": final_status,
        "identity_status": update_fields["identity_status"],
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# NEW: POST /api/vault/confirm_review
# ══════════════════════════════════════════════════════════════════════════════

@vault_bp.route("/confirm_review", methods=["POST"])
def confirm_review():
    """
    Accept the user's reviewed/corrected metadata for a document.
    Updates verified_data, generates audit trail for corrections,
    and sets the final document_status based on confidence tier.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    document_id = data.get("document_id")
    verified_fields = data.get("verified_data", {})
    corrections = data.get("corrections", [])

    if not user_id or not document_id:
        return jsonify({"error": "user_id and document_id are required"}), 400

    doc = DocumentVault.get_document_by_id(document_id, user_id=user_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    db = get_db()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 500

    # Record individual corrections in the audit trail
    for correction in corrections:
        AuditLogger.record_correction(
            user_id=user_id,
            document_id=document_id,
            field_name=correction.get("field", ""),
            ocr_value=correction.get("ocr_value", ""),
            corrected_value=correction.get("corrected_value", ""),
            reason=correction.get("reason", ""),
        )

    AuditLogger.record_review(
        user_id=user_id,
        document_id=document_id,
        decision="confirmed",
        corrections=corrections,
    )

    # Determine final document_status based on confidence
    confidence = float(doc.get("confidence", 0))
    if confidence >= 80.0:
        final_status = "Accepted"
    else:
        final_status = "Rejected"

    now = datetime.datetime.utcnow()
    update_fields = {
        "verified_data": verified_fields,
        "document_status": final_status,
        "identity_status": "Verified" if final_status == "Accepted" else "Unverified",
        "verification_status": final_status,
        "review_timestamp": now,
        "verification_timestamp": now,
        "updated_at": now,
    }

    # Also update the legacy metadata field
    if verified_fields:
        update_fields["metadata"] = verified_fields

    from bson import ObjectId as _OID
    db.vault_documents.update_one(
        {"_id": _OID(document_id), "user_id": str(user_id)},
        {"$set": update_fields}
    )

    # Invalidate eligibility cache for this user
    try:
        from routes.eligibility_routes import _ELIGIBILITY_CACHE
        keys_to_remove = [k for k in _ELIGIBILITY_CACHE if k.startswith(f"{user_id}:")]
        for k in keys_to_remove:
            del _ELIGIBILITY_CACHE[k]
    except Exception:
        pass

    logger.info("[REVIEW] Document %s confirmed by user %s -> %s", document_id, user_id, final_status)

    return jsonify({
        "message": f"Document review completed. Status: {final_status}",
        "document_id": document_id,
        "document_status": final_status,
        "identity_status": update_fields["identity_status"],
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# EXTENDED: GET /api/vault/health
# ══════════════════════════════════════════════════════════════════════════════

@vault_bp.route("/health", methods=["GET"])
def vault_health():
    """Full subsystem health check for the Document Vault."""
    import numpy as np
    import cv2
    from vault.ocr_utils import _PADDLEOCR_READER, PADDLEOCR_AVAILABLE, TESSERACT_AVAILABLE
    from vault.document_manager import TEMP_ROOT, STORAGE_ROOT, THUMBNAIL_ROOT

    health = {
        "status": "Healthy",
        "version": "2.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "subsystems": {
            "mongodb": {"status": "Unknown"},
            "paddleocr": {"status": "Unavailable", "model_loaded": False},
            "tesseract": {"status": "Unavailable"},
            "encryption": {"status": "Available"},
            "upload_directory": {"status": "Unknown"},
            "thumbnail_directory": {"status": "Unknown"},
            "preview_generator": {"status": "Available"},
        },
        "stats": {},
    }

    degraded = False

    # MongoDB
    try:
        db = get_db()
        if db is not None:
            db.command("ping")
            health["subsystems"]["mongodb"] = {"status": "Healthy"}

            # Quick stats from DB
            total = db.vault_documents.count_documents({})
            accepted = db.vault_documents.count_documents({"document_status": "Accepted"})
            rejected = db.vault_documents.count_documents({"document_status": "Rejected"})
            awaiting = db.vault_documents.count_documents({"document_status": "Awaiting Review"})

            pipeline = [{"$group": {
                "_id": None,
                "avg_conf": {"$avg": "$confidence"},
                "avg_time": {"$avg": "$processing_time"},
            }}]
            agg = list(db.vault_documents.aggregate(pipeline))
            avg_conf = round(agg[0]["avg_conf"] or 0, 2) if agg and agg[0].get("avg_conf") else 0
            avg_time = round(agg[0]["avg_time"] or 0, 2) if agg and agg[0].get("avg_time") else 0

            health["stats"] = {
                "total_documents": total,
                "accepted": accepted,
                "rejected": rejected,
                "awaiting_review": awaiting,
                "average_confidence": avg_conf,
                "average_processing_time": avg_time,
            }
        else:
            health["subsystems"]["mongodb"] = {"status": "Unavailable"}
            degraded = True
    except Exception as e:
        health["subsystems"]["mongodb"] = {"status": "Error", "error": str(e)}
        degraded = True

    # PaddleOCR
    if PADDLEOCR_AVAILABLE:
        health["subsystems"]["paddleocr"] = {
            "status": "Healthy",
            "model_loaded": _PADDLEOCR_READER is not None,
        }
    else:
        degraded = True

    # Tesseract
    if TESSERACT_AVAILABLE:
        health["subsystems"]["tesseract"] = {"status": "Healthy"}
    else:
        degraded = True

    # Directories
    for label, path in [("upload_directory", UPLOAD_FOLDER), ("thumbnail_directory", THUMBNAIL_ROOT)]:
        if os.path.isdir(path) and os.access(path, os.W_OK):
            health["subsystems"][label] = {"status": "Healthy"}
        else:
            health["subsystems"][label] = {"status": "Unavailable"}
            degraded = True

    if degraded:
        health["status"] = "Degraded"

    return jsonify(health), 200 if health["status"] == "Healthy" else 503


# ══════════════════════════════════════════════════════════════════════════════
# NEW: GET /api/vault/analytics
# ══════════════════════════════════════════════════════════════════════════════

@vault_bp.route("/analytics", methods=["GET"])
def vault_analytics():
    """Admin diagnostics dashboard data."""
    db = get_db()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 500

    collection = db.vault_documents

    # Overall counts
    total = collection.count_documents({})
    accepted = collection.count_documents({"document_status": "Accepted"})
    rejected = collection.count_documents({"document_status": "Rejected"})
    awaiting = collection.count_documents({"document_status": "Awaiting Review"})

    # Aggregates
    agg_pipeline = [{"$group": {
        "_id": None,
        "avg_confidence": {"$avg": "$confidence"},
        "avg_processing_time": {"$avg": "$processing_time"},
    }}]
    agg = list(collection.aggregate(agg_pipeline))
    avg_confidence = round(agg[0]["avg_confidence"] or 0, 2) if agg and agg[0].get("avg_confidence") else 0
    avg_processing_time = round(agg[0]["avg_processing_time"] or 0, 2) if agg and agg[0].get("avg_processing_time") else 0

    # Document type distribution
    type_pipeline = [
        {"$group": {"_id": "$document_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    type_dist = {r["_id"]: r["count"] for r in collection.aggregate(type_pipeline) if r["_id"]}

    # OCR engine usage
    engine_pipeline = [
        {"$group": {"_id": "$ocr_engine", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    engine_usage = {r["_id"]: r["count"] for r in collection.aggregate(engine_pipeline) if r["_id"]}

    # Daily uploads (last 7 days)
    seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    daily_pipeline = [
        {"$match": {"created_at": {"$gte": seven_days_ago}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    daily_uploads = {r["_id"]: r["count"] for r in collection.aggregate(daily_pipeline)}

    # OCR success rate (confidence >= 80 is considered successful)
    ocr_success = collection.count_documents({"confidence": {"$gte": 80}})
    ocr_success_rate = round((ocr_success / max(total, 1)) * 100, 1)

    # Verification success rate
    verified_count = collection.count_documents({"identity_status": "Verified"})
    verification_success_rate = round((verified_count / max(total, 1)) * 100, 1)

    # Duplicate rate
    dup_pipeline = [
        {"$match": {"version": {"$gt": 1}}},
        {"$count": "duplicates"},
    ]
    dup_result = list(collection.aggregate(dup_pipeline))
    duplicate_count = dup_result[0]["duplicates"] if dup_result else 0
    duplicate_rate = round((duplicate_count / max(total, 1)) * 100, 1)

    # Average identity match score from audit logs
    audit_collection = db.vault_audit_logs
    match_pipeline = [
        {"$match": {"action": "eligibility_check"}},
        {"$group": {
            "_id": None,
            "avg_match_score": {"$avg": "$payload.match_score"},
        }},
    ]
    match_agg = list(audit_collection.aggregate(match_pipeline))
    avg_match_score = round(match_agg[0]["avg_match_score"] or 0, 1) if match_agg and match_agg[0].get("avg_match_score") else 0

    return jsonify({
        "total_documents": total,
        "accepted": accepted,
        "rejected": rejected,
        "awaiting_review": awaiting,
        "average_confidence": avg_confidence,
        "average_processing_time": avg_processing_time,
        "average_identity_match_score": avg_match_score,
        "ocr_success_rate": ocr_success_rate,
        "verification_success_rate": verification_success_rate,
        "duplicate_rate": duplicate_rate,
        "duplicate_count": duplicate_count,
        "document_type_distribution": type_dist,
        "ocr_engine_usage": engine_usage,
        "daily_uploads": daily_uploads,
    }), 200
