"""
Translation utilities for SATYA multilingual system.
Uses direct Google Translate API (no googletrans library dependency for translation).
Thread-safe cache with periodic disk writes for performance.
"""
import re
import json
import os
import time
import threading
import urllib.request
import urllib.parse
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator

# Set seed for consistent detection
DetectorFactory.seed = 0

# Local Cache Path
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CACHE_FILE = os.path.join(CACHE_DIR, 'translation_cache.json')

# Static Map for Instant UI (Greeting, Suggestions, Fallbacks)
STATIC_UI_CACHE = {
    "greeting": {
        "en": "Hello! I am SATYA, your Govt Schemes Assistant. How can I help you today?",
        "hi": "नमस्ते! मैं SATYA हूँ, आपकी सरकारी योजना सहायक। मैं आज आपकी कैसे मदद कर सकता हूँ?",
        "ta": "வணக்கம்! நான் SATYA, உங்கள் அரசு திட்ட உதவியாளர். இன்று நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
        "te": "నమస్కారం! నేను SATYA, మీ ప్రభుత్వ పథకాల సహాయకుడిని. ఈరోజు నేను మీకు ఎలా సహాయపడగలను?",
        "kn": "ನಮಸ್ಕಾರ! ನಾನು SATYA, ನಿಮ್ಮ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳ ಸಹಾಯಕ. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
        "mr": "नमस्कार! मी SATYA आहे, आपली सरकारी योजना सहाय्यक. मी तुम्हाला आज कशी मदत करू शकतो?",
        "bn": "নমস্কার! আমি SATYA, আপনার সরকারি প্রকল্প সহকারী। আজ আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
        "gu": "નમસ્તે! હું SATYA છું, તમારી સરકારી યોજના મદદનીશ. હું આજે તમને કેવી રીતે મદદ કરી શકું?",
        "ml": "നമസ്കാരം! ഞാൻ SATYA ആണ്, നിങ്ങളുടെ സർക്കാർ പദ്ധതി സഹായി. ഇന്ന് ഞാൻ നിങ്ങൾക്ക് എങ്ങനെ സഹായിക്കും?"
    },
    "suggestions": {
        "hi": ["SATYA क्या है?", "पात्रता कैसे जांचें?", "PM किसान क्या है?", "आयुष्मान कार्ड कैसे प्राप्त करें?", "मुद्रा ऋण क्या है?"],
        "ta": ["SATYA என்றால் என்ன?", "தகுதியை எவ்வாறு சரிபார்ப்பது?", "PM கிசான் என்றால் என்ன?", "ஆயுஷ்மான் கார்டு பெறுவது எப்படி?", "முத்ரா கடன் என்றால் என்ன?"],
        "te": ["SATYA అంటే ఏమిటి?", "అర్హతను ఎలా తనిఖీ చేయాలి?", "PM కిసాన్ అంటే ఏమిటి?", "ఆయుష్మాన్ కార్డ్ ఎలా పొందాలి?", "ముద్రా లోన్ అంటే ఏమిటి?"],
        "kn": ["SATYA ಎಂದರೇನು?", "ಅರ್ಹತೆಯನ್ನು ಹೇಗೆ ಪರಿಶೀಲಿಸುವುದು?", "PM ಕಿಸಾನ್ ಎಂದರೇನು?", "ಆಯುಷ್ಮಾನ್ ಕಾರ್ಡ್ ಪಡೆಯುವುದು ಹೇಗೆ?", "ಮುದ್ರಾ ಲೋನ್ ಎಂದರೇನು?"],
        "mr": ["SATYA काय आहे?", "पात्रता कशी तपासायची?", "पीएम किसान काय आहे?", "आयुष्मान कार्ड कसे मिळवायचे?", "मुद्रा कर्ज काय आहे?"],
        "bn": ["SATYA কি?", "যোগ্যতা কিভাবে যাচাই করবেন?", "পিএম কিষাণ কি?", "আয়ুষ্মান কার্ড কীভাবে পাবেন?", "মুদ্রা ঋণ কি?"],
        "gu": ["SATYA શું છે?", "પાત્રતા કેવી રીતે તપાસવી?", "પીએમ કિસાન શું છે?", "આયુષ્માન કાર્ડ કેવી રીતે મેળવવું?", "મુદ્રા લોન શું છે?"],
        "ml": ["SATYA എന്നാൽ എന്താണ്?", "യോഗ്യത എങ്ങനെ പരിശോധിക്കാം?", "പിഎം കിസാൻ എന്നാൽ എന്താണ്?", "ആയുഷ്മാൻ കാർഡ് എങ്ങനെ ലഭിക്കും?", "മുദ്ര ലോൺ എന്നാൽ എന്താണ്?"],
        "en": ["What is SATYA?", "How to check my eligibility?", "What is PM Kisan?", "How to get Ayushman Card?", "What is Mudra Loan?"]
    },
    "fallback": {
        "en": "I'm sorry, I couldn't find an exact answer. Please try one of the suggestions below!",
        "hi": "क्षमा करें, मुझे सटीक उत्तर नहीं मिला। कृपया नीचे दिए गए सुझावों में से किसी एक को आजमाएं!",
        "ta": "மன்னிக்கவும், என்னால் சரியான பதிலைக் கண்டுபிடிக்க முடியவில்லை. கீழே உள்ள பரிந்துரைகளில் ஒன்றை முயற்சிக்கவும்!",
        "te": "క్షమించండి, నాకు ఖచ్చితమైన సమాధానం దొరకలేదు. దయచేసి క్రింది సూచనలలో ఒకదాన్ని ప్రయత్నించండి!",
        "kn": "ಕ್ಷಮಿಸಿ, ನನಗೆ ನಿಖರವಾದ ಉತ್ತರ ಸಿಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಕೆಳಗಿನ ಸಲಹೆಗಳಲ್ಲಿ ಒಂದನ್ನು ಪ್ರಯತ್ನಿಸಿ!",
        "mr": "क्षमस्व, मला अचूक उत्तर सापडले नाही. कृपया खालील सूचनांपैकी एक प्रयत्न करा!",
        "bn": "দুঃখিত, আমি সঠিক উত্তর খুঁজে পাইনি। অনুগ্রহ করে নিচের পরামর্শগুলির মধ্যে একটি চেষ্টা করুন!",
        "gu": "ક્ષમા કરશો, મને ચોક્કસ જવાબ મળ્યો નથી. કૃપા કરીને નીચેના સૂચનોમાંથી કોઈ એક અજમાવો!",
        "ml": "ക്ഷമിക്കണം, എനിക്ക് കൃത്യമായ ഉത്തരം കണ്ടെത്താനായില്ല. ദയവായി താഴെ നൽകിയിരിക്കുന്ന നിർദ്ദേശങ്ങളിൽ ഒന്ന് ശ്രമിക്കുക!"
    }
}

