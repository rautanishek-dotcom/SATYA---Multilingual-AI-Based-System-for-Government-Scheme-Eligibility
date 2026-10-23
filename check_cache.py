import sqlite3

conn = sqlite3.connect('bhashini_cache.db')
c = conn.cursor()
c.execute('SELECT target_lang, status, COUNT(*) FROM translations GROUP BY target_lang, status')
for row in c.fetchall():
    print(f"{row[0]} [{row[1]}]: {row[2]}")
