"""
BHASHINI SATYA Translation Pipeline
=====================================
- Reads BHASHINI credentials from backend/.env only
- Uses batch=30 per API call (640 estimated total calls, within 1000 budget)
- Persistent SQLite cache for resumability
- Checkpointing: safe to stop/resume at any point
- Validates every translation before writing
- Protects existing en/hi/bn translations
- Preserves {{interpolation}} placeholders
- Writes to i18n.js and MongoDB only after validation
- API call accounting log

Usage:
  python bhashini_pipeline.py --dry-run        # Audit only, no writes
  python bhashini_pipeline.py --ui-only        # Translate i18n.js only
  python bhashini_pipeline.py --schemes-only   # Translate scheme names only
  python bhashini_pipeline.py                  # Full run
  python bhashini_pipeline.py --resume         # Resume from cache (default behavior)
"""

import os
import re
import sys
import json
import time
import math
import sqlite3
import shutil
import datetime
import requests
import argparse
from dotenv import load_dotenv
from pymongo import MongoClient

# ─── CONFIG ──────────────────────────────────────────────────────────────────
load_dotenv('backend/.env')

INFERENCE_KEY = os.getenv('BHASHINI_INFERENCE_KEY')
BATCH_SIZE = 50
APPROVED_CALLS = 1000
BHASHINI_URL = 'https://dhruva-api.bhashini.gov.in/services/inference/pipeline'
SERVICE_ID = 'ai4bharat/indictrans-v2-all-gpu--t4'

CACHE_DB = 'bhashini_cache.db'
API_LOG = 'bhashini_api_log.json'
QUALITY_REPORT = 'translation_quality_report.json'
I18N_PATH = 'frontend/src/i18n.js'

PROTECTED_LANGS = {'en', 'hi', 'bn'}
TARGET_LANGS = ['mr', 'te', 'ta', 'gu', 'kn', 'ml', 'as', 'brx', 'doi', 'ks', 'kok', 'mai', 'mni', 'ne', 'or', 'pa', 'sa', 'sat', 'sd', 'ur']
ALL_LANGS = ['en', 'hi', 'bn'] + TARGET_LANGS

TECHNICAL_TERMS = {'SATYA', 'Aadhaar', 'OCR', 'OTP', 'API', 'PAN', 'JWT', 'MongoDB', 'React', 'Flask', 'MGNREGA', 'PMKISAN', 'PMFBY', 'PMAY', 'APY', 'PM-SYM', 'DBT', 'BPL', 'APL', 'SECC', 'EWS', 'LIG', 'MIG', 'SHG', 'PMJDY', 'MUDRA'}

# ─── BHASHINI LANG CODES ──────────────────────────────────────────────────────
LANG_MAP = {
    'mr': 'mr', 'te': 'te', 'ta': 'ta', 'gu': 'gu', 'kn': 'kn',
    'ml': 'ml', 'as': 'as', 'brx': 'brx', 'doi': 'doi', 'ks': 'ks',
    'kok': 'kok', 'mai': 'mai', 'mni': 'mni', 'ne': 'ne', 'or': 'or',
    'pa': 'pa', 'sa': 'sa', 'sat': 'sat', 'sd': 'sd', 'ur': 'ur'
}

# ─── CACHE ────────────────────────────────────────────────────────────────────
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
    return row

def cache_set(conn, source, lang, translated, status):
    conn.execute('INSERT OR REPLACE INTO translations (source, target_lang, translated, status, timestamp) VALUES (?,?,?,?,?)',
                 (source, lang, translated, status, datetime.datetime.now().isoformat()))
    conn.commit()

# ─── API LOG ─────────────────────────────────────────────────────────────────
api_log = {'calls': [], 'summary': {'successful': 0, 'failed': 0, 'retries': 0, 'cache_hits': 0, 'cache_misses': 0, 'total_segments': 0}}

def log_call(lang, batch_size, success, retries=0):
    api_log['calls'].append({'timestamp': datetime.datetime.now().isoformat(), 'lang': lang, 'batch_size': batch_size, 'success': success, 'retries': retries})
    if success:
        api_log['summary']['successful'] += 1
        api_log['summary']['total_segments'] += batch_size
    else:
        api_log['summary']['failed'] += 1

def save_api_log():
    with open(API_LOG, 'w', encoding='utf-8') as f:
        json.dump(api_log, f, indent=2)

# ─── PLACEHOLDER PROTECTION ───────────────────────────────────────────────────
def extract_placeholders(text):
    return re.findall(r'\{\{[^\}]+\}\}', text)

