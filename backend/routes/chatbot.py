from flask import Blueprint, request, jsonify
from database import get_db
from faq_data import get_faqs
from .translator_utils import detect_language, translate_to_english, translate_from_english

chatbot_bp = Blueprint('chatbot', __name__)

# --- MASSIVE KEYWORD LIBRARY ---
GREETINGS = {
    "hi", "hello", "hey", "hii", "hiii", "hey there", "namaste", "pranam", "vanakkam", "vanakam", "namaskara", "adaab", "satsriakal",
    "good morning", "good evening", "good afternoon", "gm", "ge", "ga", "help", "support", "greet", "start", "hi satya", "hello satya",
    "नमस्ते", "नमस्कार", "हैलो", "हाय", "வணக்கம்", "నమస్కారం", "ನಮಸ್ಕಾರ", "നമസ്കാരം", "നമസ്തേ", "નમસ્તે", "নমস্কার", "नमस्कार",
    "main menu", "menu", "go back", "back", "home", "start over"
}

THANKS = {
    "thanks", "thank you", "thank u", "thx", "thnk u", "shukriya", "dhanyawad", "dhanyavaad", "nandri", "dhanyavadagalu",
    "धन्यवाद", "शुक्रिया", "நன்றி", "ಧನ್ಯವಾದಗಳು", "ಧನ್ಯವಾದ", "ధన్యవాదాలు", "നന്ദി", "આભાર", "ধন্যবাদ"
}

SMALL_TALK = {
    "how are you", "how r u", "kaise ho", "how do you do", "who created you", "who made you", "what is your name", "who are you"
}

