from flask import current_app

def emit_new_order(restaurant_id, order_data):
    socketio = current_app.extensions['socketio']
    socketio.emit('new_order', order_data, to=f'restaurant_{restaurant_id}')

def emit_order_status_update(restaurant_id, username, status_data):
    socketio = current_app.extensions['socketio']
    socketio.emit('order_status_update', status_data, to=f'restaurant_{restaurant_id}')
    socketio.emit('order_status_update', status_data, to=f'user_{username}') 