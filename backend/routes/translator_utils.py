"""
Translation utilities for SATYA multilingual system.
Uses direct Google Translate API (no googletrans library dependency for translation).
Thread-safe cache with periodic disk writes for performance.

PERFORMANCE OPTIMISED:
- Google GTX used as PRIMARY translator (fastest, no library overhead, no rate-limit)
- Bhashini native batch API for bulk translations (one HTTP call = many texts)
- Global translation lock REMOVED – allows true parallel calls
- MyMemory removed from hot path (slowest provider)
- Persistent HTTP session for connection reuse
"""
import re
import json
import os
import requests
import time
import threading
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TooManyRequests
from language_config import SUPPORTED_LANGUAGE_CODES

# Set seed for consistent detection
DetectorFactory.seed = 0

# Thread-pool for concurrent translation batches
_translate_pool = ThreadPoolExecutor(max_workers=6)

# Persistent HTTP session – reuses TCP connections (saves ~80ms/call)
_http_session = requests.Session()
_http_session.headers.update({
    'Content-Type': 'application/json',
    'User-Agent': 'SATYA/2.0',
})

# Local Cache Path
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CACHE_FILE = os.path.join(CACHE_DIR, 'translation_cache.json')

# Static Map for Instant UI (Greeting, Suggestions, Fallbacks) — ALL 23 languages
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
        "ml": "നമസ്കാരം! ഞാൻ SATYA ആണ്, നിങ്ങളുടെ സർക്കാർ പദ്ധതി സഹായി. ഇന്ന് ഞാൻ നിങ്ങൾക്ക് എങ്ങനെ സഹായിക്കും?",
        "pa": "ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ! ਮੈਂ SATYA ਹਾਂ, ਤੁਹਾਡਾ ਸਰਕਾਰੀ ਯੋਜਨਾ ਸਹਾਇਕ। ਅੱਜ ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
        "or": "ନମସ୍କାର! ମୁଁ SATYA, ଆପଣଙ୍କ ସରକାରୀ ଯୋଜନା ସହାୟକ। ଆଜି ମୁଁ ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବି?",
        "as": "নমস্কাৰ! মই SATYA, আপোনাৰ চৰকাৰী আঁচনি সহায়ক। আজি মই আপোনাক কেনেকৈ সহায় কৰিব পাৰোঁ?",
        "ur": "السلام علیکم! میں SATYA ہوں، آپ کا سرکاری اسکیم اسسٹنٹ۔ آج میں آپ کی کیسے مدد کر سکتا ہوں؟",
        "ne": "नमस्ते! म SATYA हुँ, तपाईंको सरकारी योजना सहायक। आज म तपाईंलाई कसरी मद्दत गर्न सक्छु?",
        "sd": "سلام! مان SATYA آهيان، توهان جو سرڪاري اسڪيم اسسٹنٽ. اڄ مان توهان جي ڪيئن مدد ڪري سگهان ٿو؟",
        "sa": "नमस्कारः! अहं SATYA अस्मि, भवतः शासकीययोजनासहायकः। अद्य अहं भवन्तं कथं साहाय्यं कर्तुं शक्नोमि?",
        "ks": "السلام علیکم! میں SATYA ہوں، تُہنٛز سرکاری سکیم اسسٹنٹ۔ اَز میں تُہیٛ کِتھ مدد کٔرِتھ ہیٛکس؟",
        "kok": "नमस्कार! हांव SATYA, तुमचो सरकारी योजना सहाय्यक. आयज हांव तुमकां कशी मदत करूं येता?",
        "doi": "नमस्ते! मैं SATYA हां, तुंदा सरकारी योजना सहायक। अज्ज मैं तुंदी किय्यां मदद करी सकदा हां?",
        "brx": "नमस्कार! आं SATYA, नोंथांनि सरकारि फारामनि गोहो मदतगार। दिनै आं नोंथांखौ माबोरै मदत होनो हागौ?",
        "mai": "प्रणाम! हम SATYA छी, अहाँक सरकारी योजना सहायक। आइ हम अहाँक कोना मदति कऽ सकैत छी?",
        "mni": "খুরুমজরি! ঐ SATYA, নখোয়গী সরকারী স্কীম এসিস্টেন্ট। ঙসি ঐ নখোয়বু কমনা মতেং পাংগনি?",
        "sat": "जोहार! इञ SATYA, आमाक् सोरकारी जोजना सहायक। तिञाक् दिन इञ आमाक् ओकतो लेका गोड़ो दाड़ेयाक् दाड़ेयां?",
    },
    "suggestions": {
        "en": ["What is SATYA?", "How to check my eligibility?", "What is PM Kisan?", "How to get Ayushman Card?", "What is Mudra Loan?"],
        "hi": ["SATYA क्या है?", "पात्रता कैसे जांचें?", "PM किसान क्या है?", "आयुष्मान कार्ड कैसे प्राप्त करें?", "मुद्रा ऋण क्या है?"],
        "ta": ["SATYA என்றால் என்ன?", "தகுதியை எவ்வாறு சரிபார்ப்பது?", "PM கிசான் என்றால் என்ன?", "ஆயுஷ்மான் கார்டு பெறுவது எப்படி?", "முத்ரா கடன் என்றால் என்ன?"],
        "te": ["SATYA అంటే ఏమిటి?", "అర్హతను ఎలా తనిఖీ చేయాలి?", "PM కిసాన్ అంటే ఏమిటి?", "ఆయుష్మాన్ కార్డ్ ఎలా పొందాలి?", "ముద్రా లోన్ అంటే ఏమిటి?"],
        "kn": ["SATYA ಎಂದರೇನು?", "ಅರ್ಹತೆಯನ್ನು ಹೇಗೆ ಪರಿಶೀಲಿಸುವುದು?", "PM ಕಿಸಾನ್ ಎಂದರೇನು?", "ಆಯುಷ್ಮಾನ್ ಕಾರ್ಡ್ ಪಡೆಯುವುದು ಹೇಗೆ?", "ಮುದ್ರಾ ಲೋನ್ ಎಂದರೇನು?"],
        "mr": ["SATYA काय आहे?", "पात्रता कशी तपासायची?", "पीएम किसान काय आहे?", "आयुष्मान कार्ड कसे मिळवायचे?", "मुद्रा कर्ज काय आहे?"],
        "bn": ["SATYA কি?", "যোগ্যতা কিভাবে যাচাই করবেন?", "পিএম কিষাণ কি?", "আয়ুষ্মান কার্ড কীভাবে পাবেন?", "মুদ্রা ঋণ কি?"],
        "gu": ["SATYA શું છે?", "પાત્રતા કેવી રીતે તપાસવી?", "પીએમ કિસાન શું છે?", "આયુષ્માન કાર્ડ કેવી રીતે મેળવવું?", "મુદ્રા લોન શું છે?"],
        "ml": ["SATYA എന്നാൽ എന്താണ്?", "യോഗ്യത എങ്ങനെ പരിശോധിക്കാം?", "പിഎം കിസാൻ എന്നാൽ എന്താണ്?", "ആയുഷ്മാൻ കാർഡ് എങ്ങനെ ലഭിക്കും?", "മുദ്ര ലോൺ എന്നാൽ എന്താണ്?"],
        "pa": ["SATYA ਕੀ ਹੈ?", "ਯੋਗਤਾ ਕਿਵੇਂ ਜਾਂਚੀਏ?", "PM ਕਿਸਾਨ ਕੀ ਹੈ?", "ਆਯੁਸ਼ਮਾਨ ਕਾਰਡ ਕਿਵੇਂ ਮਿਲੇ?", "ਮੁਦਰਾ ਲੋਨ ਕੀ ਹੈ?"],
        "or": ["SATYA କ'ଣ?", "ଯୋଗ୍ୟତା କିପରି ଯାଞ୍ଚ କରିବେ?", "PM କିସାନ କ'ଣ?", "ଆୟୁଷ୍ମାନ କାର୍ଡ କିପରି ପାଇବେ?", "ମୁଦ୍ରା ଲୋନ କ'ଣ?"],
        "as": ["SATYA কি?", "যোগ্যতা কেনেকৈ পৰীক্ষা কৰিব?", "PM কিষাণ কি?", "আয়ুষ্মান কাৰ্ড কেনেকৈ পাব?", "মুদ্ৰা ঋণ কি?"],
        "ur": ["SATYA کیا ہے؟", "اہلیت کیسے جانچیں؟", "PM کسان کیا ہے؟", "آیوشمان کارڈ کیسے ملے؟", "مدرا لون کیا ہے؟"],
        "ne": ["SATYA के हो?", "योग्यता कसरी जाँच गर्ने?", "PM किसान के हो?", "आयुष्मान कार्ड कसरी पाउने?", "मुद्रा ऋण के हो?"],
        "sd": ["SATYA ڇا آهي؟", "اهليت ڪيئن جانچيو؟", "PM ڪسان ڇا آهي؟", "آيوشمان ڪارڊ ڪيئن حاصل ڪجي؟", "مدرا لون ڇا آهي؟"],
        "sa": ["SATYA किम् अस्ति?", "पात्रता कथं परीक्षेत?", "PM किसान किम्?", "आयुष्मान् कार्ड कथं प्राप्यते?", "मुद्रा ऋणं किम्?"],
        "ks": ["SATYA کیاہ چھُ?", "اہلیت کیتھ جانچِو؟", "PM کسان کیاہ چھُ?", "آیوشمان کارڈ کیتھ مِلی؟", "مدرا لون کیاہ چھُ؟"],
        "kok": ["SATYA म्हणजे कितें?", "पात्रता कशी तपासची?", "PM किसान म्हणजे कितें?", "आयुष्मान कार्ड कसो मेळोवचो?", "मुद्रा कर्ज म्हणजे कितें?"],
        "doi": ["SATYA की ऐ?", "पात्रता किय्यां जांचें?", "PM किसान की ऐ?", "आयुष्मान कार्ड किय्यां मिले?", "मुद्रा लोन की ऐ?"],
        "brx": ["SATYA माबो?", "गोनांथि माबोरै सुं?", "PM किसान माबो?", "आयुष्मान कार्ड माबोरै मोनो?", "मुद्रा लोन माबो?"],
        "mai": ["SATYA की अछि?", "पात्रता कोना जांचू?", "PM किसान की अछि?", "आयुष्मान कार्ड कोना भेटत?", "मुद्रा ऋण की अछि?"],
        "mni": ["SATYA করিগী?", "যোগ্যতা কমনা চেক তৌরগে?", "PM কিষাণ করিগী?", "আয়ুষ্মান কার্ড কমনা ফংগনি?", "মুদ্রা লোন করিগী?"],
        "sat": ["SATYA चेत् लेका?", "जोगाड़ चेत् लेका जांच?", "PM किसान चेत् लेका?", "आयुष्मान कार्ड चेत् लेका नामे?", "मुद्रा लोन चेत् लेका?"],
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
        "ml": "ക്ഷമിക്കണം, എനിക്ക് കൃത്യമായ ഉത്തരം കണ്ടെത്താനായില്ല. ദയവായി താഴെ നൽകിയിരിക്കുന്ന നിർദ്ദേശങ്ങളിൽ ഒന്ന് ശ്രമിക്കുക!",
        "pa": "ਮੁਆਫ਼ ਕਰਨਾ, ਮੈਨੂੰ ਸਹੀ ਜਵਾਬ ਨਹੀਂ ਮਿਲਿਆ। ਕਿਰਪਾ ਕਰਕੇ ਹੇਠਾਂ ਦਿੱਤੇ ਸੁਝਾਵਾਂ ਵਿੱਚੋਂ ਕੋਈ ਇੱਕ ਅਜ਼ਮਾਓ!",
        "or": "କ୍ଷମା କରନ୍ତୁ, ମୁଁ ସଠିକ ଉତ୍ତର ଖୋଜି ପାରିଲି ନାହିଁ। ଦୟାକରି ତଳେ ଥିବା ପରାମର୍ଶରୁ ଗୋଟିଏ ଚେଷ୍ଟା କରନ୍ତୁ!",
        "as": "ক্ষমা কৰিব, মই সঠিক উত্তৰ বিচাৰি নাপালোঁ। অনুগ্ৰহ কৰি তলৰ পৰামৰ্শসমূহৰ এটা চেষ্টা কৰক!",
        "ur": "معذرت، مجھے صحیح جواب نہیں ملا۔ براہ کرم نیچے دیے گئے مشوروں میں سے ایک آزمائیں!",
        "ne": "माफ गर्नुहोस्, मैले सही जवाफ फेला पार्न सकिनँ। कृपया तलका सुझावहरू मध्ये एउटा प्रयास गर्नुहोस्!",
        "sd": "معاف ڪجو، مون کي صحيح جواب نه مليو. مھرباني ڪري ھيٺ ڏنل تجويزن مان ھڪ ڪوشش ڪريو!",
        "sa": "क्षम्यताम्, मया सम्यक् उत्तरं न प्राप्तम्। कृपया अधोनिर्दिष्टेषु सूचनेषु एकं प्रयतताम्!",
        "ks": "معاف کٔرِو، مےٚ صحیح جواب نہٕ مِلیو۔ مہربانی کٔرِتھ نیچٕ دِتہٕ مشورن منٛز اکھ آزمایو!",
        "kok": "माफ करात, म्हाका अचूक जबाब मेळूंक ना। उपकार करून सकयल दिल्ल्या सुचोवण्यांतल्यान एक वापरात!",
        "doi": "माफ करो, मिगी सही जवाब नेईं मिल्ला। मेहरबानी करियै हेठां दित्ते सुझाआं च इक अजमाओ!",
        "brx": "नोंथांखौ खमा होनाय, आं सुफुं फिन्नाय मोन्नो नाजायाखै। अनसुलि सोमावसारनिफ्राय मोनसे गोनां नाजा होनानै!",
        "mai": "माफ करू, हमरा सही उत्तर नहि भेटल। कृपया नीचा देल सुझाव मे सँ एकटा प्रयास करू!",
        "mni": "করম্না, ঐনা অচুম্বা পাওরিব ফংলবদি। চানবীদুনা মখাদা পীরিবশীংদগী অমা অমা হোকচনবীরক্কদৌরিগা!",
        "sat": "माफ करो, इञ ठीक जबाब नेड़ा बाड़ायाक् दाड़ेयाक् काना। दयाते तोले दित् सुझाव रेन् होर मित् आजमाव!",
    }
}

