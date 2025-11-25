"""
WebSocket handlers for real-time market data and user updates.
"""

from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_jwt_extended import decode_token
from app import socketio, db


# Connected clients
connected_clients = {}


@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection"""
    client_id = request.sid
    connected_clients[client_id] = {
        'user_id': None,
        'subscribed_markets': set(),
        'authenticated': False
    }
    emit('connected', {'message': 'Connected to CryptoTrade WebSocket'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    client_id = request.sid
    if client_id in connected_clients:
        del connected_clients[client_id]


@socketio.on('authenticate')
def handle_authenticate(data):
    """Authenticate WebSocket connection with JWT token"""
    client_id = request.sid
    token = data.get('token')

    if not token:
        emit('auth_error', {'error': 'Token required'})
        return

    try:
        decoded = decode_token(token)
        user_id = decoded['sub']

        if client_id in connected_clients:
            connected_clients[client_id]['user_id'] = user_id
            connected_clients[client_id]['authenticated'] = True

        # Join user's private room
        join_room(f'user_{user_id}')

        emit('authenticated', {'message': 'Authentication successful', 'user_id': user_id})

    except Exception as e:
        emit('auth_error', {'error': 'Invalid token'})


@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe to market data channels"""
    client_id = request.sid
    channels = data.get('channels', [])

    for channel in channels:
        channel_type = channel.get('type')
        symbol = channel.get('symbol')

        if channel_type == 'ticker':
            room = f'ticker_{symbol}'
            join_room(room)
            if client_id in connected_clients:
                connected_clients[client_id]['subscribed_markets'].add(room)

        elif channel_type == 'orderbook':
            room = f'orderbook_{symbol}'
            join_room(room)
            if client_id in connected_clients:
                connected_clients[client_id]['subscribed_markets'].add(room)

        elif channel_type == 'trades':
            room = f'trades_{symbol}'
            join_room(room)
            if client_id in connected_clients:
                connected_clients[client_id]['subscribed_markets'].add(room)

        elif channel_type == 'market':
            room = f'market_{symbol}'
            join_room(room)
            if client_id in connected_clients:
                connected_clients[client_id]['subscribed_markets'].add(room)

    emit('subscribed', {'channels': channels})


@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Unsubscribe from market data channels"""
    client_id = request.sid
    channels = data.get('channels', [])

    for channel in channels:
        channel_type = channel.get('type')
        symbol = channel.get('symbol')

        room = f'{channel_type}_{symbol}'
        leave_room(room)

        if client_id in connected_clients:
            connected_clients[client_id]['subscribed_markets'].discard(room)

    emit('unsubscribed', {'channels': channels})


# Broadcasting functions to be called from other parts of the application

def broadcast_ticker(symbol: str, ticker_data: dict):
    """Broadcast ticker update to all subscribers"""
    socketio.emit('ticker', ticker_data, room=f'ticker_{symbol}')
    socketio.emit('ticker', ticker_data, room=f'market_{symbol}')


def broadcast_orderbook(symbol: str, orderbook_data: dict):
    """Broadcast orderbook update to all subscribers"""
    socketio.emit('orderbook', orderbook_data, room=f'orderbook_{symbol}')
    socketio.emit('orderbook', orderbook_data, room=f'market_{symbol}')


def broadcast_trade(symbol: str, trade_data: dict):
    """Broadcast new trade to all subscribers"""
    socketio.emit('trade', trade_data, room=f'trades_{symbol}')
    socketio.emit('trade', trade_data, room=f'market_{symbol}')


def broadcast_user_order_update(user_id: int, order_data: dict):
    """Broadcast order update to specific user"""
    socketio.emit('order_update', order_data, room=f'user_{user_id}')


def broadcast_user_balance_update(user_id: int, balance_data: dict):
    """Broadcast balance update to specific user"""
    socketio.emit('balance_update', balance_data, room=f'user_{user_id}')


def broadcast_user_notification(user_id: int, notification: dict):
    """Broadcast notification to specific user"""
    socketio.emit('notification', notification, room=f'user_{user_id}')
