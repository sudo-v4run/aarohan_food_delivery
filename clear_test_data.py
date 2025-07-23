import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# List all tables to clear
# Add/remove table names as needed for your project
TABLES = [
    'orders',
    'delivery_orders',
    'users',
    'delivery_partners',
    'restaurant_partners'
]

for table in TABLES:
    cursor.execute(f"DELETE FROM {table}")
    print(f"Cleared table: {table}")

conn.commit()
conn.close()
print("All test/sample data removed. You can now add your own!") 