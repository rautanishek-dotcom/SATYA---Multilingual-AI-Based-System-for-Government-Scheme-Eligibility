from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['Satya']

deadlines_map = [
    (r"PM-KISAN|Kisan Samman", "2026-10-31", "fixed"),
    (r"Fasal Bima|PMFBY", "2026-10-15", "fixed"),
    (r"NREGA|MGNREGA", "2026-11-30", "ongoing"),
    (r"Awas|PMAY", "2026-12-15", "fixed"),
    (r"Gruha Lakshmi|Yuva Nidhi|Ladki Bahin|Saraswati|Kanyashree|Ayushman|Ujjwala|Mudra|Vishwakarma", "2026-10-25", "fixed"),
    (r"Farmer|Scholarship|Education|Loan|Pension|Women|Senior", "2026-11-15", "fixed")
]

updated_total = 0
for pattern, deadline_date, status in deadlines_map:
    res = db.schemes.update_many(
        {"name": {"$regex": pattern, "$options": "i"}},
        {"$set": {"application_deadline": deadline_date, "deadline_status": status}}
    )
    updated_total += res.modified_count
    print(f"Pattern '{pattern}': updated {res.modified_count} schemes")

print(f"Total schemes updated with deadlines: {updated_total}")
