import datetime
import re
from difflib import SequenceMatcher

from bson import ObjectId

from database import get_db
from vault.policy import ACCEPT_SCORE, CONFIRM_SCORE, MISMATCH_RESPONSE
from vault.utils import VaultUtils


def _normalize_tokens(value):
    text = VaultUtils.normalize_text(value)
    return [token for token in text.split() if token]


def _field_value(value):
    if isinstance(value, dict):
        if "value" in value:
            return value.get("value", "")
        if "Value" in value:
            return value.get("Value", "")
    return value or ""


def _field_confidence(value, default=0.0):
    if isinstance(value, dict):
        if "confidence" in value:
            return float(value.get("confidence") or 0.0)
        if "Confidence" in value:
            return float(value.get("Confidence") or 0.0)
    return float(default or 0.0)


def calculate_name_similarity(name1, name2):
    tokens1 = _normalize_tokens(name1)
    tokens2 = _normalize_tokens(name2)
    if not tokens1 and not tokens2:
        return 100.0
    if not tokens1 or not tokens2:
        return 0.0

    joined1 = " ".join(tokens1)
    joined2 = " ".join(tokens2)
    ratio = SequenceMatcher(None, joined1, joined2).ratio() * 100

    if tokens1 == tokens2:
        return 100.0

    token_score = 0.0
    matched = 0
    for token in tokens1:
        if token in tokens2:
            matched += 1
            continue
        if len(token) > 1 and any(other.startswith(token[0]) or token.startswith(other[0]) for other in tokens2):
            matched += 0.5
    token_score = (matched / max(len(tokens1), len(tokens2))) * 100
    return round(max(ratio, token_score), 2)


def _identity_profile_view(user):
    profile = user.get("identity_profile") or {}
    if not profile:
        return {}
    return {
        "userId": str(user.get("_id")),
        "fullName": _field_value(profile.get("fullName") or profile.get("full_name") or user.get("name", "")),
        "dob": _field_value(profile.get("dob", "")),
        "gender": _field_value(profile.get("gender", "")),
        "maskedAadhaar": _field_value(profile.get("maskedAadhaar") or profile.get("masked_aadhaar", "")),
        "aadhaarReferenceId": _field_value(profile.get("aadhaarReferenceId") or profile.get("aadhaar_reference_id", "")),
        "identityLocked": bool(user.get("identity_locked", False)),
        "verifiedAt": _field_value(profile.get("verifiedAt") or profile.get("verified_at", "")),
        "confidence": _field_confidence(profile.get("confidence", 0), 0.0),
        "documentType": _field_value(profile.get("documentType") or profile.get("document_type", "")),
        "verificationMethod": _field_value(profile.get("verificationMethod") or profile.get("verification_method", "")),
        "verificationStatus": _field_value(profile.get("verificationStatus") or profile.get("verification_status", "")),
    }


def get_user_identity(user_id):
    db = get_db()
    if db is None:
        return None, None
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return None, None
    return user, _identity_profile_view(user)


def _get_name_from_data(extracted_data):
    if not isinstance(extracted_data, dict):
        return ""
    return _field_value(extracted_data.get("owner_name") or extracted_data.get("full_name") or extracted_data.get("name") or "")


def build_identity_lock(user_id, extracted_data, verification_context=None):
    verification_context = verification_context or {}
    document_type = verification_context.get("document_type", "")
    verification_method = verification_context.get("verification_method", "")
    confidence = verification_context.get("confidence", 0.0)
    return {
        "userId": str(user_id),
        "fullName": VaultUtils.canonicalize_name(_get_name_from_data(extracted_data)),
        "dob": VaultUtils.normalize_date(_field_value(extracted_data.get("dob", ""))),
        "gender": VaultUtils.normalize_gender(_field_value(extracted_data.get("gender", ""))),
        "maskedAadhaar": VaultUtils.mask_aadhaar(_field_value(extracted_data.get("masked_aadhaar", ""))),
        "aadhaarReferenceId": str(_field_value(extracted_data.get("reference_id") or extracted_data.get("aadhaar_reference_id") or "")),
        "identityLocked": True,
        "verifiedAt": VaultUtils.now_iso(),
        "confidence": round(float(confidence or 0.0), 2),
        "documentType": document_type,
        "verificationMethod": verification_method,
        "verificationStatus": "Verified",
    }


def lock_identity_if_needed(user_id, extracted_data, verification_context=None):
    db = get_db()
    if db is None:
        return False, None, "Database unavailable"

    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return False, None, "User not found"

    if user.get("identity_locked"):
        return False, _identity_profile_view(user), "Identity already locked"

    full_name = VaultUtils.canonicalize_name(_get_name_from_data(extracted_data))
    dob = VaultUtils.normalize_date(_field_value(extracted_data.get("dob", "")))
    if not full_name or not dob:
        return False, None, "Aadhaar verification failed. Full name and DOB are required."

    lock = build_identity_lock(user_id, extracted_data, verification_context=verification_context)
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "identity_locked": True,
                "identity_profile": lock,
                "aadhaar_verified": True,
                "aadhaar_verified_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow(),
            },
            "$unset": {
                "identity_reset_pending": "",
                "identity_reset_token": "",
            },
        },
    )
    return True, lock, "Identity successfully verified and locked."


