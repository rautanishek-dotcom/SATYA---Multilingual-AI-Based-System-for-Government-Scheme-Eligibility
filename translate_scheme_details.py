"""
translate_scheme_details.py
Translates scheme descriptions, benefits, and target_beneficiaries across all 23 languages
and stores them in MongoDB Satya.schemes and bhashini_cache.db.
"""
import os
import sys
import json
import time
import sqlite3
import datetime
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
import urllib.parse
from deep_translator import GoogleTranslator

load_dotenv('backend/.env')

INFERENCE_KEY = os.getenv('BHASHINI_INFERENCE_KEY')
BHASHINI_URL = 'https://dhruva-api.bhashini.gov.in/services/inference/pipeline'
SERVICE_ID = 'ai4bharat/indictrans-v2-all-gpu--t4'
CACHE_DB = 'bhashini_cache.db'

# All 22 Indian languages to translate from English
TARGET_LANGS = [
    'hi', 'bn', 'mr', 'te', 'ta', 'gu', 'kn', 'ml', 'as', 'brx',
    'doi', 'ks', 'kok', 'mai', 'mni', 'ne', 'or', 'pa', 'sa', 'sat', 'sd', 'ur'
]

# Google Translate fallback mapping for languages with different codes or scripts
GOOGLE_LANG_MAP = {
    'kok': 'gom',        # Goan Konkani (Devanagari)
    'mni': 'mni-Mtei',   # Manipuri / Meitei
    'doi': 'doi',        # Dogri
    'mai': 'mai',        # Maithili
    'sa': 'sa',          # Sanskrit
    'sd': 'sd',          # Sindhi
    'ur': 'ur',          # Urdu
    'as': 'as',          # Assamese
    'bn': 'bn',          # Bengali
    'gu': 'gu',          # Gujarati
    'hi': 'hi',          # Hindi
    'kn': 'kn',          # Kannada
    'ml': 'ml',          # Malayalam
    'mr': 'mr',          # Marathi
    'ne': 'ne',          # Nepali
    'or': 'or',          # Odia
    'pa': 'pa',          # Punjabi
    'ta': 'ta',          # Tamil
    'te': 'te',          # Telugu
}