# ============ CACHE SYSTEM ============

_cache_lock = threading.Lock()
_google_unavailable_until = 0.0

MYMEMORY_LANGUAGE_CODES = {
    'en': 'en-US',
    'as': 'as-IN', 'bn': 'bn-IN', 'gu': 'gu-IN', 'hi': 'hi-IN',
    'kn': 'kn-IN', 'ks': 'kas-IN', 'kok': 'kok-IN', 'mai': 'mai-IN',
    'ml': 'ml-IN', 'mni': 'mni-IN', 'mr': 'mr-IN', 'ne': 'ne-NP',
    'or': 'or-IN', 'pa': 'pa-IN', 'sa': 'sa-IN', 'sat': 'sat-IN',
    'sd': 'sd-PK', 'ta': 'ta-IN', 'te': 'te-IN', 'ur': 'ur-PK',
    'brx': 'as-IN', 'doi': 'hi-IN',
}


GOOGLE_LANG_MAP = {
    'kok': 'gom', 'brx': 'as', 'doi': 'hi', 'ks': 'ur', 'mai': 'bho',
    'mni': 'bn', 'sat': 'bn', 'en': 'en',
}


# ============ LOW-LEVEL TRANSLATORS (ordered fastest → slowest) ============

def _translate_with_google_gtx(text, target_lang, source_lang='en'):
    """FASTEST translator – direct HTTP call to Google, no library, no lock."""
    google_source = GOOGLE_LANG_MAP.get(source_lang, source_lang)
    google_lang = GOOGLE_LANG_MAP.get(target_lang, target_lang)
    url = (
        'https://translate.googleapis.com/translate_a/single'
        f'?client=gtx&sl={google_source}&tl={google_lang}&dt=t&q={urllib.parse.quote(text)}'
    )
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        translated = ''.join(part[0] for part in result[0] if part[0])
        return translated if translated else None
    except Exception:
        return None


