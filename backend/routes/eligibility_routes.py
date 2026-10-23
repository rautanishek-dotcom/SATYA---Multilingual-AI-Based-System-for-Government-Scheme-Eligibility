"""
Eligibility verification routes for the SATYA system.

Enforces strict identity verification against Accepted vault documents
before allowing scheme generation. Uses verified_data (never raw OCR).
Includes eligibility cache using document SHA-256 hash.
"""

from flask import Blueprint, request, jsonify
from database import get_db
import datetime
import hashlib
import json
import logging
from bson import ObjectId

from vault.utils import VaultUtils
from vault.audit import AuditLogger
from routes.schemes import calculate_eligible_schemes_internal
from services.otp_service import verify_otp

logger = logging.getLogger(__name__)
eligibility_bp = Blueprint('eligibility', __name__)

# In-memory eligibility cache: { "user_id:doc_hash" -> result }
_ELIGIBILITY_CACHE: dict = {}


def _cache_key(user_id: str, doc_hash: str, profile: dict) -> str:
    """Keep cached results scoped to both the verified document and profile."""
    cache_profile = {
        key: value
        for key, value in profile.items()
        if key not in {"otp_code", "force_recheck", "lang"}
    }
    profile_hash = hashlib.sha256(
        json.dumps(cache_profile, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return f"{user_id}:{doc_hash}:{profile_hash}"


def _first_value(*values):
    """Return the first non-empty vault value, including field-wrapper values."""
    for value in values:
        if isinstance(value, dict):
            value = value.get("value") or value.get("Value")
        if value not in (None, ""):
            return value
    return ""


def _verified_disability_profile(user_record):
    """Return disability data saved by the dedicated certificate verifier."""
    certificate = ((user_record or {}).get("documents") or {}).get("disability") or {}
    if certificate.get("status") not in {"Verified", "Partially Verified"}:
        return {}

    extracted = certificate.get("extracted_data") or {}
    percentage = _first_value(
        extracted.get("percentage"),
        extracted.get("disability_percentage"),
    )
    try:
        percentage = int(percentage)
    except (TypeError, ValueError):
        percentage = None

    if percentage is not None and not 0 <= percentage <= 100:
        percentage = None

    return {
        "is_disabled": bool(certificate.get("is_disabled")),
        "has_disability_certificate": True,
        "certificate_uploaded": True,
        "disability_type": _first_value(extracted.get("disability_type")),
        "disability_percentage": percentage if percentage is not None else "",
    }



def _perform_verification_and_eligibility(user_id, data, db, verified_with_otp=False):

    # 1. Prefer the newest accepted Aadhaar identity document. A later income,
    # caste, or other document must not replace the user's identity source.
    accepted_document_query = {
        "user_id": str(user_id),
        "document_status": "Accepted",
        "is_active": True,
    }
    doc = db.vault_documents.find_one(
        {
            **accepted_document_query,
            "$or": [
                {"document_type": {"$regex": "aadhaar", "$options": "i"}},
                {"document_label": {"$regex": "aadhaar", "$options": "i"}},
            ],
        },
        sort=[("created_at", -1)]
    )
    if not doc:
        # Retain compatibility with legacy vault records that did not store a
        # document type, while still requiring an accepted active document.
        doc = db.vault_documents.find_one(accepted_document_query, sort=[("created_at", -1)])

    if not doc:
        return {
            "identity_verified": False,
            "reason": "No verified document found in your Document Vault. "
                      "Upload and verify a government document before checking eligibility."
        }

    # 2. Check eligibility cache
    doc_hash = doc.get("document_hash", "")
    cache_k = _cache_key(str(user_id), doc_hash, data)
    cached = _ELIGIBILITY_CACHE.get(cache_k)
    if cached and not data.get("force_recheck"):
        logger.info("[ELIGIBILITY] Cache hit for user=%s doc_hash=%s", user_id, doc_hash[:12])
        if not verified_with_otp and "eligible_schemes" in cached:
            cached_copy = cached.copy()
            cached_copy["eligible_schemes"] = None
            return cached_copy
        return cached

    # 3. Extract and normalize fields – check verified_data, metadata, and user identity profile fallback
    vdata = doc.get("verified_data") or doc.get("metadata", {})
    user_record = db.users.find_one({"_id": ObjectId(user_id)}) if user_id and ObjectId.is_valid(str(user_id)) else {}
    u_identity = (user_record or {}).get("identity_profile", {})
    caste_identity = (user_record or {}).get("caste_identity_profile", {})
    verified_disability = _verified_disability_profile(user_record)

    data_name = VaultUtils.canonicalize_name(data.get("name"))
    data_dob = VaultUtils.normalize_date(data.get("dob"))
    data_gender = VaultUtils.normalize_gender(data.get("gender"))
    data_state = (data.get("state") or "").strip().lower()
    data_district = (data.get("district") or "").strip().lower()

    # The identity lock is built from a verified vault document. Prefer it, then
    # use the accepted document's verified fields for older vault records.
    doc_name = VaultUtils.canonicalize_name(_first_value(
        u_identity.get("fullName"), u_identity.get("full_name"), u_identity.get("name"),
        vdata.get("owner_name"), vdata.get("full_name"), vdata.get("name"),
    ))
    doc_dob = VaultUtils.normalize_date(_first_value(u_identity.get("dob"), vdata.get("dob")))
    doc_gender = VaultUtils.normalize_gender(_first_value(u_identity.get("gender"), vdata.get("gender")))
    doc_state = str(_first_value(u_identity.get("state"), vdata.get("state")) or "").strip().lower()
    doc_district = str(_first_value(u_identity.get("district"), vdata.get("district")) or "").strip().lower()

    # 4. Calculate weighted identity score
    name_similarity = VaultUtils.similarity(data_name, doc_name)
    name_score = (name_similarity / 100.0) * 50

    # Flexible DOB match: match full date or birth year if full date missing in document
    dob_match = False
    if data_dob and doc_dob:
        if data_dob == doc_dob:
            dob_match = True
        elif len(data_dob) == 4 and doc_dob.startswith(data_dob):
            dob_match = True
        elif len(doc_dob) == 4 and data_dob.startswith(doc_dob):
            dob_match = True

    dob_score = 30 if dob_match else 0

    gender_match = (data_gender != "" and doc_gender != "" and data_gender.lower() == doc_gender.lower())
    gender_score = 10 if gender_match else 0

    # State + District
    if doc_district and data_district:
        state_match = (data_state == doc_state and data_state != "")
        state_score = 5 if state_match else 0
        district_match = (data_district == doc_district)
        district_score = 5 if district_match else 0
    else:
        state_match = (data_state == doc_state and data_state != "")
        state_score = 10 if state_match else 0
        district_score = 0
        district_match = False

    total_score = name_score + dob_score + gender_score + state_score + district_score
    confidence = doc.get("confidence", 0)

    # 5. Determine verification outcome
    verified = True
    reason = ""

    if confidence < 80:
        verified = False
        reason = "OCR confidence too low. Please upload a clearer document."
    elif not dob_match:
        verified = False
        reason = "Date of Birth does not match your document."
    elif total_score < 90:
        verified = False
        reason = f"Identity match score ({total_score:.1f}%) is below the required threshold (90%)."

    # 6. Calculate eligible schemes if verified
    result = None
    if verified:
        # Match schemes using verified vault identity details, while retaining
        # the eligibility-specific answers supplied in the form.
        eligibility_profile = {**data}
        eligibility_profile.update({
            "name": doc_name or data.get("name", ""),
            "dob": doc_dob or data.get("dob", ""),
            "gender": doc_gender or data.get("gender", ""),
            "state": doc_state or data.get("state", ""),
            "district": doc_district or data.get("district", ""),
            "user_id": user_id,
        })
        if (user_record or {}).get("caste_locked"):
            eligibility_profile["category"] = _first_value(
                caste_identity.get("category"), (user_record or {}).get("caste_category"), data.get("category")
            )
        if verified_disability:
            eligibility_profile.update(verified_disability)
        result = calculate_eligible_schemes_internal(eligibility_profile, db)

    # 7. Build response
    match_breakdown = {
        "name": {"score": round(name_score, 1), "similarity": round(name_similarity, 1)},
        "dob": {"score": dob_score, "match": dob_match},
        "gender": {"score": gender_score, "match": gender_match},
        "state": {"score": state_score, "match": state_match},
        "district": {"score": district_score, "match": district_match},
        "total": round(total_score, 1),
    }

    response = {
        "identity_verified": verified,
        "match_score": round(total_score, 1),
        "match_breakdown": match_breakdown,
        "matched_document_id": str(doc["_id"]),
        "document_type": doc.get("document_type", ""),
        "confidence": confidence,
    }

    if verified:
        if verified_with_otp:
            response["eligible_schemes"] = result
        else:
            response["eligible_schemes"] = None
            response["requires_otp"] = True
    else:
        response["reason"] = reason

    # 8. Audit trail
    audit_data = {
        "user_id": user_id,
        "matched_document_id": str(doc["_id"]),
        "match_score": round(total_score, 1),
        "identity_verified": verified,
        "verified_at": datetime.datetime.utcnow().isoformat(),
        "eligible_scheme_count": len(result.get("eligible", [])) if verified and result else 0,
        "match_breakdown": match_breakdown,
        "verified_with_otp": verified_with_otp,
    }
    AuditLogger.record("eligibility_check", user_id, audit_data, document_id=str(doc["_id"]))

    # 9. Update user record
    try:
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "identity_verified": verified,
                "identity_match_score": round(total_score, 1),
                "matched_document_id": str(doc["_id"]),
                "verification_timestamp": audit_data["verified_at"]
            }}
        )
    except Exception as e:
        logger.error("Error updating user verification metadata: %s", e)

    # 10. Cache the result if verified
    if verified and doc_hash:
        # Cache the complete result. The first verification hides schemes until
        # OTP succeeds, but the OTP-confirmed request must receive this result.
        cache_entry = response.copy()
        cache_entry["eligible_schemes"] = result
        cache_entry.pop("requires_otp", None)
        _ELIGIBILITY_CACHE[cache_k] = cache_entry

    return response


