from flask import Blueprint, jsonify, request
from bson import ObjectId
import json
import os
import re
import datetime
from pymongo import MongoClient
from .translator_utils import SUPPORTED_LANGUAGES, translate_batch_from_english

# Database connection helper
def get_db():
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    return client["Satya"]

schemes_bp = Blueprint('schemes', __name__)

def translate_scheme(scheme, target_lang):
    if not scheme or target_lang not in SUPPORTED_LANGUAGES or target_lang == 'en':
        return scheme

    # 1. Direct dictionary mappings
    for field, dict_key in [
        ('name', 'name_translations'),
        ('description', 'description_translations'),
        ('benefits', 'benefits_translations'),
        ('target_beneficiaries', 'target_beneficiaries_translations'),
    ]:
        trans_dict = scheme.get(dict_key)
        if isinstance(trans_dict, dict) and trans_dict.get(target_lang):
            scheme[field] = trans_dict[target_lang]

    # 2. Batch fallback for any remaining untranslated fields
    fields = ('name', 'description', 'benefits', 'target_beneficiaries', 'how_to_apply')
    pending_fields = []
    source_values = []
    for field in fields:
        dict_key = f"{field}_translations"
        if isinstance(scheme.get(dict_key), dict) and scheme[dict_key].get(target_lang):
            continue
        val = scheme.get(field)
        if isinstance(val, str) and val.strip():
            pending_fields.append(field)
            source_values.append(val)

    if source_values:
        translated_values = translate_batch_from_english(source_values, target_lang)
        for field, trans in zip(pending_fields, translated_values):
            scheme[field] = trans
    return scheme

def translate_schemes_in_batch(schemes, target_lang):
    if not schemes or target_lang not in SUPPORTED_LANGUAGES or target_lang == 'en':
        return schemes

    for scheme in schemes:
        # Apply pre-translated fields directly from MongoDB document
        for field, dict_key in [
            ('name', 'name_translations'),
            ('description', 'description_translations'),
            ('benefits', 'benefits_translations'),
            ('target_beneficiaries', 'target_beneficiaries_translations'),
        ]:
            trans_dict = scheme.get(dict_key)
            if isinstance(trans_dict, dict) and trans_dict.get(target_lang):
                scheme[field] = trans_dict[target_lang]

    return schemes

@schemes_bp.route('/', methods=['GET'])
def get_all_schemes():
    db = get_db()
    lang = request.args.get('lang', 'en')
    schemes = list(db.schemes.find({"status": "active", "is_active": True}))
    
    for scheme in schemes:
        scheme["_id"] = str(scheme["_id"])
        
    if lang != 'en':
        translate_schemes_in_batch(schemes, lang)
        
    return jsonify(schemes), 200

@schemes_bp.route('/meta', methods=['GET'])
def get_scheme_directory_metadata():
    db = get_db()
    latest = db.schemes.find_one(
        {"status": "active", "is_active": True, "last_verified": {"$exists": True}},
        {"last_verified": 1},
        sort=[("last_verified", -1)],
    )
    return jsonify({"last_verified": latest.get("last_verified") if latest else None}), 200

