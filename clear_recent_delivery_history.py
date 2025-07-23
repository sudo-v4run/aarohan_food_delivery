import sqlite3

def clear_recent_delivery_history():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Delete only delivered orders from delivery_orders
    cursor.execute('DELETE FROM delivery_orders WHERE status = "Delivered"')
    conn.commit()
    conn.close()
    print('Recent delivery history cleared for all delivery partners.')

if __name__ == '__main__':
    clear_recent_delivery_history() 