@eligibility_bp.route('/verify', methods=['POST'])
def verify_eligibility():
    data = request.json or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    db = get_db()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 500

    response = _perform_verification_and_eligibility(user_id, data, db, verified_with_otp=False)
    return jsonify(response), 200


@eligibility_bp.route('/verify-with-otp', methods=['POST'])
def verify_eligibility_with_otp():
    data = request.json or {}
    user_id = data.get("user_id")
    otp_code = data.get("otp_code")
    
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
        
    if not otp_code:
        return jsonify({"error": "OTP is required"}), 400

    # 1. Verify OTP first
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ua = request.headers.get("User-Agent", "")
    
    otp_result = verify_otp(
        user_id=user_id,
        otp_code=otp_code,
        purpose="eligibility_check",
        ip_address=ip,
        user_agent=ua
    )
    
    if not otp_result.get("success"):
        status_code = 400
        if "attempt" in otp_result.get("message", "").lower():
            status_code = 429
        return jsonify({
            "error": otp_result.get("message"),
            "identity_verified": False
        }), status_code

    db = get_db()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 500

    response = _perform_verification_and_eligibility(user_id, data, db, verified_with_otp=True)
    return jsonify(response), 200



@eligibility_bp.route('/cache/invalidate', methods=['POST'])
def invalidate_cache():
    """Invalidate the eligibility cache for a user (called when documents change)."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    keys_to_remove = [k for k in _ELIGIBILITY_CACHE if k.startswith(f"{user_id}:")]
    for k in keys_to_remove:
        del _ELIGIBILITY_CACHE[k]

    return jsonify({"message": f"Cache cleared ({len(keys_to_remove)} entries)"}), 200