@schemes_bp.route('/<scheme_id>', methods=['GET'])
def get_scheme(scheme_id):
    db = get_db()
    lang = request.args.get('lang', 'en')
    try:
        scheme = db.schemes.find_one({"_id": ObjectId(scheme_id), "status": "active", "is_active": True})
        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404
        scheme["_id"] = str(scheme["_id"])
        translate_scheme(scheme, lang)
        return jsonify(scheme), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def calculate_eligible_schemes_internal(profile, db):
    # Support both flat and nested profile payload attributes
    dob = profile.get("dob")
    age = profile.get("age") or 0
    if not age and dob:
        try:
            birth_date = datetime.datetime.strptime(dob, "%Y-%m-%d").date()
            today = datetime.datetime.utcnow().date()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except Exception:
            age = 0
    if not age:
        age = 25 # fallback default

    income = int(profile.get("income") or 0)
    category = (profile.get("category") or "").strip().lower()
    occupation = (profile.get("occupation") or "").strip().lower()
    state = (profile.get("state") or "").strip().lower()
    gender = (profile.get("gender") or "").strip().lower()

    # Disability - support flat and nested
    disability_dict = profile.get("disability") if isinstance(profile.get("disability"), dict) else {}
    is_disabled = profile.get("is_disabled") or profile.get("disabled") or disability_dict.get("disabled") or False
    disability_percent = profile.get("disability_percentage") or disability_dict.get("percentage") or 0
    disability_type = (profile.get("disability_type") or disability_dict.get("type") or "").strip().lower()
    certificate_uploaded = profile.get("certificate_uploaded") or profile.get("has_disability_certificate") or disability_dict.get("certificate_uploaded") or False

    # Special Category - support flat and nested
    spec_dict = profile.get("special_category") if isinstance(profile.get("special_category"), dict) else {}
    is_widow = profile.get("is_widow") or profile.get("widow") or spec_dict.get("widow") or False
    is_minority = profile.get("is_minority") or profile.get("minority") or spec_dict.get("minority") or False
    is_single_parent = profile.get("is_single_parent") or profile.get("single_parent") or spec_dict.get("single_parent") or False

    user_id = profile.get("user_id") or profile.get("_id")
    if user_id:
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "profile": {
                        "dob": dob,
                        "age": age,
                        "income": income,
                        "category": category,
                        "occupation": occupation,
                        "state": state,
                        "gender": gender,
                        "disability": {
                            "disabled": bool(is_disabled),
                            "percentage": disability_percent,
                            "type": disability_type,
                            "certificate_uploaded": bool(certificate_uploaded)
                        },
                        "special_category": {
                            "widow": bool(is_widow),
                            "minority": bool(is_minority),
                            "single_parent": bool(is_single_parent)
                        }
                    }
                }}
            )
        except Exception as e:
            print("Error updating profile:", str(e))

    all_schemes = list(db.schemes.find({"status": "active", "is_active": True}))
    eligible_schemes = []
    ineligible_schemes = []

    for scheme in all_schemes:
        reasons = []
        rules = scheme.get("rules") or {}
        total_criteria = 0
        matched_criteria = 0
        
        # State Check
        scheme_state = (scheme.get("state") or "Central").strip()
        if scheme_state not in ("Central", "All India"):
            total_criteria += 1
            if scheme_state.lower() == state or not state:
                matched_criteria += 1
            else:
                reasons.append(f"StateMismatch: scheme is for {scheme_state} state, but your profile state is {state.capitalize() if state else 'Not specified'}")

        # Gender Check
        if rules.get("gender"):
            rule_g = rules.get("gender")
            g_list = [str(g).lower() for g in rule_g] if isinstance(rule_g, list) else [str(rule_g).lower()]
            if "all" not in g_list:
                total_criteria += 1
                if gender in g_list:
                    matched_criteria += 1
                else:
                    reasons.append(f"GenderMismatch: scheme requires {', '.join(g_list).capitalize()}, but your gender is {gender.capitalize() if gender else 'Not specified'}")

        # Age Check
        min_age_val = rules.get("min_age")
        if min_age_val is not None:
            total_criteria += 1
            if age >= min_age_val:
                matched_criteria += 1
            else:
                reasons.append(f"AgeTooLow: minimum required age is {min_age_val}, your age is {age}")

        max_age_val = rules.get("max_age")
        if max_age_val is not None:
            total_criteria += 1
            if age <= max_age_val:
                matched_criteria += 1
            else:
                reasons.append(f"AgeTooHigh: maximum allowed age is {max_age_val}, your age is {age}")
            
        # Income Check
        max_inc_val = rules.get("max_income")
        if max_inc_val is not None:
            total_criteria += 1
            if income <= max_inc_val:
                matched_criteria += 1
            else:
                reasons.append(f"IncomeTooHigh: annual family income limit is ₹{max_inc_val:,}, your income is ₹{income:,}")
            
        # Category Check
        allowed_cats = rules.get("allowed_categories")
        if allowed_cats:
            cats_list = [str(c).lower() for c in allowed_cats] if isinstance(allowed_cats, list) else ["all"]
            if "all" not in cats_list:
                total_criteria += 1
                if category in cats_list:
                    matched_criteria += 1
                else:
                    reasons.append(f"CategoryMismatch: scheme is restricted to {', '.join(cats_list).upper()} category")

        # Occupation Check
        allowed_occs = rules.get("occupation")
        if allowed_occs:
            occs_list = [str(o).lower() for o in allowed_occs] if isinstance(allowed_occs, list) else ["all"]
            if "all" not in occs_list:
                total_criteria += 1
                if occupation in occs_list:
                    matched_criteria += 1
                else:
                    reasons.append(f"OccupationMismatch: scheme applies to {', '.join(occs_list)}")

        # Disability Logic
        if rules.get("disability_required") or "min_disability" in rules:
            total_criteria += 1
            min_d = rules.get("min_disability", 40)
            if is_disabled and disability_percent >= min_d:
                if not certificate_uploaded:
                    reasons.append("DisabilityCertificateRequired: disability certificate is required for verification")
                else:
                    matched_criteria += 1
            else:
                reasons.append(f"DisabilityRequired: minimum {min_d}% disability required")

        # Special Category Checks
        if rules.get("widow_only"):
            total_criteria += 1
            if is_widow:
                matched_criteria += 1
            else:
                reasons.append("WidowOnlyScheme: scheme is exclusively for widows")

        if rules.get("minority_only"):
            total_criteria += 1
            if is_minority:
                matched_criteria += 1
            else:
                reasons.append("MinorityOnlyScheme: scheme is exclusively for minority community members")

        if rules.get("single_parent_only"):
            total_criteria += 1
            if is_single_parent:
                matched_criteria += 1
            else:
                reasons.append("SingleParentOnlyScheme: scheme is exclusively for single parents")

        match_score = (matched_criteria / total_criteria * 100) if total_criteria > 0 else 100.0
        scheme_id = str(scheme["_id"])

        # Scheme is ELIGIBLE only if NO criteria failed (match_score == 100 or len(reasons) == 0)
        if len(reasons) == 0:
            eligible_schemes.append({
                "id": scheme_id,
                "scheme_id": scheme_id,
                "name": scheme.get("name"),
                "description": scheme.get("description"),
                "match_score": round(match_score, 1),
                "reasons": [],
                "benefits": scheme.get("benefits"),
                "official_website": scheme.get("official_website"),
                "official_application_url": scheme.get("official_application_url"),
                "application_deadline": scheme.get("application_deadline"),
                "deadline_status": scheme.get("deadline_status", "not_specified"),
                "state": scheme.get("state", "Central"),
                "name_translations": scheme.get("name_translations", {}),
                "description_translations": scheme.get("description_translations", {}),
                "benefits_translations": scheme.get("benefits_translations", {}),
                "target_beneficiaries_translations": scheme.get("target_beneficiaries_translations", {}),
            })
        else:
            ineligible_schemes.append({
                "id": scheme_id,
                "name": scheme.get("name"),
                "description": scheme.get("description"),
                "match_score": round(match_score, 1),
                "reasons": reasons,
                "official_website": scheme.get("official_website"),
                "state": scheme.get("state", "Central"),
                "name_translations": scheme.get("name_translations", {}),
                "description_translations": scheme.get("description_translations", {}),
                "benefits_translations": scheme.get("benefits_translations", {}),
                "target_beneficiaries_translations": scheme.get("target_beneficiaries_translations", {}),
            })

    return {
        "eligible": eligible_schemes,
        "ineligible": ineligible_schemes,
        "total_analyzed": len(all_schemes)
    }

