from flask import Blueprint, request, jsonify
from database import get_db
from faq_data import get_faqs
from .translator_utils import detect_language, translate_to_english, translate_from_english

chatbot_bp = Blueprint('chatbot', __name__)

# --- MASSIVE KEYWORD LIBRARY ---
GREETINGS = {
    "hi", "hello", "hey", "hii", "hiii", "hey there", "namaste", "pranam", "vanakkam", "vanakam", "namaskara", "adaab", "satsriakal",
    "good morning", "good evening", "good afternoon", "gm", "ge", "ga", "help", "support", "greet", "start", "hi satya", "hello satya",
    "नमस्ते", "नमस्कार", "हैलो", "हाय", "வணக்கம்", "నమస్కారం", "ನಮಸ್ಕಾರ", "നമസ്കാരം", "നമസ്തേ", "નમસ્તે", "নমস্কার", "नमस्कार"
}

THANKS = {
    "thanks", "thank you", "thank u", "thx", "thnk u", "shukriya", "dhanyawad", "dhanyavaad", "nandri", "dhanyavadagalu",
    "धन्यवाद", "शुक्रिया", "நன்றி", "ಧನ್ಯವಾದಗಳು", "ಧನ್ಯವಾದ", "ధన్యవాదాలు", "നന്ദി", "આભાર", "ধন্যবাদ"
}

# Exhaustive Mapping: 150+ keywords found in schemes and common user queries
CATEGORY_MAP = {
    # Agriculture / Farmers
    "farmer": "agriculture", "kisan": "agriculture", "krishi": "agriculture", "agriculture": "agriculture", 
    "crop": "agriculture", "land": "agriculture", "tractor": "agriculture", "fertilizer": "agriculture", 
    "seed": "agriculture", "farming": "agriculture", "cultivation": "agriculture", "fasal": "agriculture",
    "bima": "agriculture", "insurance": "agriculture", "irrigation": "agriculture", "pumps": "agriculture",
    "organic": "agriculture", "harvest": "agriculture", "soil": "agriculture", "matsya": "agriculture",
    "fisheries": "agriculture", "bees": "agriculture", "honey": "agriculture", "dairy": "agriculture",
    
    # Health / Medical
    "health": "health", "medical": "health", "doctor": "health", "medicine": "health", 
    "hospital": "health", "insurance": "health", "card": "health", "ayushman": "health", 
    "sick": "health", "disease": "health", "emergency": "health", "treatment": "health",
    "pregnant": "health", "maternity": "health", "delivery": "health", "nutrition": "health",
    "poshan": "health", "vaccine": "health", "injection": "health", "generic": "health",
    "ambulance": "health", "mental": "health", "disability": "health", "handicap": "health",
    
    # Housing / Toilets / Electricity
    "house": "housing", "home": "housing", "stay": "housing", "building": "housing", 
    "awas": "housing", "yojana": "housing", "toilet": "housing", "electricity": "housing", 
    "water": "housing", "tap": "housing", "shelter": "housing", "rural": "housing",
    "urban": "housing", "slum": "housing", "gas": "housing", "lpg": "housing", "saubhagya": "housing",
    
    # Business / Loans / Jobs
    "business": "business", "startup": "business", "loan": "business", "money": "business", 
    "finance": "business", "entrepreneur": "business", "industry": "business", "msme": "business", 
    "mudra": "business", "shop": "business", "credit": "business", "investment": "business",
    "work": "business", "job": "business", "employment": "business", "mgnrega": "business",
    "unemployed": "business", "skill": "business", "training": "business", "artisan": "business",
    "khadi": "business", "weaver": "business", "craft": "business", "tender": "business",
    
    # Students / Education
    "student": "students", "education": "students", "school": "students", "college": "students", 
    "scholarship": "students", "study": "students", "laptop": "students", "tablet": "students", 
    "exam": "students", "degree": "students", "university": "students", "course": "students",
    "literacy": "students", "schooling": "students", "teacher": "students", "fellowship": "students",
    "phd": "students", "merit": "students", "online": "students", "training": "students",
    
    # Social Welfare / Pension / Identity
    "social": "social", "pension": "social", "poor": "social", "elderly": "social", 
    "widow": "social", "disabled": "social", "worker": "social", "bpl": "social", 
    "security": "social", "welfare": "social", "poverty": "social", "old": "social",
    "orphan": "social", "transgender": "social", "tribal": "social", "sc": "social", "st": "social",
    
    # Documents / Identification
    "identity": "documents", "aadhaar": "documents", "pan": "documents", "document": "documents", 
    "certificate": "documents", "card": "documents", "ration": "documents", "voter": "documents", 
    "passport": "documents", "verify": "documents", "link": "documents", "apply": "documents",
    "digilocker": "documents", "birth": "documents", "caste": "documents", "income": "documents",
    "domicile": "documents", "residence": "documents", "address": "documents",

    # States
    "maharashtra": "state_maharashtra", "karnataka": "state_karnataka", "tamil nadu": "state_tamil_nadu",
    "tamilnadu": "state_tamil_nadu", "up": "state_uttar_pradesh", "uttar pradesh": "state_uttar_pradesh",
    "west bengal": "state_west_bengal", "bengal": "state_west_bengal", "gujarat": "state_gujarat",
    "rajasthan": "state_rajasthan", "kerala": "state_kerala", "punjab": "state_punjab",
    "delhi": "state_delhi", "haryana": "state_haryana", "bihar": "state_bihar", "mp": "state_madhya_pradesh"
}

