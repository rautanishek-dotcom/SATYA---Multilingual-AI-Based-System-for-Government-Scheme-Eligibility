from flask import Blueprint, request, jsonify
from database import get_db
from faq_data import get_faqs
from language_config import SUPPORTED_LANGUAGE_CODES
from .translator_utils import detect_language, translate_to_english, translate_from_english

import time
import threading
import hashlib

chatbot_bp = Blueprint('chatbot', __name__)

# ============ PRE-TRANSLATED STATIC RESPONSES (ALL 23 LANGUAGES) ============
# These avoid any API calls for common interactions.

STATIC_THANKS_RESPONSE = {
    "en": "You're very welcome! I am happy to help. Do you have any other questions about government schemes?",
    "hi": "आपका बहुत-बहुत स्वागत है! मुझे मदद करके खुशी हुई। क्या आपके सरकारी योजनाओं के बारे में कोई और सवाल हैं?",
    "ta": "மிக்க நன்றி! உதவ மகிழ்ச்சி. அரசு திட்டங்கள் பற்றி வேறு ஏதாவது கேள்விகள் உள்ளதா?",
    "te": "స్వాగతం! సహాయం చేయడం సంతోషం. ప్రభుత్వ పథకాల గురించి మీకు ఇంకా ఏవైనా ప్రశ్నలు ఉన్నాయా?",
    "kn": "ಸ್ವಾಗತ! ಸಹಾಯ ಮಾಡಲು ಸಂತೋಷ. ಸರ್ಕಾರಿ ಯೋಜನೆಗಳ ಬಗ್ಗೆ ನಿಮಗೆ ಇನ್ನೂ ಪ್ರಶ್ನೆಗಳಿವೆಯೇ?",
    "mr": "आपले स्वागत आहे! मदत करून आनंद वाटला. सरकारी योजनांबद्दल तुमचे आणखी काही प्रश्न आहेत का?",
    "bn": "স্বাগতম! সাহায্য করে আনন্দিত। সরকারি প্রকল্প সম্পর্কে আপনার আর কোনো প্রশ্ন আছে?",
    "gu": "આપનું સ્વાગત છે! મદદ કરીને ખુશી થઈ. સરકારી યોજનાઓ વિશે તમારા બીજા કોઈ પ્રશ્નો છે?",
    "ml": "സ്വാഗതം! സഹായിക്കാൻ സന്തോഷം. സർക്കാർ പദ്ധതികളെക്കുറിച്ച് നിങ്ങൾക്ക് മറ്റ് ചോദ്യങ്ങൾ ഉണ്ടോ?",
    "pa": "ਜੀ ਆਇਆਂ ਨੂੰ! ਮਦਦ ਕਰਕੇ ਖੁਸ਼ੀ ਹੋਈ। ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਬਾਰੇ ਤੁਹਾਡੇ ਹੋਰ ਕੋਈ ਸਵਾਲ ਹਨ?",
    "or": "ସ୍ବାଗତ! ସାହାଯ୍ୟ କରି ଖୁସି ଲାଗିଲା। ସରକାରୀ ଯୋଜନା ବିଷୟରେ ଆପଣଙ୍କର ଆଉ କିଛି ପ୍ରଶ୍ନ ଅଛି?",
    "as": "স্বাগতম! সহায় কৰি ভাল লাগিল। চৰকাৰী আঁচনিৰ বিষয়ে আপোনাৰ আৰু কিবা প্ৰশ্ন আছে নেকি?",
    "ur": "آپ کا شکریہ! مدد کرکے خوشی ہوئی۔ کیا آپ کے سرکاری اسکیموں کے بارے میں کوئی اور سوال ہیں؟",
    "ne": "स्वागतम्! मद्दत गर्न खुसी लाग्यो। सरकारी योजनाहरूबारे तपाईंका अरू कुनै प्रश्नहरू छन्?",
    "sd": "توهان جو ڀلي ڪري آيا! مدد ڪري خوشي ٿي. سرڪاري اسڪيمن بابت توهان جا ٻيا ڪي سوال آهن؟",
    "sa": "स्वागतम्! साहाय्यं कृत्वा आनन्दः। शासकीययोजनासु भवतः अन्ये प्रश्नाः सन्ति?",
    "ks": "شکریہ! مدد کٔرِتھ خوشی آیہٕ۔ سرکاری سکیمن بابت تُہنٛز ہور کانٛہ سوال چھُ؟",
    "kok": "स्वागत! मदत करून आनंद जालो. सरकारी योजनांविशीं तुमचे आनीक काय प्रस्न आसात?",
    "doi": "शुकरिया! मदद करियै खुशी होई। सरकारी योजनाएं दे बारे च तुंदे होर कोई सवाल हन?",
    "brx": "नोंथांखौ स्वागत! मदत होनानै गोजों जायो। सरकारि फारामनि बादि नोंथांनि जेबो सोंनाय दं?",
    "mai": "स्वागत! मदति कऽ कऽ खुशी भेल। सरकारी योजनाक बारे मे अहाँक आर कोनो प्रश्न अछि?",
    "mni": "থাগৎলে! মতেং পাংবা য়াম্না নুংঙাইবা তারকপা। সরকারী স্কীমশীংগী মতুংদা নখোয়গী অতোপ্পা ৱাহং লৈরব্রা?",
    "sat": "जोहार! गोड़ो दाड़ेयाक् दाड़ेयां खुसी मेनेदा। सोरकारी जोजनाक् बारे रे आमाक् जेतेगे सोंना दं?",
}

