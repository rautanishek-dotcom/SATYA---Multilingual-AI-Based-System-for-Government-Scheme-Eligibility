import json

with open('frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    content = f.read()

def extract_lang_dict(content, lang):
    pos = content.find(f'  {lang}: {{')
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

en_dict = extract_lang_dict(content, 'en')

print("TEST STRING IN EN:", en_dict.get('secVaultTitle'))
print("TEST STRING 2 IN EN:", en_dict.get('docAccepted'))

for lang in ['hi', 'mr', 'bn', 'te', 'ta']:
    d = extract_lang_dict(content, lang)
    print(f"\n{lang}:")
    print("  secVaultTitle:", repr(d.get('secVaultTitle')))
    print("  docAccepted:", repr(d.get('docAccepted')))
