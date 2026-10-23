from pymongo import MongoClient

c = MongoClient('mongodb://localhost:27017/')
db = c['Satya']
schemes = list(db['schemes'].find({}, {'name': 1, 'name_translations': 1}))

print(f"Total schemes in MongoDB: {len(schemes)}")

LANGS = ['en', 'hi', 'bn', 'mr', 'te', 'ta', 'gu', 'kn', 'ml', 'as', 'brx', 'doi', 'ks', 'kok', 'mai', 'mni', 'ne', 'or', 'pa', 'sa', 'sat', 'sd', 'ur']

lang_counts = {l: 0 for l in LANGS}
for s in schemes:
    nt = s.get('name_translations', {})
    for l in LANGS:
        if nt.get(l) and nt[l] != s.get('name'):
            lang_counts[l] += 1

print("\nScheme localized names available per language:")
for l, count in lang_counts.items():
    print(f"  {l}: {count} / {len(schemes)}")
