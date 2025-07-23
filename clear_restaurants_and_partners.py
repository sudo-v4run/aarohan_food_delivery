import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Delete all restaurant owners (partners)
cursor.execute('DELETE FROM restaurant_owners')
# Delete all restaurants
cursor.execute('DELETE FROM restaurants')
# Optionally, delete all food items, hours, holidays, reviews related to restaurants
cursor.execute('DELETE FROM food_items')
cursor.execute('DELETE FROM restaurant_hours')
cursor.execute('DELETE FROM restaurant_holidays')
cursor.execute('DELETE FROM reviews')

conn.commit()
conn.close()
print('All restaurants and partner accounts have been deleted.') 