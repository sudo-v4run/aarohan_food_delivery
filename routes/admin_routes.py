from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
import json
import logging

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('user.login'))
    try:
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
    except Exception as e:
        logging.error(f"Admin dashboard error: {e}")
        flash('An error occurred while loading the admin dashboard. Please try again later.', 'danger')
        return render_template('admin.html', orders=[], status_options=[])

@admin_bp.route('/admin/foods')
def admin_foods():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('user.login'))
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM food_items")
        foods = cursor.fetchall()
        conn.close()
        return render_template('admin_foods.html', foods=foods)
    except Exception as e:
        logging.error(f"Admin foods error: {e}")
        flash('An error occurred while loading food items. Please try again later.', 'danger')
        return render_template('admin_foods.html', foods=[])

@admin_bp.route('/admin/foods/add', methods=['POST'])
def add_food():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('user.login'))
    try:
        name = request.form['name']
        price = request.form['price']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO food_items (name, price) VALUES (?, ?)", (name, price))
        conn.commit()
        conn.close()
        flash("Food item added!", "success")
        return redirect(url_for('admin.admin_foods'))
    except Exception as e:
        logging.error(f"Add food error: {e}")
        flash('An error occurred while adding the food item. Please try again later.', 'danger')
        return redirect(url_for('admin.admin_foods'))

@admin_bp.route('/admin/foods/delete/<int:item_id>')
def delete_food(item_id):
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('user.login'))
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM food_items WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
        flash("Food item deleted.", "danger")
        return redirect(url_for('admin.admin_foods'))
    except Exception as e:
        logging.error(f"Delete food error: {e}")
        flash('An error occurred while deleting the food item. Please try again later.', 'danger')
        return redirect(url_for('admin.admin_foods'))

@admin_bp.route('/admin/assign_orders')
def admin_assign_orders():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('user.login'))
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Fetch orders that are not delivered and not assigned
        cursor.execute('''
            SELECT o.id, o.username, o.items, o.total, o.order_status, o.timestamp,
                   do.delivery_partner_id
            FROM orders o
            LEFT JOIN delivery_orders do ON o.id = do.order_id
            WHERE o.order_status != 'Delivered' AND do.delivery_partner_id IS NULL
            ORDER BY o.timestamp ASC
        ''')
        all_orders = cursor.fetchall()
        orders = []
        for oid, username, items, total, order_status, timestamp, delivery_partner_id in all_orders:
            item_list = json.loads(items)
            assigned_to = None
            if delivery_partner_id:
                cursor.execute('SELECT name FROM delivery_partners WHERE id=?', (delivery_partner_id,))
                partner_row = cursor.fetchone()
                assigned_to = partner_row[0] if partner_row else 'Unknown'
            orders.append({
                'id': oid,
                'username': username,
                'items': item_list,
                'total': total,
                'order_status': order_status,
                'timestamp': timestamp,
                'assigned_to': assigned_to
            })
        # Fetch all delivery partners
        cursor.execute('SELECT id, name, vehicle_type, current_location, rating FROM delivery_partners')
        partners = cursor.fetchall()
        conn.close()
        return render_template('admin_assign_orders.html', orders=orders, partners=partners)
    except Exception as e:
        logging.error(f"Admin assign orders error: {e}")
        flash('An error occurred while loading assign orders.', 'danger')
        return render_template('admin_assign_orders.html', orders=[], partners=[])

@admin_bp.route('/admin/assign_order/<int:order_id>', methods=['POST'])
def assign_order_to_partner(order_id):
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('user.login'))
    delivery_partner_id = request.form.get('delivery_partner_id')
    if not delivery_partner_id:
        flash('Please select a delivery partner.', 'danger')
        return redirect(url_for('admin_assign_orders'))
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Check if already assigned
        cursor.execute('SELECT id FROM delivery_orders WHERE order_id=?', (order_id,))
        if cursor.fetchone():
            flash('Order is already assigned to a delivery partner.', 'warning')
            conn.close()
            return redirect(url_for('admin_assign_orders'))
        # Assign order
        cursor.execute('INSERT INTO delivery_orders (order_id, delivery_partner_id, status) VALUES (?, ?, ?)', (order_id, delivery_partner_id, 'Assigned'))
        # Optionally update order status
        cursor.execute('UPDATE orders SET order_status=? WHERE id=?', ('Out for Delivery', order_id))
        conn.commit()
        conn.close()
        flash('Order assigned to delivery partner!', 'success')
    except Exception as e:
        logging.error(f"Assign order error: {e}")
        flash('An error occurred while assigning the order.', 'danger')
    return redirect(url_for('admin_assign_orders')) 