STATIC_SMALLTALK_RESPONSE = {
    "en": "I am doing great! I am SATYA, your AI assistant designed to help you with government schemes. How can I assist you today?",
    "hi": "मैं बहुत अच्छा हूँ! मैं SATYA हूँ, सरकारी योजनाओं में आपकी मदद करने के लिए बना AI सहायक। आज मैं आपकी कैसे मदद कर सकता हूँ?",
    "ta": "நான் நலமாக இருக்கிறேன்! நான் SATYA, அரசு திட்டங்களில் உதவ வடிவமைக்கப்பட்ட AI உதவியாளர். இன்று நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
    "te": "నేను బాగున్నాను! నేను SATYA, ప్రభుత్వ పథకాలలో మీకు సహాయం చేయడానికి రూపొందించిన AI సహాయకుడిని. ఈరోజు నేను మీకు ఎలా సహాయపడగలను?",
    "kn": "ನಾನು ಚೆನ್ನಾಗಿದ್ದೇನೆ! ನಾನು SATYA, ಸರ್ಕಾರಿ ಯೋಜನೆಗಳಲ್ಲಿ ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ವಿನ್ಯಾಸಗೊಳಿಸಿದ AI ಸಹಾಯಕ. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
    "mr": "मी खूप छान आहे! मी SATYA, सरकारी योजनांबद्दल मदत करण्यासाठी तयार AI सहाय्यक. आज मी तुम्हाला कशी मदत करू शकतो?",
    "bn": "আমি ভালো আছি! আমি SATYA, সরকারি প্রকল্পে সাহায্য করার জন্য তৈরি AI সহকারী। আজ আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
    "gu": "હું ખૂબ સારું છું! હું SATYA છું, સરકારી યોજનાઓમાં મદદ કરવા માટે બનાવેલ AI સહાયક. આજે હું તમને કેવી રીતે મદદ કરી શકું?",
    "ml": "ഞാൻ നന്നായിരിക്കുന്നു! ഞാൻ SATYA ആണ്, സർക്കാർ പദ്ധതികളിൽ സഹായിക്കാൻ രൂപകൽപ്പന ചെയ്ത AI സഹായി. ഇന്ന് ഞാൻ നിങ്ങൾക്ക് എങ്ങനെ സഹായിക്കും?",
    "pa": "ਮੈਂ ਬਹੁਤ ਵਧੀਆ ਹਾਂ! ਮੈਂ SATYA ਹਾਂ, ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਬਾਰੇ ਮਦਦ ਲਈ ਬਣਾਇਆ AI ਸਹਾਇਕ। ਅੱਜ ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
    "or": "ମୁଁ ଭଲ ଅଛି! ମୁଁ SATYA, ସରକାରୀ ଯୋଜନାରେ ସାହାଯ୍ୟ ପାଇଁ ନିର୍ମିତ AI ସହାୟକ। ଆଜି ମୁଁ ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବି?",
    "as": "মই ভাল আছোঁ! মই SATYA, চৰকাৰী আঁচনিত সহায় কৰিবলৈ নিৰ্মিত AI সহায়ক। আজি মই আপোনাক কেনেকৈ সহায় কৰিব পাৰোঁ?",
    "ur": "میں بہت اچھا ہوں! میں SATYA ہوں، سرکاری اسکیموں میں مدد کے لیے بنایا گیا AI اسسٹنٹ۔ آج میں آپ کی کیسے مدد کر سکتا ہوں?",
    "ne": "म राम्रो छु! म SATYA हुँ, सरकारी योजनामा मद्दत गर्न बनाइएको AI सहायक। आज म तपाईंलाई कसरी मद्दत गर्न सक्छु?",
    "sd": "مان ٺيڪ آهيان! مان SATYA آهيان، سرڪاري اسڪيمن ۾ مدد لاءِ ٺاهيل AI اسسٽنٽ. اڄ مان توهان جي ڪيئن مدد ڪري سگهان ٿو?",
    "sa": "अहं सम्यक् अस्मि! अहं SATYA, शासकीययोजनासु साहाय्यार्थं निर्मितः AI सहायकः। अद्य अहं भवन्तं कथं साहाय्यं कर्तुं शक्नोमि?",
    "ks": "میں ٹھیک چھس! میں SATYA ہوں، سرکاری سکیمن منٛز مدد کرنہٕ خاطرٕ بناونمت AI اسسٹنٹ۔ اَز میں تُہیٛ کِتھ مدد کٔرِتھ ہیٛکس?",
    "kok": "हांव बरो आसां! हांव SATYA, सरकारी योजनांत मदत करपाक तयार केल्लो AI सहाय्यक. आयज हांव तुमकां कशी मदत करूं येता?",
    "doi": "मैं बड़ा ठीक हां! मैं SATYA हां, सरकारी योजनाएं च मदद करने आस्तै बनाया AI सहायक। अज्ज मैं तुंदी किय्यां मदद करी सकदा हां?",
    "brx": "आं गोजों दं! आं SATYA, सरकारि फारामनिफ्राय मदत होनो थाखाय रचित AI गोहो मदतगार। दिनै आं नोंथांखौ माबोरै मदत होनो हागौ?",
    "mai": "हम बहुत नीक छी! हम SATYA छी, सरकारी योजना मे मदति करबाक लेल बनाएल AI सहायक। आइ हम अहाँकेँ कोना मदति कऽ सकैत छी?",
    "mni": "ঐ ফবা লৈরি! ঐ SATYA, সরকারী স্কীমশীংদা মতেং পাংবা থৌরাং তৌবদা শেমগৎলবা AI এসিস্টেন্ট। ঙসি ঐ নখোয়বু কমনা মতেং পাংগনি?",
    "sat": "इञ ठीक मेनेदा! इञ SATYA, सोरकारी जोजनाक् रे गोड़ो दाड़ेयाक् लागित् ओल आकान AI गोड़ो दाड़ेयां। तिञाक् दिन इञ आमाक् ओकतो लेका गोड़ो दाड़ेयाक् दाड़ेयां?",
}

