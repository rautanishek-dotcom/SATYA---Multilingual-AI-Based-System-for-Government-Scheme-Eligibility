from flask import Blueprint, request, jsonify
from database import get_db
from routes.auth import token_required, admin_required
from bson.objectid import ObjectId
import datetime

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard-stats', methods=['GET'])
@token_required
@admin_required
def get_admin_stats(current_user_id, current_user_role):
    """Returns basic stats for the admin dashboard."""
    db = get_db()
    total_users = db.users.count_documents({})
    total_schemes = db.schemes.count_documents({})
    
    return jsonify({
        "total_users": total_users,
        "total_schemes": total_schemes
    }), 200

@admin_bp.route('/add-scheme', methods=['POST'])
@token_required
@admin_required
def add_scheme(current_user_id, current_user_role):
    """Protected API to add a new scheme."""
    db = get_db()
    data = request.json
    
    if not data or not data.get("name"):
        return jsonify({"error": "Scheme name is required"}), 400
        
    new_scheme = {
        "name": data["name"],
        "description": data.get("description", ""),
        "eligibility": data.get("eligibility", ""),
        "benefits": data.get("benefits", ""),
        "category": data.get("category", "General"),
        "state": data.get("state", "All India"),
        "rules": data.get("rules", {}),
        "created_at": datetime.datetime.utcnow(),
        "created_by": current_user_id
    }
    
    result = db.schemes.insert_one(new_scheme)
    return jsonify({
        "message": "Scheme added successfully",
        "scheme_id": str(result.inserted_id)
    }), 201

@admin_bp.route('/delete-scheme/<scheme_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_scheme(current_user_id, current_user_role, scheme_id):
    """Protected API to delete a scheme."""
    db = get_db()
    try:
        result = db.schemes.delete_one({"_id": ObjectId(scheme_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Scheme not found"}), 404
        return jsonify({"message": "Scheme deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Invalid ID format", "details": str(e)}), 400
@admin_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def get_all_users(current_user_id, current_user_role):
    """Returns a list of all users for management."""
    db = get_db()
    users = list(db.users.find({}, {"password": 0})) # Exclude passwords
    for user in users:
        user["_id"] = str(user["_id"])
    return jsonify(users), 200

@admin_bp.route('/all-schemes', methods=['GET'])
@token_required
@admin_required
def get_all_schemes_admin(current_user_id, current_user_role):
    """Returns all schemes with their IDs for management."""
    db = get_db()
    schemes = list(db.schemes.find({}))
    for s in schemes:
        s["_id"] = str(s["_id"])
    return jsonify(schemes), 200

@admin_bp.route('/delete-user/<user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user_id, current_user_role, user_id):
    """Protected API to delete a user. Admins cannot delete themselves."""
    if current_user_id == user_id:
        return jsonify({"error": "You cannot delete your own admin account"}), 400
        
    db = get_db()
    try:
        result = db.users.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Invalid ID format", "details": str(e)}), 400
