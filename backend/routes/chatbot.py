from flask import Blueprint, request, jsonify
from database import get_db

chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route('/', methods=['POST'])
def chat():
    data = request.json
    query = data.get("query", "").lower()
    db = get_db()
    
    # NLP Processing: Simple keyword matching
    keywords = ["farmer", "women", "student", "senior citizen", "disabled", "loan", "health", "insurance", "pension", "education"]
    matched_keywords = [kw for kw in keywords if kw in query]
    
    if "how to apply for" in query:
        scheme_name = query.split("how to apply for")[-1].strip()
        scheme = db.schemes.find_one({"name": {"$regex": scheme_name, "$options": "i"}})
        if scheme:
            response = f"To apply for {scheme['name']}, please follow these steps: {scheme.get('application_process', 'Visit the official website.')} Link: {scheme.get('official_website')}"
            return jsonify({"response": response}), 200
            
    if matched_keywords:
        schemes = list(db.schemes.find({"description": {"$regex": matched_keywords[0], "$options": "i"}}).limit(3))
        if schemes:
            bullet_points = "\\n".join([f"- {s['name']}: {s['description'][:100]}..." for s in schemes])
            response = f"Based on your query, here are some relevant schemes:\\n{bullet_points}"
            return jsonify({"response": response}), 200
            
    # Default response
    fallback = "I'm SATYA, your Govt Schemes Assistant. Try asking things like 'Which schemes are available for farmers?' or 'How to apply for PM Awas Yojana?'"
    return jsonify({"response": fallback}), 200