# ============ AGGRESSIVE CACHING LAYER ============
# Goal: After the FIRST request for a language, all subsequent requests are near-instant.

_faq_cache = {"data": None, "ts": 0}
_scheme_cache = {"data": None, "ts": 0}
_suggestions_cache = {}           # lang → (list, ts)
_greeting_cache = {}              # lang → (text, ts)
_response_cache = {}              # (query_hash, lang) → (response_dict, ts)
_FAQ_TTL = 300                    # 5 min
_SUGGESTION_TTL = 300
_RESPONSE_TTL = 600               # 10 min for full responses

_cache_lock = threading.Lock()

# Track which languages have been pre-warmed in background
_prewarmed_langs = {'en'}
_prewarm_lock = threading.Lock()


def _get_cached_faqs(db):
    now = time.time()
    if _faq_cache["data"] is not None and (now - _faq_cache["ts"]) < _FAQ_TTL:
        return _faq_cache["data"]
    faqs = load_chatbot_faqs(db)
    _faq_cache["data"] = faqs
    _faq_cache["ts"] = now
    return faqs


def _get_cached_schemes(db):
    now = time.time()
    if _scheme_cache["data"] is not None and (now - _scheme_cache["ts"]) < _FAQ_TTL:
        return _scheme_cache["data"]
    schemes = list(db.schemes.find({})) if db is not None else []
    _scheme_cache["data"] = schemes
    _scheme_cache["ts"] = now
    return schemes


def _get_cached_greeting(lang):
    now = time.time()
    if lang in _greeting_cache:
        cached_text, ts = _greeting_cache[lang]
        if (now - ts) < _SUGGESTION_TTL:
            return cached_text
    text = get_localized_greeting(lang)
    _greeting_cache[lang] = (text, now)
    return text


def _get_cached_suggestions(lang, faqs=None):
    now = time.time()
    if lang in _suggestions_cache:
        cached_list, ts = _suggestions_cache[lang]
        if (now - ts) < _SUGGESTION_TTL:
            return cached_list
    suggestions = get_localized_suggestions(lang, faqs)
    _suggestions_cache[lang] = (suggestions, now)
    return suggestions


def _make_response_key(query, lang):
    """Hash the query to use as cache key."""
    normalized = query.lower().strip().replace("?", "").replace(".", "").replace("!", "").replace(",", "")
    return hashlib.md5(f"{lang}:{normalized}".encode()).hexdigest()