def _translate_with_deep_translator(text, target_lang):
    """FALLBACK – uses deep-translator library. Slower but reliable."""
    global _google_unavailable_until
    if time.monotonic() < _google_unavailable_until:
        return None
    try:
        translated = GoogleTranslator(source='en', target=target_lang).translate(text)
        if translated and translated.strip() != text.strip() and "Error 500" not in str(translated):
            return translated
    except TooManyRequests:
        _google_unavailable_until = time.monotonic() + 60
    except Exception:
        pass
    return None


def _translate_with_bhashini(text, source_lang, target_lang):
    """Single-text Bhashini translation."""
    inference_key = os.getenv('BHASHINI_INFERENCE_KEY')
    if not inference_key or not text or source_lang == target_lang:
        return None
    payload = {
        'pipelineTasks': [{'taskType': 'translation', 'config': {
            'language': {'sourceLanguage': source_lang, 'targetLanguage': target_lang},
            'serviceId': 'ai4bharat/indictrans-v2-all-gpu--t4',
        }}],
        'inputData': {'input': [{'source': text}]},
    }
    try:
        response = _http_session.post(
            'https://dhruva-api.bhashini.gov.in/services/inference/pipeline',
            headers={'Authorization': inference_key},
            json=payload, timeout=5,
        )
        if response.status_code != 200:
            return None
        outputs = response.json().get('pipelineResponse', [{}])[0].get('output', [])
        translated = str(outputs[0].get('target', '')).strip() if outputs else ''
        return translated if translated and translated.casefold() != text.casefold() else None
    except Exception:
        return None


