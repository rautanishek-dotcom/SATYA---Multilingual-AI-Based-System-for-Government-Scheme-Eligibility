from googletrans import Translator
from langdetect import detect, DetectorFactory
import re
import json
import os

# Set seed for consistent detection
DetectorFactory.seed = 0

translator = Translator()

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

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache_data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except:
        pass

# Initialize persistnet cache
PERSISTENT_CACHE = load_cache()

def detect_language(text):
    if not text or len(text.strip()) < 2:
        return 'en'
    
    scripts = {
        'hi': r'[\u0900-\u097F]',
        'bn': r'[\u0980-\u09FF]',
        'ta': r'[\u0B80-\u0BFF]',
        'te': r'[\u0C00-\u0C7F]',
        'kn': r'[\u0C80-\u0CFF]',
        'ml': r'[\u0D00-\u0D7F]',
        'gu': r'[\u0A80-\u0AFF]'
    }
    
    for lang, pattern in scripts.items():
        if re.search(pattern, text):
            return lang
            
    try:
        detected = detect(text)
        if detected == 'mr': return 'hi'
        return detected
    except:
        return 'en'

def translate_to_english(text):
    # Check cache first
    cache_key = f"to_en:{text}"
    if cache_key in PERSISTENT_CACHE:
        return PERSISTENT_CACHE[cache_key]

    try:
        result = translator.translate(text, dest='en')
        PERSISTENT_CACHE[cache_key] = result.text
        save_cache(PERSISTENT_CACHE)
        return result.text
    except Exception as e:
        print(f"Translation to English error: {e}")
        return text

def translate_from_english(text, target_lang):
    if target_lang == 'en':
        return text
    
    # Check cache first
    cache_key = f"{target_lang}:{text}"
    if cache_key in PERSISTENT_CACHE:
        return PERSISTENT_CACHE[cache_key]

    try:
        result = translator.translate(text, dest=target_lang)
        PERSISTENT_CACHE[cache_key] = result.text
        save_cache(PERSISTENT_CACHE)
        return result.text
    except Exception as e:
        print(f"Translation from English error: {e}")
        return text