def _get_cached_response(query, lang):
    """Check if we already have a cached response for this exact (query, lang)."""
    key = _make_response_key(query, lang)
    if key in _response_cache:
        resp, ts = _response_cache[key]
        if (time.time() - ts) < _RESPONSE_TTL:
            return resp
    return None


def _cache_response(query, lang, response_dict):
    """Cache a complete chatbot response."""
    key = _make_response_key(query, lang)
    _response_cache[key] = (response_dict, time.time())
    # Limit cache size to prevent memory bloat
    if len(_response_cache) > 2000:
        # Remove oldest 500 entries
        sorted_keys = sorted(_response_cache.keys(), key=lambda k: _response_cache[k][1])
        for k in sorted_keys[:500]:
            del _response_cache[k]


def _prewarm_language(lang, faqs):
    """Background thread: pre-translate ALL FAQ answers + questions for a language.
    After this runs, all subsequent chatbot responses for this language are instant."""
    if lang == 'en' or lang in _prewarmed_langs:
        return
    try:
        from .translator_utils import translate_batch_from_english

        # Collect all unique texts from FAQs
        all_texts = set()
        for faq in faqs:
            en_data = faq.get("en", faq)
            ans = en_data.get("answer", "")
            q = en_data.get("question", "")
            if ans:
                all_texts.add(ans)
            if q:
                all_texts.add(q)

        # Add common nav/UI strings
        all_texts.update([
            "Main Menu", "List All Schemes",
            "You're very welcome! I am happy to help. Do you have any other questions about government schemes?",
            "I am doing great! I am SATYA, your AI assistant designed to help you with government schemes. How can I assist you today?",
            "ELIGIBILITY CRITERIA", "REQUIRED DOCUMENTS", "HOW TO APPLY", "BENEFITS", "OFFICIAL WEBSITE",
            "• Aadhaar Card", "• Identity Proof", "• Income Certificate", "• Bank Details",
        ])

        text_list = list(all_texts)
        # Translate in chunks of 50 to avoid overwhelming the API
        batch_size = 50
        for i in range(0, len(text_list), batch_size):
            batch = text_list[i:i + batch_size]
            translate_batch_from_english(batch, lang)

        with _prewarm_lock:
            _prewarmed_langs.add(lang)
    except Exception:
        pass  # Non-critical background task


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

CATEGORY_MAP = {
    "farmer": "agriculture", "farmers": "agriculture", "kisan": "agriculture", "krishi": "agriculture", "agriculture": "agriculture",
    "crop": "agriculture", "land": "agriculture", "tractor": "agriculture", "fertilizer": "agriculture",
    "seed": "agriculture", "farming": "agriculture", "cultivation": "agriculture", "fasal": "agriculture",
    "bima": "agriculture", "insurance": "agriculture", "irrigation": "agriculture", "pumps": "agriculture",
    "organic": "agriculture", "harvest": "agriculture", "soil": "agriculture", "matsya": "agriculture",
    "fisheries": "agriculture", "bees": "agriculture", "honey": "agriculture", "dairy": "agriculture",
    "health": "health", "medical": "health", "doctor": "health", "medicine": "health",
    "hospital": "health", "ayushman": "health",
    "sick": "health", "disease": "health", "emergency": "health", "treatment": "health",
    "pregnant": "health", "maternity": "health", "delivery": "health", "nutrition": "health",
    "poshan": "health", "vaccine": "health", "injection": "health", "generic": "health",
    "ambulance": "health", "mental": "health", "disability": "health", "handicap": "health",
    "house": "housing", "building": "housing",
    "awas": "housing", "toilet": "housing", "electricity": "housing",
    "water": "housing", "tap": "housing", "shelter": "housing",
    "urban": "housing", "slum": "housing", "gas": "housing", "lpg": "housing", "saubhagya": "housing",
    "business": "business", "startup": "business", "loan": "business", "loans": "business", "money": "business",
    "finance": "business", "entrepreneur": "business", "industry": "business", "msme": "business",
    "mudra": "business", "shop": "business", "credit": "business", "investment": "business",
    "work": "business", "job": "business", "employment": "business", "mgnrega": "business",
    "unemployed": "business", "skill": "business", "artisan": "business",
    "khadi": "business", "weaver": "business", "craft": "business", "tender": "business",
    "student": "education", "students": "education", "education": "education", "school": "education", "college": "education",
    "scholarship": "education", "scholarships": "education", "study": "education",
    "exam": "education", "degree": "education", "university": "education", "course": "education",
    "literacy": "education", "schooling": "education", "teacher": "education", "fellowship": "education",
    "phd": "education", "merit": "education",
    "social": "social", "pension": "social", "poor": "social", "elderly": "social",
    "widow": "social", "widows": "social", "disabled": "social", "worker": "social", "workers": "social", "bpl": "social",
    "security": "social", "welfare": "social", "poverty": "social", "old": "social",
    "orphan": "social", "transgender": "social", "tribal": "social", "sc": "social", "st": "social",
    "retirement": "social",
    "maharashtra": "state_maharashtra", "karnataka": "state_karnataka", "tamil nadu": "state_tamil_nadu",
    "tamilnadu": "state_tamil_nadu", "up": "state_uttar_pradesh", "uttar pradesh": "state_uttar_pradesh",
    "west bengal": "state_west_bengal", "bengal": "state_west_bengal", "gujarat": "state_gujarat",
    "rajasthan": "state_rajasthan", "kerala": "state_kerala", "punjab": "state_punjab",
    "delhi": "state_delhi", "haryana": "state_haryana", "bihar": "state_bihar", "mp": "state_madhya_pradesh"
}