def _translate_batch_with_bhashini(texts, source_lang, target_lang):
    """NATIVE Bhashini batch API – translates ALL texts in ONE HTTP call."""
    inference_key = os.getenv('BHASHINI_INFERENCE_KEY')
    if not inference_key or not texts or source_lang == target_lang:
        return None
    # Bhashini doesn't support some languages
    unsupported = {'kok'}
    if target_lang in unsupported or source_lang in unsupported:
        return None
    payload = {
        'pipelineTasks': [{'taskType': 'translation', 'config': {
            'language': {'sourceLanguage': source_lang, 'targetLanguage': target_lang},
            'serviceId': 'ai4bharat/indictrans-v2-all-gpu--t4',
        }}],
        'inputData': {'input': [{'source': t} for t in texts]},
    }
    try:
        response = _http_session.post(
            'https://dhruva-api.bhashini.gov.in/services/inference/pipeline',
            headers={'Authorization': inference_key},
            json=payload, timeout=12,
        )
        if response.status_code != 200:
            return None
        outputs = response.json().get('pipelineResponse', [{}])[0].get('output', [])
        if len(outputs) != len(texts):
            return None
        results = []
        for src, out in zip(texts, outputs):
            translated = str(out.get('target', '')).strip()
            if translated and translated.casefold() != src.casefold():
                results.append(translated)
            else:
                results.append(None)  # Mark as failed
        return results
    except Exception:
        return None


