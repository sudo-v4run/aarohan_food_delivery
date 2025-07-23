import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Delete all reviews by users
cursor.execute('DELETE FROM reviews')
# Delete all orders by users
cursor.execute('DELETE FROM orders')
# Delete all users
cursor.execute('DELETE FROM users')

conn.commit()
conn.close()
print('All customer accounts, their orders, and reviews have been deleted.') 