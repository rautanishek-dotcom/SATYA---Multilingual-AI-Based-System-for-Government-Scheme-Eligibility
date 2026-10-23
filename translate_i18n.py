import os
import json
import time
from typing import Dict, List
import translators as ts

# Language codes matching i18n
LANGS = ["mr", "te", "ta", "gu", "kn", "ml", "as", "doi", "ks", "kok", "mai", "mni", "ne", "or", "pa", "sa", "sat", "sd", "ur", "brx"]

# mapping to google translate codes
MAP_CODE = {
    "or": "or",    # Odia
    "as": "as",    # Assamese
    "pa": "pa",    # Punjabi
    "sa": "sa",    # Sanskrit
    "mai": "mai",  # Maithili
    "doi": "doi",  # Dogri
    "mni": "mni",  # Meiteilon (may not work well, fallback if needed)
    "kok": "kok",  # Konkani
    "ks": "ks",    # Kashmiri
    "sat": "sat",
    "brx": "hi",   # Fallback to Hindi if brx fails on all APIs
}

def clean_dict_content(content: str) -> Dict[str, str]:
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
        except Exception:
            pass
    return pairs

def robust_translate(text: str, target: str) -> str:
    # Try google
    try:
        return ts.translate_text(text, translator='google', from_language='en', to_language=target)
    except:
        # Try bing
        try:
            return ts.translate_text(text, translator='bing', from_language='en', to_language=target)
        except Exception as e:
            # Maybe language code unsupported? Fallback to hindi if really unsupported/failed
            try:
                return ts.translate_text(text, translator='google', from_language='en', to_language='hi')
            except:
                return text

def main():
    with open("frontend/src/i18n.js", "r", encoding="utf-8") as f:
        content = f.read()

    start_en = content.find("en: {")
    if start_en == -1:
        start_en = content.find("en:{")
    
    start_trans = content.find("translation:", start_en)
    start_dict = content.find("{", start_trans)
    dept = 1
    end_dict = start_dict + 1
    while dept > 0 and end_dict < len(content):
        if content[end_dict] == "{": dept += 1
        elif content[end_dict] == "}": dept -= 1
        end_dict += 1
        
    en_dict_content = content[start_dict:end_dict]
    en_keys = clean_dict_content(en_dict_content)
    
    print(f"Translating {len(en_keys)} core UI keys to 20 languages.")
    
    keys = list(en_keys.keys())
    values = list(en_keys.values())

    for lang in LANGS:
        gl_code = MAP_CODE.get(lang, lang)
        print(f"Translating for {lang} using {gl_code}...")
        
        translated_vals = []
        for i, val in enumerate(values):
            if val == "":
                translated_vals.append("")
                continue
            translated = robust_translate(val, gl_code)
            translated_vals.append(translated)
            
            # Print occasionally to show process
            if i % 100 == 0:
                print(f" {i}/{len(values)}")
            time.sleep(0.3)
            
        # Ensure parity
        if len(translated_vals) < len(values):
            translated_vals.extend(values[len(translated_vals):])
        if len(translated_vals) > len(values):
            translated_vals = translated_vals[:len(values)]
            
        # Replace in i18n
        search = f"  {lang}: {{"
        pos = content.find(search)
        if pos == -1:
            search = f"{lang}: {{"
            pos = content.find(search)
        if pos == -1:
            print(f"Lang {lang} not found in i18n.js!")
            continue
            
        start_trans = content.find("translation:", pos)
        start_dict = content.find("{", start_trans)
        dept = 1
        end_var = start_dict + 1
        while dept > 0 and end_var < len(content):
            if content[end_var] == "{": dept += 1
            elif content[end_var] == "}": dept -= 1
            end_var += 1
            
        new_pairs = []
        for i, k in enumerate(keys):
            val = translated_vals[i] if translated_vals[i] else values[i]
            # escape for JS
            val = val.replace('"', '\\"').replace('\n', ' ')
            new_pairs.append(f'      "{k}": "{val}"')
            
        injection = "{\n" + ",\n".join(new_pairs) + "\n    }"
        content = content[:start_dict] + injection + content[end_var:]
        
    with open("frontend/src/i18n.js", "w", encoding="utf-8") as f:
        f.write(content)
        
    print("UI Translations successfully injected!")

if __name__ == '__main__':
    main()
