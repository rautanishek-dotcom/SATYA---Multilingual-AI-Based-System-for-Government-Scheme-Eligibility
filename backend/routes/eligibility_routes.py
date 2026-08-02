"""
Eligibility verification routes for the SATYA system.

Enforces strict identity verification against Accepted vault documents
before allowing scheme generation. Uses verified_data (never raw OCR).
Includes eligibility cache using document SHA-256 hash.
"""

from flask import Blueprint, request, jsonify
from database import get_db
import datetime
import logging
from bson import ObjectId

from vault.utils import VaultUtils
from vault.audit import AuditLogger
from routes.schemes import calculate_eligible_schemes_internal

logger = logging.getLogger(__name__)
eligibility_bp = Blueprint('eligibility', __name__)

# In-memory eligibility cache: { "user_id:doc_hash" -> result }
_ELIGIBILITY_CACHE: dict = {}


def _cache_key(user_id: str, doc_hash: str) -> str:
    return f"{user_id}:{doc_hash}"


@eligibility_bp.route('/verify', methods=['POST'])
def verify_eligibility():
    data = request.json
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    db = get_db()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 500

    # 1. Fetch newest Accepted document (strict enforcement)
    doc = db.vault_documents.find_one(
        {
            "user_id": str(user_id),
            "document_status": "Accepted",
            "is_active": True,
        },
        sort=[("created_at", -1)]
    )

    if not doc:
        return jsonify({
            "identity_verified": False,
            "reason": "No verified document found in your Document Vault. "
                      "Upload and verify a government document before checking eligibility."
        }), 200

    # 2. Check eligibility cache
    doc_hash = doc.get("document_hash", "")
    cache_k = _cache_key(str(user_id), doc_hash)
    cached = _ELIGIBILITY_CACHE.get(cache_k)
    if cached and not data.get("force_recheck"):
        logger.info("[ELIGIBILITY] Cache hit for user=%s doc_hash=%s", user_id, doc_hash[:12])
        return jsonify(cached), 200

    # 3. Extract and normalize fields – use verified_data, never raw OCR
    vdata = doc.get("verified_data") or doc.get("metadata", {})

    data_name = VaultUtils.canonicalize_name(data.get("name"))
    data_dob = VaultUtils.normalize_date(data.get("dob"))
    data_gender = VaultUtils.normalize_gender(data.get("gender"))
    data_state = (data.get("state") or "").strip().lower()
    data_district = (data.get("district") or "").strip().lower()

    doc_name = VaultUtils.canonicalize_name(vdata.get("owner_name"))
    doc_dob = VaultUtils.normalize_date(vdata.get("dob"))
    doc_gender = VaultUtils.normalize_gender(vdata.get("gender"))
    doc_state = (vdata.get("state") or "").strip().lower()
    doc_district = (vdata.get("district") or "").strip().lower()

    # 4. Calculate weighted identity score
    name_similarity = VaultUtils.similarity(data_name, doc_name)
    name_score = (name_similarity / 100.0) * 50

    dob_match = (data_dob == doc_dob and data_dob != "")
    dob_score = 30 if dob_match else 0

    gender_match = (data_gender == doc_gender and data_gender != "")
    gender_score = 10 if gender_match else 0

    # State + District (5% each if district available, else state gets 10%)
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
        result = calculate_eligible_schemes_internal(data, db)

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
        response["eligible_schemes"] = result
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

    # 10. Cache the result (only if verified, to avoid caching failures)
    if verified and doc_hash:
        _ELIGIBILITY_CACHE[cache_k] = response

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