def protect_placeholders(text):
    placeholders = extract_placeholders(text)
    protected = text
    mapping = {}
    for i, ph in enumerate(placeholders):
        token = f'SATYAPH{i}END'
        protected = protected.replace(ph, token)
        mapping[token] = ph
    return protected, mapping

def restore_placeholders(text, mapping):
    for token, ph in mapping.items():
        text = text.replace(token, ph)
    return text

# ─── VALIDATION ───────────────────────────────────────────────────────────────
def validate_translation(source, translated, lang):
    if not translated or not translated.strip():
        return False, 'empty'
    if translated.lower() in ['null', 'undefined', 'translation unavailable', 'error']:
        return False, 'api_artifact'
    if '<' in translated and '>' in translated:
        return False, 'html_corruption'
    # Check placeholders preserved
    src_ph = set(extract_placeholders(source))
    tgt_ph = set(extract_placeholders(translated))
    if src_ph != tgt_ph:
        return False, f'placeholder_mismatch: expected {src_ph}, got {tgt_ph}'
    # Identity check — reject if same as English for non-technical strings
    if source == translated and lang not in PROTECTED_LANGS:
        if source not in TECHNICAL_TERMS and len(source) > 3:
            return False, 'identical_to_english'
    return True, 'ok'

# ─── BHASHINI API ────────────────────────────────────────────────────────────
def bhashini_translate_batch(texts, target_lang, retries=3):
    """Translate a batch of texts. Returns list of translated strings (or None for failures)."""
    bhashini_lang = LANG_MAP.get(target_lang, target_lang)
    
    # Protect placeholders
    protected_texts = []
    mappings = []
    for t in texts:
        p, m = protect_placeholders(t)
        protected_texts.append(p)
        mappings.append(m)
    
    headers = {'Authorization': INFERENCE_KEY, 'Content-Type': 'application/json'}
    payload = {
        'pipelineTasks': [{'taskType': 'translation', 'config': {
            'language': {'sourceLanguage': 'en', 'targetLanguage': bhashini_lang},
            'serviceId': SERVICE_ID
        }}],
        'inputData': {'input': [{'source': t} for t in protected_texts]}
    }
    
    for attempt in range(retries):
        try:
            resp = requests.post(BHASHINI_URL, headers=headers, json=payload, timeout=40)
            if resp.status_code == 200:
                outputs = resp.json().get('pipelineResponse', [{}])[0].get('output', [])
                results = []
                for i, o in enumerate(outputs):
                    translated = o.get('target', '')
                    # Restore placeholders
                    translated = restore_placeholders(translated, mappings[i])
                    results.append(translated)
                log_call(target_lang, len(texts), True, retries=attempt)
                return results
            elif resp.status_code == 429:
                wait = (2 ** attempt) * 5
                print(f"  Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  API error {resp.status_code}: {resp.text[:200]}")
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  Request error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
    
    log_call(target_lang, len(texts), False, retries=retries)
    return [None] * len(texts)

# ─── i18n PARSER ─────────────────────────────────────────────────────────────
def extract_lang_dict(content, lang):
    pos = content.find(f'  {lang}: {{')
    if pos == -1: pos = content.find(f'{lang}: {{')
    if pos == -1: return {}, -1, -1
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
    return pairs, sd, ed

def rebuild_dict_block(pairs):
    lines = []
    for i, (k, v) in enumerate(pairs.items()):
        comma = ',' if i < len(pairs) - 1 else ''
        v_escaped = v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
        lines.append(f'      "{k}": "{v_escaped}"{comma}')
    return '{\n' + '\n'.join(lines) + '\n    }'

