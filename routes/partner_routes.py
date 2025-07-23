from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
import json
import logging

partner_bp = Blueprint('partner', __name__)

@partner_bp.route('/partner_register', methods=['GET', 'POST'])
def partner_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        contact = request.form['contact']
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO restaurant_owners (username, password, contact) VALUES (?, ?, ?)', (username, password, contact))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('partner.partner_login'))
        except Exception as e:
            logging.error(f"Partner registration error: {e}")
            flash('Username already exists or registration failed!', 'danger')
        finally:
            if 'conn' in locals():
                conn.close()
    return render_template('partner_register.html')

@partner_bp.route('/partner_login', methods=['GET', 'POST'])
def partner_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM restaurant_owners WHERE username=? AND password=?', (username, password))
            owner = cursor.fetchone()
            conn.close()
            if owner:
                session['partner'] = username
                flash('Logged in as restaurant partner!', 'success')
                return redirect(url_for('partner.partner_dashboard'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            logging.error(f"Partner login error: {e}")
            flash('An error occurred during login. Please try again later.', 'danger')
    return render_template('partner_login.html')

@partner_bp.route('/partner_dashboard')
def partner_dashboard():
    if 'partner' not in session:
        return redirect(url_for('partner.partner_login'))
    return render_template('partner_dashboard.html', partner=session['partner'])

@partner_bp.route('/partner_restaurant_profile', methods=['GET', 'POST'])
def partner_restaurant_profile():
    if 'partner' not in session:
        return redirect(url_for('partner.partner_login'))
    username = session['partner']
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Get owner id and linked restaurant_id
        cursor.execute('SELECT id, restaurant_id FROM restaurant_owners WHERE username=?', (username,))
        owner = cursor.fetchone()
        if not owner:
            conn.close()
            flash('Partner not found.', 'danger')
            return redirect(url_for('partner.partner_dashboard'))
        owner_id = owner[0]
        restaurant_id = owner[1]
        # Check if restaurant exists for this owner
        restaurant = None
        if restaurant_id:
            cursor.execute('SELECT id, name, cuisine, is_open FROM restaurants WHERE id=?', (restaurant_id,))
            restaurant = cursor.fetchone()
        if request.method == 'POST':
            name = request.form['name']
            cuisine = request.form['cuisine']
            is_open = 1 if request.form.get('is_open') == 'on' else 0
            if restaurant:
                cursor.execute('UPDATE restaurants SET name=?, cuisine=?, is_open=? WHERE id=?', (name, cuisine, is_open, restaurant_id))
                flash('Restaurant profile updated!', 'success')
            else:
                cursor.execute('INSERT INTO restaurants (name, cuisine, is_open) VALUES (?, ?, ?)', (name, cuisine, is_open))
                new_restaurant_id = cursor.lastrowid
                cursor.execute('UPDATE restaurant_owners SET restaurant_id=? WHERE id=?', (new_restaurant_id, owner_id))
                flash('Restaurant profile created!', 'success')
                restaurant_id = new_restaurant_id
                cursor.execute('SELECT id, name, cuisine, is_open FROM restaurants WHERE id=?', (restaurant_id,))
                restaurant = cursor.fetchone()
            conn.commit()
        conn.close()
        return render_template('partner_restaurant_profile.html', restaurant=restaurant)
    except Exception as e:
        logging.error(f"Partner restaurant profile error: {e}")
        flash('An error occurred while updating the restaurant profile. Please try again later.', 'danger')
        return render_template('partner_restaurant_profile.html', restaurant=None)

@partner_bp.route('/partner_menu', methods=['GET', 'POST'])
def partner_menu():
    if 'partner' not in session:
        return redirect(url_for('partner.partner_login'))
    username = session['partner']
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT restaurant_id FROM restaurant_owners WHERE username=?', (username,))
        row = cursor.fetchone()
        if not row or not row[0]:
            conn.close()
            flash('Please create your restaurant profile first.', 'warning')
            return redirect(url_for('partner.partner_restaurant_profile'))
        restaurant_id = row[0]
        # Handle add menu item
        if request.method == 'POST' and 'add_item' in request.form:
            name = request.form['name']
            price = request.form['price']
            description = request.form['description']
            cursor.execute('INSERT INTO food_items (restaurant_id, name, price, description) VALUES (?, ?, ?, ?)', (restaurant_id, name, price, description))
            conn.commit()
            flash('Menu item added!', 'success')
        # Handle delete menu item
        if request.method == 'POST' and 'delete_item_id' in request.form:
            item_id = request.form['delete_item_id']
            cursor.execute('DELETE FROM food_items WHERE id=? AND restaurant_id=?', (item_id, restaurant_id))
            conn.commit()
            flash('Menu item deleted.', 'danger')
        # Get all menu items for this restaurant
        cursor.execute('SELECT id, name, price, description FROM food_items WHERE restaurant_id=?', (restaurant_id,))
        menu_items = cursor.fetchall()
        conn.close()
        return render_template('partner_menu.html', menu_items=menu_items)
    except Exception as e:
        logging.error(f"Partner menu error: {e}")
        flash('An error occurred while managing the menu. Please try again later.', 'danger')
        return render_template('partner_menu.html', menu_items=[])

@partner_bp.route('/partner_menu/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_menu_item(item_id):
    if 'partner' not in session:
        return redirect(url_for('partner.partner_login'))
    username = session['partner']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Get owner id and restaurant
    cursor.execute('SELECT id FROM restaurant_owners WHERE username=?', (username,))
    owner = cursor.fetchone()
    if not owner:
        conn.close()
        flash('Partner not found.', 'danger')
        return redirect(url_for('partner.partner_dashboard'))
    owner_id = owner[0]
    cursor.execute('SELECT id FROM restaurants WHERE id=?', (owner_id,))
    restaurant = cursor.fetchone()
    if not restaurant:
        conn.close()
        flash('Please create your restaurant profile first.', 'warning')
        return redirect(url_for('partner.partner_restaurant_profile'))
    restaurant_id = restaurant[0]
    # Get the menu item
    cursor.execute('SELECT id, name, price, description FROM food_items WHERE id=? AND restaurant_id=?', (item_id, restaurant_id))
    item = cursor.fetchone()
    if not item:
        conn.close()
        flash('Menu item not found.', 'danger')
        return redirect(url_for('partner.partner_menu'))
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        cursor.execute('UPDATE food_items SET name=?, price=?, description=? WHERE id=? AND restaurant_id=?', (name, price, description, item_id, restaurant_id))
        conn.commit()
        conn.close()
        flash('Menu item updated!', 'success')
        return redirect(url_for('partner.partner_menu'))
    conn.close()
    return render_template('edit_menu_item.html', item=item)

@partner_bp.route('/partner_orders', methods=['GET', 'POST'])
def partner_orders():
    if 'partner' not in session:
        return redirect(url_for('partner.partner_login'))
    username = session['partner']
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT restaurant_id FROM restaurant_owners WHERE username=?', (username,))
        row = cursor.fetchone()
        if not row or not row[0]:
            conn.close()
            flash('Please create your restaurant profile first.', 'warning')
            return redirect(url_for('partner.partner_restaurant_profile'))
        restaurant_id = row[0]
        # Handle status update
        if request.method == 'POST':
            order_id = request.form['order_id']
            new_status = request.form['order_status']
            cursor.execute('UPDATE orders SET order_status=? WHERE id=?', (new_status, order_id))
            conn.commit()
            flash('Order status updated!', 'success')
        # Get all orders for this restaurant
        cursor.execute('SELECT id, username, items, total, order_status, timestamp FROM orders WHERE restaurant_id=? ORDER BY timestamp DESC', (restaurant_id,))
        all_orders = cursor.fetchall()
        partner_orders = []
        for oid, username, items, total, order_status, timestamp in all_orders:
            item_list = json.loads(items)
            partner_orders.append({
                'id': oid,
                'username': username,
                'items': item_list,
                'total': total,
                'order_status': order_status,
                'timestamp': timestamp
            })
        conn.close()
        status_options = ['Order Placed', 'Preparing', 'Ready', 'Out for Delivery', 'Delivered']
        return render_template('partner_orders.html', orders=partner_orders, status_options=status_options, restaurant_id=restaurant_id)
    except Exception as e:
        logging.error(f"Partner orders error: {e}")
        flash('An error occurred while loading orders. Please try again later.', 'danger')
        return render_template('partner_orders.html', orders=[], status_options=[], restaurant_id=None)

@partner_bp.route('/partner_reviews')
def partner_reviews():
    if 'partner' not in session:
        return redirect(url_for('partner.partner_login'))
    username = session['partner']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT restaurant_id FROM restaurant_owners WHERE username=?', (username,))
    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close()
        flash('Please create your restaurant profile first.', 'warning')
        return redirect(url_for('partner.partner_restaurant_profile'))
    restaurant_id = row[0]
    cursor.execute('SELECT name FROM restaurants WHERE id=?', (restaurant_id,))
    restaurant_name = cursor.fetchone()[0]
    cursor.execute('SELECT rating, review, timestamp FROM reviews WHERE restaurant_id=? ORDER BY timestamp DESC', (restaurant_id,))
    reviews = cursor.fetchall()
    conn.close()
    return render_template('partner_reviews.html', reviews=reviews, restaurant_name=restaurant_name)

@partner_bp.route('/partner_hours', methods=['GET', 'POST'])
def partner_hours():
    if 'partner' not in session:
        return redirect(url_for('partner.partner_login'))
    username = session['partner']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT restaurant_id FROM restaurant_owners WHERE username=?', (username,))
    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close()
        flash('Please create your restaurant profile first.', 'warning')
        return redirect(url_for('partner.partner_restaurant_profile'))
    restaurant_id = row[0]
    cursor.execute('SELECT name FROM restaurants WHERE id=?', (restaurant_id,))
    restaurant_name = cursor.fetchone()[0]
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    # Handle hours update
    if request.method == 'POST' and 'update_hours' in request.form:
        for day in days:
            open_time = request.form.get(f'open_{day}')
            close_time = request.form.get(f'close_{day}')
            if open_time and close_time:
                cursor.execute('REPLACE INTO restaurant_hours (restaurant_id, day_of_week, open_time, close_time) VALUES (?, ?, ?, ?)', (restaurant_id, day, open_time, close_time))
        conn.commit()
        flash('Hours updated!', 'success')
    # Handle add holiday
    if request.method == 'POST' and 'add_holiday' in request.form:
        holiday_date = request.form['holiday_date']
        cursor.execute('INSERT OR IGNORE INTO restaurant_holidays (restaurant_id, holiday_date) VALUES (?, ?)', (restaurant_id, holiday_date))
        conn.commit()
        flash('Holiday added!', 'success')
    # Handle remove holiday
    if request.method == 'POST' and 'remove_holiday' in request.form:
        holiday_date = request.form['remove_holiday']
        cursor.execute('DELETE FROM restaurant_holidays WHERE restaurant_id=? AND holiday_date=?', (restaurant_id, holiday_date))
        conn.commit()
        flash('Holiday removed.', 'danger')
    # Fetch current hours and holidays
    cursor.execute('SELECT day_of_week, open_time, close_time FROM restaurant_hours WHERE restaurant_id=?', (restaurant_id,))
    hours = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    cursor.execute('SELECT holiday_date FROM restaurant_holidays WHERE restaurant_id=? ORDER BY holiday_date', (restaurant_id,))
    holidays = [row[0] for row in cursor.fetchall()]
    conn.close()
    return render_template('partner_hours.html', restaurant_name=restaurant_name, days=days, hours=hours, holidays=holidays)

@partner_bp.route('/partner_delete_restaurant', methods=['POST'])
def partner_delete_restaurant():
    if 'partner' not in session:
        return redirect(url_for('partner.partner_login'))
    username = session['partner']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT restaurant_id FROM restaurant_owners WHERE username=?', (username,))
    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close()
        flash('No restaurant to delete.', 'warning')
        return redirect(url_for('partner.partner_dashboard'))
    restaurant_id = row[0]
    # Delete all associated data
    cursor.execute('DELETE FROM food_items WHERE restaurant_id=?', (restaurant_id,))
    cursor.execute('DELETE FROM restaurant_hours WHERE restaurant_id=?', (restaurant_id,))
    cursor.execute('DELETE FROM restaurant_holidays WHERE restaurant_id=?', (restaurant_id,))
    cursor.execute('DELETE FROM reviews WHERE restaurant_id=?', (restaurant_id,))
    cursor.execute('DELETE FROM restaurants WHERE id=?', (restaurant_id,))
    cursor.execute('UPDATE restaurant_owners SET restaurant_id=NULL WHERE username=?', (username,))
    conn.commit()
    conn.close()
    flash('Your restaurant and all associated data have been deleted.', 'success')
    return redirect(url_for('partner.partner_dashboard')) 