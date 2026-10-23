import sqlite3

conn = sqlite3.connect('bhashini_cache.db')
c = conn.cursor()

c.execute("SELECT status, COUNT(*) FROM translations GROUP BY status")
print("Cache DB status summary:")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