STATE_OPTIONS = [
    "Maharashtra", "Karnataka", "Tamil Nadu", "Uttar Pradesh", "West Bengal", "Gujarat", "Rajasthan", "Kerala", "Punjab"
]

# Matches that boost retrieval confidence
SCHEME_BOOSTER = set(CATEGORY_MAP.keys()) | {
    "kanya", "sumangala", "vatsalya", "sukanya", "samriddhi", "jan", "dhan", "pmegp", "svanidhi", 
    "vishwakarma", "diksha", "nipun", "samagra", "shreyas", "karmayogi", "agnipath", "suraksha", "bima", "jyoti"
}

# --- HELPERS ---

def get_localized_suggestions(lang):
    from .translator_utils import STATIC_UI_CACHE
    return STATIC_UI_CACHE["suggestions"].get(lang, STATIC_UI_CACHE["suggestions"]["en"])

def find_best_match_doc(query, faqs):
    query_lower = query.lower().strip()
    query_clean = query_lower.replace("?", "").replace(".", "").replace("!", "").replace(",", "").strip()
    query_words = set(query_clean.split())
    stop_words = {"what", "is", "the", "how", "to", "for", "a", "an", "in", "of", "and", "are", "can", "do", "i", "my", "me", "please", "tell", "about", "which", "give", "show", "list", "know", "want", "need", "get"}
    query_keywords = query_words - stop_words
    
    best_match = None
    best_score = 0
    
    for faq in faqs:
        # Ultra-safe document traversal
        en_data = faq.get("en", faq) # Fallback to top-level if not nested correctly
        faq_q = en_data.get("question", "").lower().replace("?", "").replace(".", "").replace("!", "")
        if not faq_q: continue
        
        faq_words = set(faq_q.split()) - stop_words
        if query_clean == faq_q.strip(): return faq
        
        if query_keywords and faq_words:
            common = query_keywords & faq_words
            score = len(common) / max(len(query_keywords), 1)
            
            booster_matches = query_keywords & faq_words & SCHEME_BOOSTER
            if booster_matches: score += (0.3 * len(booster_matches))
            if query_clean in faq_q or faq_q in query_clean: score += 0.4
                
            if score > best_score:
                best_score = score
                best_match = faq
    
    return best_match if best_score >= 0.3 else None

# --- ROUTES ---