def _score_address(address_a, address_b):
    if not address_a or not address_b:
        return 0.0
    return VaultUtils.similarity(address_a, address_b)


def _extract_family_members(extracted_data):
    raw_members = extracted_data.get("family_members", [])
    if isinstance(raw_members, str):
        parts = re.split(r"[,;/|]\s*|\n+", raw_members)
        return [VaultUtils.canonicalize_name(part) for part in parts if part.strip()]
    if isinstance(raw_members, list):
        return [VaultUtils.canonicalize_name(part) for part in raw_members if str(part).strip()]
    return []


def _family_member_match(user, identity_profile, extracted_data):
    family_members = _extract_family_members(extracted_data)
    if not family_members:
        return False

    candidates = [
        VaultUtils.canonicalize_name(identity_profile.get("fullName", "")),
        VaultUtils.canonicalize_name(user.get("name", "")),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        candidate_tokens = [token for token in candidate.split() if len(token) > 1]
        for member in family_members:
            if not member:
                continue
            member_text = member.lower()
            if candidate.lower() == member_text:
                return True
            if calculate_name_similarity(candidate, member) >= 85:
                return True
            if any(token.lower() in member_text for token in candidate_tokens if len(token) > 2):
                return True
    return False


def _weighted_identity_score(identity_profile, extracted_data):
    name_score = calculate_name_similarity(_field_value(identity_profile.get("fullName", "")), _get_name_from_data(extracted_data))
    dob_score = 100.0 if VaultUtils.normalize_date(_field_value(identity_profile.get("dob", ""))) == VaultUtils.normalize_date(_field_value(extracted_data.get("dob", ""))) else 0.0

    profile_gender = VaultUtils.normalize_gender(_field_value(identity_profile.get("gender", "")))
    doc_gender = VaultUtils.normalize_gender(_field_value(extracted_data.get("gender", "")))
    gender_score = 100.0 if profile_gender and doc_gender and profile_gender == doc_gender else 0.0

    # Only use name, dob, gender — aadhaar_number and address are excluded
    overall = (
        (name_score * 0.50)
        + (dob_score * 0.30)
        + (gender_score * 0.20)
    )
    return round(overall, 2), {
        "name": round(name_score, 2),
        "dob": round(dob_score, 2),
        "gender": round(gender_score, 2),
    }


def evaluate_identity_match(user_id, document_type, extracted_data):
    db = get_db()
    if db is None:
        return False, 0.0, False, "Database not available", {}

    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return False, 0.0, False, "User not found", {}

    identity_locked = bool(user.get("identity_locked", False))
    identity_profile = _identity_profile_view(user)

    doc_type_clean = (document_type or "").lower().replace(" ", "_")

    if not identity_locked:
        if doc_type_clean not in {"aadhaar_ekyc", "aadhaar_ocr", "aadhaar_card", "aadhaar"}:
            return False, 0.0, False, "Identity Lock required. Please verify Aadhaar first.", identity_profile
        locked, lock_profile, message = lock_identity_if_needed(
            user_id,
            extracted_data,
            verification_context={
                "document_type": "Aadhaar Card" if "ocr" in doc_type_clean or "card" in doc_type_clean or doc_type_clean == "aadhaar" else "Aadhaar Offline e-KYC",
                "verification_method": "Offline eKYC + AI OCR" if doc_type_clean == "aadhaar_ekyc" else "Aadhaar OCR + AI",
                "confidence": 98.0,
            },
        )
        if not locked:
            return False, 0.0, False, message, identity_profile
        return True, 100.0, False, message, lock_profile

    if document_type == "ration_card":
        if _family_member_match(user, identity_profile, extracted_data):
            return True, 100.0, False, "Ration Card family verification succeeded.", identity_profile
        return False, 42.0, False, "Identity Mismatch. The logged-in user is not listed as a family member on this Ration Card.", identity_profile

    overall_score, breakdown = _weighted_identity_score(identity_profile, extracted_data)
    dob_matches = VaultUtils.normalize_date(_field_value(identity_profile.get("dob", ""))) == VaultUtils.normalize_date(_field_value(extracted_data.get("dob", "")))

    if overall_score >= ACCEPT_SCORE and dob_matches:
        return True, overall_score, False, "Identity Match succeeded.", identity_profile
    if CONFIRM_SCORE <= overall_score < ACCEPT_SCORE:
        return True, overall_score, True, "This document is similar to your identity profile. Please confirm to continue.", identity_profile

    return False, overall_score, False, MISMATCH_RESPONSE["message"], identity_profile