STATE_OPTIONS = [
    "Maharashtra", "Karnataka", "Tamil Nadu", "Uttar Pradesh", "West Bengal", "Gujarat", "Rajasthan", "Kerala", "Punjab"
]

SCHEME_BOOSTER = set(CATEGORY_MAP.keys()) | {
    "kanya", "sumangala", "vatsalya", "sukanya", "samriddhi", "jan", "dhan", "pmegp", "svanidhi",
    "vishwakarma", "diksha", "nipun", "samagra", "shreyas", "karmayogi", "agnipath", "suraksha", "bima", "jyoti"
}

# --- HELPERS ---

def normalize_chat_language(language, fallback="en"):
    if not language:
        return fallback
    normalized = str(language).strip().lower().replace("_", "-").split("-", 1)[0]
    return normalized if normalized in SUPPORTED_LANGUAGE_CODES else fallback


def get_localized_greeting(language):
    from .translator_utils import STATIC_UI_CACHE
    greetings = STATIC_UI_CACHE["greeting"]
    return greetings.get(language) or translate_from_english(greetings["en"], language)


def build_scheme_faqs(schemes):
    generated = []
    for scheme in schemes:
        name = str(scheme.get("name", "")).strip()
        if not name:
            continue
        answers = [
            (f"What is {name}?", scheme.get("description")),
            (f"What benefits does {name} provide?", scheme.get("benefits")),
            (f"Who is eligible for {name}?", scheme.get("target_beneficiaries")),
            (f"How can I apply for {name}?", scheme.get("application_process") or scheme.get("steps")),
        ]
        for question, answer in answers:
            if isinstance(answer, str) and answer.strip():
                generated.append({
                    "question": question,
                    "answer": answer.strip(),
                    "category": scheme.get("category") or "schemes",
                    "scheme": name,
                })
    return generated


def load_chatbot_faqs(db):
    stored_faqs = list(db.faqs.find({}, {"_id": 0})) if db is not None else []
    schemes = list(db.schemes.find({}, {"_id": 0})) if db is not None else []
    combined = []
    seen = set()
    for faq in stored_faqs + get_faqs() + build_scheme_faqs(schemes):
        english = faq.get("en", faq)
        question = str(english.get("question", "")).strip().casefold()
        scheme = str(faq.get("scheme", "")).strip().casefold()
        key = (scheme, question)
        if question and key not in seen:
            seen.add(key)
            combined.append(faq)
    return combined


