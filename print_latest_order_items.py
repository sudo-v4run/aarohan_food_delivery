import sqlite3
import json

def print_latest_order_items():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, items FROM orders ORDER BY id DESC LIMIT 5')
    rows = cursor.fetchall()
    for row in rows:
        print(f'Order ID: {row[0]}')
        print(f'Raw items field: {row[1]}')
        try:
            items = json.loads(row[1])
            print(f'Parsed items: {items}')
        except Exception as e:
            print(f'Error parsing items JSON: {e}')
        print('-' * 40)
    conn.close()

if __name__ == '__main__':
    print_latest_order_items() 