def init_cache():
    conn = sqlite3.connect(CACHE_DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS translations (
        source TEXT,
        target_lang TEXT,
        translated TEXT,
        status TEXT,
        timestamp TEXT,
        PRIMARY KEY (source, target_lang)
    )''')
    conn.commit()
    return conn

def get_cached(conn, source, lang):
    row = conn.execute('SELECT translated FROM translations WHERE source=? AND target_lang=?', (source, lang)).fetchone()
    if row and row[0] and row[0].strip() and row[0].strip() != source.strip():
        return row[0].strip()
    return None

def set_cached(conn, source, lang, translated):
    conn.execute('INSERT OR REPLACE INTO translations (source, target_lang, translated, status, timestamp) VALUES (?,?,?,?,?)',
                 (source, lang, translated, 'success', datetime.datetime.now().isoformat()))
    conn.commit()

def translate_with_google(text, lang):
    """Fallback translation via Google Translate (direct endpoint + deep_translator)"""
    gt_lang = GOOGLE_LANG_MAP.get(lang, lang)
    if not gt_lang:
        return None
    # Method 1: GoogleTranslator library
    try:
        t = GoogleTranslator(source='en', target=gt_lang).translate(text)
        if t and t.strip() and t.strip() != text.strip():
            return t.strip()
    except Exception:
        pass

    # Method 2: Direct Google Translate GTX endpoint
    try:
        encoded = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={gt_lang}&dt=t&q={encoded}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0]:
                res = "".join(seg[0] for seg in data[0] if seg and seg[0])
                if res and res.strip() and res.strip() != text.strip():
                    return res.strip()
    except Exception:
        pass
    return None

def translate_batch_bhashini(sources, target_lang):
    """Calls BHASHINI API for a batch of strings."""
    if not INFERENCE_KEY or target_lang == 'kok':
        return None  # kok returns 500 on BHASHINI, use fallback directly
    
    headers = {
        'Authorization': INFERENCE_KEY,
        'Content-Type': 'application/json',
        'User-Agent': 'SATYA-TranslationPipeline/1.0'
    }
    input_list = [{'source': s} for s in sources]
    payload = {
        'pipelineTasks': [{
            'taskType': 'translation',
            'config': {
                'language': {'sourceLanguage': 'en', 'targetLanguage': target_lang},
                'serviceId': SERVICE_ID
            }
        }],
        'inputData': {'input': input_list}
    }
    try:
        resp = requests.post(BHASHINI_URL, headers=headers, json=payload, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            out = data.get('pipelineResponse', [{}])[0].get('output', [])
            return [o.get('target', '') for o in out]
        else:
            return None
    except Exception:
        return None

def main():
    conn = init_cache()
    client = MongoClient('mongodb://localhost:27017/')
    db = client['Satya']
    schemes = list(db.schemes.find({}))
    print(f"Loaded {len(schemes)} schemes from MongoDB Satya.schemes")

    # Collect unique non-empty source strings from schemes
    desc_set = set(s.get('description', '').strip() for s in schemes if s.get('description', '').strip())
    ben_set = set(s.get('benefits', '').strip() for s in schemes if s.get('benefits', '').strip())
    target_set = set(s.get('target_beneficiaries', '').strip() for s in schemes if s.get('target_beneficiaries', '').strip())

    all_unique_texts = list(desc_set | ben_set | target_set)
    print(f"Unique strings to ensure translated: {len(all_unique_texts)} (Descriptions: {len(desc_set)}, Benefits: {len(ben_set)}, Targets: {len(target_set)})")

    # Translate for each target language
    for lang in TARGET_LANGS:
        needed = []
        for text in all_unique_texts:
            cached = get_cached(conn, text, lang)
            if not cached:
                needed.append(text)

        print(f"Language [{lang}]: {len(all_unique_texts) - len(needed)} cached, {len(needed)} needed")

        # Process needed in batches
        BATCH_SIZE = 25
        for i in range(0, len(needed), BATCH_SIZE):
            chunk = needed[i:i + BATCH_SIZE]
            results = None
            
            # Try BHASHINI first (if not kok)
            if lang != 'kok':
                results = translate_batch_bhashini(chunk, lang)
                time.sleep(0.3)

            # Fallback to Google / GTX if BHASHINI failed or was skipped
            if not results or len(results) != len(chunk) or any(not r for r in results):
                results = []
                for s in chunk:
                    tr = translate_with_google(s, lang)
                    if not tr:
                        # Secondary regional fallback for special languages
                        if lang == 'brx':
                            tr = translate_with_google(s, 'as') or translate_with_google(s, 'hi')
                        elif lang == 'sat':
                            tr = translate_with_google(s, 'bn')
                        elif lang == 'ks':
                            tr = translate_with_google(s, 'ur')
                    results.append(tr or s)
                    time.sleep(0.1)

            # Store results in cache
            for src, tr in zip(chunk, results):
                if tr and tr.strip() and tr.strip() != src.strip():
                    set_cached(conn, src, lang, tr.strip())
                elif tr:
                    set_cached(conn, src, lang, tr.strip())

    print("\n--- Translation caching complete. Now updating MongoDB scheme documents ---")

    # Update MongoDB schemes with full translation dictionaries
    updated_count = 0
    for scheme in schemes:
        name = scheme.get('name', '')
        desc = scheme.get('description', '').strip()
        ben = scheme.get('benefits', '').strip()
        target = scheme.get('target_beneficiaries', '').strip()

        desc_trans = scheme.get('description_translations', {})
        ben_trans = scheme.get('benefits_translations', {})
        target_trans = scheme.get('target_beneficiaries_translations', {})

        desc_trans['en'] = desc
        ben_trans['en'] = ben
        target_trans['en'] = target

        for lang in TARGET_LANGS:
            if desc:
                tr_desc = get_cached(conn, desc, lang)
                if tr_desc:
                    desc_trans[lang] = tr_desc
            if ben:
                tr_ben = get_cached(conn, ben, lang)
                if tr_ben:
                    ben_trans[lang] = tr_ben
            if target:
                tr_target = get_cached(conn, target, lang)
                if tr_target:
                    target_trans[lang] = tr_target

        db.schemes.update_one(
            {'_id': scheme['_id']},
            {'$set': {
                'description_translations': desc_trans,
                'benefits_translations': ben_trans,
                'target_beneficiaries_translations': target_trans
            }}
        )
        updated_count += 1

    print(f"Successfully updated {updated_count} schemes in MongoDB Satya.schemes with translations!")

if __name__ == '__main__':
    main()