# ============ FAST SINGLE-TEXT TRANSLATOR ============

def _translate_single(text, target_lang):
    """Translate a single string. GTX FIRST (fastest), then fallbacks. NO LOCK."""
    if target_lang not in SUPPORTED_LANGUAGES or target_lang == 'en':
        return text

    # 1. Google GTX – fastest (~100-300ms), no library, no rate-limit
    result = _translate_with_google_gtx(text, target_lang)
    if result and result.strip() and result.strip().casefold() != text.strip().casefold():
        return result

    # 2. deep-translator GoogleTranslator – slower but different endpoint
    result = _translate_with_deep_translator(text, target_lang)
    if result:
        return result

    # 3. Bhashini – last resort for Indic languages
    result = _translate_with_bhashini(text, 'en', target_lang)
    if result:
        return result

    return text


# ============ CACHE PERSISTENCE ============

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

def _do_save_cache():
    """Internal: actual disk write, runs in background thread."""
    global _cache_dirty, _last_save_time
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with _cache_lock:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(PERSISTENT_CACHE, f, ensure_ascii=False, indent=2)
            _cache_dirty = False
            _last_save_time = time.time()
    except:
        pass

def save_cache_to_disk(force=False):
    global _cache_dirty, _last_save_time
    if not _cache_dirty:
        return
    current_time = time.time()
    if not force and (current_time - _last_save_time < 10):
        return
    # Non-blocking: save in background thread
    threading.Thread(target=_do_save_cache, daemon=True).start()

def cache_put(key, value):
    global _cache_dirty
    # Safety Check: Never cache error messages as translations
    if not value or "Error 500" in str(value) or "Server Error" in str(value):
        return

    with _cache_lock:
        PERSISTENT_CACHE[key] = value
        _CACHE_INDEX[key.lower()] = value
        _cache_dirty = True

# For backward compat with prime script
def save_cache(cache_data):
    save_cache_to_disk()

PERSISTENT_CACHE = load_cache()
SUPPORTED_LANGUAGES = SUPPORTED_LANGUAGE_CODES

# Build a lowercase lookup index at startup for O(1) case-insensitive lookups
_CACHE_INDEX = {k.lower(): v for k, v in PERSISTENT_CACHE.items()}


# ============ SCHEME STEPS TRANSLATOR ============

