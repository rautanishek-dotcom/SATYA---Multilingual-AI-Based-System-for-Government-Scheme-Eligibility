import sqlite3

conn = sqlite3.connect('bhashini_cache.db')
c = conn.cursor()
c.execute("SELECT target_lang, COUNT(*) FROM translations WHERE status='ok' GROUP BY target_lang")
with open('cache_ok_report.utf8.txt', 'w', encoding='utf-8') as f:
    for row in c.fetchall():
        f.write(f"{row[0]}: {row[1]}\n")