# ─── TRANSLATE UI ─────────────────────────────────────────────────────────────
def translate_ui(conn, dry_run=False):
    print('\n=== UI TRANSLATION ===')
    with open(I18N_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    en_dict, _, _ = extract_lang_dict(content, 'en')
    en_keys = list(en_dict.keys())
    en_vals = list(en_dict.values())
    print(f'English keys: {len(en_keys)}')
    
    quality_report = {}
    
    for lang in TARGET_LANGS:
        print(f'\nProcessing {lang}...')
        lang_dict, sd, ed = extract_lang_dict(content, lang)
        
        # Identify which keys need translation
        to_translate_keys = []
        to_translate_vals = []
        for k, en_v in en_dict.items():
            existing = lang_dict.get(k, '')
            # Skip if already translated (different from English for non-technical)
            if existing and existing != en_v:
                api_log['summary']['cache_hits'] += 1
                continue
            # Skip technical terms
            if en_v in TECHNICAL_TERMS or len(en_v.strip()) <= 2:
                lang_dict[k] = en_v  # Keep as-is
                continue
            # Check persisted cache
            cached = cache_get(conn, en_v, lang)
            if cached and cached[1] == 'ok':
                lang_dict[k] = cached[0]
                api_log['summary']['cache_hits'] += 1
                continue
            to_translate_keys.append(k)
            to_translate_vals.append(en_v)
        
        print(f'  Need to translate: {len(to_translate_keys)} strings')
        if dry_run:
            continue
        
        # Check remaining budget
        calls_needed = math.ceil(len(to_translate_vals) / BATCH_SIZE)
        total_used = api_log['summary']['successful'] + api_log['summary']['failed']
        if total_used + calls_needed > APPROVED_CALLS:
            print(f'  STOP: Budget risk. Used={total_used}, Need={calls_needed}, Budget={APPROVED_CALLS}')
            break
        
        failures = []
        for i in range(0, len(to_translate_vals), BATCH_SIZE):
            batch_keys = to_translate_keys[i:i+BATCH_SIZE]
            batch_vals = to_translate_vals[i:i+BATCH_SIZE]
            
            api_log['summary']['cache_misses'] += len(batch_vals)
            results = bhashini_translate_batch(batch_vals, lang)
            
            for j, (k, src, tgt) in enumerate(zip(batch_keys, batch_vals, results)):
                if tgt is None:
                    cache_set(conn, src, lang, '', 'failed')
                    failures.append({'key': k, 'source': src, 'reason': 'api_error'})
                    continue
                valid, reason = validate_translation(src, tgt, lang)
                if valid:
                    lang_dict[k] = tgt
                    cache_set(conn, src, lang, tgt, 'ok')
                else:
                    cache_set(conn, src, lang, tgt, f'invalid:{reason}')
                    failures.append({'key': k, 'source': src, 'translated': tgt, 'reason': reason})
            
            time.sleep(0.5)  # rate limit protection
        
        quality_report[lang] = {'failures': failures, 'translated': len(to_translate_keys) - len(failures)}
        
        # Rebuild dict block and inject back
        new_block = rebuild_dict_block({**en_dict, **lang_dict})
        content = content[:sd] + new_block + content[ed:]
        print(f'  Done: {len(to_translate_keys) - len(failures)} translated, {len(failures)} failures')
    
    if not dry_run:
        # Save i18n.js
        backup = I18N_PATH + f'.bak_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(I18N_PATH, backup)
        print(f'\nBackup saved: {backup}')
        with open(I18N_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print('i18n.js updated.')
    
    with open(QUALITY_REPORT, 'w', encoding='utf-8') as f:
        json.dump(quality_report, f, indent=2, ensure_ascii=False)
    print(f'Quality report saved: {QUALITY_REPORT}')

# ─── TRANSLATE SCHEMES ────────────────────────────────────────────────────────
def translate_schemes(conn, dry_run=False):
    print('\n=== SCHEME NAME TRANSLATION ===')
    try:
        mongo = MongoClient('mongodb://localhost:27017/')
        db = mongo['Satya']
        schemes_col = db['schemes']
    except Exception as e:
        print(f'MongoDB connection failed: {e}')
        return
    
    schemes = list(schemes_col.find({}, {'_id': 1, 'name': 1, 'name_translations': 1}))
    print(f'Total schemes: {len(schemes)}')
    
    if dry_run:
        needs = sum(1 for s in schemes for l in TARGET_LANGS if not s.get('name_translations', {}).get(l))
        print(f'Scheme translations needed: {needs}')
        return
    
    # Backup translation data
    backup = []
    for s in schemes:
        backup.append({'_id': str(s['_id']), 'name_translations': s.get('name_translations', {})})
    with open('scheme_translations_backup.json', 'w', encoding='utf-8') as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)
    print('Scheme translation backup saved: scheme_translations_backup.json')
    
    # Group schemes by language for efficient batching
    for lang in TARGET_LANGS:
        print(f'\nProcessing schemes for {lang}...')
        to_translate = []
        for s in schemes:
            en_name = s.get('name', '')
            existing_trans = s.get('name_translations', {}).get(lang, '')
            if existing_trans and existing_trans != en_name:
                api_log['summary']['cache_hits'] += 1
                continue
            cached = cache_get(conn, en_name, lang)
            if cached and cached[1] == 'ok':
                continue  # Will be applied below from cache
            to_translate.append((str(s['_id']), en_name))
        
        print(f'  Need translation: {len(to_translate)}')
        
        for i in range(0, len(to_translate), BATCH_SIZE):
            batch = to_translate[i:i+BATCH_SIZE]
            ids = [b[0] for b in batch]
            names = [b[1] for b in batch]
            
            total_used = api_log['summary']['successful'] + api_log['summary']['failed']
            if total_used >= APPROVED_CALLS:
                print('STOP: API budget exhausted.')
                break
            
            api_log['summary']['cache_misses'] += len(names)
            results = bhashini_translate_batch(names, lang)
            
            for scheme_id, en_name, tgt in zip(ids, names, results):
                if tgt is None:
                    cache_set(conn, en_name, lang, '', 'failed')
                    continue
                valid, reason = validate_translation(en_name, tgt, lang)
                if valid:
                    cache_set(conn, en_name, lang, tgt, 'ok')
                    schemes_col.update_one(
                        {'_id': __import__('bson').ObjectId(scheme_id)},
                        {'$set': {f'name_translations.{lang}': tgt}}
                    )
            time.sleep(0.5)
        
        # Apply cached translations for this lang
        for s in schemes:
            en_name = s.get('name', '')
            cached = cache_get(conn, en_name, lang)
            if cached and cached[1] == 'ok':
                schemes_col.update_one(
                    {'_id': s['_id']},
                    {'$set': {f'name_translations.{lang}': cached[0]}}
                )
    
    print('\nScheme translations done.')

# ─── FINAL AUDIT ─────────────────────────────────────────────────────────────
def final_audit(conn):
    print('\n=== FINAL AUDIT ===')
    with open(I18N_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    en_dict, _, _ = extract_lang_dict(content, 'en')
    
    for lang in ALL_LANGS:
        d, _, _ = extract_lang_dict(content, lang)
        missing = sum(1 for k in en_dict if k not in d)
        empty = sum(1 for v in d.values() if not v.strip())
        placeholders = 0
        if lang not in PROTECTED_LANGS:
            for k in en_dict:
                en_v = en_dict.get(k, '')
                t_v = d.get(k, '')
                if t_v == en_v and en_v not in TECHNICAL_TERMS and len(en_v) > 3:
                    placeholders += 1
        print(f'{lang}: keys={len(d)}, missing={missing}, empty={empty}, en_placeholders={placeholders}')
    
    try:
        mongo = MongoClient('mongodb://localhost:27017/')
        db = mongo['Satya']
        schemes = list(db['schemes'].find({}, {'name': 1, 'name_translations': 1}))
        complete = 0
        for s in schemes:
            t = s.get('name_translations', {})
            if all(t.get(l) and t[l] != s.get('name','') for l in TARGET_LANGS):
                complete += 1
        print(f'\nSchemes: total={len(schemes)}, complete_23_lang={complete}, incomplete={len(schemes)-complete}')
    except Exception as e:
        print(f'MongoDB audit error: {e}')

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--ui-only', action='store_true')
    parser.add_argument('--schemes-only', action='store_true')
    parser.add_argument('--resume', action='store_true', help='(default) Resume from cache')
    args = parser.parse_args()
    
    if not INFERENCE_KEY:
        print('STOP: BHASHINI_INFERENCE_KEY not configured.')
        sys.exit(1)
    
    print('BHASHINI credentials detected: YES')
    print(f'Mode: {"DRY RUN" if args.dry_run else "LIVE"}')
    print(f'Batch size: {BATCH_SIZE}')
    
    conn = init_cache()
    
    if args.dry_run:
        print('\n--- DRY RUN: No writes will be made ---')
        translate_ui(conn, dry_run=True)
        translate_schemes(conn, dry_run=True)
        return
    
    if not args.schemes_only:
        translate_ui(conn, dry_run=False)
    
    if not args.ui_only:
        translate_schemes(conn, dry_run=False)
    
    final_audit(conn)
    save_api_log()
    
    print('\n=== API CALL SUMMARY ===')
    s = api_log['summary']
    print(f"Successful requests: {s['successful']}")
    print(f"Failed requests:     {s['failed']}")
    print(f"Cache hits:          {s['cache_hits']}")
    print(f"Cache misses:        {s['cache_misses']}")
    print(f"Total segments:      {s['total_segments']}")
    total_used = s['successful'] + s['failed']
    print(f"Total API calls:     {total_used} / {APPROVED_CALLS} budget")
    conn.close()

if __name__ == '__main__':
    main()
