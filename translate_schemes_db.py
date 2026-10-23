import os
import translators as ts
from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor

LANGS = ["mr", "te", "ta", "gu", "kn", "ml", "as", "doi", "ks", "kok", "mai", "mni", "ne", "or", "pa", "sa", "sat", "sd", "ur", "brx"]

MAP_CODE = {
    "or": "or", "as": "as", "pa": "pa", "sa": "sa", "mai": "mai",
    "doi": "doi", "mni": "mni", "kok": "kok", "ks": "ks", "sat": "sat",
    "brx": "hi"
}

def fast_translate(text: str, target: str) -> str:
    if not text: return text
    try:
        return ts.translate_text(text, translator='bing', from_language='en', to_language=target)
    except:
        try:
            return ts.translate_text(text, translator='google', from_language='en', to_language=target)
        except:
            return text

client = MongoClient("mongodb://localhost:27017/")
db = client["satya"]
schemes_col = db["schemes"]

def translate_scheme(s):
    name_translations = s.get('name_translations', {})
    en_name = s.get('name', '')
    
    updated = False
    for lang in LANGS:
        if lang not in name_translations or name_translations[lang] == en_name:
            if lang in ["en", "hi", "bn"]: continue
            gl_code = MAP_CODE.get(lang, lang)
            t = fast_translate(en_name, gl_code)
            if t and t != en_name:
                name_translations[lang] = t
                updated = True
    
    if updated:
        schemes_col.update_one({"_id": s["_id"]}, {"$set": {"name_translations": name_translations}})
        return 1
    return 0

def main():
    schemes = list(schemes_col.find({}))
    print(f"Translating {len(schemes)} schemes DB...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(translate_scheme, schemes))
    print("Scheme DB translations complete!")

if __name__ == '__main__':
    main()