@schemes_bp.route('/check-eligibility', methods=['POST'])
def check_eligibility():
    db = get_db()
    data = request.json or {}
    lang = data.get('lang') or request.args.get('lang', 'en')
    results = calculate_eligible_schemes_internal(data, db)
    if lang != 'en':
        for item in results.get('eligible', []):
            translate_scheme(item, lang)
        for item in results.get('ineligible', []):
            translate_scheme(item, lang)
    return jsonify(results), 200

@schemes_bp.route('/deadline-alerts/<user_id>', methods=['GET'])
def get_personalized_deadline_alerts(user_id):
    db = get_db()
    lang = request.args.get('lang', 'en')
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = None

    if not user:
        return jsonify({
            "alerts": [],
            "message": "Verify your Aadhaar and/or required caste certificate in Document Vault to receive personalized eligibility and deadline alerts for applicable schemes."
        }), 200

    aadhaar_verified = bool(user.get("identity_locked"))
    caste_verified = bool(user.get("caste_locked"))
    
    if not aadhaar_verified:
        return jsonify({
            "alerts": [],
            "message": "Verify your Aadhaar and/or required caste certificate in Document Vault to receive personalized eligibility and deadline alerts for applicable schemes.",
            "aadhaar_verified": False,
            "caste_verified": caste_verified
        }), 200

    profile = user.get("profile", {}) or {}
    identity_profile = user.get("identity_profile", {}) or {}
    caste_profile = user.get("caste_identity_profile", {}) or {}

    # Merge verified identity into profile
    if identity_profile.get("dob"):
        try:
            dob_parts = str(identity_profile.get("dob")).split("-")
            if len(dob_parts) >= 1:
                birth_year = int(dob_parts[0])
                profile["age"] = datetime.datetime.now().year - birth_year
        except Exception:
            pass
            
    if identity_profile.get("gender"):
        profile["gender"] = identity_profile.get("gender")

    if caste_verified and caste_profile.get("category"):
        profile["category"] = caste_profile.get("category")

    profile["user_id"] = user_id

    eligibility = calculate_eligible_schemes_internal(profile, db)
    alerts = []
    
    today = datetime.datetime.utcnow().date()
    
    for scheme in eligibility.get("eligible", []):
        deadline_str = scheme.get("application_deadline")
        status = scheme.get("deadline_status")
        
        if not deadline_str or status not in ("fixed", "ongoing"):
            continue
            
        try:
            deadline_date = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()
            days_remaining = (deadline_date - today).days
        except Exception:
            continue

        if days_remaining < 0:
            continue

        urgency = "upcoming"
        label = "Upcoming"
        msg = f"{scheme.get('name')} application deadline is {days_remaining} days away."

        if days_remaining == 0:
            urgency = "today"
            label = "Last Day"
            msg = f"Last day to apply. The application deadline for {scheme.get('name')} is today."
        elif days_remaining <= 6:
            urgency = "urgent"
            label = "Urgent"
            msg = f"Apply soon \u2014 only {days_remaining} days remain before the application deadline."
        elif days_remaining <= 14:
            urgency = "apply_soon"
            label = "Closing Soon"
            msg = f"Application deadline approaching: {days_remaining} days remaining to apply for this scheme."

        eligibility_reason = "You are eligible for this scheme based on your verified profile."
        if caste_verified and profile.get("category") and scheme.get("rules", {}).get("allowed_categories"):
            eligibility_reason = "Your verified caste category matches the scheme's eligibility requirements."

        # Translate scheme name for alerts
        localized_name = scheme.get("name")
        if lang != 'en':
            name_trans = scheme.get('name_translations', {})
            if isinstance(name_trans, dict) and lang in name_trans and name_trans[lang]:
                localized_name = name_trans[lang]

        alerts.append({
            "id": scheme.get("id"),
            "name": localized_name,
            "state": scheme.get("state"),
            "application_deadline": deadline_str,
            "days_remaining": days_remaining,
            "urgency": urgency,
            "level": urgency,
            "label": label,
            "message": msg,
            "eligibility_reason": eligibility_reason,
            "official_website": scheme.get("official_website"),
            "official_application_url": scheme.get("official_application_url"),
        })
        
    alerts.sort(key=lambda x: x["days_remaining"])

    return jsonify({
        "alerts": alerts,
        "message": "",
        "aadhaar_verified": aadhaar_verified,
        "caste_verified": caste_verified,
        "total_eligible": len(alerts)
    }), 200