@chatbot_bp.route('', methods=['POST'])
@chatbot_bp.route('/', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    manual_lang = data.get("lang")
    
    detected_lang = detect_language(query)
    target_lang = manual_lang if manual_lang and manual_lang != 'auto' else detected_lang
    
    from .translator_utils import STATIC_UI_CACHE
    
    if not query:
        msg = STATIC_UI_CACHE["greeting"].get(target_lang, STATIC_UI_CACHE["greeting"]["en"])
        return jsonify({"response": msg, "suggestions": get_localized_suggestions(target_lang)}), 200

    q_lower = query.lower().strip().replace("!", "").replace(".", "")
    
    # Check for Greetings
    if q_lower in GREETINGS or any(g in q_lower for g in ["who are you", "what are you", "help me"]):
        msg = STATIC_UI_CACHE["greeting"].get(target_lang, STATIC_UI_CACHE["greeting"]["en"])
        return jsonify({"response": msg, "suggestions": get_localized_suggestions(target_lang)}), 200

    # Check for Thank You
    if any(t in q_lower for t in THANKS):
        thanks_msg = "You're very welcome! I am happy to help. Do you have any other questions about government schemes?"
        response_text = translate_from_english(thanks_msg, target_lang)
        return jsonify({"response": response_text, "suggestions": get_localized_suggestions(target_lang)}), 200

    english_query = translate_to_english(query) if target_lang != 'en' else query
    
    db = get_db()
    faqs = list(db.faqs.find({}, {"_id": 0}))

    # Punctuation cleaning
    eq_lower = english_query.lower().replace("?", "").replace(".", "").replace(",", "").strip()
    
    # --- SPECIAL: STATE MENU ---
    if eq_lower == "state" or any(s in eq_lower for g in ["which state", "my state", "state list"] for s in [g]):
        prompt = "Which state are you from? Please select or type your state name."
        response_text = translate_from_english(prompt, target_lang)
        # Localize state options
        from .translator_utils import translate_batch_from_english
        localized_states = translate_batch_from_english(STATE_OPTIONS, target_lang)
        return jsonify({"response": response_text, "suggestions": localized_states, "detected_lang": detected_lang}), 200

    # Category detection (Improved: checks each word)
    matched_cat = None
    query_words = eq_lower.split()
    for word in query_words:
        word = word.strip()
        if word in CATEGORY_MAP:
            matched_cat = CATEGORY_MAP[word]
            break
            
    if matched_cat:
        cat_faqs = [f for f in faqs if f.get("category") == matched_cat]
        if cat_faqs:
            display_name = matched_cat.replace("state_", "").replace("_", " ").title()
            if "state_" in matched_cat:
                intro = f"Here are the major government schemes available in {display_name}:"
            else:
                intro = f"I found several schemes related to {display_name}."
            
            response_text = translate_from_english(intro, target_lang)
            suggestions = [f.get(target_lang, f.get("en", f)).get("question", "Scheme Info") for f in cat_faqs[:5]]
            return jsonify({"response": response_text, "suggestions": suggestions, "detected_lang": detected_lang}), 200

    # FAQ Match
    match_doc = find_best_match_doc(english_query, faqs)
    if match_doc:
        en_data = match_doc.get("en", match_doc)
        lang_data = match_doc.get(target_lang, en_data)
        final_answer = lang_data.get('answer', en_data.get('answer', "I'm sorry, I don't have the translation for this yet."))
        
        related = []
        for f in faqs:
            if f.get("category") == match_doc.get("category") and f != match_doc:
                f_en = f.get("en", f)
                related.append(f.get(target_lang, f_en).get('question'))
                if len(related) >= 4: break
                
        return jsonify({"response": final_answer, "suggestions": [r for r in related if r], "detected_lang": detected_lang}), 200

    # Scheme Search
    scheme = db.schemes.find_one({"name": {"$regex": eq_lower.split()[0] if eq_lower.split() else "", "$options": "i"}})
    if scheme:
        intro = f"I found information on {scheme['name']}: {scheme['description']}."
        return jsonify({"response": translate_from_english(intro, target_lang), "suggestions": get_localized_suggestions(target_lang)}), 200

    # Fallback
    fallback_msg = STATIC_UI_CACHE["fallback"].get(target_lang, STATIC_UI_CACHE["fallback"]["en"])
    return jsonify({"response": fallback_msg, "suggestions": get_localized_suggestions(target_lang), "detected_lang": detected_lang}), 200

@chatbot_bp.route('/suggestions', methods=['GET'])
def get_suggestions_route():
    from .translator_utils import STATIC_UI_CACHE
    lang = request.args.get("lang", "en").lower()
    welcome_msg = STATIC_UI_CACHE["greeting"].get(lang, STATIC_UI_CACHE["greeting"]["en"])
    return jsonify({"suggestions": get_localized_suggestions(lang), "welcome_message": welcome_msg}), 200