# ============ CACHE SYSTEM ============

_cache_lock = threading.Lock()
_cache_dirty = False

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

_last_save_time = 0

def save_cache_to_disk(force=False):
    global _cache_dirty, _last_save_time
    if not _cache_dirty:
        return
        
    current_time = time.time()
    # Throttling disk writes to every 10 seconds unless forced
    if not force and (current_time - _last_save_time < 10):
        return
        
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with _cache_lock:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(PERSISTENT_CACHE, f, ensure_ascii=False, indent=2)
            _cache_dirty = False
            _last_save_time = current_time
    except:
        pass

def cache_put(key, value):
    global _cache_dirty
    # Safety Check: Never cache error messages as translations
    if not value or "Error 500" in str(value) or "Server Error" in str(value):
        return
        
    with _cache_lock:
        PERSISTENT_CACHE[key] = value
        _cache_dirty = True

# For backward compat with prime script
def save_cache(cache_data):
    save_cache_to_disk()

PERSISTENT_CACHE = load_cache()
SUPPORTED_LANGUAGES = {'en', 'hi', 'ta', 'te', 'kn', 'mr', 'bn', 'gu', 'ml'}

# ============ DIRECT GOOGLE TRANSLATE (no googletrans library) ============
def _translate_single(text, target_lang):
    """Translate a single string using deep-translator with retry logic."""
    for attempt in range(3):
        try:
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated = translator.translate(text)
            if translated and "Error 500" not in str(translated):
                return translated
        except Exception as e:
            if "TooManyRequests" in str(e) or "429" in str(e):
                break # Hard abort on rate limits
            pass
        time.sleep(0.5)
    return text  # Return original on all failures

# ============ LANGUAGE DETECTION ============

def detect_language(text):
    if not text or len(text.strip()) < 2:
        return 'en'
    scripts = {
        'hi': r'[\u0900-\u097F]', 'bn': r'[\u0980-\u09FF]',
        'ta': r'[\u0B80-\u0BFF]', 'te': r'[\u0C00-\u0C7F]',
        'kn': r'[\u0C80-\u0CFF]', 'ml': r'[\u0D00-\u0D7F]',
        'gu': r'[\u0A80-\u0AFF]'
    }
    for lang, pattern in scripts.items():
        if re.search(pattern, text):
            return lang
    try:
        detected = detect(text)
        return detected if detected in SUPPORTED_LANGUAGES else 'en'
    except:
        return 'en'