def translate_scheme_steps(texts, target_lang):
    """Translate scheme application steps using the Indic provider and safe cache keys."""
    if not texts or target_lang not in SUPPORTED_LANGUAGES or target_lang == 'en':
        return texts

    results = [None] * len(texts)
    pending = []
    for index, text in enumerate(texts):
        cache_key = f"scheme_step:{target_lang}:{text}"
        cached = PERSISTENT_CACHE.get(cache_key)
        if cached and cached != text:
            results[index] = cached
        else:
            pending.append((index, text, cache_key))

    # Try Bhashini native batch first
    if pending:
        pending_texts = [text for _, text, _ in pending]
        batch_result = _translate_batch_with_bhashini(pending_texts, 'en', target_lang)
        if batch_result and len(batch_result) == len(pending):
            for (index, source, cache_key), translated in zip(pending, batch_result):
                if translated:
                    results[index] = translated
                    cache_put(cache_key, translated)

    # Fallback: parallel GTX for anything still missing
    still_pending = [(i, s, ck) for i, s, ck in pending if results[i] is None]
    if still_pending:
        def _gtx_one(item):
            index, source, cache_key = item
            translated = _translate_with_google_gtx(source, target_lang)
            if translated and translated.strip() and translated.strip().casefold() != source.casefold():
                return index, translated.strip(), cache_key
            return index, source, cache_key
        futures = [_translate_pool.submit(_gtx_one, item) for item in still_pending]
        for f in as_completed(futures):
            try:
                index, translated, cache_key = f.result()
                results[index] = translated
                if translated != still_pending[0][1]:  # != source
                    cache_put(cache_key, translated)
            except:
                pass
        # Fill any remaining Nones
        for index, source, _ in still_pending:
            if results[index] is None:
                results[index] = source

    save_cache_to_disk()
    return results

# ============ LANGUAGE DETECTION ============

