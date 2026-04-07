from flask import Blueprint, request, jsonify
from database import get_db
import bcrypt
import jwt
import os
import datetime

auth_bp = Blueprint('auth', __name__)
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-satya-key")

@auth_bp.route('/register', methods=['POST'])
def register():
    db = get_db()
    data = request.json
    
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
        
    users = db.users
    existing_user = users.find_one({"email": data["email"]})
    if existing_user:
        return jsonify({"error": "User already exists"}), 400
        
    hashed_password = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt())
    
    user = {
        "name": data.get("name", ""),
        "email": data["email"],
        "password": hashed_password,
        "role": "user",
        "created_at": datetime.datetime.utcnow()
        # Profile fields can be updated later
    }
    
    result = users.insert_one(user)
    return jsonify({"message": "User registered successfully", "user_id": str(result.inserted_id)}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    db = get_db()
    data = request.json
    
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
        
    users = db.users
    user = users.find_one({"email": data["email"]})
    
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
        
    if bcrypt.checkpw(data["password"].encode('utf-8'), user["password"]):
        token = jwt.encode({
            "user_id": str(user["_id"]),
            "role": user.get("role", "user"),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, JWT_SECRET, algorithm="HS256")
        
        # In newer PyJWT versions, encode returns a string. If bytes, decode.
        if isinstance(token, bytes):
            token = token.decode('utf-8')
            
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": str(user["_id"]),
                "name": user.get("name"),
                "email": user["email"],
                "role": user.get("role"),
                "aadhaar_verified": user.get("aadhaar_verified", False),
                "profile": user.get("profile", {})
            }
        }), 200
        
    return jsonify({"error": "Invalid credentials"}), 401
