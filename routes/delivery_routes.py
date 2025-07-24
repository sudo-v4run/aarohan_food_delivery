from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
import json
import logging
from datetime import datetime
from realtime_utils import emit_order_status_update

delivery_bp = Blueprint('delivery', __name__)

@delivery_bp.route('/delivery_register', methods=['GET', 'POST'])
def delivery_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        phone = request.form['phone']
        vehicle_number = request.form['vehicle_number']
        vehicle_type = request.form['vehicle_type']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute('SELECT * FROM delivery_partners WHERE username = ?', (username,))
        if cursor.fetchone():
            flash('Username already exists!', 'error')
            conn.close()
            return render_template('delivery_register.html')
        
        # Insert new delivery partner
        cursor.execute('''INSERT INTO delivery_partners 
                         (username, password, name, phone, vehicle_number, vehicle_type) 
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (username, password, name, phone, vehicle_number, vehicle_type))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('delivery.delivery_login'))
    
    return render_template('delivery_register.html')

@delivery_bp.route('/delivery_login', methods=['GET', 'POST'])
def delivery_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM delivery_partners WHERE username=? AND password=?', (username, password))
            partner = cursor.fetchone()
            conn.close()
            if partner:
                session['delivery_partner'] = username
                session['delivery_partner_id'] = partner[0]
                flash('Logged in as delivery partner!', 'success')
                return redirect(url_for('delivery.delivery_dashboard'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            logging.error(f"Delivery partner login error: {e}")
            flash('An error occurred during login. Please try again later.', 'danger')
    return render_template('delivery_login.html')

@delivery_bp.route('/delivery_dashboard')
def delivery_dashboard():
    # Use both session keys for backward compatibility
    delivery_partner_username = session.get('delivery_partner')
    delivery_partner_id = session.get('delivery_partner_id')
    if not delivery_partner_username and not delivery_partner_id:
        return redirect(url_for('delivery.delivery_login'))
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Fetch partner info by id if available, else by username
        if delivery_partner_id:
            cursor.execute('SELECT * FROM delivery_partners WHERE id=?', (delivery_partner_id,))
        else:
            cursor.execute('SELECT * FROM delivery_partners WHERE username=?', (delivery_partner_username,))
        partner = cursor.fetchone()
        if not partner:
            conn.close()
            flash('Delivery partner not found.', 'danger')
            return redirect(url_for('delivery.delivery_login'))
        # Set session id for future use
        session['delivery_partner_id'] = partner[0]
        partner_id = partner[0]
        partner_data = {
            'id': partner[0],
            'username': partner[1],
            'name': partner[3],
            'phone': partner[4],
            'vehicle_number': partner[5],
            'vehicle_type': partner[6],
            'is_available': partner[7],
            'current_location': partner[8],
            'rating': partner[9],
            'total_deliveries': partner[10]
        }
        # Assigned orders (not delivered)
        cursor.execute('''SELECT do.id, do.order_id, o.username, o.items, o.total, o.order_status, do.status, o.timestamp
                         FROM delivery_orders do
                         JOIN orders o ON do.order_id = o.id
                         WHERE do.delivery_partner_id = ? AND do.status != 'Delivered'
                         ORDER BY do.id DESC''', (partner_id,))
        assigned_orders = cursor.fetchall()
        # Available orders (Ready and not assigned)
        cursor.execute('''SELECT o.id, o.username, o.items, o.total, o.order_status, o.timestamp
                         FROM orders o
                         LEFT JOIN delivery_orders do ON o.id = do.order_id
                         WHERE o.order_status = 'Ready' AND do.id IS NULL
                         ORDER BY o.timestamp ASC''')
        available_orders = cursor.fetchall()
        # Delivery history (delivered)
        cursor.execute('''SELECT do.id, do.order_id, o.username, o.items, o.total, o.order_status, do.status, o.timestamp, do.delivery_time
                         FROM delivery_orders do
                         JOIN orders o ON do.order_id = o.id
                         WHERE do.delivery_partner_id = ? AND do.status = 'Delivered'
                         ORDER BY do.delivery_time DESC
                         LIMIT 10''', (partner_id,))
        delivery_history = cursor.fetchall()
        # Fetch delivery feedback/ratings
        cursor.execute('''SELECT dr.rating, dr.review, dr.timestamp, dr.customer_username, o.id as order_id
                          FROM delivery_ratings dr
                          JOIN orders o ON dr.order_id = o.id
                          WHERE dr.delivery_partner_id = ?
                          ORDER BY dr.timestamp DESC''', (partner_id,))
        ratings = cursor.fetchall()
        cursor.execute('SELECT AVG(rating) FROM delivery_ratings WHERE delivery_partner_id=?', (partner_id,))
        avg_rating = cursor.fetchone()[0]
        conn.close()
        # Process orders for template
        def process_items(items):
            try:
                return json.loads(items) if items else []
            except Exception:
                return []
        processed_assigned = [
            {
                'delivery_order_id': row[0],
                'order_id': row[1],
                'username': row[2],
                'items': process_items(row[3]),
                'total': row[4],
                'order_status': row[5],
                'delivery_status': row[6],
                'timestamp': row[7]
            } for row in assigned_orders
        ]
        processed_available = [
            {
                'order_id': row[0],
                'username': row[1],
                'items': process_items(row[2]),
                'total': row[3],
                'order_status': row[4],
                'timestamp': row[5]
            } for row in available_orders
        ]
        processed_history = [
            {
                'delivery_order_id': row[0],
                'order_id': row[1],
                'username': row[2],
                'items': process_items(row[3]),
                'total': row[4],
                'order_status': row[5],
                'delivery_status': row[6],
                'timestamp': row[7],
                'delivery_time': row[8]
            } for row in delivery_history
        ]
        ratings_list = []
        for rating, review, timestamp, customer, order_id in ratings:
            ratings_list.append({
                'rating': rating,
                'review': review,
                'timestamp': timestamp,
                'customer': customer,
                'order_id': order_id
            })
        return render_template(
            'delivery_dashboard.html',
            partner=partner_data,
            assigned_orders=processed_assigned,
            available_orders=processed_available,
            delivery_history=processed_history,
            ratings=ratings_list,
            avg_rating=avg_rating
        )
    except Exception as e:
        logging.error(f"Delivery dashboard error: {e}")
        flash('An error occurred while loading your dashboard. Please try again later.', 'danger')
        return render_template('delivery_dashboard.html', partner=None, assigned_orders=[], available_orders=[], delivery_history=[], ratings=[], avg_rating=None)

@delivery_bp.route('/delivery_logout')
def delivery_logout():
    session.pop('delivery_partner', None)
    session.pop('delivery_partner_id', None)
    flash('Logged out.')
    return redirect(url_for('delivery.delivery_login'))

@delivery_bp.route('/toggle_availability', methods=['POST'])
def toggle_availability():
    if 'delivery_partner' not in session:
        return redirect(url_for('delivery.delivery_login'))
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT is_available FROM delivery_partners WHERE username=?', (session['delivery_partner'],))
        row = cursor.fetchone()
        if not row:
            conn.close()
            flash('Delivery partner not found.', 'danger')
            return redirect(url_for('delivery.delivery_dashboard'))
        current_status = row[0]
        new_status = 0 if current_status == 1 else 1
        cursor.execute('UPDATE delivery_partners SET is_available=? WHERE username=?', (new_status, session['delivery_partner']))
        conn.commit()
        conn.close()
        flash(f"Availability status set to {'Available' if new_status == 1 else 'Not Available'}.", 'success')
    except Exception as e:
        logging.error(f"Toggle availability error: {e}")
        flash('An error occurred while updating your availability. Please try again later.', 'danger')
    return redirect(url_for('delivery.delivery_dashboard'))

@delivery_bp.route('/update_availability', methods=['POST'])
def update_availability():
    if 'delivery_partner_id' not in session:
        return redirect(url_for('delivery.delivery_login'))
    
    is_available = request.form.get('is_available', 0)
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE delivery_partners SET is_available = ? WHERE id = ?', 
                      (is_available, session['delivery_partner_id']))
        conn.commit()
    except Exception as e:
        logging.error(f"Update availability error: {e}")
        flash('An error occurred while updating availability. Please try again later.', 'danger')
    finally:
        conn.close()
    
    flash('Availability updated!', 'success')
    return redirect(url_for('delivery.delivery_dashboard'))

@delivery_bp.route('/assign_order/<int:order_id>', methods=['POST'])
def assign_order(order_id):
    if 'delivery_partner' not in session:
        return redirect(url_for('delivery.delivery_login'))
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Get delivery partner id
        cursor.execute('SELECT id FROM delivery_partners WHERE username=?', (session['delivery_partner'],))
        partner = cursor.fetchone()
        if not partner:
            conn.close()
            flash('Delivery partner not found.', 'danger')
            return redirect(url_for('delivery.delivery_dashboard'))
        partner_id = partner[0]
        # Check if order is still available
        cursor.execute('SELECT id FROM orders WHERE id=? AND order_status="Ready"', (order_id,))
        order = cursor.fetchone()
        if not order:
            conn.close()
            flash('Order is no longer available for assignment.', 'danger')
            return redirect(url_for('delivery.delivery_dashboard'))
        # Check if already assigned
        cursor.execute('SELECT id FROM delivery_orders WHERE order_id=?', (order_id,))
        already_assigned = cursor.fetchone()
        if already_assigned:
            conn.close()
            flash('Order has already been assigned to another partner.', 'danger')
            return redirect(url_for('delivery.delivery_dashboard'))
        # Assign order
        cursor.execute('INSERT INTO delivery_orders (order_id, delivery_partner_id, status) VALUES (?, ?, ?)', (order_id, partner_id, 'Assigned'))
        conn.commit()
        conn.close()
        flash('Order accepted and assigned to you!', 'success')
    except Exception as e:
        logging.error(f"Assign order error: {e}")
        flash('An error occurred while accepting the order. Please try again later.', 'danger')
    return redirect(url_for('delivery.delivery_dashboard'))

@delivery_bp.route('/update_order_status', methods=['POST'])
def update_order_status():
    if 'delivery_partner' not in session:
        return redirect(url_for('delivery.delivery_login'))
    try:
        delivery_order_id = request.form.get('delivery_order_id')
        new_status = request.form.get('status')
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Get delivery partner id
        cursor.execute('SELECT id FROM delivery_partners WHERE username=?', (session['delivery_partner'],))
        partner = cursor.fetchone()
        if not partner:
            conn.close()
            flash('Delivery partner not found.', 'danger')
            return redirect(url_for('delivery.delivery_dashboard'))
        partner_id = partner[0]
        # Update delivery order status
        if new_status == 'Delivered':
            delivery_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('UPDATE delivery_orders SET status=?, delivery_time=? WHERE id=? AND delivery_partner_id=?', (new_status, delivery_time, delivery_order_id, partner_id))
        else:
            cursor.execute('UPDATE delivery_orders SET status=? WHERE id=? AND delivery_partner_id=?', (new_status, delivery_order_id, partner_id))
        # If delivered, update order status in orders table
        if new_status == 'Delivered':
            cursor.execute('SELECT order_id FROM delivery_orders WHERE id=?', (delivery_order_id,))
            order_row = cursor.fetchone()
            if order_row:
                order_id = order_row[0]
                cursor.execute('UPDATE orders SET order_status=? WHERE id=?', ('Delivered', order_id))
        conn.commit()
        conn.close()
        flash('Order status updated!', 'success')
    except Exception as e:
        logging.error(f"Update order status error: {e}")
        flash('An error occurred while updating the order status. Please try again later.', 'danger')
    return redirect(url_for('delivery.delivery_dashboard'))

@delivery_bp.route('/delivery_profile', methods=['GET', 'POST'])
def delivery_profile():
    if 'delivery_partner_id' not in session:
        return redirect(url_for('delivery.delivery_login'))
    
    delivery_partner_id = session['delivery_partner_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        if request.method == 'POST':
            name = request.form['name']
            phone = request.form['phone']
            vehicle_number = request.form['vehicle_number']
            vehicle_type = request.form['vehicle_type']
            
            cursor.execute('''UPDATE delivery_partners 
                              SET name=?, phone=?, vehicle_number=?, vehicle_type=? 
                              WHERE id=?''', 
                           (name, phone, vehicle_number, vehicle_type, delivery_partner_id))
            conn.commit()
            flash('Profile updated successfully!', 'success')
        
        cursor.execute('SELECT * FROM delivery_partners WHERE id=?', (delivery_partner_id,))
        partner = cursor.fetchone()
    except Exception as e:
        logging.error(f"Delivery profile update error: {e}")
        flash('An error occurred while updating your profile. Please try again later.', 'danger')
    finally:
        conn.close()
    
    if partner:
        partner_data = {
            'id': partner[0],
            'username': partner[1],
            'name': partner[3],
            'phone': partner[4],
            'vehicle_number': partner[5],
            'vehicle_type': partner[6],
            'is_available': partner[7],
            'current_location': partner[8],
            'rating': partner[9],
            'total_deliveries': partner[10]
        }
    else:
        partner_data = None
    
    return render_template('delivery_profile.html', partner=partner_data)

@delivery_bp.route('/delivery_ratings')
def delivery_ratings():
    if 'delivery_partner_id' not in session:
        return redirect(url_for('delivery.delivery_login'))
    
    delivery_partner_id = session['delivery_partner_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Get all ratings and reviews
        cursor.execute('''SELECT dr.rating, dr.review, dr.timestamp, dr.customer_username, o.id as order_id
                          FROM delivery_ratings dr
                          JOIN orders o ON dr.order_id = o.id
                          WHERE dr.delivery_partner_id = ?
                          ORDER BY dr.timestamp DESC''', (delivery_partner_id,))
        ratings = cursor.fetchall()
        
        # Calculate average rating
        cursor.execute('SELECT AVG(rating) FROM delivery_ratings WHERE delivery_partner_id=?', (delivery_partner_id,))
        avg_rating = cursor.fetchone()[0]
        
    except Exception as e:
        logging.error(f"Delivery ratings error: {e}")
        flash('An error occurred while loading your ratings. Please try again later.', 'danger')
    finally:
        conn.close()
    
    ratings_list = []
    for rating, review, timestamp, customer, order_id in ratings:
        ratings_list.append({
            'rating': rating,
            'review': review,
            'timestamp': timestamp,
            'customer': customer,
            'order_id': order_id
        })
    
    return render_template('delivery_ratings.html', ratings=ratings_list, avg_rating=avg_rating)

@delivery_bp.route('/update_profile', methods=['POST'])
def update_profile():
    if 'delivery_partner_id' not in session:
        return redirect(url_for('delivery.delivery_login'))
    
    name = request.form['name']
    phone = request.form['phone']
    vehicle_number = request.form['vehicle_number']
    vehicle_type = request.form['vehicle_type']
    current_location = request.form['current_location']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''UPDATE delivery_partners 
                         SET name = ?, phone = ?, vehicle_number = ?, vehicle_type = ?, current_location = ?
                         WHERE id = ?''',
                      (name, phone, vehicle_number, vehicle_type, current_location, session['delivery_partner_id']))
        conn.commit()
    except Exception as e:
        logging.error(f"Update delivery profile error: {e}")
        flash('An error occurred while updating your profile. Please try again later.', 'danger')
    finally:
        conn.close()
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('delivery.delivery_profile')) 