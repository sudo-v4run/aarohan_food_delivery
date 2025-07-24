from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
import json
import datetime
from realtime_utils import emit_new_order
import re
import logging

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def index():
    return render_template('index.html')

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        # Password strength check
        if len(pwd) < 8 or not re.search(r'[A-Za-z]', pwd) or not re.search(r'[0-9]', pwd):
            flash("Password must be at least 8 characters and include letters and numbers.", "danger")
            return render_template('register.html')
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=?", (uname,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash("Username already taken. Please choose another or use Forgot Password.", "danger")
            else:
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (uname, pwd))
                conn.commit()
                flash("Registration successful! Please login.", "success")
                conn.close()
                return redirect(url_for('user.login'))
            conn.close()
        except Exception as e:
            logging.error(f"Registration error: {e}")
            flash("An error occurred during registration. Please try again later.", "danger")
    return render_template('register.html')

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        try:
            # Admin check
            if uname == 'admin' and pwd == 'admin123':
                session['user'] = 'admin'
                session['admin'] = True
                return redirect(url_for('admin.admin_dashboard'))
            # Normal user check
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (uname, pwd))
            user = cursor.fetchone()
            conn.close()
            if user:
                session['user'] = uname
                session['admin'] = False
                return redirect(url_for('user.menu'))
            else:
                flash("Invalid credentials. Please try again or use Forgot Password.", "danger")
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash("An error occurred during login. Please try again later.", "danger")
    return render_template('login.html')

@user_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out.")
    return redirect(url_for('user.login'))

@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE username=?', (session['user'],))
        user = cursor.fetchone()
        user_id = user[0]
        username = user[1]
        current_password = user[2]
        # Handle profile update
        if request.method == 'POST' and 'update_profile' in request.form:
            new_username = request.form['new_username'].strip()
            new_password = request.form['new_password'].strip()
            error = None
            if new_username and new_username != username:
                cursor.execute('SELECT id FROM users WHERE username=?', (new_username,))
                if cursor.fetchone():
                    error = 'Username already taken.'
                else:
                    cursor.execute('UPDATE users SET username=? WHERE id=?', (new_username, user_id))
                    session['user'] = new_username
                    username = new_username
            if new_password:
                if len(new_password) < 8 or not re.search(r'[A-Za-z]', new_password) or not re.search(r'[0-9]', new_password):
                    error = 'Password must be at least 8 characters and include letters and numbers.'
                else:
                    cursor.execute('UPDATE users SET password=? WHERE id=?', (new_password, user_id))
            if error:
                flash(error, 'danger')
            else:
                conn.commit()
                flash('Profile updated!', 'success')
            return redirect(url_for('user.profile'))
        # Handle address update
        if request.method == 'POST' and 'update_address_id' in request.form:
            address_id = request.form['update_address_id']
            new_address = request.form['new_address'].strip()
            if not new_address:
                flash('Address cannot be empty.', 'danger')
            else:
                cursor.execute('UPDATE addresses SET address=? WHERE id=? AND user_id=?', (new_address, address_id, user_id))
                conn.commit()
                flash('Address updated!', 'success')
            return redirect(url_for('user.profile'))
        # Handle delete address
        if request.method == 'POST' and 'delete_address_id' in request.form:
            address_id = request.form['delete_address_id']
            cursor.execute('SELECT COUNT(*) FROM addresses WHERE user_id=?', (user_id,))
            address_count = cursor.fetchone()[0]
            if address_count <= 1:
                flash('At least one address is required. Cannot delete last address.', 'warning')
            else:
                cursor.execute('DELETE FROM addresses WHERE id=? AND user_id=?', (address_id, user_id))
                conn.commit()
                flash('Address deleted!', 'danger')
            return redirect(url_for('user.profile'))
        # Handle add address
        if request.method == 'POST' and 'add_address' in request.form:
            new_address = request.form['address'].strip()
            if not new_address:
                flash('Address cannot be empty.', 'danger')
            else:
                cursor.execute('INSERT INTO addresses (user_id, address) VALUES (?, ?)', (user_id, new_address))
                conn.commit()
                flash('Address added!', 'success')
            return redirect(url_for('user.profile'))
        cursor.execute('SELECT id, address FROM addresses WHERE user_id=?', (user_id,))
        addresses = cursor.fetchall()
    except Exception as e:
        logging.error(f"Profile/address error: {e}")
        flash('An error occurred while updating your profile or address. Please try again later.', 'danger')
        addresses = []
    finally:
        if 'conn' in locals():
            conn.close()
    return render_template('profile.html', username=username, addresses=addresses)

