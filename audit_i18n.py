import re
import json

with open('frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    content = f.read()

LANGS = ['en','hi','bn','mr','te','ta','gu','kn','ml','as','brx','doi','ks','kok','mai','mni','ne','or','pa','sa','sat','sd','ur']
TECHNICAL = {'SATYA','OCR','OTP','API','Aadhaar','PAN','JWT'}

def extract_dict(content, lang):
    pos = content.find(f'  {lang}: {{')
    if pos == -1:
        pos = content.find(f'{lang}: {{')
    if pos == -1:
        return {}
    st = content.find('translation:', pos)
    sd = content.find('{', st)
    d = 1
    ed = sd + 1
    while d > 0 and ed < len(content):
        if content[ed] == '{': d += 1
        elif content[ed] == '}': d -= 1
        ed += 1
    pairs = {}
    for line in content[sd:ed].split('\n'):
        line = line.strip()
        if ':' not in line:
            continue
        parts = line.split(':', 1)
        k = parts[0].strip().strip('"').strip("'")
        v = parts[1].strip().rstrip(',').strip('"').strip("'")
        if k and v:
            pairs[k] = v
    return pairs

en_dict = extract_dict(content, 'en')
print(f'Total EN keys: {len(en_dict)}')
print()

results = {}
for lang in LANGS:
    d = extract_dict(content, lang)
    missing = sum(1 for k in en_dict if k not in d)
    empty = sum(1 for k, v in d.items() if not v.strip())
    placeholders = 0
    if lang not in ['en', 'hi', 'bn']:
        for k in en_dict:
            en_v = en_dict.get(k, '')
            t_v = d.get(k, '')
            if t_v == en_v and en_v not in TECHNICAL and len(en_v) > 3:
                placeholders += 1
    results[lang] = {'keys': len(d), 'missing': missing, 'empty': empty, 'placeholders': placeholders}
    print(f'{lang}: keys={len(d)}, missing={missing}, empty={empty}, en_placeholders={placeholders}')

with open('audit_i18n_results.json', 'w', encoding='utf-8') as f:
    json.dump({'total_en_keys': len(en_dict), 'langs': results}, f, indent=2)
print('\nFull results saved to audit_i18n_results.json')