def get_localized_suggestions(lang, faqs=None):
    from .translator_utils import STATIC_UI_CACHE
    import random

    source_suggestions = ["Main Menu", "List All Schemes"]

    if faqs and len(faqs) > 3:
        categories = list(set([f.get('category', 'general') for f in faqs]))
        diverse_sample = []
        cat_pool = {c: [f for f in faqs if f.get('category') == c] for c in categories}

        priority_categories = ["schemes", "vault", "eligibility", "verification", "general"]
        preferred_questions = {
            "vault": "What is the Document Vault?",
            "eligibility": "How to check eligibility?",
        }
        ordered_categories = [c for c in priority_categories if c in cat_pool]
        other_categories = [c for c in categories if c not in ordered_categories]
        random.shuffle(other_categories)
        ordered_categories.extend(other_categories)

        for c in ordered_categories[:5]:
            if cat_pool[c]:
                preferred_question = preferred_questions.get(c)
                preferred_faq = next((
                    faq for faq in cat_pool[c]
                    if faq.get("en", faq).get("question") == preferred_question
                ), None)
                diverse_sample.append(preferred_faq or random.choice(cat_pool[c]))

        remaining = [f for f in faqs if f not in diverse_sample]
        if remaining:
            diverse_sample.extend(random.sample(remaining, min(len(remaining), 5 - len(diverse_sample))))

        q_ens = []
        for f in diverse_sample:
            q_en = f.get("en", f).get("question")
            if q_en:
                q_ens.append(q_en)

        source_suggestions.extend(q_ens)
        if lang != 'en':
            from .translator_utils import translate_batch_from_english
            localized = translate_batch_from_english(source_suggestions, lang)
        else:
            localized = source_suggestions

        suggestions = localized[:2]
        for q in localized[2:]:
            if q and q not in suggestions:
                suggestions.append(q)
        return suggestions[:7]

    # Fallback
    base = list(STATIC_UI_CACHE["suggestions"].get(lang, STATIC_UI_CACHE["suggestions"]["en"]))
    source_suggestions.extend(base)
    if lang != 'en':
        from .translator_utils import translate_batch_from_english
        localized = translate_batch_from_english(source_suggestions, lang)
    else:
        localized = source_suggestions
    mn, ls = localized[:2]
    base = localized[2:]
    if mn not in base:
        base = [mn] + base
    if ls not in base:
        base = [ls] + base
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
        en_data = faq.get("en", faq)
        faq_q = en_data.get("question", "").lower().replace("?", "").replace(".", "").replace("!", "")
        if not faq_q:
            continue

        faq_words = set(faq_q.split()) - stop_words
        if query_clean == faq_q.strip():
            return faq

        if query_keywords and faq_words:
            common = query_keywords & faq_words
            score = len(common) / max(len(query_keywords), 1)

            booster_matches = query_keywords & faq_words & SCHEME_BOOSTER
            if booster_matches:
                score += (0.3 * len(booster_matches))
            if query_clean in faq_q or faq_q in query_clean:
                score += 0.4

            if score > best_score:
                best_score = score
                best_match = faq

    return best_match if best_score >= 0.3 else None


def build_scheme_response(found_scheme, faqs, target_lang, detected_lang):
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

    # Collect scheme-specific question texts (English)
    nav_labels = ["Main Menu", "List All Schemes"]
    scheme_q_ens = []
    tagged = [f for f in faqs if f.get("scheme", "").lower() == found_scheme['name'].lower()]
    name_words = found_scheme['name'].lower().split()
    key_words = [w for w in name_words if len(w) > 3]
    for f in faqs:
        if f in tagged:
            continue
        q = f.get("question", "").lower()
        if any(kw in q for kw in key_words):
            tagged.append(f)
    seen_qs = set()
    for f in tagged:
        q_en = f.get("en", f).get("question", "")
        if q_en and q_en not in seen_qs:
            seen_qs.add(q_en)
            scheme_q_ens.append(q_en)

    if not scheme_q_ens:
        cat_faqs = [f for f in faqs if f.get("category") == found_scheme.get("target_beneficiaries", "").lower()]
        for f in cat_faqs[:5]:
            q_en = f.get("en", f).get("question", "")
            if q_en:
                scheme_q_ens.append(q_en)

    # SINGLE batch for ALL texts
    if target_lang != 'en':
        all_texts = response_parts + nav_labels + scheme_q_ens
        all_translated = translate_batch_from_english(all_texts, target_lang)
        translated_parts = all_translated[:len(response_parts)]
        translated_nav = all_translated[len(response_parts):len(response_parts) + len(nav_labels)]
        translated_qs = all_translated[len(response_parts) + len(nav_labels):]
    else:
        translated_parts = response_parts
        translated_nav = nav_labels
        translated_qs = scheme_q_ens

    final_response = ""
    for orig, trans in zip(response_parts, translated_parts):
        if orig in ["ELIGIBILITY CRITERIA", "REQUIRED DOCUMENTS", "HOW TO APPLY", "BENEFITS", "OFFICIAL WEBSITE"]:
            final_response += f"\n\n{trans}:\n"
        elif orig.startswith("• "):
            final_response += f"{trans}\n"
        else:
            final_response += f"{trans} "

    mn, ls = translated_nav[0], translated_nav[1]
    nav_suggestions = [mn, ls] + [q for q in translated_qs if q and q != mn and q != ls]

    return {
        "response": final_response,
        "suggestions": nav_suggestions[:10],
        "detected_lang": detected_lang
    }


# --- ROUTES ---