# ============ PUBLIC TRANSLATION FUNCTIONS ============

def translate_to_english(text):
    cache_key = f"to_en:{text}"
    if cache_key in PERSISTENT_CACHE:
        return PERSISTENT_CACHE[cache_key]
    
    try:
        translator = GoogleTranslator(source='auto', target='en')
        result = translator.translate(text)
        if result and result != text:
            cache_put(cache_key, result)
            save_cache_to_disk()
            return result
    except Exception as e:
        pass
    return text

def translate_from_english(text, target_lang):
    """Translate a single text from English. Cache-first, then API."""
    if not text or not target_lang or target_lang == 'en':
        return text

    cache_key = f"{target_lang}:{text}"
    cached = PERSISTENT_CACHE.get(cache_key)
    if cached:
        return cached

    # For long compound text, split and translate parts in parallel
    if len(text) > 100 and ('. ' in text or '\n' in text):
        separator = '\n' if '\n' in text else '. '
        parts = [p.strip() for p in text.split(separator) if p.strip()]
        translated_parts = translate_batch_from_english(parts, target_lang)
        result = separator.join(translated_parts)
        if result:
            cache_put(cache_key, result)
            save_cache_to_disk()
        return result

    # Single text
    result = _translate_single(text, target_lang)
    if result:
        cache_put(cache_key, result)
        save_cache_to_disk()
    return result


