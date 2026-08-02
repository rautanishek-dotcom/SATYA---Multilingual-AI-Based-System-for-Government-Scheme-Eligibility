from flask import Blueprint, request, jsonify
from database import get_db
from bson import ObjectId
from .translator_utils import translate_from_english
from datetime import datetime

schemes_bp = Blueprint('schemes', __name__)

def calculate_age(dob_str):
    if not dob_str:
        return 0
    try:
        # Normalize date format
        dob_str = str(dob_str).strip()
        if '-' in dob_str:
            # Check for YYYY-MM-DD
            if dob_str.count('-') == 2:
                parts = dob_str.split('-')
                if len(parts[0]) == 4: # YYYY-MM-DD
                    dob = datetime.strptime(dob_str, "%Y-%m-%d")
                else: # DD-MM-YYYY
                    dob = datetime.strptime(dob_str, "%d-%m-%Y")
            else:
                 return 0
        elif '/' in dob_str:
             # Check for DD/MM/YYYY
             dob = datetime.strptime(dob_str, "%d/%m/%Y")
        elif len(dob_str) == 4 and dob_str.isdigit():
             # Just year
             return datetime.today().year - int(dob_str)
        else:
             return 0
             
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        return 0

def translate_scheme(scheme, target_lang):
    if not target_lang or target_lang == 'en':
        return scheme
    
    fields_to_translate = ['name', 'description', 'target_beneficiaries', 'application_process', 'benefits', 'steps']
    for field in fields_to_translate:
        if field in scheme and scheme[field]:
            scheme[field] = translate_from_english(scheme[field], target_lang)
    
    # Translate rules if present
    if 'rules' in scheme and scheme['rules']:
        rules = scheme['rules']
        # Categories translation
        if 'allowed_categories' in rules and isinstance(rules['allowed_categories'], list):
            if 'all' in rules['allowed_categories']:
                rules['allowed_categories'] = [translate_from_english("All Categories", target_lang)]
            else:
                rules['allowed_categories'] = [translate_from_english(cat.upper() if len(cat) <= 3 else cat.title(), target_lang) for cat in rules['allowed_categories']]
        
        # Gender translation
        if 'gender' in rules and isinstance(rules['gender'], list):
            if 'all' in rules['gender']:
                rules['gender'] = [translate_from_english("All", target_lang)]
            else:
                rules['gender'] = [translate_from_english(g.title(), target_lang) for g in rules['gender']]
                
        # Special category translation
        if 'special_category' in rules and isinstance(rules['special_category'], list):
            if 'all' in rules['special_category']:
                rules['special_category'] = [translate_from_english("None", target_lang)]
            else:
                rules['special_category'] = [translate_from_english(sc.replace('_', ' ').title(), target_lang) for sc in rules['special_category']]

    # Translate state if it's not "All India"
    if 'state' in scheme and scheme['state'] and scheme['state'] != 'All India':
        scheme['state'] = translate_from_english(scheme['state'], target_lang)
    
    return scheme

