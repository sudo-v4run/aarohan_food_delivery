from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import json
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.partner_routes import partner_bp
from routes.delivery_routes import delivery_bp
from flask_socketio import SocketIO
import logging

app = Flask(__name__)
app.secret_key = 'secret123'  # Used to manage sessions

# Initialize SocketIO
socketio = SocketIO(app, async_mode='eventlet')
app.extensions = getattr(app, 'extensions', {})
app.extensions['socketio'] = socketio

# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(partner_bp)
app.register_blueprint(delivery_bp)

# Import socketio events and emit functions
# import socketio_events

# Initialize the database
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Orders table
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    items TEXT NOT NULL,
    total REAL NOT NULL,
    address_id INTEGER,
    payment_mode TEXT,
    order_status TEXT DEFAULT 'Order Placed',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)''')

    # Restaurants table
    cursor.execute('''CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cuisine TEXT,
        rating REAL DEFAULT 0,
        delivery_time INTEGER,
        thumbnail TEXT,
        is_open INTEGER DEFAULT 1
    )''')

    # Food Items table (link to restaurant)
    cursor.execute('''CREATE TABLE IF NOT EXISTS food_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        image TEXT,
        FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
    )''')

    # Insert sample restaurants if empty
    cursor.execute("SELECT COUNT(*) FROM restaurants")
    if cursor.fetchone()[0] == 0:
        restaurant_samples = [
            ('Pizza Palace', 'Italian', 4.5, 30, '', 1),
            ('Burger Hub', 'American', 4.2, 25, '', 1),
            ('Spice Villa', 'Indian', 4.7, 35, '', 1),
        ]
        cursor.executemany("INSERT INTO restaurants (name, cuisine, rating, delivery_time, thumbnail, is_open) VALUES (?, ?, ?, ?, ?, ?)", restaurant_samples)

    # Insert sample food items if empty
    cursor.execute("SELECT COUNT(*) FROM food_items")
    if cursor.fetchone()[0] == 0:
        # Get restaurant ids
        cursor.execute("SELECT id FROM restaurants ORDER BY id")
        rids = [row[0] for row in cursor.fetchall()]
        food_samples = [
            (rids[0], 'Margherita Pizza', 199, 'Classic cheese pizza with herbs', ''),
            (rids[0], 'Farmhouse Pizza', 249, 'Loaded with veggies and cheese', ''),
            (rids[1], 'Veg Burger', 99, 'Crispy patty with lettuce and mayo', ''),
            (rids[1], 'French Fries', 79, 'Golden potato fries with masala', ''),
            (rids[2], 'Paneer Wrap', 149, 'Soft wrap stuffed with spicy paneer', ''),
            (rids[2], 'Masala Dosa', 129, 'South Indian rice crepe with spicy potato', ''),
        ]
        cursor.executemany("INSERT INTO food_items (restaurant_id, name, price, description, image) VALUES (?, ?, ?, ?, ?)", food_samples)

    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )''')

    # Addresses table
    cursor.execute('''CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        address TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Reviews table
    cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        restaurant_id INTEGER NOT NULL,
        order_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        review TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(restaurant_id) REFERENCES restaurants(id),
        FOREIGN KEY(order_id) REFERENCES orders(id)
    )''')

    # Restaurant Owners table (now with restaurant_id)
    cursor.execute('''CREATE TABLE IF NOT EXISTS restaurant_owners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        contact TEXT,
        restaurant_id INTEGER,
        FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
    )''')

    # Restaurant Hours table
    cursor.execute('''CREATE TABLE IF NOT EXISTS restaurant_hours (
        restaurant_id INTEGER NOT NULL,
        day_of_week TEXT NOT NULL,
        open_time TEXT NOT NULL,
        close_time TEXT NOT NULL,
        PRIMARY KEY (restaurant_id, day_of_week),
        FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
    )''')
    # Restaurant Holidays table
    cursor.execute('''CREATE TABLE IF NOT EXISTS restaurant_holidays (
        restaurant_id INTEGER NOT NULL,
        holiday_date TEXT NOT NULL,
        PRIMARY KEY (restaurant_id, holiday_date),
        FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
    )''')

    # Delivery Partners table
    cursor.execute('''CREATE TABLE IF NOT EXISTS delivery_partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        vehicle_number TEXT,
        vehicle_type TEXT,
        is_available INTEGER DEFAULT 1,
        current_location TEXT,
        rating REAL DEFAULT 0,
        total_deliveries INTEGER DEFAULT 0
    )''')

    # Delivery Orders table (to track which delivery partner is assigned to which order)
    cursor.execute('''CREATE TABLE IF NOT EXISTS delivery_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        delivery_partner_id INTEGER,
        pickup_time DATETIME,
        delivery_time DATETIME,
        status TEXT DEFAULT 'Assigned',
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(delivery_partner_id) REFERENCES delivery_partners(id)
    )''')

    # Delivery Ratings table (for customers to rate delivery partners)
    cursor.execute('''CREATE TABLE IF NOT EXISTS delivery_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        delivery_partner_id INTEGER NOT NULL,
        customer_username TEXT NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        review TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(delivery_partner_id) REFERENCES delivery_partners(id),
        UNIQUE(order_id, delivery_partner_id)
    )''')

    # Insert sample delivery partners if empty
    cursor.execute("SELECT COUNT(*) FROM delivery_partners")
    if cursor.fetchone()[0] == 0:
        delivery_samples = [
            ('delivery1', 'password123', 'Rahul Kumar', '9876543210', 'DL01AB1234', 'Bike', 1, 'Central Delhi', 4.5, 25),
            ('delivery2', 'password123', 'Priya Singh', '9876543211', 'MH02CD5678', 'Scooter', 1, 'Mumbai Central', 4.2, 18),
            ('delivery3', 'password123', 'Amit Patel', '9876543212', 'KA03EF9012', 'Bike', 0, 'Bangalore South', 4.7, 32),
        ]
        cursor.executemany("INSERT INTO delivery_partners (username, password, name, phone, vehicle_number, vehicle_type, is_available, current_location, rating, total_deliveries) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", delivery_samples)

    conn.commit()
    conn.close()

