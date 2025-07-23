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