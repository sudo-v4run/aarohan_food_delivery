import sqlite3

def fix_delivery_time(default_time=30):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE restaurants SET delivery_time=? WHERE delivery_time IS NULL OR delivery_time=0', (default_time,))
    conn.commit()
    conn.close()
    print(f'Set delivery_time={default_time} for all restaurants with missing or zero delivery time.')

if __name__ == '__main__':
    fix_delivery_time() 