@user_bp.route('/menu')
def menu():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT food_items.id, food_items.name, food_items.price, food_items.description, restaurants.name as restaurant_name FROM food_items JOIN restaurants ON food_items.restaurant_id = restaurants.id''')
    food_items = cursor.fetchall()
    conn.close()
    return render_template('menu.html', food_items=food_items)

@user_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    item_id = request.form['item_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, restaurant_id FROM food_items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    if item:
        item_restaurant_id = item[3]
        if 'cart' not in session or not session['cart']:
            session['cart'] = []
            session['cart_restaurant_id'] = item_restaurant_id
        elif session.get('cart_restaurant_id') != item_restaurant_id:
            flash('You can only order from one restaurant at a time. Please clear your cart to add items from another restaurant.', 'warning')
            return redirect(url_for('user.cart'))
        cart = session['cart']
        for cart_item in cart:
            if cart_item['id'] == item[0]:
                cart_item['quantity'] += 1
                break
        else:
            cart.append({
                'id': item[0],
                'name': item[1],
                'price': item[2],
                'quantity': 1
            })
        session['cart'] = cart
        flash(f"{item[1]} added to cart!", 'success')
    return redirect(url_for('user.cart'))

@user_bp.route('/update_cart', methods=['POST'])
def update_cart():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    item_id = int(request.form['item_id'])
    action = request.form['action']
    cart = session.get('cart', [])
    updated_cart = []
    for item in cart:
        if item['id'] == item_id:
            if action == 'increase':
                item['quantity'] += 1
                updated_cart.append(item)
            elif action == 'decrease':
                if item['quantity'] > 1:
                    item['quantity'] -= 1
                    updated_cart.append(item)
            elif action == 'remove':
                continue
        else:
            updated_cart.append(item)
    session['cart'] = updated_cart
    if not updated_cart:
        session.pop('cart_restaurant_id', None)
    return redirect(url_for('user.cart'))

@user_bp.route('/cart')
def cart():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    try:
        cart_items = session.get('cart', [])
        total = sum(item['price'] * item.get('quantity', 1) for item in cart_items)
        addresses = []
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username=?', (session['user'],))
        user = cursor.fetchone()
        if user:
            user_id = user[0]
            cursor.execute('SELECT id, address FROM addresses WHERE user_id=?', (user_id,))
            addresses = cursor.fetchall()
        conn.close()
        if not cart_items:
            flash('Your cart is empty.', 'warning')
        return render_template('cart.html', cart_items=cart_items, total=total, addresses=addresses)
    except Exception as e:
        logging.error(f"Cart error: {e}")
        flash('An error occurred while loading your cart. Please try again later.', 'danger')
        return render_template('cart.html', cart_items=[], total=0, addresses=[])

@user_bp.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    flash("Cart cleared.")
    return redirect(url_for('user.cart'))

@user_bp.route('/place_order', methods=['POST'])
def place_order():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    try:
        cart_items = session.get('cart', [])
        if not cart_items:
            flash("Your cart is empty.", "warning")
            return redirect(url_for('user.menu'))
        payment_mode = request.form.get('payment_mode')
        address = request.form.get('address')
        restaurant_id = session.get('cart_restaurant_id')
        if not address or not payment_mode or not restaurant_id:
            flash('Please enter a delivery address, select a payment mode, and make sure your cart is valid.', 'danger')
            return redirect(url_for('user.cart'))
        items_json = json.dumps(cart_items)
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        username = session['user']
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO orders (username, items, total, address_id, payment_mode, order_status, timestamp, restaurant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, items_json, total, address, payment_mode, 'Order Placed', timestamp, restaurant_id)
        )
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        session.pop('cart', None)
        session.pop('cart_restaurant_id', None)
        # Emit new_order event
        emit_new_order(restaurant_id, {
            'order_id': order_id,
            'username': username,
            'total': total,
            'timestamp': timestamp,
            'status': 'Order Placed'
        })
        flash("Order placed successfully!", "success")
        return redirect(url_for('user.order_history'))
    except Exception as e:
        logging.error(f"Order placement error: {e}")
        flash('An error occurred while placing your order. Please try again later.', 'danger')
        return redirect(url_for('user.cart'))

@user_bp.route('/order_history')
def order_history():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, items, total, timestamp, order_status FROM orders WHERE username=? ORDER BY timestamp DESC", (session['user'],))
    orders = cursor.fetchall()
    conn.close()
    order_list = []
    for oid, items, total, timestamp, order_status in orders:
        item_list = json.loads(items)
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT rating, review FROM reviews WHERE order_id=?', (oid,))
        review_row = cursor.fetchone()
        
        # Get delivery partner info and rating
        delivery_info = None
        delivery_rating = None
        if order_status == 'Delivered':
            cursor.execute('''SELECT dp.id, dp.name, dp.phone, dr.rating, dr.review 
                              FROM delivery_orders do 
                              JOIN delivery_partners dp ON do.delivery_partner_id = dp.id 
                              LEFT JOIN delivery_ratings dr ON do.order_id = dr.order_id AND do.delivery_partner_id = dr.delivery_partner_id
                              WHERE do.order_id=?''', (oid,))
            delivery_row = cursor.fetchone()
            if delivery_row:
                delivery_info = {
                    'id': delivery_row[0],
                    'name': delivery_row[1],
                    'phone': delivery_row[2]
                }
                if delivery_row[3]:  # If rating exists
                    delivery_rating = {
                        'rating': delivery_row[3],
                        'review': delivery_row[4]
                    }
        
        conn.close()
        review = None
        if review_row:
            review = {'rating': review_row[0], 'text': review_row[1]}
        order_list.append({
            'id': oid,
            'items': item_list,
            'total': total,
            'timestamp': timestamp,
            'order_status': order_status,
            'review': review,
            'delivery_info': delivery_info,
            'delivery_rating': delivery_rating
        })
    return render_template('order_history.html', orders=order_list, username=session['user'])

@user_bp.route('/restaurants')
def restaurants():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, cuisine, rating, delivery_time, thumbnail, is_open FROM restaurants')
    restaurants = cursor.fetchall()
    today = datetime.datetime.now().strftime('%A')
    now_time = datetime.datetime.now().strftime('%H:%M')
    now_time_obj = datetime.datetime.strptime(now_time, '%H:%M').time()
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    restaurant_list = []
    for r in restaurants:
        rid = r[0]
        cursor.execute('SELECT 1 FROM restaurant_holidays WHERE restaurant_id=? AND holiday_date=?', (rid, today_date))
        is_holiday = cursor.fetchone() is not None
        cursor.execute('SELECT open_time, close_time FROM restaurant_hours WHERE restaurant_id=? AND day_of_week=?', (rid, today))
        hours = cursor.fetchone()
        is_open = r[6]
        debug_msg = f"[DEBUG] {r[1]} | Day: {today} | Now: {now_time} | Hours: {hours} | Holiday: {is_holiday} | DB is_open: {r[6]}"
        if is_holiday or not hours:
            is_open = 0
            debug_msg += " | Marked Closed"
        else:
            try:
                open_time_obj = datetime.datetime.strptime(hours[0], '%H:%M').time()
                close_time_obj = datetime.datetime.strptime(hours[1], '%H:%M').time()
                if open_time_obj <= now_time_obj <= close_time_obj:
                    is_open = 1
                    debug_msg += " | Marked Open"
                else:
                    is_open = 0
                    debug_msg += " | Marked Closed (out of hours)"
            except Exception as e:
                is_open = 0
                debug_msg += f" | Marked Closed (parse error: {e})"
        print(debug_msg)
        restaurant_list.append(list(r[:6]) + [is_open])
    conn.close()
    return render_template('restaurants.html', restaurants=restaurant_list)

@user_bp.route('/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    if 'user' not in session:
        return redirect(url_for('user.login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, cuisine, rating, delivery_time, thumbnail, is_open FROM restaurants WHERE id=?', (restaurant_id,))
    restaurant = list(cursor.fetchone())
    today = datetime.datetime.now().strftime('%A')
    now_time = datetime.datetime.now().strftime('%H:%M')
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    rid = restaurant[0]
    cursor.execute('SELECT 1 FROM restaurant_holidays WHERE restaurant_id=? AND holiday_date=?', (rid, today_date))
    is_holiday = cursor.fetchone() is not None
    cursor.execute('SELECT open_time, close_time FROM restaurant_hours WHERE restaurant_id=? AND day_of_week=?', (rid, today))
    hours = cursor.fetchone()
    debug_msg = f"[DEBUG] {restaurant[1]} | Day: {today} | Now: {now_time} | Hours: {hours} | Holiday: {is_holiday} | DB is_open: {restaurant[6]}"
    if is_holiday or not hours or not (hours[0] <= now_time <= hours[1]):
        restaurant[6] = 0
        debug_msg += " | Marked Closed"
    else:
        debug_msg += " | Marked Open"
    print(debug_msg)
    cursor.execute('SELECT id, name, price, description, image FROM food_items WHERE restaurant_id=?', (restaurant_id,))
    menu_items = cursor.fetchall()
    cursor.execute('SELECT rating, review, timestamp FROM reviews WHERE restaurant_id=? ORDER BY timestamp DESC', (restaurant_id,))
    reviews = cursor.fetchall()
    avg_rating = None
    if reviews:
        avg_rating = round(sum(r[0] for r in reviews) / len(reviews), 2)
    conn.close()
    return render_template('restaurant_detail.html', restaurant=restaurant, menu_items=menu_items, reviews=reviews, avg_rating=avg_rating)

@user_bp.route('/submit_review/<int:order_id>', methods=['POST'])
def submit_review(order_id):
    if 'user' not in session:
        return redirect(url_for('user.login'))
    rating = int(request.form['rating'])
    review_text = request.form['review']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username=?', (session['user'],))
    user = cursor.fetchone()
    if not user:
        conn.close()
        flash('User not found.', 'danger')
        return redirect(url_for('user.order_history'))
    user_id = user[0]
    cursor.execute('SELECT items FROM orders WHERE id=?', (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        flash('Order not found.', 'danger')
        return redirect(url_for('user.order_history'))
    items = json.loads(order[0])
    item_id = items[0]['id']
    cursor.execute('SELECT restaurant_id FROM food_items WHERE id=?', (item_id,))
    rest = cursor.fetchone()
    if not rest:
        conn.close()
        flash('Restaurant not found.', 'danger')
        return redirect(url_for('user.order_history'))
    restaurant_id = rest[0]
    cursor.execute('SELECT id FROM reviews WHERE user_id=? AND order_id=?', (user_id, order_id))
    if cursor.fetchone():
        conn.close()
        flash('You have already reviewed this order.', 'info')
        return redirect(url_for('user.order_history'))
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO reviews (user_id, restaurant_id, order_id, rating, review, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                   (user_id, restaurant_id, order_id, rating, review_text, now))
    # Update restaurant's average rating
    cursor.execute('SELECT AVG(rating) FROM reviews WHERE restaurant_id=?', (restaurant_id,))
    avg_rating = cursor.fetchone()[0]
    cursor.execute('UPDATE restaurants SET rating=? WHERE id=?', (avg_rating, restaurant_id))
    conn.commit()
    conn.close()
    flash('Thank you for your review!', 'success')
    return redirect(url_for('user.order_history'))

@user_bp.route('/rate_delivery/<int:order_id>', methods=['POST'])
def rate_delivery(order_id):
    if 'user' not in session:
        return redirect(url_for('user.login'))
    
    rating = int(request.form['rating'])
    review_text = request.form.get('review', '')
    
    if rating < 1 or rating > 5:
        flash('Rating must be between 1 and 5.', 'danger')
        return redirect(url_for('user.order_history'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if order exists and is delivered
    cursor.execute('SELECT order_status FROM orders WHERE id=? AND username=?', (order_id, session['user']))
    order = cursor.fetchone()
    if not order:
        conn.close()
        flash('Order not found.', 'danger')
        return redirect(url_for('user.order_history'))
    
    if order[0] != 'Delivered':
        conn.close()
        flash('You can only rate delivery for completed orders.', 'warning')
        return redirect(url_for('user.order_history'))
    
    # Get delivery partner for this order
    cursor.execute('SELECT delivery_partner_id FROM delivery_orders WHERE order_id=?', (order_id,))
    delivery_order = cursor.fetchone()
    if not delivery_order or not delivery_order[0]:
        conn.close()
        flash('No delivery partner found for this order.', 'warning')
        return redirect(url_for('user.order_history'))
    
    delivery_partner_id = delivery_order[0]
    
    # Check if already rated
    cursor.execute('SELECT id FROM delivery_ratings WHERE order_id=? AND delivery_partner_id=?', 
                   (order_id, delivery_partner_id))
    if cursor.fetchone():
        conn.close()
        flash('You have already rated this delivery.', 'info')
        return redirect(url_for('user.order_history'))
    
    # Insert rating
    cursor.execute('''INSERT INTO delivery_ratings 
                      (order_id, delivery_partner_id, customer_username, rating, review) 
                      VALUES (?, ?, ?, ?, ?)''',
                   (order_id, delivery_partner_id, session['user'], rating, review_text))
    
    # Update delivery partner's average rating
    cursor.execute('''SELECT AVG(rating) FROM delivery_ratings 
                      WHERE delivery_partner_id=?''', (delivery_partner_id,))
    avg_rating = cursor.fetchone()[0]
    
    cursor.execute('UPDATE delivery_partners SET rating=? WHERE id=?', 
                   (round(avg_rating, 2), delivery_partner_id))
    
    conn.commit()
    conn.close()
    
    flash('Thank you for rating your delivery partner!', 'success')
    return redirect(url_for('user.order_history')) 