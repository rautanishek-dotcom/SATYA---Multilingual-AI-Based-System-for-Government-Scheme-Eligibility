from flask import Blueprint, request, jsonify
from database import get_db
from bson import ObjectId
from .translator_utils import translate_from_english

schemes_bp = Blueprint('schemes', __name__)

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

@schemes_bp.route('/eligible', methods=['POST'])
def get_eligible_schemes():
    # Expects user profile data in body
    # age, income, category, gender, occupation, special_category, state
    data = request.json
    db = get_db()
    
    age = int(data.get("age", 0)) if data.get("age") else 0
    income = int(data.get("income", 0)) if data.get("income") else 0
    category = data.get("category", "").lower()
    gender = data.get("gender", "").lower()
    occupation = data.get("occupation", "").lower()
    special_category = data.get("special_category", "").lower()
    state = data.get("state", "").lower()
    
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
                        "district": data.get("district"),
                        "income": income,
                        "occupation": occupation,
                        "category": category,
                        "special_category": special_category
                    }
                }}
            )
        except Exception as e:
            print("Error updating user profile:", str(e))

    all_schemes = list(db.schemes.find({}))
    eligible_schemes = []

    for scheme in all_schemes:
        # State check - Priority filter
        scheme_state = scheme.get("state", "All India")
        state_match = (scheme_state == "All India") or (scheme_state.lower() == state.lower())
        
        if not state_match:
            continue

        # Simple Rule Based Matching
        matches = True
        rules = scheme.get("rules", {})
        
        # Age check
        if "min_age" in rules and age < rules["min_age"]:
            matches = False
        if "max_age" in rules and age > rules["max_age"]:
            matches = False
            
        # Income check
        if "max_income" in rules and income > rules["max_income"]:
            matches = False
            
        # Category check (SC/ST/OBC/General)
        if "allowed_categories" in rules and category not in rules["allowed_categories"] and "all" not in rules["allowed_categories"]:
            matches = False
            
        # Gender check
        if "gender" in rules and gender not in rules["gender"] and "all" not in rules["gender"]:
            matches = False
            
        # Special category check
        if "special_category" in rules and special_category not in rules["special_category"] and "all" not in rules["special_category"]:
            matches = False
            
        if matches:
            scheme["_id"] = str(scheme["_id"])
            
            # Use original values for internal logic, translate for display
            display_scheme = {
                "id": scheme["_id"],
                "name": scheme.get("name"),
                "description": scheme.get("description"),
                "official_website": scheme.get("official_website"),
                "target_beneficiaries": scheme.get("target_beneficiaries"),
                "application_process": scheme.get("application_process"),
                "benefits": scheme.get("benefits"),
                "steps": scheme.get("steps"),
                "state": scheme_state,
                "rules": rules,
                "match_score": 100 
            }
            
            eligible_schemes.append(display_scheme)
            
    lang = data.get("lang", "en")
    if lang != 'en':
        translate_schemes_in_batch(eligible_schemes, lang)

    return jsonify(eligible_schemes), 200

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
