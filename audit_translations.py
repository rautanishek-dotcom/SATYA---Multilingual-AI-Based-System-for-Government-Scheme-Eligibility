from pymongo import MongoClient

LANG_CODES = ['en', 'hi', 'bn', 'mr', 'te', 'ta', 'gu', 'kn', 'ml', 'as', 'brx', 'doi', 'ks', 'kok', 'mai', 'mni', 'ne', 'or', 'pa', 'sa', 'sat', 'sd', 'ur']

client = MongoClient('mongodb://localhost:27017/')
db = client['Satya']
schemes = list(db.schemes.find({}))
total = len(schemes)

fully_covered = 0
missing_list = []

for s in schemes:
    nt = s.get('name_translations', {})
    if not isinstance(nt, dict):
        missing_list.append({'name': s.get('name'), 'missing_langs': LANG_CODES})
        continue
    m = [l for l in LANG_CODES if not nt.get(l)]
    if not m:
        fully_covered += 1
    else:
        missing_list.append({'name': s.get('name'), 'missing_langs': m})

print(f'Total schemes: {total}')
print(f'Fully covered (all 23 langs): {fully_covered}')
print(f'Missing translations: {len(missing_list)}')
for item in missing_list[:5]:
    print(f'  - {item["name"]} | missing: {item["missing_langs"]}')

# Sample check for a well-known scheme
sample = db.schemes.find_one({'name': {'$regex': 'Pradhan Mantri Kisan Samman', '$options': 'i'}})
if sample:
    nt_sample = sample.get('name_translations', {})
    print()
    print('Sample - PM Kisan Samman Nidhi translations:')
    for lang in ['en', 'hi', 'ta', 'kn', 'ml', 'bn', 'gu', 'ur', 'pa']:
        print(f'  [{lang}]: {nt_sample.get(lang, "MISSING")}')
