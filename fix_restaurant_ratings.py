import sqlite3

def fix_restaurant_ratings():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM restaurants')
    restaurants = cursor.fetchall()
    for rid, name in restaurants:
        cursor.execute('SELECT AVG(rating) FROM reviews WHERE restaurant_id=?', (rid,))
        avg_rating = cursor.fetchone()[0]
        if avg_rating is not None:
            cursor.execute('UPDATE restaurants SET rating=? WHERE id=?', (avg_rating, rid))
            print(f"Updated {name} (ID: {rid}) to average rating {avg_rating:.2f}")
        else:
            cursor.execute('UPDATE restaurants SET rating=0 WHERE id=?', (rid,))
            print(f"Set {name} (ID: {rid}) rating to 0 (no reviews)")
    conn.commit()
    conn.close()
    print('All restaurant ratings updated.')

if __name__ == '__main__':
    fix_restaurant_ratings() 