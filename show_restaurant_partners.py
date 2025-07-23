import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("\n=== Restaurants and Their Partner Usernames ===\n")
cursor.execute("SELECT r.id, r.name, o.username FROM restaurants r LEFT JOIN restaurant_owners o ON r.id = o.restaurant_id")
rows = cursor.fetchall()
for rid, rname, username in rows:
    print(f"Restaurant: {rname} (ID: {rid}) | Partner Username: {username if username else 'None'}")

conn.close() 