def translate_schemes_in_batch(schemes, target_lang):
    if not target_lang or target_lang == 'en' or not schemes:
        return schemes
    
    from .translator_utils import translate_batch_from_english
    
    # 1. Collect all strings to translate
    strings_to_translate = []
    text_fields = ['name', 'description', 'target_beneficiaries', 'application_process', 'benefits', 'steps', 'state']
    
    for s in schemes:
        for field in text_fields:
            if field in s and s[field]:
                strings_to_translate.append(s[field])
        
        # Rules (Categories, Gender, Special Category)
        if 'rules' in s and s['rules']:
            r = s['rules']
            if 'allowed_categories' in r and isinstance(r['allowed_categories'], list):
                if 'all' in r['allowed_categories']: strings_to_translate.append("All Categories")
                else: 
                    strings_to_translate.extend([cat.upper() if len(cat) <= 3 else cat.title() for cat in r['allowed_categories']])
            
            if 'gender' in r and isinstance(r['gender'], list):
                if 'all' in r['gender']: strings_to_translate.append("All")
                else: strings_to_translate.extend([g.title() for g in r['gender']])
                
            if 'special_category' in r and isinstance(r['special_category'], list):
                if 'all' in r['special_category']: strings_to_translate.append("None")
                else: strings_to_translate.extend([sc.replace('_', ' ').title() for sc in r['special_category']])
                
            if 'state' in r and isinstance(r['state'], list):
                if 'all' in [st.lower() for st in r['state']]: strings_to_translate.append("All India")
                else: strings_to_translate.extend([st.replace('_', ' ').title() for st in r['state']])

    # 2. Batch Translate
    translated_list = translate_batch_from_english(strings_to_translate, target_lang)
    trans_map = dict(zip(strings_to_translate, translated_list))

    # 3. Apply back to schemes
    for s in schemes:
        for field in text_fields:
            if field in s and s[field] in trans_map:
                s[field] = trans_map[s[field]]
        
        if 'rules' in s and s['rules']:
            r = s['rules']
            if 'allowed_categories' in r and isinstance(r['allowed_categories'], list):
                if 'all' in r['allowed_categories']:
                    r['allowed_categories'] = [trans_map.get("All Categories", "All Categories")]
                else:
                    r['allowed_categories'] = [trans_map.get(cat.upper() if len(cat) <= 3 else cat.title(), cat) for cat in r['allowed_categories']]
            
            if 'gender' in r and isinstance(r['gender'], list):
                if 'all' in r['gender']: r['gender'] = [trans_map.get("All", "All")]
                else: r['gender'] = [trans_map.get(g.title(), g) for g in r['gender']]
                
            if 'special_category' in r and isinstance(r['special_category'], list):
                if 'all' in r['special_category']: r['special_category'] = [trans_map.get("None", "None")]
                else: r['special_category'] = [trans_map.get(sc.replace('_', ' ').title(), sc) for sc in r['special_category']]
                
            if 'state' in r and isinstance(r['state'], list):
                if 'all' in [st.lower() for st in r['state']]: r['state'] = [trans_map.get("All India", "All India")]
                else: r['state'] = [trans_map.get(st.replace('_', ' ').title(), st) for st in r['state']]

    return schemes

@schemes_bp.route('/', methods=['GET'])
def get_all_schemes():
    db = get_db()
    lang = request.args.get('lang', 'en')
    schemes = list(db.schemes.find({}))
    
    # Convert ObjectIds to strings
    for scheme in schemes:
        scheme["_id"] = str(scheme["_id"])
        
    if lang != 'en':
        translate_schemes_in_batch(schemes, lang)
        
    return jsonify(schemes), 200

