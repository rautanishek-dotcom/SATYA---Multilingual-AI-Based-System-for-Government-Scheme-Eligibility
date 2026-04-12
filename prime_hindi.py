import os
import sys
sys.path.insert(0, './backend')
import time
from database import init_db, get_db
from routes.translator_utils import translate_batch_from_english, translate_from_english

class DummyApp: pass
init_db(DummyApp())
db = get_db()

print("Priming Scheme Translations...")
schemes = list(db.schemes.find({}))
text_fields = ['name', 'description', 'target_beneficiaries', 'application_process', 'benefits', 'steps']

all_text = []
for s in schemes:
    for field in text_fields:
        if s.get(field):
            all_text.append(s[field])
    
print(f"Translating {len(all_text)} scheme fields to Hindi...")
# Process in batches of 10 to avoid huge timeout
for i in range(0, len(all_text), 10):
    batch = all_text[i:i+10]
    translate_batch_from_english(batch, 'hi')
    print(f"Processed {i+len(batch)}/{len(all_text)}")
    time.sleep(2)

print("\nPriming FAQs...")
faqs = list(db.faqs.find({}))
for i, f in enumerate(faqs):
    en_data = f.get('en', f)
    q = en_data.get('question')
    a = en_data.get('answer')
    if q: translate_from_english(q, 'hi')
    if a: translate_from_english(a, 'hi')
    if i % 10 == 0:
        print(f"Processed FAQ {i}/{len(faqs)}")
        
print("DONE!")
