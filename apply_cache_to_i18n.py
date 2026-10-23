import sqlite3

with open('frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    content = f.read()

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

conn = sqlite3.connect('bhashini_cache.db')
c = conn.cursor()

en_dict, _, _ = extract_lang_dict(content, 'en')
src_to_key = {}
for k, v in en_dict.items():
    src_to_key[v] = k

TARGET_LANGS = ['mr', 'te', 'ta', 'gu', 'kn', 'ml', 'as', 'brx', 'doi', 'ks', 'kok', 'mai', 'mni', 'ne', 'or', 'pa', 'sa', 'sat', 'sd', 'ur']

applied_total = 0

for lang in TARGET_LANGS:
    lang_dict, sd, ed = extract_lang_dict(content, lang)
    if sd == -1:
        print(f"Language {lang} block not found!")
        continue
    
    c.execute("SELECT source, translated FROM translations WHERE target_lang=? AND status='ok'", (lang,))
    lang_rows = c.fetchall()
    
    for src, trans in lang_rows:
        if src in src_to_key:
            k = src_to_key[src]
            lang_dict[k] = trans
            applied_total += 1
            
    # Combine en structure with updated values
    merged = {**en_dict, **lang_dict}
    new_block = rebuild_dict_block(merged)
    content = content[:sd] + new_block + content[ed:]
    print(f"Applied to {lang}")

with open('frontend/src/i18n.js', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"DONE! Applied total {applied_total} translations to i18n.js.")
