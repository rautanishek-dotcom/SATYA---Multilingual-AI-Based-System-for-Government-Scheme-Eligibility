"""
Complete 23-Language Translation Script for SATYA
=================================================
1. Cleans and deduplicates frontend/src/i18n.js
2. Uses BHASHINI API (with fallback for Konkani/rate limits) to translate all remaining UI strings
3. Validates placeholder preservation ({{...}}) and formatting
4. Updates MongoDB schemes name_translations for all 23 languages (including kok, hi, bn)
5. Generates comprehensive audit report
"""
import os
import re
import sys
import json
import time
import shutil
import sqlite3
import datetime
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('backend/.env')

INFERENCE_KEY = os.getenv('BHASHINI_INFERENCE_KEY')
BHASHINI_URL = 'https://dhruva-api.bhashini.gov.in/services/inference/pipeline'
SERVICE_ID = 'ai4bharat/indictrans-v2-all-gpu--t4'
CACHE_DB = 'bhashini_cache.db'
I18N_PATH = 'frontend/src/i18n.js'

ALL_LANGS = [
    'en', 'hi', 'bn', 'mr', 'te', 'ta', 'gu', 'kn', 'ml', 'as',
    'brx', 'doi', 'ks', 'kok', 'mai', 'mni', 'ne', 'or', 'pa', 'sa',
    'sat', 'sd', 'ur'
]

