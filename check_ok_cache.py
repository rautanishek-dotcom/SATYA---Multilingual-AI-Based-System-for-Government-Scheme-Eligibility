import sqlite3

conn = sqlite3.connect('bhashini_cache.db')
c = conn.cursor()
c.execute("SELECT target_lang, COUNT(*) FROM translations WHERE status='ok' GROUP BY target_lang")
for row in c.fetchall():
    print(f"{row[0]}: {row[1]} cached OK translations")