def translate_batch_from_english(texts, target_lang):
    """Batch translation. Cache-first, then parallel API calls for misses."""
    if not texts or not target_lang or target_lang == 'en':
        return texts

    # 1. Expand compound texts
    expanded_map = {}
    all_fragments = []

    for text in texts:
        if not text:
            expanded_map[text] = [text]
            continue
        if len(text) > 100 and ('. ' in text or '\n' in text):
            separator = '\n' if '\n' in text else '. '
            parts = [p.strip() for p in text.split(separator) if p.strip()]
            expanded_map[text] = parts
            all_fragments.extend(parts)
        else:
            expanded_map[text] = [text]
            all_fragments.append(text)

    # 2. Deduplicate and check cache
    unique_fragments = list(set(all_fragments))
    fragment_results = {}
    to_translate = []

    # Hardcoded Proper Nouns for specific regional accuracy
    PROPER_NOUN_FIXES = {
        # --- State Names (all 18 states used in scheme data) ---
        "Maharashtra": {"hi": "महाराष्ट्र", "mr": "महाराष्ट्र", "ta": "மகாராஷ்டிரா", "te": "మహారాష్ట్ర", "kn": "ಮಹಾರಾಷ್ಟ್ರ", "bn": "মহারাষ্ট্র", "gu": "મહારાષ્ટ્ર", "ml": "മഹാരാഷ്ട്ര"},
        "Karnataka": {"hi": "कर्नाटक", "kn": "ಕರ್ನಾಟಕ", "ta": "கர்நாடகா", "te": "కర్ణాటక", "mr": "कर्नाटक", "bn": "কর্ণাটক", "gu": "કર્ણાટક", "ml": "കർണാടക"},
        "Tamil Nadu": {"hi": "तमिलनाडु", "ta": "தமிழ்நாடு", "te": "తమిళనాడు", "kn": "ತಮಿಳುನಾಡು", "mr": "तमिळनाडू", "bn": "তামিলনাড়ু", "gu": "તમિલનાડુ", "ml": "തമിഴ്നാട്"},
        "Andhra Pradesh": {"hi": "आंध्र प्रदेश", "ta": "ஆந்திர பிரதேசம்", "te": "ఆంధ్ర ప్రదేశ్", "kn": "ಆಂಧ್ರ ಪ್ರದೇಶ", "mr": "आंध्र प्रदेश", "bn": "অন্ধ্র প্রদেশ", "gu": "આંધ્ર પ્રદેશ", "ml": "ആന്ധ്രപ്രദേശ്"},
        "Telangana": {"hi": "तेलंगाना", "ta": "தெலங்கானா", "te": "తెలంగాణ", "kn": "ತೆಲಂಗಾಣ", "mr": "तेलंगणा", "bn": "তেলেঙ্গানা", "gu": "તેલંગાણા", "ml": "തെലങ്കാന"},
        "Kerala": {"hi": "केरल", "ml": "കേരളം", "ta": "கேரளா", "te": "కేరళ", "kn": "ಕೇರಳ", "mr": "केरळ", "bn": "কেরালা", "gu": "કેરળ"},
        "West Bengal": {"hi": "पश्चिम बंगाल", "bn": "পশ্চিমবঙ্গ", "ta": "மேற்கு வங்கம்", "te": "పశ్చిమ బెంగాల్", "kn": "ಪಶ್ಚಿಮ ಬಂಗಾಳ", "mr": "पश्चिम बंगाल", "gu": "પશ્ચિમ બંગાળ", "ml": "പശ്ചിമ ബംഗാൾ"},
        "Bihar": {"hi": "बिहार", "te": "బీహార్", "ta": "பீகார்", "kn": "ಬಿಹಾರ", "mr": "बिहार", "bn": "বিহার", "gu": "બિહાર", "ml": "ബിഹാർ"},
        "Madhya Pradesh": {"hi": "मध्य प्रदेश", "ta": "மத்தியப் பிரதேசம்", "te": "మధ్య ప్రదేశ్", "kn": "ಮಧ್ಯ ಪ್ರದೇಶ", "mr": "मध्य प्रदेश", "bn": "মধ্য প্রদেশ", "gu": "મધ્ય પ્રદેશ", "ml": "മധ്യപ്രദേശ്"},
        "Uttar Pradesh": {"hi": "उत्तर प्रदेश", "ta": "உத்தரப் பிரதேசம்", "te": "ఉత్తర ప్రదేశ్", "kn": "ಉತ್ತರ ಪ್ರದೇಶ", "mr": "उत्तर प्रदेश", "bn": "উত্তর প্রদেশ", "gu": "ઉત્તર પ્રદેશ", "ml": "ഉത്തർപ്രദേശ്"},
        "Gujarat": {"hi": "गुजरात", "gu": "ગુજરાત", "ta": "குஜராத்", "te": "గుజరాత్", "kn": "ಗುಜರಾತ್", "mr": "गुजरात", "bn": "গুজরাট", "ml": "ഗുജറാത്ത്"},
        "Rajasthan": {"hi": "राजस्थान", "ta": "ராஜஸ்தான்", "te": "రాజస్థాన్", "kn": "ರಾಜಸ್ಥಾನ", "mr": "राजस्थान", "bn": "রাজস্থান", "gu": "રાજસ્થાન", "ml": "രാജസ്ഥാൻ"},
        "Odisha": {"hi": "ओडिशा", "ta": "ஒடிசா", "te": "ఒడిషా", "kn": "ಒಡಿಶಾ", "mr": "ओडिशा", "bn": "ওড়িশা", "gu": "ઓડિશા", "ml": "ഒഡീഷ"},
        "Assam": {"hi": "असम", "ta": "அசாம்", "te": "అసోం", "kn": "ಅಸ್ಸಾಂ", "mr": "आसाम", "bn": "অসম", "gu": "આસામ", "ml": "അസം"},
        "Chhattisgarh": {"hi": "छत्तीसगढ़", "ta": "சத்தீஸ்கர்", "te": "ఛత్తీస్‌గఢ్", "kn": "ಛತ್ತೀಸ್‌ಗಢ", "mr": "छत्तीसगड", "bn": "ছত্তিসগড়", "gu": "છત્તીસગઢ", "ml": "ഛത്തീസ്ഗഡ്"},
        "Punjab": {"hi": "पंजाब", "ta": "பஞ்சாப்", "te": "పంజాబ్", "kn": "ಪಂಜಾಬ್", "mr": "पंजाब", "bn": "পাঞ্জাব", "gu": "પંજાબ", "ml": "പഞ്ചാബ്"},
        "Haryana": {"hi": "हरियाणा", "ta": "ஹரியாணா", "te": "హర్యానా", "kn": "ಹರಿಯಾಣ", "mr": "हरियाणा", "bn": "হরিয়ানা", "gu": "હરિયાણા", "ml": "ഹരിയാണ"},
        "Jharkhand": {"hi": "झारखंड", "ta": "ஜார்கண்ட்", "te": "జార్ఖండ్", "kn": "ಜಾರ್ಖಂಡ್", "mr": "झारखंड", "bn": "ঝাড়খণ্ড", "gu": "ઝારખંડ", "ml": "ഝാർഖണ്ഡ്"},
        # --- Common Abbreviations ---
        "Central": {"hi": "केंद्रीय", "mr": "केंद्रीय", "ta": "மத்திய", "te": "కేంద్ర", "kn": "ಕೇಂದ್ರ", "bn": "কেন্দ্রীয়", "gu": "કેન્દ્રીય", "ml": "കേന്ദ്ര"},
        "All India": {"hi": "अखिल भारतीय", "mr": "अखिल भारतीय", "ta": "அகில இந்திய", "te": "అఖిల భారత", "kn": "ಅಖಿಲ ಭಾರತ", "bn": "সর্বভারতীয়", "gu": "અખિલ ભારતીય", "ml": "അഖിലേന്ത്യ"},
        "PM": {"hi": "पीएम", "mr": "पीएम", "ta": "பிஎம்", "te": "పీఎం", "kn": "ಪಿಎಂ", "bn": "পিএম", "gu": "પીએમ", "ml": "പിഎം"},
        "AP": {"hi": "एपी", "ta": "ஏபி", "te": "ఏపీ"},
        "UP": {"hi": "यूपी", "ta": "யூபி", "te": "యూపీ"},
        "MP": {"hi": "एमपी", "mr": "एमपी", "te": "ఎంపీ"},
        "eVidya": {"hi": "ई-विद्या", "mr": "ई-विद्या", "ta": "ஈ-வித்யா", "te": "ఈ-విద్యా"},
        "SC": {"hi": "एससी", "ta": "எஸ்சி", "te": "ఎస్సీ"},
        "ST": {"hi": "एसटी", "ta": "எஸ்டி", "te": "ఎస్టీ"},
        "BPL": {"hi": "बीपीएल", "ta": "பிபிஎல்", "te": "బీపీఎల్"},
    }

    for frag in unique_fragments:
        if not frag:
            fragment_results[frag] = frag
            continue
            
        frag_clean = frag.strip()
            
        # Check hardcoded fixes first
        if frag_clean in PROPER_NOUN_FIXES and target_lang in PROPER_NOUN_FIXES[frag_clean]:
            fragment_results[frag] = PROPER_NOUN_FIXES[frag_clean][target_lang]
            continue

        cache_key = f"{target_lang}:{frag_clean}"
        cached = PERSISTENT_CACHE.get(cache_key)
        
        if not cached:
            # Case-insensitive fallback
            search_key = cache_key.lower()
            for k, v in PERSISTENT_CACHE.items():
                if k.lower() == search_key:
                    cached = v
                    break
                    
        if cached:
            fragment_results[frag] = cached
        else:
            to_translate.append(frag_clean)

    # 3. Translate missing fragments iteratively in grouped batches
    if to_translate:
        batch_size = 10 # Send 10 strings per HTTP request
        grouped_batches = [to_translate[i:i + batch_size] for i in range(0, len(to_translate), batch_size)]
        
        for g_batch in grouped_batches:
            # Wrap short fragments (likely titles) in context to help Google Translate
            wrapped_batch = []
            for item in g_batch:
                if len(item.split()) <= 5:
                    wrapped_batch.append(f"Title: {item}")
                else:
                    wrapped_batch.append(item)

            combined_text = " \n\n ".join(wrapped_batch)
            res = _translate_single(combined_text, target_lang)
            
            # If the proxy failed entirely, do not map or cache as success
            if not res or res.strip() == combined_text.strip():
                for frag in g_batch:
                    fragment_results[frag] = frag
                continue
                
            translated_arr = [s.strip() for s in res.split('\n\n') if s.strip()]
            
            # Clean "Title: " prefix (more robustly)
            cleaned_translations = []
            for s in translated_arr:
                # Remove common Title prefixes in various languages
                s_clean = s
                if ":" in s_clean:
                    parts = s_clean.split(":", 1)
                    prefix = parts[0].strip().lower()
                    if prefix in ["शीर्षक", "தலைப்பு", "title", "மகுடம்", "제목", "नाव", "नाम", "தலைப்பு"]:
                        s_clean = parts[1].strip()
                
                # Strip potential quotes
                s_clean = s_clean.strip(' "\"\'')
                cleaned_translations.append(s_clean)

            # Map results if segment count matches
            if len(cleaned_translations) == len(g_batch):
                for orig, trans in zip(g_batch, cleaned_translations):
                    fragment_results[orig] = trans
                    cache_put(f"{target_lang}:{orig}", trans)
            else:
                for frag in g_batch:
                    fragment_results[frag] = frag

        save_cache_to_disk()

    # 4. Reconstruct original texts
    final_results = []
    for text in texts:
        if not text:
            final_results.append(text)
            continue
        parts = expanded_map.get(text, [text])
        translated_parts = [fragment_results.get(p, p) for p in parts]

        if len(text) > 100 and ('. ' in text or '\n' in text):
            separator = '\n' if '\n' in text else '. '
        else:
            separator = '. '
        final_text = separator.join(translated_parts)

        if final_text:
            cache_put(f"{target_lang}:{text}", final_text)
        final_results.append(final_text)

    save_cache_to_disk()
    return final_results