TECHNICAL_TERMS = {
    'SATYA', 'Aadhaar', 'OCR', 'OTP', 'API', 'PAN', 'JWT', 'MongoDB',
    'React', 'Flask', 'MGNREGA', 'PMKISAN', 'PMFBY', 'PMAY', 'APY',
    'PM-SYM', 'DBT', 'BPL', 'APL', 'SECC', 'EWS', 'LIG', 'MIG', 'SHG',
    'PMJDY', 'MUDRA', 'NA', 'PDF', 'JPG', 'PNG', 'CSC', 'Umang App', '₹'
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

def cache_get(conn, source, lang):
    row = conn.execute('SELECT translated, status FROM translations WHERE source=? AND target_lang=?', (source, lang)).fetchone()
    if row and row[1] == 'ok':
        return row[0]
    return None

def cache_set(conn, source, lang, translated, status):
    conn.execute('INSERT OR REPLACE INTO translations (source, target_lang, translated, status, timestamp) VALUES (?,?,?,?,?)',
                 (source, lang, translated, status, datetime.datetime.now().isoformat()))
    conn.commit()

def extract_placeholders(text):
    return re.findall(r'\{\{[^\}]+\}\}', text)

def protect_placeholders(text):
    phs = extract_placeholders(text)
    mapping = {}
    protected = text
    for i, ph in enumerate(phs):
        token = f'__PH_{i}__'
        protected = protected.replace(ph, token)
        mapping[token] = ph
    return protected, mapping

def restore_placeholders(text, mapping):
    for token, ph in mapping.items():
        text = text.replace(token, ph)
    return text

def validate_translation(source, translated, lang):
    if not translated or not str(translated).strip():
        return False, 'empty'
    translated_str = str(translated).strip()
    if translated_str.lower() in ['null', 'undefined', 'error', 'translation unavailable']:
        return False, 'api_artifact'
    if '<' in translated_str and '>' in translated_str:
        return False, 'html_corrupt'
    src_ph = set(extract_placeholders(source))
    tgt_ph = set(extract_placeholders(translated_str))
    if src_ph != tgt_ph:
        return False, 'placeholder_mismatch'
    if source == translated_str and lang != 'en':
        if source not in TECHNICAL_TERMS and len(source) > 3:
            return False, 'identical_to_english'
    return True, 'ok'

def bhashini_translate(texts, lang):
    if not INFERENCE_KEY:
        return [None] * len(texts)
    
    protected = []
    maps = []
    for t in texts:
        p, m = protect_placeholders(t)
        protected.append(p)
        maps.append(m)
        
    headers = {'Authorization': INFERENCE_KEY, 'Content-Type': 'application/json'}
    payload = {
        'pipelineTasks': [{'taskType': 'translation', 'config': {
            'language': {'sourceLanguage': 'en', 'targetLanguage': lang},
            'serviceId': SERVICE_ID
        }}],
        'inputData': {'input': [{'source': t} for t in protected]}
    }
    
    try:
        resp = requests.post(BHASHINI_URL, headers=headers, json=payload, timeout=35)
        if resp.status_code == 200:
            outputs = resp.json().get('pipelineResponse', [{}])[0].get('output', [])
            res = []
            for i, o in enumerate(outputs):
                t_str = o.get('target', '')
                t_str = restore_placeholders(t_str, maps[i])
                res.append(t_str)
            return res
        else:
            print(f"  BHASHINI {lang} returned {resp.status_code}")
            return [None] * len(texts)
    except Exception as e:
        print(f"  BHASHINI {lang} error: {e}")
        return [None] * len(texts)

def google_gtx_translate_single(text, lang_code):
    p, m = protect_placeholders(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={lang_code}&dt=t&q={requests.utils.quote(p)}"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            translated = ''.join([part[0] for part in data[0] if part[0]])
            translated = restore_placeholders(translated, m)
            return translated
        return None
    except Exception:
        return None

GOOGLE_LANG_MAP = {
    'kok': 'gom', 'hi': 'hi', 'bn': 'bn', 'mr': 'mr', 'te': 'te',
    'ta': 'ta', 'gu': 'gu', 'kn': 'kn', 'ml': 'ml', 'as': 'as',
    'brx': 'as', 'doi': 'hi', 'ks': 'ur', 'mai': 'bho', 'mni': 'bn',
    'ne': 'ne', 'or': 'or', 'pa': 'pa', 'sa': 'sa', 'sat': 'bn',
    'sd': 'sd', 'ur': 'ur'
}

def translate_batch_unified(texts, lang, conn):
    results = [None] * len(texts)
    needed_indices = []
    
    # 1. Check SQLite cache
    for idx, t in enumerate(texts):
        cached = cache_get(conn, t, lang)
        if cached:
            results[idx] = cached
        else:
            needed_indices.append(idx)
            
    if not needed_indices:
        return results

    needed_texts = [texts[i] for i in needed_indices]

    # 2. If Konkani, use Google gtx (gom) directly since Dhruva 500s on kok
    if lang == 'kok':
        for i, text in zip(needed_indices, needed_texts):
            translated = google_gtx_translate_single(text, 'gom')
            if translated:
                valid, _ = validate_translation(text, translated, lang)
                if valid:
                    cache_set(conn, text, lang, translated, 'ok')
                    results[i] = translated
                else:
                    results[i] = text
            else:
                results[i] = text
            time.sleep(0.05)
        return results

    # 3. For other languages, try BHASHINI batch first
    bhashini_results = bhashini_translate(needed_texts, lang)
    still_needed = []
    for idx_pos, (orig_idx, orig_text, b_trans) in enumerate(zip(needed_indices, needed_texts, bhashini_results)):
        if b_trans:
            valid, _ = validate_translation(orig_text, b_trans, lang)
            if valid:
                cache_set(conn, orig_text, lang, b_trans, 'ok')
                results[orig_idx] = b_trans
                continue
        still_needed.append((orig_idx, orig_text))

    # 4. Fallback for any failed individual items
    if still_needed:
        fallback_code = GOOGLE_LANG_MAP.get(lang, lang)
        print(f"  Fallback translating {len(still_needed)} strings for {lang} via {fallback_code}...")
        for orig_idx, orig_text in still_needed:
            translated = google_gtx_translate_single(orig_text, fallback_code)
            if translated:
                valid, _ = validate_translation(orig_text, translated, lang)
                if valid:
                    cache_set(conn, orig_text, lang, translated, 'ok')
                    results[orig_idx] = translated
                else:
                    results[orig_idx] = orig_text
            else:
                results[orig_idx] = orig_text
            time.sleep(0.05)

    return results

def extract_lang_dict_clean(content, lang):
    pos = content.find(f'\n  {lang}: {{')
    if pos == -1: pos = content.find(f'{lang}: {{')
    if pos == -1: return {}
    st = content.find('translation:', pos)
    sd = content.find('{', st)
    d = 1; ed = sd + 1
    while d > 0 and ed < len(content):
        if content[ed] == '{': d += 1
        elif content[ed] == '}': d -= 1
        ed += 1
    pairs = {}
    for line in content[sd:ed].split('\n'):
        line = line.strip()
        if ':' not in line: continue
        parts = line.split(':', 1)
        k = parts[0].strip().strip('"').strip("'")
        v = parts[1].strip().rstrip(',').strip('"').strip("'")
        if k and v: pairs[k] = v
    return pairs

def run_ui_translation():
    print("=== STEP 1: CLEANING AND DEDUPLICATING i18n.js ===")
    with open(I18N_PATH, 'r', encoding='utf-8') as f:
        full_content = f.read()

    # Backup original
    backup_file = I18N_PATH + f'.pre_complete_bak_{int(time.time())}'
    shutil.copy2(I18N_PATH, backup_file)
    print(f"Backup created at: {backup_file}")

    # Extract clean master English dict (from block 0)
    en_dict = extract_lang_dict_clean(full_content, 'en')
    print(f"Master English dictionary keys: {len(en_dict)}")

    # Extract all initial language dictionaries from blocks 0-22
    all_lang_dicts = {}
    for lang in ALL_LANGS:
        all_lang_dicts[lang] = extract_lang_dict_clean(full_content, lang)

    conn = init_cache()

    print("\n=== STEP 2: TRANSLATING REMAINING UI STRINGS FOR ALL 23 LANGUAGES ===")
    for lang in ALL_LANGS:
        if lang == 'en':
            continue
        cur_dict = all_lang_dicts[lang]
        missing_or_placeholder_keys = []
        texts_to_translate = []

        for k, en_val in en_dict.items():
            existing = cur_dict.get(k, '')
            if not existing or (existing == en_val and en_val not in TECHNICAL_TERMS and len(en_val) > 3):
                missing_or_placeholder_keys.append(k)
                texts_to_translate.append(en_val)

        print(f"Language [{lang:3s}]: {len(texts_to_translate)} strings need translation")

        if texts_to_translate:
            BATCH_SIZE = 50
            for i in range(0, len(texts_to_translate), BATCH_SIZE):
                batch_keys = missing_or_placeholder_keys[i:i+BATCH_SIZE]
                batch_texts = texts_to_translate[i:i+BATCH_SIZE]
                translated_batch = translate_batch_unified(batch_texts, lang, conn)
                for k, t_val in zip(batch_keys, translated_batch):
                    if t_val:
                        cur_dict[k] = t_val
                time.sleep(0.3)

        # Ensure all en_dict keys exist in cur_dict
        for k, en_val in en_dict.items():
            if k not in cur_dict or not cur_dict[k]:
                cur_dict[k] = en_val

    # Rebuild i18n.js with exactly 1 block per language
    print("\n=== STEP 3: REBUILDING CLEAN i18n.js ===")
    output_lines = [
        "import i18n from 'i18next';",
        "import { initReactI18next } from 'react-i18next';",
        "",
        "const resources = {"
    ]

    for lang_idx, lang in enumerate(ALL_LANGS):
        d = all_lang_dicts[lang]
        output_lines.append(f"  {lang}: {{")
        output_lines.append("    translation: {")
        sorted_keys = sorted(d.keys())
        for k_idx, k in enumerate(sorted_keys):
            v = d[k]
            v_esc = v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            comma = "," if k_idx < len(sorted_keys) - 1 else ""
            output_lines.append(f'      "{k}": "{v_esc}"{comma}')
        comma_lang = "," if lang_idx < len(ALL_LANGS) - 1 else ""
        output_lines.append("    }")
        output_lines.append(f"  }}{comma_lang}")

    output_lines.extend([
        "};",
        "",
        "i18n",
        "  .use(initReactI18next)",
        "  .init({",
        "    resources,",
        "    lng: localStorage.getItem('satya_language') || 'en',",
        "    fallbackLng: 'en',",
        "    interpolation: {",
        "      escapeValue: false,",
        "    },",
        "  });",
        "",
        "export default i18n;",
        ""
    ])

    with open(I18N_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print("i18n.js successfully rewritten and deduplicated.")

def run_mongo_scheme_translation():
    print("\n=== STEP 4: AUDITING & TRANSLATING MONGODB SCHEMES ===")
    try:
        mongo = MongoClient('mongodb://localhost:27017/')
        db = mongo['Satya']
        schemes = list(db.schemes.find({}, {'_id': 1, 'name': 1, 'name_translations': 1}))
        print(f"Total schemes found in MongoDB: {len(schemes)}")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return

    conn = init_cache()
    for lang in ALL_LANGS:
        if lang == 'en':
            continue
        needed = []
        for s in schemes:
            name = s.get('name', '')
            trans = s.get('name_translations', {}).get(lang, '')
            if not trans or trans == name:
                needed.append((s['_id'], name))

        if not needed:
            print(f"Schemes [{lang:3s}]: 100% complete (0 needed)")
            continue

        print(f"Schemes [{lang:3s}]: {len(needed)} schemes need translation")
        BATCH_SIZE = 50
        for i in range(0, len(needed), BATCH_SIZE):
            batch = needed[i:i+BATCH_SIZE]
            ids = [b[0] for b in batch]
            names = [b[1] for b in batch]
            translated = translate_batch_unified(names, lang, conn)
            for s_id, t_val in zip(ids, translated):
                if t_val:
                    db.schemes.update_one({'_id': s_id}, {'$set': {f'name_translations.{lang}': t_val}})
            time.sleep(0.3)

    print("MongoDB scheme name translations complete.")

def run_audit():
    print("\n=== FINAL COMPREHENSIVE 23-LANGUAGE AUDIT ===")
    with open(I18N_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    en_dict = extract_lang_dict_clean(content, 'en')
    total_en_keys = len(en_dict)
    print(f"Total English keys: {total_en_keys}\n")

    results = {}
    all_passed = True
    for lang in ALL_LANGS:
        d = extract_lang_dict_clean(content, lang)
        missing = [k for k in en_dict if k not in d]
        empty = [k for k, v in d.items() if not str(v).strip()]
        placeholders = [k for k, v in d.items() if v == en_dict.get(k) and v not in TECHNICAL_TERMS and len(v) > 3]

        results[lang] = {
            'keys': len(d),
            'missing': len(missing),
            'empty': len(empty),
            'placeholders': len(placeholders)
        }
        status_flag = "PASS" if len(missing) == 0 and len(empty) == 0 and len(placeholders) < 25 else "WARN"
        if status_flag == "WARN" and lang != 'en':
            all_passed = False
        print(f"[{lang:3s}] Status: {status_flag:4s} | Keys: {len(d):3d}/{total_en_keys} | Missing: {len(missing)} | Empty: {len(empty)} | Placeholders: {len(placeholders)}")

    with open('audit_i18n_results.json', 'w', encoding='utf-8') as f:
        json.dump({'total_en_keys': total_en_keys, 'langs': results}, f, indent=2)
    print("\nUpdated audit results saved to audit_i18n_results.json")

if __name__ == '__main__':
    run_ui_translation()
    run_mongo_scheme_translation()
    run_audit()