def detect_language(text):
    if not text or len(text.strip()) < 2:
        return 'en'
    scripts = {
        'hi': r'[\u0900-\u097F]', 'as': r'[\u0980-\u09FF]',
        'bn': r'[\u0980-\u09FF]', 'gu': r'[\u0A80-\u0AFF]',
        'or': r'[\u0B00-\u0B7F]', 'ta': r'[\u0B80-\u0BFF]',
        'te': r'[\u0C00-\u0C7F]', 'kn': r'[\u0C80-\u0CFF]',
        'ml': r'[\u0D00-\u0D7F]', 'pa': r'[\u0A00-\u0A7F]',
        'ur': r'[\u0600-\u06FF]', 'ks': r'[\u0600-\u06FF]',
        'sat': r'[\u1C50-\u1C7F]'
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

def translate_to_english(text, source_lang=None):
    """Translate text to English. GTX first (fastest), then fallbacks."""
    if not text:
        return text

    source_lang = source_lang if source_lang in SUPPORTED_LANGUAGES else None
    cache_key = f"to_en:{source_lang}:{text}" if source_lang else f"to_en:{text}"

    # Check cache first
    cached = PERSISTENT_CACHE.get(cache_key)
    if cached:
        return cached
    cached = _CACHE_INDEX.get(cache_key.lower())
    if cached:
        return cached

    # 1. GTX first – fastest
    result = _translate_with_google_gtx(text, 'en', source_lang or 'auto')
    if result and result.strip() and result != text:
        cache_put(cache_key, result)
        save_cache_to_disk()
        return result

    # 2. deep-translator fallback
    try:
        translator = GoogleTranslator(source=source_lang or 'auto', target='en')
        result = translator.translate(text)
        if result and result != text:
            cache_put(cache_key, result)
            save_cache_to_disk()
            return result
    except Exception:
        pass

    # 3. Bhashini fallback
    if source_lang and source_lang != 'en':
        result = _translate_with_bhashini(text, source_lang, 'en')
        if result:
            cache_put(cache_key, result)
            save_cache_to_disk()
            return result

    return text

def translate_from_english(text, target_lang):
    """Translate a single text from English. Cache-first, then API."""
    if not text or not target_lang or target_lang == 'en':
        return text

    cache_key = f"{target_lang}:{text}"
    cached = PERSISTENT_CACHE.get(cache_key)
    if cached and cached != text:
        return cached
    # Case-insensitive fallback
    cached = _CACHE_INDEX.get(cache_key.lower())
    if cached and cached != text:
        return cached

    # For long compound text, split and translate parts in batch
    if len(text) > 100 and ('. ' in text or '\n' in text):
        separator = '\n' if '\n' in text else '. '
        parts = [p.strip() for p in text.split(separator) if p.strip()]
        translated_parts = translate_batch_from_english(parts, target_lang)
        result = separator.join(translated_parts)
        if result:
            cache_put(cache_key, result)
            save_cache_to_disk()
        return result

    # Single text – fast path
    result = _translate_single(text, target_lang)
    if result and result != text:
        cache_put(cache_key, result)
        save_cache_to_disk()
    return result


def translate_batch_from_english(texts, target_lang):
    """Batch translation. Cache-first, then Bhashini batch API, then parallel GTX."""
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
        "E-Shram": {"hi": "ई-श्रम", "ta": "இ-ஷ்ரம்", "te": "ఈ-శ్రమ్", "mr": "ई-श्रम"},
        "Jan Dhan": {"hi": "जन धन", "ta": "ஜன் தன்", "te": "జన్ ధన్", "mr": "जन धन"},
        "Ujjwala": {"hi": "उज्ज्वला", "ta": "உஜ்வாலா", "te": "ఉజ్వల", "mr": "उज्ज्वला"},
        "Mudra": {"hi": "मुद्रा", "ta": "முத்ரா", "te": "ముద్రా", "mr": "मुद्रा"},
        "Aadhaar": {"hi": "आधार", "ta": "ஆதார்", "te": "ఆధార్", "mr": "आधार", "kn": "ಆಧಾರ್", "ml": "ಆಧಾರ್", "gu": "આધાર", "bn": "আধার"},
    }

    # --- Term Mapping (Bidirectional Enhancement) ---
    TERM_MAPPING = {
        "kisan": "farmer",
        "mazdoor": "worker",
        "chatra": "student",
        "vidyarthi": "student",
        "divyang": "disabled",
        "viklang": "disabled",
        "udyami": "entrepreneur",
        "mahila": "woman",
        "nari": "woman",
        "gramin": "rural",
        "shehari": "urban"
    }

    for frag in unique_fragments:
        if not frag:
            fragment_results[frag] = frag
            continue

        frag_clean = frag.strip()
        frag_lower = frag_clean.lower()

        # Apply Term Mapping first
        if frag_lower in TERM_MAPPING:
            frag_clean = TERM_MAPPING[frag_lower]

        # Check hardcoded fixes first
        if frag_clean in PROPER_NOUN_FIXES and target_lang in PROPER_NOUN_FIXES[frag_clean]:
            fragment_results[frag] = PROPER_NOUN_FIXES[frag_clean][target_lang]
            continue

        cache_key = f"{target_lang}:{frag_clean}"
        cached = PERSISTENT_CACHE.get(cache_key)

        if not cached:
            # O(1) case-insensitive lookup via pre-built index
            cached = _CACHE_INDEX.get(cache_key.lower())

        if cached and cached != frag_clean:
            fragment_results[frag] = cached
        else:
            to_translate.append(frag_clean)

    # 3. Translate missing fragments – Bhashini batch first, then parallel GTX
    if to_translate:
        # === STRATEGY A: Try Bhashini native batch API (ONE HTTP call for ALL texts) ===
        bhashini_results = _translate_batch_with_bhashini(to_translate, 'en', target_lang)
        if bhashini_results and len(bhashini_results) == len(to_translate):
            still_missing = []
            for frag, translated in zip(to_translate, bhashini_results):
                if translated:
                    fragment_results[frag] = translated
                    cache_put(f"{target_lang}:{frag}", translated)
                else:
                    still_missing.append(frag)
        else:
            still_missing = list(to_translate)

        # === STRATEGY B: Parallel GTX for anything Bhashini missed ===
        if still_missing:
            def _gtx_translate(frag):
                result = _translate_with_google_gtx(frag, target_lang)
                if result and result.strip() and result.strip().casefold() != frag.strip().casefold():
                    return frag, result.strip()
                # Last resort: deep-translator
                result = _translate_with_deep_translator(frag, target_lang)
                if result:
                    return frag, result
                return frag, frag

            futures = {_translate_pool.submit(_gtx_translate, frag): frag for frag in still_missing}
            for future in as_completed(futures):
                try:
                    orig, translated = future.result()
                    fragment_results[orig] = translated
                    if translated != orig:
                        cache_put(f"{target_lang}:{orig}", translated)
                except Exception:
                    frag = futures[future]
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