# All user/customer-related routes have been moved to routes/user_routes.py and are now removed from this file.
# Only admin and partner routes, database setup, and app setup remain.

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        order_id = request.form['order_id']
        new_status = request.form['order_status']
        cursor.execute('UPDATE orders SET order_status=? WHERE id=?', (new_status, order_id))
        conn.commit()
        flash('Order status updated!', 'success')
    cursor.execute("SELECT id, username, items, total, timestamp, order_status FROM orders ORDER BY timestamp DESC")
    all_orders = cursor.fetchall()
    conn.close()

    import json
    orders = []
    for oid, username, items, total, timestamp, order_status in all_orders:
        item_list = json.loads(items)
        orders.append({
            'id': oid,
            'username': username,
            'items': item_list,
            'total': total,
            'timestamp': timestamp,
            'order_status': order_status
        })
    status_options = ['Order Placed', 'Preparing', 'Ready', 'Out for Delivery', 'Delivered']
    return render_template('admin.html', orders=orders, status_options=status_options)

# ✅ View All Food Items
@app.route('/admin/foods')
def admin_foods():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM food_items")
    foods = cursor.fetchall()
    conn.close()

    return render_template('admin_foods.html', foods=foods)

# ✅ Add New Food Item
@app.route('/admin/foods/add', methods=['POST'])
def add_food():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('login'))

    name = request.form['name']
    price = request.form['price']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO food_items (name, price) VALUES (?, ?)", (name, price))
    conn.commit()
    conn.close()

    flash("Food item added!", "success")
    return redirect(url_for('admin_foods'))

# ✅ Delete Food Item
@app.route('/admin/foods/delete/<int:item_id>')
def delete_food(item_id):
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM food_items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

    flash("Food item deleted.", "danger")
    return redirect(url_for('admin_foods'))

# ✅ Admin Order Assignment
@app.route('/admin/assign_orders')
def admin_assign_orders():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get orders ready for delivery
    cursor.execute("SELECT id, username, items, total, timestamp, order_status FROM orders WHERE order_status = 'Ready' ORDER BY timestamp ASC")
    ready_orders = cursor.fetchall()
    
    # Get available delivery partners
    cursor.execute("SELECT id, name, vehicle_type, current_location, rating FROM delivery_partners WHERE is_available = 1")
    available_partners = cursor.fetchall()
    
    # Get already assigned orders
    cursor.execute("SELECT do.order_id, do.delivery_partner_id, dp.name FROM delivery_orders do JOIN delivery_partners dp ON do.delivery_partner_id = dp.id")
    assigned_orders = cursor.fetchall()
    
    conn.close()

    # Process orders
    orders = []
    for oid, username, items, total, timestamp, order_status in ready_orders:
        item_list = json.loads(items)
        # Check if already assigned
        assigned_to = None
        for assigned in assigned_orders:
            if assigned[0] == oid:
                assigned_to = assigned[2]
                break
        
        orders.append({
            'id': oid,
            'username': username,
            'items': item_list,
            'total': total,
            'timestamp': timestamp,
            'order_status': order_status,
            'assigned_to': assigned_to
        })

    return render_template('admin_assign_orders.html', orders=orders, partners=available_partners)

# ✅ Assign Order to Delivery Partner
@app.route('/admin/assign_order/<int:order_id>', methods=['POST'])
def assign_order_to_partner(order_id):
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('login'))

    delivery_partner_id = request.form['delivery_partner_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if order is already assigned
    cursor.execute("SELECT id FROM delivery_orders WHERE order_id = ?", (order_id,))
    if cursor.fetchone():
        flash('Order is already assigned!', 'error')
        conn.close()
        return redirect(url_for('admin_assign_orders'))
    
    # Assign order
    cursor.execute("INSERT INTO delivery_orders (order_id, delivery_partner_id, status) VALUES (?, ?, 'Assigned')", (order_id, delivery_partner_id))
    cursor.execute("UPDATE orders SET order_status = 'Out for Delivery' WHERE id = ?", (order_id,))
    
    conn.commit()
    conn.close()
    
    flash('Order assigned successfully!', 'success')
    return redirect(url_for('admin_assign_orders'))

@app.route('/partner_register', methods=['GET', 'POST'])
def partner_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        contact = request.form['contact']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO restaurant_owners (username, password, contact) VALUES (?, ?, ?)', (username, password, contact))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('partner_login'))
        except:
            flash('Username already exists!', 'danger')
        finally:
            conn.close()
    return render_template('partner_register.html')

@app.route('/partner_login', methods=['GET', 'POST'])
def partner_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM restaurant_owners WHERE username=? AND password=?', (username, password))
        owner = cursor.fetchone()
        conn.close()
        if owner:
            session['partner'] = username
            flash('Logged in as restaurant partner!', 'success')
            return redirect(url_for('partner_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('partner_login.html')

@app.route('/partner_dashboard')
def partner_dashboard():
    if 'partner' not in session:
        return redirect(url_for('partner_login'))
    return render_template('partner_dashboard.html', partner=session['partner'])

# Set up basic logging
logging.basicConfig(filename='app_errors.log', level=logging.ERROR,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Server Error: {error}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    init_db()
    socketio.run(app, port=5001, debug=True)