@chatbot_bp.route('', methods=['POST'])
@chatbot_bp.route('/', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    manual_lang = data.get("lang")

    detected_lang = normalize_chat_language(detect_language(query))
    if not manual_lang or str(manual_lang).strip().lower() == 'auto':
        target_lang = detected_lang
    else:
        target_lang = normalize_chat_language(manual_lang, detected_lang)

    # === CHECK FULL RESPONSE CACHE FIRST ===
    if query:
        cached_resp = _get_cached_response(query, target_lang)
        if cached_resp:
            return jsonify(cached_resp), 200

    db = get_db()
    faqs = _get_cached_faqs(db)
    schemes_data = _get_cached_schemes(db)

    # === START BACKGROUND PRE-WARM for this language ===
    if target_lang != 'en' and target_lang not in _prewarmed_langs:
        threading.Thread(target=_prewarm_language, args=(target_lang, faqs), daemon=True).start()

    if not query:
        msg = _get_cached_greeting(target_lang)
        resp = {"response": msg, "suggestions": _get_cached_suggestions(target_lang, faqs)}
        return jsonify(resp), 200

    q_lower = query.lower().strip().replace("!", "").replace(".", "")

    if q_lower in GREETINGS or any(g in q_lower for g in ["who are you", "what are you", "help me"]):
        msg = _get_cached_greeting(target_lang)
        resp = {"response": msg, "suggestions": _get_cached_suggestions(target_lang, faqs)}
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    if any(t in q_lower for t in THANKS):
        response_text = STATIC_THANKS_RESPONSE.get(target_lang, STATIC_THANKS_RESPONSE["en"])
        resp = {"response": response_text, "suggestions": _get_cached_suggestions(target_lang, faqs)}
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    if any(st in q_lower for st in SMALL_TALK):
        response_text = STATIC_SMALLTALK_RESPONSE.get(target_lang, STATIC_SMALLTALK_RESPONSE["en"])
        resp = {"response": response_text, "suggestions": _get_cached_suggestions(target_lang, faqs)}
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    english_query = translate_to_english(query, source_lang=target_lang) if target_lang != 'en' else query
    eq_lower = english_query.lower().replace("?", "").replace(".", "").replace(",", "").strip()

    if "main menu" in eq_lower or eq_lower == "menu":
        msg = _get_cached_greeting(target_lang)
        resp = {"response": msg, "suggestions": _get_cached_suggestions(target_lang, faqs)}
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    trigger_words = ["all schemes", "list schemes", "show schemes", "schemes list", "available schemes", "list all schemes"]

    if db is None:
        mn = translate_from_english("Main Menu", target_lang)
        return jsonify({"response": "I am having trouble connecting to my knowledge base. Please try again later.", "suggestions": [mn, translate_from_english("List All Schemes", target_lang)]}), 503

    # Direct scheme name match
    found_scheme = None
    for s in schemes_data:
        if eq_lower == s['name'].lower().strip():
            found_scheme = s
            break

    if found_scheme:
        resp = build_scheme_response(found_scheme, faqs, target_lang, detected_lang)
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    # --- ALL SCHEMES LIST ---
    trigger_words.extend(["सभी योजनाएं", "सभी योजनाओं"])
    if any(tw in eq_lower for tw in trigger_words):
        schemes = list(db.schemes.find({}, {"name": 1, "_id": 0}))
        scheme_names = [s["name"] for s in schemes]

        intro = f"I found {len(scheme_names)} government schemes. Click any scheme name below to see Eligibility, Benefits, and Steps to Apply. \n\nYou can also browse by category: Agriculture, Health, Housing, Education, or Business."

        if target_lang != 'en':
            from .translator_utils import translate_batch_from_english
            all_texts = [intro, "Main Menu"] + scheme_names
            all_translated = translate_batch_from_english(all_texts, target_lang)
            translated_intro = all_translated[0]
            mn = all_translated[1]
            localized_schemes = all_translated[2:]
        else:
            translated_intro = intro
            mn = "Main Menu"
            localized_schemes = scheme_names

        resp = {"response": translated_intro, "suggestions": [mn] + localized_schemes, "detected_lang": detected_lang}
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    # --- STATE MENU ---
    if eq_lower == "state" or any(s in eq_lower for g in ["which state", "my state", "state list"] for s in [g]):
        prompt = "Which state are you from? Please select or type your state name."

        if target_lang != 'en':
            from .translator_utils import translate_batch_from_english
            all_texts = [prompt, "Main Menu"] + STATE_OPTIONS
            all_translated = translate_batch_from_english(all_texts, target_lang)
            response_text = all_translated[0]
            mn = all_translated[1]
            localized_states = all_translated[2:]
        else:
            response_text = prompt
            mn = "Main Menu"
            localized_states = STATE_OPTIONS

        resp = {"response": response_text, "suggestions": [mn] + localized_states, "detected_lang": detected_lang}
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    # Category detection
    matched_cat = None
    query_words = eq_lower.split()
    for word in query_words:
        word = word.strip()
        if word in CATEGORY_MAP:
            matched_cat = CATEGORY_MAP[word]
            break

    if matched_cat:
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
                    if found_scheme:
                        break

        if found_scheme:
            resp = build_scheme_response(found_scheme, faqs, target_lang, detected_lang)
            _cache_response(query, target_lang, resp)
            return jsonify(resp), 200

        cat_faqs = [f for f in faqs if f.get("category") == matched_cat]
        if cat_faqs:
            display_name = matched_cat.replace("state_", "").replace("_", " ").title()
            if "state_" in matched_cat:
                intro = f"Here are the major government schemes available in {display_name}:"
            else:
                intro = f"I found several schemes related to {display_name}."

            q_ens = []
            for f in cat_faqs:
                q_en = f.get("en", f).get("question")
                if q_en:
                    q_ens.append(q_en)

            if target_lang != 'en':
                from .translator_utils import translate_batch_from_english
                all_texts = [intro, "Main Menu", "List All Schemes"] + q_ens
                all_translated = translate_batch_from_english(all_texts, target_lang)
                response_text = all_translated[0]
                mn = all_translated[1]
                ls = all_translated[2]
                translated_qs = all_translated[3:]
            else:
                response_text = intro
                mn = "Main Menu"
                ls = "List All Schemes"
                translated_qs = q_ens

            suggestions = [mn, ls]
            for q in translated_qs:
                if q and q not in suggestions:
                    suggestions.append(q)
            resp = {"response": response_text, "suggestions": suggestions[:12], "detected_lang": detected_lang}
            _cache_response(query, target_lang, resp)
            return jsonify(resp), 200

    # FAQ Match
    match_doc = find_best_match_doc(english_query, faqs)
    if match_doc:
        en_data = match_doc.get("en", match_doc)
        en_ans = en_data.get('answer', "I'm sorry, I don't have the translation for this yet.")
        match_scheme = match_doc.get("scheme")
        q_ens = []
        if match_scheme:
            for f in faqs:
                if f.get("scheme") == match_scheme and f != match_doc:
                    q_en = f.get("en", f).get('question')
                    if q_en and q_en not in q_ens and len(q_ens) < 5:
                        q_ens.append(q_en)

        for f in faqs:
            if f.get("category") == match_doc.get("category") and f != match_doc:
                q_en = f.get("en", f).get('question')
                if q_en and q_en not in q_ens and len(q_ens) < 5:
                    q_ens.append(q_en)

        source_texts = [en_ans, "Main Menu", "List All Schemes"] + q_ens
        if target_lang != 'en':
            from .translator_utils import translate_batch_from_english
            translated_texts = translate_batch_from_english(source_texts, target_lang)
        else:
            translated_texts = source_texts

        final_answer, mn, ls = translated_texts[:3]
        related = [mn, ls]

        for q in translated_texts[3:]:
            if q and q not in related:
                related.append(q)

        resp = {"response": final_answer, "suggestions": related[:10], "detected_lang": detected_lang}
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    # --- FINAL SCHEME SEARCH ---
    found_scheme = None
    for s in schemes_data:
        if s['name'].lower() in eq_lower:
            found_scheme = s
            break

    if not found_scheme:
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
        resp = build_scheme_response(found_scheme, faqs, target_lang, detected_lang)
        _cache_response(query, target_lang, resp)
        return jsonify(resp), 200

    # Fallback
    fallback_text = (
        "Sorry, I couldn't understand your question clearly. \n"
        "You can try asking about:\n"
        "• Specific schemes (e.g., 'What is PM Kisan?')\n"
        "• Eligibility criteria and Documents\n"
        "• Application steps\n\n"
        "You can also select 'List All Schemes' to see everything available."
    )

    dynamic_suggestions = _get_cached_suggestions(target_lang, faqs)

    resp = {
        "response": translate_from_english(fallback_text, target_lang),
        "suggestions": dynamic_suggestions[:7],
        "detected_lang": detected_lang
    }
    _cache_response(query, target_lang, resp)
    return jsonify(resp), 200


@chatbot_bp.route('/suggestions', methods=['GET'])
def get_suggestions_route():
    lang = normalize_chat_language(request.args.get("lang", "en"))
    db = get_db()
    faqs = _get_cached_faqs(db)

    # Trigger pre-warm for this language
    if lang != 'en' and lang not in _prewarmed_langs:
        threading.Thread(target=_prewarm_language, args=(lang, faqs), daemon=True).start()

    welcome_msg = _get_cached_greeting(lang)
    base_suggestions = _get_cached_suggestions(lang, faqs)

    return jsonify({"suggestions": base_suggestions[:7], "welcome_message": welcome_msg}), 200
