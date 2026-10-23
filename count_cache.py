import sqlite3

conn = sqlite3.connect('bhashini_cache.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM translations WHERE status='ok'")
print("Total OK translations in cache:", c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM translations WHERE status!='ok'")
print("Total non-OK in cache:", c.fetchone()[0])