# Exhaustive Mapping: keywords to categories
CATEGORY_MAP = {
    # Agriculture / Farmers
    "farmer": "agriculture", "farmers": "agriculture", "kisan": "agriculture", "krishi": "agriculture", "agriculture": "agriculture", 
    "crop": "agriculture", "land": "agriculture", "tractor": "agriculture", "fertilizer": "agriculture", 
    "seed": "agriculture", "farming": "agriculture", "cultivation": "agriculture", "fasal": "agriculture",
    "bima": "agriculture", "insurance": "agriculture", "irrigation": "agriculture", "pumps": "agriculture",
    "organic": "agriculture", "harvest": "agriculture", "soil": "agriculture", "matsya": "agriculture",
    "fisheries": "agriculture", "bees": "agriculture", "honey": "agriculture", "dairy": "agriculture",
    
    # Health / Medical
    "health": "health", "medical": "health", "doctor": "health", "medicine": "health", 
    "hospital": "health", "ayushman": "health", 
    "sick": "health", "disease": "health", "emergency": "health", "treatment": "health",
    "pregnant": "health", "maternity": "health", "delivery": "health", "nutrition": "health",
    "poshan": "health", "vaccine": "health", "injection": "health", "generic": "health",
    "ambulance": "health", "mental": "health", "disability": "health", "handicap": "health",
    
    # Housing / Toilets / Electricity
    "house": "housing", "building": "housing", 
    "awas": "housing", "toilet": "housing", "electricity": "housing", 
    "water": "housing", "tap": "housing", "shelter": "housing",
    "urban": "housing", "slum": "housing", "gas": "housing", "lpg": "housing", "saubhagya": "housing",
    
    # Business / Loans / Jobs
    "business": "business", "startup": "business", "loan": "business", "loans": "business", "money": "business", 
    "finance": "business", "entrepreneur": "business", "industry": "business", "msme": "business", 
    "mudra": "business", "shop": "business", "credit": "business", "investment": "business",
    "work": "business", "job": "business", "employment": "business", "mgnrega": "business",
    "unemployed": "business", "skill": "business", "artisan": "business",
    "khadi": "business", "weaver": "business", "craft": "business", "tender": "business",
    
    # Students / Education
    "student": "education", "students": "education", "education": "education", "school": "education", "college": "education", 
    "scholarship": "education", "scholarships": "education", "study": "education",
    "exam": "education", "degree": "education", "university": "education", "course": "education",
    "literacy": "education", "schooling": "education", "teacher": "education", "fellowship": "education",
    "phd": "education", "merit": "education",
    
    # Social Welfare / Pension / Identity
    "social": "social", "pension": "social", "poor": "social", "elderly": "social", 
    "widow": "social", "widows": "social", "disabled": "social", "worker": "social", "workers": "social", "bpl": "social", 
    "security": "social", "welfare": "social", "poverty": "social", "old": "social",
    "orphan": "social", "transgender": "social", "tribal": "social", "sc": "social", "st": "social",
    "retirement": "social",

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

def get_scheme_questions(scheme_name, faqs, lang):
    """Get ALL questions related to a specific scheme. Uses the 'scheme' tag for precise matching."""
    import random
    
    # 1. Match by scheme tag (primary, most accurate)
    tagged = [f for f in faqs if f.get("scheme", "").lower() == scheme_name.lower()]
    
    # 2. Also match by scheme name appearing in the question text (secondary)
    name_words = scheme_name.lower().split()
    key_words = [w for w in name_words if len(w) > 3]  # skip small words
    
    for f in faqs:
        if f in tagged:
            continue
        q = f.get("question", "").lower()
        if any(kw in q for kw in key_words):
            tagged.append(f)
    
    # Deduplicate
    seen = set()
    unique = []
    for f in tagged:
        q = f.get("question", "")
        if q not in seen:
            seen.add(q)
            unique.append(f)
    
    q_ens = []
    for f in unique:
        q_en = f.get("en", f).get("question")
        if q_en: q_ens.append(q_en)
        
    if lang != 'en' and q_ens:
        from .translator_utils import translate_batch_from_english
        localized = translate_batch_from_english(q_ens, lang)
    else:
        localized = q_ens
    
    return localized


def get_localized_suggestions(lang, faqs=None):
    from .translator_utils import STATIC_UI_CACHE
    import random
    
    # Navigation triggers — ALWAYS present
    mn = translate_from_english("Main Menu", lang)
    ls = translate_from_english("List All Schemes", lang)
    
    if faqs and len(faqs) > 3:
        # Sample from different categories for diversity
        categories = list(set([f.get('category', 'general') for f in faqs]))
        diverse_sample = []
        random.shuffle(categories)
        cat_pool = {c: [f for f in faqs if f.get('category') == c] for c in categories}
        
        for c in categories[:5]:
            if cat_pool[c]:
                diverse_sample.append(random.choice(cat_pool[c]))
        
        # Fill remaining
        remaining = [f for f in faqs if f not in diverse_sample]
        if remaining:
            diverse_sample.extend(random.sample(remaining, min(len(remaining), 5 - len(diverse_sample))))

        q_ens = []
        for f in diverse_sample:
            q_en = f.get("en", f).get("question")
            if q_en: q_ens.append(q_en)
            
        if lang != 'en' and q_ens:
            from .translator_utils import translate_batch_from_english
            translated_qs = translate_batch_from_english(q_ens, lang)
        else:
            translated_qs = q_ens
            
        localized = [mn, ls]
        for q in translated_qs:
            if q and q not in localized:
                localized.append(q)
        return localized[:7]
        
    # Fallback
    base = list(STATIC_UI_CACHE["suggestions"].get(lang, STATIC_UI_CACHE["suggestions"]["en"]))
    if mn not in base: base = [mn] + base
    if ls not in base: base = [ls] + base
    return base[:7]

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


def build_scheme_response(found_scheme, faqs, target_lang, detected_lang):
    """Build the full response for a matched scheme. Used in both priority and fallback scheme search."""
    from .translator_utils import translate_batch_from_english
    
    response_parts = [f"{found_scheme['name'].upper()}", found_scheme.get('description', '')]
    rules = found_scheme.get('rules', {})
    eligibility = []
    if rules.get('min_age') is not None: 
        eligibility.append(f"• Age: {rules['min_age']}-{rules.get('max_age', 'Unlimited')} years")
    if rules.get('max_income'): 
        eligibility.append(f"• Max Annual Income: Up to ₹{rules['max_income']}")
    if rules.get('allowed_categories') and 'all' not in rules['allowed_categories']: 
        eligibility.append(f"• Categories: {', '.join([c.upper() for c in rules['allowed_categories']])}")
    if rules.get('gender') and 'all' not in rules['gender']:
        eligibility.append(f"• Gender: {', '.join([g.title() for g in rules['gender']])}")
    if eligibility:
        response_parts.append("ELIGIBILITY CRITERIA")
        response_parts.extend(eligibility)
    response_parts.append("REQUIRED DOCUMENTS")
    response_parts.extend(["• Aadhaar Card", "• Identity Proof", "• Income Certificate", "• Bank Details"])
    steps = found_scheme.get('application_process', "Apply via official portal.")
    response_parts.append("HOW TO APPLY")
    response_parts.append(steps)
    if found_scheme.get('benefits'):
        response_parts.append("BENEFITS")
        response_parts.append(found_scheme['benefits'])
    if found_scheme.get('official_website'):
        response_parts.append("OFFICIAL WEBSITE")
        response_parts.append(found_scheme['official_website'])
    
    # Translate all parts in parallel
    translated_parts = translate_batch_from_english(response_parts, target_lang)
    
    # Re-assemble with proper formatting
    final_response = ""
    for orig, trans in zip(response_parts, translated_parts):
        if orig in ["ELIGIBILITY CRITERIA", "REQUIRED DOCUMENTS", "HOW TO APPLY", "BENEFITS", "OFFICIAL WEBSITE"]:
            final_response += f"\n\n{trans}:\n"
        elif orig.startswith("• "):
            final_response += f"{trans}\n"
        else:
            final_response += f"{trans} "

    
    # Build scheme-specific suggestions
    mn = translate_from_english("Main Menu", target_lang)
    ls = translate_from_english("List All Schemes", target_lang)
    
    # Get scheme-specific questions from the database
    scheme_qs = get_scheme_questions(found_scheme['name'], faqs, target_lang)
    
    # If no scheme-specific questions, use category questions
    if not scheme_qs:
        cat_faqs = [f for f in faqs if f.get("category") == found_scheme.get("target_beneficiaries", "").lower()]
        q_ens = []
        for f in cat_faqs[:5]:
            q_en = f.get("en", f).get("question", "")
            if q_en: q_ens.append(q_en)
            
        if target_lang != 'en' and q_ens:
            scheme_qs = translate_batch_from_english(q_ens, target_lang)
        else:
            scheme_qs = q_ens
    
    nav_suggestions = [mn, ls] + [q for q in scheme_qs if q and q != mn and q != ls]
    
    return jsonify({
        "response": final_response, 
        "suggestions": nav_suggestions[:10],  # Show up to 10 scheme-specific questions
        "detected_lang": detected_lang
    }), 200


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
    
    db = get_db()
    faqs = []
    if db is not None:
         faqs = list(db.faqs.find({}, {"_id": 0}))

    if not query:
        msg = STATIC_UI_CACHE["greeting"].get(target_lang, STATIC_UI_CACHE["greeting"]["en"])
        return jsonify({"response": msg, "suggestions": get_localized_suggestions(target_lang, faqs)}), 200

    q_lower = query.lower().strip().replace("!", "").replace(".", "")
    
    # --- SPECIAL: EXACT LOCALIZED MATCHES ---
    from .translator_utils import translate_from_english
    loc_menu = translate_from_english("Main Menu", target_lang).lower()
    loc_list = translate_from_english("List All Schemes", target_lang).lower()
    
    if query.lower().strip() == loc_menu or "menu" in q_lower:
        msg = STATIC_UI_CACHE["greeting"].get(target_lang, STATIC_UI_CACHE["greeting"]["en"])
        return jsonify({"response": msg, "suggestions": get_localized_suggestions(target_lang, faqs)}), 200

    # Ensure "List All Schemes" triggers natively
    trigger_words = [loc_list, "all schemes", "list schemes", "show schemes", "schemes list", "available schemes", "list all schemes"]
    
    # Check for Greetings
    if q_lower in GREETINGS or any(g in q_lower for g in ["who are you", "what are you", "help me"]):
        msg = STATIC_UI_CACHE["greeting"].get(target_lang, STATIC_UI_CACHE["greeting"]["en"])
        return jsonify({"response": msg, "suggestions": get_localized_suggestions(target_lang, faqs)}), 200    # Check for Thank You
    if any(t in q_lower for t in THANKS):
        thanks_msg = "You're very welcome! I am happy to help. Do you have any other questions about government schemes?"
        response_text = translate_from_english(thanks_msg, target_lang)
        return jsonify({"response": response_text, "suggestions": get_localized_suggestions(target_lang, faqs)}), 200

    # Check for Small Talk
    if any(st in q_lower for st in SMALL_TALK):
        st_msg = "I am doing great! I am SATYA, your AI assistant designed to help you with government schemes. How can I assist you today?"
        return jsonify({"response": translate_from_english(st_msg, target_lang), "suggestions": get_localized_suggestions(target_lang, faqs)}), 200

    english_query = translate_to_english(query) if target_lang != 'en' else query
    eq_lower = english_query.lower().replace("?", "").replace(".", "").replace(",", "").strip()
    
    if db is None:
         mn = translate_from_english("Main Menu", target_lang)
         return jsonify({"response": "I am having trouble connecting to my knowledge base. Please try again later.", "suggestions": [mn, translate_from_english("List All Schemes", target_lang)]}), 503

    # --- NEW: DIRECT LOCALIZED MATCH (Highest Priority for clicks) ---
    schemes_data = list(db.schemes.find({}))
    found_scheme = None
    curr_q = query.lower().strip().replace("?", "")
    
    for s in schemes_data:
        # Check against the EXACT localized version we serve in suggestions
        localized_name = translate_from_english(s['name'], target_lang).lower().strip()
        if curr_q == localized_name or curr_q == s['name'].lower():
            found_scheme = s
            break
    
    if found_scheme:
        return build_scheme_response(found_scheme, faqs, target_lang, detected_lang)

    # Punctuation cleaning
    eq_lower = english_query.lower().replace("?", "").replace(".", "").replace(",", "").strip()

    # --- SPECIAL: ALL SCHEMES LIST ---
    trigger_words.extend(["सभी योजनाएं", "सभी योजनाओं"])
    if any(tw in eq_lower for tw in trigger_words) or query.lower().strip() == loc_list:
        schemes = list(db.schemes.find({}, {"name": 1, "_id": 0}))
        scheme_names = [s["name"] for s in schemes]
        
        # Localize all scheme names in the suggestion list
        from .translator_utils import translate_batch_from_english
        localized_schemes = translate_batch_from_english(scheme_names, target_lang)
        
        intro = f"I found {len(scheme_names)} government schemes. Click any scheme name below to see Eligibility, Benefits, and Steps to Apply. \n\nYou can also browse by category: Agriculture, Health, Housing, Education, or Business."
        mn = translate_from_english("Main Menu", target_lang)
        return jsonify({
            "response": translate_from_english(intro, target_lang),
            "suggestions": [mn] + localized_schemes,
            "detected_lang": detected_lang
        }), 200
    
    # --- SPECIAL: STATE MENU ---
    if eq_lower == "state" or any(s in eq_lower for g in ["which state", "my state", "state list"] for s in [g]):
        prompt = "Which state are you from? Please select or type your state name."
        response_text = translate_from_english(prompt, target_lang)
        from .translator_utils import translate_batch_from_english
        localized_states = translate_batch_from_english(STATE_OPTIONS, target_lang)
        mn = translate_from_english("Main Menu", target_lang)
        return jsonify({"response": response_text, "suggestions": [mn] + localized_states, "detected_lang": detected_lang}), 200

    # Category detection (Improved: checks each word)
    matched_cat = None
    query_words = eq_lower.split()
    for word in query_words:
        word = word.strip()
        if word in CATEGORY_MAP:
            matched_cat = CATEGORY_MAP[word]
            break
            
    if matched_cat:
        # Check if query also matches a specific scheme name (Smarter Match)
        schemes_data = list(db.schemes.find({}))
        found_scheme = None
        for s in schemes_data:
            if s['name'].lower() in eq_lower:
                found_scheme = s
                break
        if not found_scheme:
             specific_keywords = ["ayushman", "pm kisan", "mudra", "awas", "jan dhan", "sukanya", "suraksha", "ujjwala"]
             for kw in specific_keywords:
                 if kw in eq_lower:
                     found_scheme = db.schemes.find_one({"name": {"$regex": kw, "$options": "i"}})
                     if found_scheme: break

        if found_scheme:
             return build_scheme_response(found_scheme, faqs, target_lang, detected_lang)

        # If no specific scheme, return category info with MANY category questions
        cat_faqs = [f for f in faqs if f.get("category") == matched_cat]
        if cat_faqs:
            display_name = matched_cat.replace("state_", "").replace("_", " ").title()
            if "state_" in matched_cat:
                intro = f"Here are the major government schemes available in {display_name}:"
            else:
                intro = f"I found several schemes related to {display_name}."
            
            response_text = translate_from_english(intro, target_lang)
            mn = translate_from_english("Main Menu", target_lang)
            ls = translate_from_english("List All Schemes", target_lang)
            q_ens = []
            for f in cat_faqs:
                q_en = f.get("en", f).get("question")
                if q_en: q_ens.append(q_en)
                
            if target_lang != 'en' and q_ens:
                from .translator_utils import translate_batch_from_english
                translated_qs = translate_batch_from_english(q_ens, target_lang)
            else:
                translated_qs = q_ens
                
            suggestions = [mn, ls]
            for q in translated_qs:
                if q and q not in suggestions:
                    suggestions.append(q)
            return jsonify({"response": response_text, "suggestions": suggestions[:12], "detected_lang": detected_lang}), 200

    # FAQ Match
    match_doc = find_best_match_doc(english_query, faqs)
    if match_doc:
        en_data = match_doc.get("en", match_doc)
        en_ans = en_data.get('answer', "I'm sorry, I don't have the translation for this yet.")
        final_answer = translate_from_english(en_ans, target_lang) if target_lang != 'en' else en_ans
        
        # Get related questions from the SAME category and SAME scheme
        mn = translate_from_english("Main Menu", target_lang)
        ls = translate_from_english("List All Schemes", target_lang)
        related = [mn, ls]
        
        match_scheme = match_doc.get("scheme")
        
        # Gather related questions
        q_ens = []
        if match_scheme:
            for f in faqs:
                if f.get("scheme") == match_scheme and f != match_doc:
                    q_en = f.get("en", f).get('question')
                    if q_en and len(q_ens) < 8: q_ens.append(q_en)
                    
        for f in faqs:
            if f.get("category") == match_doc.get("category") and f != match_doc:
                q_en = f.get("en", f).get('question')
                if q_en and q_en not in q_ens and len(q_ens) < 10: q_ens.append(q_en)
                
        if target_lang != 'en' and q_ens:
            from .translator_utils import translate_batch_from_english
            translated_qs = translate_batch_from_english(q_ens, target_lang)
        else:
            translated_qs = q_ens
            
        for q in translated_qs:
            if q and q not in related: related.append(q)
                
        return jsonify({"response": final_answer, "suggestions": related[:10], "detected_lang": detected_lang}), 200

    # --- FINAL SCHEME SEARCH (If no category/FAQ match) ---
    schemes_data = list(db.schemes.find({}))
    found_scheme = None
    for s in schemes_data:
        if s['name'].lower() in eq_lower:
            found_scheme = s
            break
    
    if not found_scheme:
        # Try partial name match
        for s in schemes_data:
            name_words = s['name'].lower().split()
            key_words = [w for w in name_words if len(w) > 3]
            match_count = sum(1 for kw in key_words if kw in eq_lower)
            if match_count >= 2:
                found_scheme = s
                break
    
    if not found_scheme:
        found_scheme = db.schemes.find_one({"name": {"$regex": eq_lower.split()[0] if eq_lower.split() else "", "$options": "i"}})

    if found_scheme:
        return build_scheme_response(found_scheme, faqs, target_lang, detected_lang)

    # Fallback Handling (Structured)
    fallback_text = (
        "Sorry, I couldn't understand your question clearly. \n"
        "You can try asking about:\n"
        "• Specific schemes (e.g., 'What is PM Kisan?')\n"
        "• Eligibility criteria and Documents\n"
        "• Application steps\n\n"
        "You can also select 'List All Schemes' to see everything available."
    )
    
    dynamic_suggestions = get_localized_suggestions(target_lang, faqs)
    
    return jsonify({
        "response": translate_from_english(fallback_text, target_lang), 
        "suggestions": dynamic_suggestions[:7], 
        "detected_lang": detected_lang
    }), 200

@chatbot_bp.route('/suggestions', methods=['GET'])
def get_suggestions_route():
    from .translator_utils import STATIC_UI_CACHE, translate_from_english
    lang = request.args.get("lang", "en").lower()
    welcome_msg = STATIC_UI_CACHE["greeting"].get(lang, STATIC_UI_CACHE["greeting"]["en"])
    
    base_suggestions = get_localized_suggestions(lang)

    return jsonify({"suggestions": base_suggestions[:7], "welcome_message": welcome_msg}), 200
