from flask import Blueprint, request, jsonify
from database import get_db
from bson import ObjectId

schemes_bp = Blueprint('schemes', __name__)

@schemes_bp.route('/', methods=['GET'])
def get_all_schemes():
    db = get_db()
    schemes = list(db.schemes.find({}))
    # Convert ObjectIds to strings
    for scheme in schemes:
        scheme["_id"] = str(scheme["_id"])
    return jsonify(schemes), 200

@schemes_bp.route('/<scheme_id>', methods=['GET'])
def get_scheme(scheme_id):
    db = get_db()
    try:
        scheme = db.schemes.find_one({"_id": ObjectId(scheme_id)})
        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404
        scheme["_id"] = str(scheme["_id"])
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
            
        # State check
        if "state" in rules and state not in rules["state"] and "all" not in rules["state"]:
             matches = False
             
        if matches:
            scheme["_id"] = str(scheme["_id"])
            eligible_schemes.append({
                "id": scheme["_id"],
                "name": scheme.get("name"),
                "description": scheme.get("description"),
                "official_website": scheme.get("official_website"),
                "target_beneficiaries": scheme.get("target_beneficiaries"),
                "application_process": scheme.get("application_process"),
                "match_score": 100 # For complex ML this would vary
            })
            
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
