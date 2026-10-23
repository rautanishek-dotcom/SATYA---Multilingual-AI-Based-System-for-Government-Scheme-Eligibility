import os
import json
from pymongo import MongoClient

LANGS = ["en", "hi", "bn", "mr", "te", "ta", "gu", "kn", "ml", "as", "brx", "doi", "ks", "kok", "mai", "mni", "ne", "or", "pa", "sa", "sat", "sd", "ur"]

def clean_dict_content(content: str) -> dict:
    pairs = {}
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('//') or line == '{' or line == '}' or line == '},':
            continue
        try:
            parts = line.split(":", 1)
            if len(parts) == 2:
                k = parts[0].strip().strip('"').strip("'")
                v = parts[1].strip()
                if v.endswith(','): v = v[:-1]
                v = v.strip('"').strip("'")
                if k and v:
                    pairs[k] = v
        except:
            pass
    return pairs

def main():
    print("--- DRY RUN REPORT ---")
    
    # 1. Evaluate i18n
    with open("frontend/src/i18n.js", "r", encoding="utf-8") as f:
        content = f.read()

    total_keys = 0
    missing_by_lang = {}
    placeholders_by_lang = {}
    
    # Extract English keys first for benchmark
    en_start = content.find("en: {")
    if en_start == -1: en_start = content.find("en:{")
    st = content.find("translation:", en_start)
    sd = content.find("{", st)
    d = 1
    ed = sd + 1
    while d > 0 and ed < len(content):
        if content[ed] == "{": d+=1
        elif content[ed] == "}": d-=1
        ed +=1
    en_dict = clean_dict_content(content[sd:ed])
    total_keys = len(en_dict)
    
    for lang in LANGS:
        missing_by_lang[lang] = 0
        placeholders_by_lang[lang] = 0
        
        pos = content.find(f"  {lang}: {{")
        if pos == -1:
            pos = content.find(f"{lang}: {{")
        if pos == -1:
            missing_by_lang[lang] = total_keys
            continue
            
        st = content.find("translation:", pos)
        sd = content.find("{", st)
        d = 1
        ed = sd + 1
        while d > 0 and ed < len(content):
            if content[ed] == "{": d+=1
            elif content[ed] == "}": d-=1
            ed +=1
        l_dict = clean_dict_content(content[sd:ed])
        
        for k, en_v in en_dict.items():
            if k not in l_dict:
                missing_by_lang[lang] += 1
            else:
                # Same as English is a placeholder except for certain known English terms
                if lang not in ["en", "hi", "bn"] and l_dict[k] == en_v:
                    if en_v.strip() not in ["SATYA", "OCR", "OTP", "API"]:
                        placeholders_by_lang[lang] += 1

    print(f"Total i18n Translation Keys per Lang: {total_keys}")
    
    tot_miss = sum(missing_by_lang.values())
    tot_place = sum(placeholders_by_lang.values())
    print(f"Total Missing i18n Keys: {tot_miss}")
    print(f"Total English Placeholders inside non-English dicts: {tot_place}")
    
    print("\ni18n Language Needs:")
    for lang in LANGS:
        if missing_by_lang[lang] > 0 or placeholders_by_lang[lang] > 0:
            print(f" - {lang}: {missing_by_lang[lang]} missing, {placeholders_by_lang[lang]} placeholders")

    # 2. Evaluate Schemes
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["satya"]
        schemes = list(db["schemes"].find({}))
        
        print(f"\nTotal Scheme Records: {len(schemes)}")
        
        schemes_incomplete = 0
        langs_missing_schemes = {l: 0 for l in LANGS}
        
        for s in schemes:
            trans = s.get("name_translations", {})
            en_name = s.get("name", "")
            comp = True
            for l in LANGS:
                if l not in trans or trans[l] == en_name:
                    if l != "en":
                        langs_missing_schemes[l] += 1
                        comp = False
            if not comp:
                schemes_incomplete += 1
                
        print(f"Schemes Requiring Translations: {schemes_incomplete}")
        print("\nScheme Translations Need By Language:")
        for k, v in langs_missing_schemes.items():
            if v > 0:
                print(f" - {k}: missing {v} scheme translations")
                
    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")

if __name__ == '__main__':
    main()