@schemes_bp.route('/<scheme_id>', methods=['GET'])
def get_scheme(scheme_id):
    db = get_db()
    lang = request.args.get('lang', 'en')
    try:
        scheme = db.schemes.find_one({"_id": ObjectId(scheme_id)})
        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404
        scheme["_id"] = str(scheme["_id"])
        translate_scheme(scheme, lang)
        return jsonify(scheme), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def calculate_eligible_schemes_internal(data, db):
    lang = data.get("lang", "en")
    
    # --- 1. Utility: Normalize Data ---
    def normalize(val):
        if val is None: return ""
        return str(val).lower().strip()

    # --- 2. Extract & Normalize Profile Data ---
    age = int(data.get("age", 0)) if data.get("age") else 0
    if not age and data.get("dob"):
        age = calculate_age(data.get("dob"))
        
    income = int(str(data.get("income", 0)).replace(',', '')) if data.get("income") else 0
    category = normalize(data.get("category", ""))
    gender = normalize(data.get("gender", ""))
    occupation = normalize(data.get("occupation", ""))
    state = normalize(data.get("state", ""))
    district = normalize(data.get("district", ""))
    
    # New Socio-Economic Fields
    residence = normalize(data.get("residence", ""))
    bpl_status = data.get("bpl_status")
    income_category = normalize(data.get("income_category", ""))
    ration_card_type = normalize(data.get("ration_card_type", ""))
    
    # Education Fields
    education_level = normalize(data.get("education_level", ""))
    is_student = data.get("is_student")
    
    # Occupation Specifics
    landholding = float(data.get("landholding_size", 0)) if data.get("landholding_size") else 0
    employment_type = normalize(data.get("employment_type", ""))
    business_type = normalize(data.get("business_type", ""))
    business_turnover = int(data.get("business_turnover", 0)) if data.get("business_turnover") else 0
    
    # Special Conditions (Disability, Widow, Minority)
    is_disabled = data.get("is_disabled")
    disability_type = normalize(data.get("disability_type", ""))
    disability_percent = int(data.get("disability_percentage", 0)) if data.get("disability_percentage") else 0
    certificate_uploaded = data.get("certificate_uploaded", False)
    is_widow = data.get("is_widow")
    is_minority = data.get("is_minority")
    is_single_parent = data.get("is_single_parent")
    is_senior_citizen = age >= 60

    # --- 2. Update User Profile in DB ---
    user_id = data.get("user_id")
    if user_id:
        try:
            db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "profile": {
                        "name": data.get("name"),
                        "age": age,
                        "gender": gender,
                        "state": state,
                        "district": district,
                        "income": income,
                        "occupation": occupation,
                        "category": category,
                        "residence": residence,
                        "bpl_status": bpl_status,
                        "education_level": education_level,
                        "is_student": is_student,
                        "landholding": landholding,
                        "special_conditions": {
                            "disabled": is_disabled,
                            "widow": is_widow,
                            "minority": is_minority,
                            "single_parent": is_single_parent
                        }
                    }
                }}
            )
        except Exception as e:
            print("Error updating profile:", str(e))

    # --- 3. Process Eligibility ---
    all_schemes = list(db.schemes.find({}))
    eligible_schemes = []
    ineligible_schemes = []

    for scheme in all_schemes:
        reasons = []
        rules = scheme.get("rules", {})
        total_criteria = 0
        matched_criteria = 0
        
        # State Check
        total_criteria += 1
        scheme_state = scheme.get("state", "All India")
        if scheme_state == "All India" or scheme_state.lower() == state:
            matched_criteria += 1
        else:
            reasons.append(f"StateMismatch:{{'state':'{scheme_state}'}}")

        # Age Check
        if "min_age" in rules:
            total_criteria += 1
            if age >= rules["min_age"]: matched_criteria += 1
            else: reasons.append(f"AgeTooLow:{{'userAge':{age}, 'min':{rules['min_age']}}}")
        if "max_age" in rules:
            total_criteria += 1
            if age <= rules["max_age"]: matched_criteria += 1
            else: reasons.append(f"AgeTooHigh:{{'userAge':{age}, 'max':{rules['max_age']}}}")
            
        # Income Check
        if "max_income" in rules:
            total_criteria += 1
            max_inc = rules["max_income"]
            if income <= max_inc: matched_criteria += 1
            else: reasons.append(f"IncomeTooHigh:{{'userIncome':{income}, 'limit':{max_inc}, 'diff':{income - max_inc}}}")
            
        # Category Check
        if "allowed_categories" in rules and category: # Skip if user skipped
            total_criteria += 1
            allowed = [c.lower() for c in rules["allowed_categories"]]
            if category in allowed or "all" in allowed: matched_criteria += 1
            else: reasons.append(f"CategoryMismatch:{{'allowed':'{', '.join(allowed).upper()}'}}")
            
        # Occupation Check
        if "occupation" in rules and occupation: # Skip if user skipped
            total_criteria += 1
            allowed_occ = [o.lower() for o in rules["occupation"]]
            if occupation in allowed_occ or "all" in allowed_occ: matched_criteria += 1
            else: reasons.append("OccupationMismatch")

        # Disability Logic (Strict)
        if rules.get("disability_required") or "min_disability" in rules:
            total_criteria += 1
            min_d = rules.get("min_disability", 40)
            if is_disabled and disability_percent >= min_d:
                if not certificate_uploaded:
                    reasons.append("DisabilityCertificateRequired")
                else:
                    matched_criteria += 1
                    # Soft Type Match
                    if "disability_type" in rules:
                        allowed_dt = [dt.lower() for dt in rules["disability_type"]]
                        if disability_type not in allowed_dt:
                            reasons.append(f"DisabilityTypeWarning:{{'type':'{', '.join(allowed_dt).title()}'}}")
            else:
                reasons.append(f"DisabilityLow:{{'userPercent':{disability_percent}, 'min':{min_d}}}")

        # BPL / Ration Card Check
        if rules.get("bpl_required") and not bpl_status:
            total_criteria += 1
            reasons.append("BPLStatusRequired")
        elif bpl_status: # If user matches a positive condition
            matched_criteria += 1

        # Calculate Score
        match_score = int((matched_criteria / total_criteria) * 100) if total_criteria > 0 else 100
        
        status = "Eligible"
        if match_score < 100 and match_score >= 50: status = "Partially Eligible"
        elif match_score < 50: status = "Not Eligible"

        scheme_data = {
            "id": str(scheme["_id"]),
            "name": scheme.get("name"),
            "description": scheme.get("description"),
            "official_website": scheme.get("official_website"),
            "target_beneficiaries": scheme.get("target_beneficiaries"),
            "benefits": scheme.get("benefits"),
            "steps": scheme.get("steps"),
            "state": scheme_state,
            "match_score": match_score,
            "status": status,
            "reasons": reasons
        }

        if status == "Eligible": eligible_schemes.append(scheme_data)
        elif status == "Partially Eligible": eligible_schemes.append(scheme_data) # Show partials in main list with tag
        else: ineligible_schemes.append(scheme_data)
            
    # --- 4. Batch Translation ---
    if lang != 'en':
        # Translate reasons
        all_reasons = []
        for s in eligible_schemes + ineligible_schemes:
            all_reasons.extend(s["reasons"])
        
        # We need to translate reasons too
        from .translator_utils import translate_batch_from_english
        translated_reasons = translate_batch_from_english(list(set(all_reasons)), lang)
        reason_map = dict(zip(list(set(all_reasons)), translated_reasons))
        
        for s in eligible_schemes + ineligible_schemes:
            s["reasons"] = [reason_map.get(r, r) for r in s["reasons"]]
            
        translate_schemes_in_batch(eligible_schemes, lang)
        translate_schemes_in_batch(ineligible_schemes, lang)

    return {
        "eligible": eligible_schemes,
        "ineligible": ineligible_schemes
    }

@schemes_bp.route('/eligible', methods=['POST'])
def get_eligible_schemes():
    data = request.json
    db = get_db()
    result = calculate_eligible_schemes_internal(data, db)
    return jsonify(result), 200

# Admin route to add a scheme
@schemes_bp.route('/add', methods=['POST'])
def add_scheme():
    db = get_db()
    data = request.json
    db.schemes.insert_one(data)
    return jsonify({"message": "Scheme added successfully"}), 201

# Admin route to update a scheme
@schemes_bp.route('/update/<scheme_id>', methods=['PUT'])
def update_scheme(scheme_id):
    db = get_db()
    data = request.json
    try:
        result = db.schemes.update_one(
            {"_id": ObjectId(scheme_id)},
            {"$set": data}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Scheme not found"}), 404
        return jsonify({"message": "Scheme updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Admin route to delete a scheme
@schemes_bp.route('/delete/<scheme_id>', methods=['DELETE'])
def delete_scheme(scheme_id):
    db = get_db()
    try:
        result = db.schemes.delete_one({"_id": ObjectId(scheme_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Scheme not found"}), 404
        return jsonify({"message": "Scheme deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
