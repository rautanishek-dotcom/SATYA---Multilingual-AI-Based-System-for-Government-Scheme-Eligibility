import json
import time
from deep_translator import GoogleTranslator

CACHE_FILE = 'backend/data/translation_cache.json'
try:
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        cache = json.load(f)
except:
    cache = {}

print(f"Total cache items: {len(cache)}")
broken_keys = []
for k, v in cache.items():
    if k.endswith(v) or v.strip() == k.split(':', 1)[1].strip():
        # It's english!
        broken_keys.append(k)

print(f"Found {len(broken_keys)} broken (untranslated) items in cache. Repairing...")

def translate_slow(text, target):
    try:
        translated = GoogleTranslator(source='auto', target=target).translate(text)
        if translated and translated.strip() != text.strip():
            return translated
    except:
        pass
    return text

fixed = 0
for k in broken_keys:
    lang, text = k.split(':', 1)
    if not text.strip(): continue
    
    res = translate_slow(text, lang)
    if res and res.strip() != text.strip():
        cache[k] = res
        fixed += 1
        print(f"Fixed: {res}")
    time.sleep(1.5)  # slow it down!

with open(CACHE_FILE, 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print(f"Done! Repaired {fixed} out of {len(broken_keys)} items.")
