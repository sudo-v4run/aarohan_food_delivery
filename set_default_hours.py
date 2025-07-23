import sqlite3

def set_default_hours():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    open_time = '09:00'
    close_time = '22:00'
    cursor.execute('SELECT id, name FROM restaurants')
    restaurants = cursor.fetchall()
    for rid, name in restaurants:
        for day in days:
            cursor.execute('SELECT 1 FROM restaurant_hours WHERE restaurant_id=? AND day_of_week=?', (rid, day))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO restaurant_hours (restaurant_id, day_of_week, open_time, close_time) VALUES (?, ?, ?, ?)',
                               (rid, day, open_time, close_time))
                print(f"Set hours for {name} on {day}: {open_time}-{close_time}")
    conn.commit()
    conn.close()
    print('Default hours set for all restaurants.')

if __name__ == '__main__':
    set_default_hours() 