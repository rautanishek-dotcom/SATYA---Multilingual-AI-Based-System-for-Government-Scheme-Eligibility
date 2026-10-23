import requests, json, sys, re

sys.stdout.reconfigure(encoding='utf-8')

# Test 1: Scheme list endpoint includes name_translations
r = requests.get('http://localhost:5000/api/schemes/?lang=hi', timeout=10)
print(f'Scheme list status: {r.status_code}, count: {len(r.json())}')
data = r.json()
s = data[0]

# name in API response?
has_name_trans = 'name_translations' in s
print(f'name_translations in scheme API response: {has_name_trans}')
if has_name_trans:
    trans = s.get('name_translations', {})
    print(f'  name_translations key count: {len(trans)}')
    for lc in ['hi', 'bn', 'kok', 'ur', 'sd', 'sat', 'mr', 'as']:
        val = trans.get(lc, 'MISSING')
        if val != 'MISSING':
            val = (val[:40] + '..') if len(val) > 40 else val
        print(f'  [{lc}]: {val}')

# Test 2: i18n.js structure
with open('frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    content = f.read()

lang_blocks = list(re.finditer(r'\n  ([a-z]{2,3}): \{\s*\n\s*translation:', content))
print(f'\nLanguage blocks in rebuilt i18n.js: {len(lang_blocks)}')
if len(lang_blocks) != 23:
    print('  WARNING: Expected exactly 23 language blocks!')
for m in lang_blocks:
    print(f'  {m.group(1)}')

# Test 3: Sample translations (the key column)
def get_translation(content, lang, key):
    lang_start = content.find(f'\n  {lang}: {{')
    if lang_start == -1:
        return 'LANG_NOT_FOUND'
    # get next lang block start to bound search
    next_pos = content.find('\n  ', lang_start + 10)
    # search forward for the key
    section_end = content.find('\n  ', next_pos + 5) if next_pos != -1 else len(content)
    section = content[lang_start:section_end + 5000]
    pat = f'"{key}":'
    key_pos = section.find(pat)
    if key_pos == -1:
        return 'KEY_NOT_FOUND'
    line = section[key_pos:key_pos+300].split('\n')[0]
    val = line.split(':', 1)[1].strip().strip(',').strip('"')
    return val

print('\nSample i18n key translations:')
langs_to_check = ['hi', 'bn', 'kok', 'ur', 'sd', 'sat']
keys_to_check = ['Home', 'Login', 'Schemes']
for lc in langs_to_check:
    vals = []
    for k in keys_to_check:
        v = get_translation(content, lc, k)
        vals.append(f'{k}="{v[:25]}"')
    print(f'  [{lc}]: {", ".join(vals)}')

# Test 4: Verify 'CheckEligibility' key (was previously failing)
print('\nCheckEligibility key in each language:')
for lc in langs_to_check:
    v = get_translation(content, lc, 'CheckEligibility')
    print(f'  [{lc}]: {v[:40]}')
