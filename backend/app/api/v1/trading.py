from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal, InvalidOperation
from datetime import datetime

from app.api.v1 import api_v1_bp
from app import db, socketio, limiter
from app.models.user import User
from app.models.wallet import Currency
from app.models.balance import Balance, Transaction, TransactionType
from app.models.trading import (
    TradingPair, Order, OrderType, OrderSide, OrderStatus,
    Trade, MarginAccount, MarginPosition
)
from app.services.trading_engine import MatchingEngine


@api_v1_bp.route('/trading/pairs', methods=['GET'])
def get_trading_pairs():
    """
    Get All Trading Pairs
    ---
    tags:
      - Trading
    responses:
      200:
        description: List of all active trading pairs
        schema:
          type: object
          properties:
            pairs:
              type: array
              items:
                type: object
                properties:
                  symbol:
                    type: string
                    example: BTC/USDT
                  last_price:
                    type: string
                  price_change_24h:
                    type: string
                  volume_24h:
                    type: string
    """
    pairs = TradingPair.query.filter_by(is_active=True).all()
    return jsonify({
        'pairs': [p.to_dict() for p in pairs]
    }), 200


@api_v1_bp.route('/trading/pairs/<symbol>', methods=['GET'])
def get_trading_pair(symbol):
    """
    Get Specific Trading Pair Info
    ---
    tags:
      - Trading
    parameters:
      - name: symbol
        in: path
        required: true
        type: string
        description: Trading pair symbol
        example: BTC/USDT
    responses:
      200:
        description: Trading pair details
        schema:
          type: object
          properties:
            pair:
              type: object
      404:
        description: Trading pair not found
    """
    pair = TradingPair.query.filter_by(symbol=symbol.upper(), is_active=True).first()
    if not pair:
        return jsonify({'error': 'Trading pair not found'}), 404

    return jsonify({'pair': pair.to_dict()}), 200


@api_v1_bp.route('/trading/orders', methods=['POST'])
@jwt_required()
@limiter.limit("100/hour")  # SECURITY: Prevent order spam
def create_order():
    """
    Create Trading Order
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - pair
            - type
            - side
            - amount
          properties:
            pair:
              type: string
              example: BTC/USDT
            type:
              type: string
              enum: [limit, market]
              example: limit
            side:
              type: string
              enum: [buy, sell]
              example: buy
            price:
              type: string
              example: "50000.00"
              description: Required for limit orders
            amount:
              type: string
              example: "0.01"
    responses:
      201:
        description: Order created successfully
      400:
        description: Invalid input or insufficient balance
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()

    # Validate input
    pair_symbol = data.get('pair', '').upper()
    order_type = data.get('type', '').lower()
    side = data.get('side', '').lower()

    try:
        amount = Decimal(str(data.get('amount', 0)))
        price = Decimal(str(data.get('price', 0))) if data.get('price') else None
    except (InvalidOperation, TypeError):
        return jsonify({'error': 'Invalid amount or price'}), 400

    # Validate trading pair - convert BTC_USDT to BTC/USDT
    pair_symbol_normalized = pair_symbol.replace('_', '/')
    pair = TradingPair.query.filter_by(symbol=pair_symbol_normalized, is_active=True).first()
    if not pair:
        return jsonify({'error': 'Trading pair not found or inactive'}), 404

    # Validate order type
    if order_type not in [t.value for t in OrderType]:
        return jsonify({'error': 'Invalid order type'}), 400

    if side not in [s.value for s in OrderSide]:
        return jsonify({'error': 'Invalid order side'}), 400

    # Validate amount
    if amount < pair.min_order_size:
        return jsonify({'error': f'Minimum order size is {pair.min_order_size}'}), 400
    if amount > pair.max_order_size:
        return jsonify({'error': f'Maximum order size is {pair.max_order_size}'}), 400

    # Limit orders require price
    if order_type == OrderType.LIMIT.value and not price:
        return jsonify({'error': 'Price is required for limit orders'}), 400

    # Calculate required balance
    if side == OrderSide.BUY.value:
        # Need quote currency (e.g., USDT)
        if order_type == OrderType.MARKET.value:
            # For market buy, estimate based on last price
            required = amount * pair.last_price * Decimal('1.01')  # 1% buffer
        else:
            required = amount * price
        balance_currency_id = pair.quote_currency_id
    else:
        # Need base currency (e.g., BTC)
        required = amount
        balance_currency_id = pair.base_currency_id

    # Check balance with row-level locking to prevent race conditions
    from sqlalchemy import select

    balance = db.session.execute(
        select(Balance).filter_by(
            user_id=user_id,
            currency_id=balance_currency_id
        ).with_for_update()
    ).scalar_one_or_none()

    if not balance or balance.available < required:
        db.session.rollback()
        return jsonify({'error': 'Insufficient balance'}), 400

    # Lock funds atomically
    balance.available -= required
    balance.locked += required
    balance.update_total()

    # Create order
    order = Order(
        user_id=user_id,
        trading_pair_id=pair.id,
        order_type=order_type,
        side=side,
        status=OrderStatus.OPEN.value,
        price=price,
        amount=amount,
        remaining_amount=amount
    )

    db.session.add(order)
    db.session.commit()

    # Try to match order
    try:
        engine = MatchingEngine(pair)
        trades = engine.match_order(order)

        if trades:
            # Emit WebSocket updates
            socketio.emit('order_update', order.to_dict(), room=f'user_{user_id}')
            for trade in trades:
                socketio.emit('trade', trade.to_dict(), room=f'market_{pair.symbol}')

    except Exception as e:
        current_app.logger.error(f"Matching engine error: {e}")

    return jsonify({
        'message': 'Order created successfully',
        'order': order.to_dict()
    }), 201


@api_v1_bp.route('/trading/orders', methods=['GET'])
@jwt_required()
def get_orders():
    """
    Get User Orders
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    parameters:
      - name: status
        in: query
        type: string
        description: Filter by order status
        enum: [open, filled, cancelled, partially_filled]
      - name: pair
        in: query
        type: string
        description: Filter by trading pair
        example: BTC/USDT
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Paginated list of orders
        schema:
          type: object
          properties:
            orders:
              type: array
              items:
                type: object
            total:
              type: integer
            pages:
              type: integer
            current_page:
              type: integer
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    status = request.args.get('status')
    pair = request.args.get('pair')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Order.query.filter_by(user_id=user_id)

    if status:
        query = query.filter_by(status=status)
    if pair:
        trading_pair = TradingPair.query.filter_by(symbol=pair.upper()).first()
        if trading_pair:
            query = query.filter_by(trading_pair_id=trading_pair.id)

    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'orders': [o.to_dict() for o in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'current_page': page
    }), 200


@api_v1_bp.route('/trading/orders/open', methods=['GET'])
@jwt_required()
def get_open_orders():
    """
    Get User's Open Orders
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    parameters:
      - name: pair
        in: query
        type: string
        description: Filter by trading pair
        example: BTC/USDT
    responses:
      200:
        description: List of open orders
        schema:
          type: object
          properties:
            orders:
              type: array
              items:
                type: object
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    pair = request.args.get('pair')

    query = Order.query.filter(
        Order.user_id == user_id,
        Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value])
    )

    if pair:
        trading_pair = TradingPair.query.filter_by(symbol=pair.upper()).first()
        if trading_pair:
            query = query.filter_by(trading_pair_id=trading_pair.id)

    orders = query.order_by(Order.created_at.desc()).all()

    return jsonify({
        'orders': [o.to_dict() for o in orders]
    }), 200


@api_v1_bp.route('/trading/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """
    Get Specific Order
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        required: true
        type: integer
        description: Order ID
    responses:
      200:
        description: Order details
        schema:
          type: object
          properties:
            order:
              type: object
      404:
        description: Order not found
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    return jsonify({'order': order.to_dict()}), 200


@api_v1_bp.route('/trading/orders/<int:order_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_order(order_id):
    """
    Cancel an Open Order
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    parameters:
      - name: order_id
        in: path
        required: true
        type: integer
        description: Order ID to cancel
    responses:
      200:
        description: Order cancelled successfully
        schema:
          type: object
          properties:
            message:
              type: string
            order:
              type: object
      400:
        description: Order status changed, cannot cancel
      404:
        description: Order not found or cannot be cancelled
      401:
        description: Unauthorized
    """
    from sqlalchemy import select

    user_id = get_jwt_identity()

    # Lock order row to prevent concurrent modifications
    order = db.session.execute(
        select(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id,
            Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value])
        ).with_for_update()
    ).scalar_one_or_none()

    if not order:
        db.session.rollback()
        return jsonify({'error': 'Order not found or cannot be cancelled'}), 404

    # Prevent cancellation if order is being matched
    if order.status not in [OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]:
        db.session.rollback()
        return jsonify({'error': 'Order status changed, cannot cancel'}), 400

    pair = order.trading_pair

    # Calculate amount to unlock
    if order.side == OrderSide.BUY.value:
        unlock_amount = order.remaining_amount * (order.price or pair.last_price)
        balance_currency_id = pair.quote_currency_id
    else:
        unlock_amount = order.remaining_amount
        balance_currency_id = pair.base_currency_id

    # Lock balance row atomically
    balance = db.session.execute(
        select(Balance).filter_by(
            user_id=user_id,
            currency_id=balance_currency_id
        ).with_for_update()
    ).scalar_one_or_none()

    if balance:
        # Only unlock what's actually locked
        actual_unlock = min(unlock_amount, balance.locked)
        balance.locked -= actual_unlock
        balance.available += actual_unlock
        balance.update_total()

    # Mark order as cancelled atomically
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = datetime.utcnow()

    db.session.commit()

    # Emit WebSocket update
    socketio.emit('order_update', order.to_dict(), room=f'user_{user_id}')

    return jsonify({
        'message': 'Order cancelled',
        'order': order.to_dict()
    }), 200


@api_v1_bp.route('/trading/trades', methods=['GET'])
@jwt_required()
def get_trades():
    """
    Get User Trade History
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    parameters:
      - name: pair
        in: query
        type: string
        description: Filter by trading pair
        example: BTC/USDT
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Paginated list of trades
        schema:
          type: object
          properties:
            trades:
              type: array
              items:
                type: object
            total:
              type: integer
            pages:
              type: integer
            current_page:
              type: integer
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    pair = request.args.get('pair')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Trade.query.filter(
        (Trade.buyer_id == user_id) | (Trade.seller_id == user_id)
    )

    if pair:
        trading_pair = TradingPair.query.filter_by(symbol=pair.upper()).first()
        if trading_pair:
            query = query.filter_by(trading_pair_id=trading_pair.id)

    trades = query.order_by(Trade.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'trades': [t.to_dict() for t in trades.items],
        'total': trades.total,
        'pages': trades.pages,
        'current_page': page
    }), 200


@api_v1_bp.route('/trading/convert', methods=['POST'])
@jwt_required()
def convert():
    """
    Quick Convert Between Currencies
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - from
            - to
            - amount
          properties:
            from:
              type: string
              example: BTC
              description: Source currency
            to:
              type: string
              example: USDT
              description: Target currency
            amount:
              type: string
              example: "0.1"
              description: Amount to convert
    responses:
      200:
        description: Conversion successful
        schema:
          type: object
          properties:
            message:
              type: string
            from:
              type: string
            to:
              type: string
            amount:
              type: string
            rate:
              type: string
            converted:
              type: string
            fee:
              type: string
      400:
        description: Invalid amount or conversion pair not available
      404:
        description: Currency not found
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    from_currency = data.get('from', '').upper()
    to_currency = data.get('to', '').upper()

    try:
        amount = Decimal(str(data.get('amount', 0)))
    except (InvalidOperation, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400

    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    # Find trading pair
    pair_symbol = f'{from_currency}_{to_currency}'
    pair = TradingPair.query.filter_by(symbol=pair_symbol, is_active=True).first()

    reverse_pair = False
    if not pair:
        pair_symbol = f'{to_currency}_{from_currency}'
        pair = TradingPair.query.filter_by(symbol=pair_symbol, is_active=True).first()
        reverse_pair = True

    if not pair:
        return jsonify({'error': 'Conversion pair not available'}), 400

    # Calculate conversion
    rate = pair.last_price
    if not rate or rate == 0:
        return jsonify({'error': 'Market rate not available'}), 400

    if reverse_pair:
        converted_amount = amount / rate
        side = OrderSide.BUY.value
    else:
        converted_amount = amount * rate
        side = OrderSide.SELL.value

    # Apply fee
    fee_percent = Decimal('0.001')  # 0.1%
    fee = converted_amount * fee_percent
    final_amount = converted_amount - fee

    # Check source balance
    from_cur = Currency.query.filter_by(symbol=from_currency).first()
    to_cur = Currency.query.filter_by(symbol=to_currency).first()

    if not from_cur or not to_cur:
        return jsonify({'error': 'Currency not found'}), 404

    from_balance = Balance.query.filter_by(user_id=user_id, currency_id=from_cur.id).first()
    if not from_balance or from_balance.available < amount:
        return jsonify({'error': 'Insufficient balance'}), 400

    # Execute conversion
    from_balance.available -= amount
    from_balance.update_total()

    to_balance = Balance.query.filter_by(user_id=user_id, currency_id=to_cur.id).first()
    if not to_balance:
        to_balance = Balance(user_id=user_id, currency_id=to_cur.id)
        db.session.add(to_balance)

    to_balance.available += final_amount
    to_balance.update_total()

    db.session.commit()

    return jsonify({
        'message': 'Conversion successful',
        'from': from_currency,
        'to': to_currency,
        'amount': str(amount),
        'rate': str(rate),
        'converted': str(final_amount),
        'fee': str(fee)
    }), 200


# Margin Trading Endpoints

@api_v1_bp.route('/trading/margin/account', methods=['GET'])
@jwt_required()
def get_margin_account():
    """
    Get User Margin Account
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    responses:
      200:
        description: Margin account details
        schema:
          type: object
          properties:
            account:
              type: object
              properties:
                collateral:
                  type: string
                borrowed:
                  type: string
                max_leverage:
                  type: integer
      404:
        description: Margin account not found
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()

    account = MarginAccount.query.filter_by(user_id=user_id).first()
    if not account:
        return jsonify({'error': 'Margin account not found'}), 404

    return jsonify({'account': account.to_dict()}), 200


@api_v1_bp.route('/trading/margin/account', methods=['POST'])
@jwt_required()
def create_margin_account():
    """
    Create Margin Trading Account
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    responses:
      201:
        description: Margin account created
        schema:
          type: object
          properties:
            message:
              type: string
            account:
              type: object
      400:
        description: Margin account already exists
      403:
        description: KYC level 2 required for margin trading
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # Check KYC level
    if user.kyc_level < 2:
        return jsonify({'error': 'KYC level 2 required for margin trading'}), 403

    existing = MarginAccount.query.filter_by(user_id=user_id).first()
    if existing:
        return jsonify({'error': 'Margin account already exists'}), 400

    account = MarginAccount(user_id=user_id, max_leverage=5)
    db.session.add(account)
    db.session.commit()

    return jsonify({
        'message': 'Margin account created',
        'account': account.to_dict()
    }), 201


@api_v1_bp.route('/trading/margin/transfer', methods=['POST'])
@jwt_required()
def margin_transfer():
    """
    Transfer Funds To/From Margin Account
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - direction
            - amount
          properties:
            direction:
              type: string
              enum: [to_margin, from_margin]
              example: to_margin
            amount:
              type: string
              example: "1000.00"
    responses:
      200:
        description: Transfer successful
        schema:
          type: object
          properties:
            message:
              type: string
            account:
              type: object
      400:
        description: Invalid direction, amount, or insufficient balance/margin ratio
      404:
        description: Margin account not found
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    direction = data.get('direction')  # 'to_margin' or 'from_margin'

    try:
        amount = Decimal(str(data.get('amount', 0)))
    except (InvalidOperation, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400

    if direction not in ['to_margin', 'from_margin']:
        return jsonify({'error': 'Invalid direction'}), 400

    account = MarginAccount.query.filter_by(user_id=user_id).first()
    if not account:
        return jsonify({'error': 'Margin account not found'}), 404

    # Get USDT balance (collateral currency)
    usdt = Currency.query.filter_by(symbol='USDT').first()
    balance = Balance.query.filter_by(user_id=user_id, currency_id=usdt.id).first()

    if direction == 'to_margin':
        if not balance or balance.available < amount:
            return jsonify({'error': 'Insufficient balance'}), 400

        balance.available -= amount
        balance.update_total()
        account.collateral += amount
    else:
        # Check if withdrawal is safe (margin ratio)
        if account.collateral - amount < account.borrowed * Decimal('1.2'):
            return jsonify({'error': 'Cannot withdraw, margin ratio too low'}), 400

        account.collateral -= amount
        balance.available += amount
        balance.update_total()

    db.session.commit()

    return jsonify({
        'message': 'Transfer successful',
        'account': account.to_dict()
    }), 200


@api_v1_bp.route('/trading/margin/positions', methods=['GET'])
@jwt_required()
def get_margin_positions():
    """
    Get Open Margin Positions
    ---
    tags:
      - Trading
    security:
      - Bearer: []
    responses:
      200:
        description: List of open margin positions
        schema:
          type: object
          properties:
            positions:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  trading_pair:
                    type: string
                  side:
                    type: string
                    enum: [long, short]
                  entry_price:
                    type: string
                  amount:
                    type: string
                  leverage:
                    type: integer
                  status:
                    type: string
      404:
        description: Margin account not found
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()

    account = MarginAccount.query.filter_by(user_id=user_id).first()
    if not account:
        return jsonify({'error': 'Margin account not found'}), 404

    positions = MarginPosition.query.filter_by(
        margin_account_id=account.id,
        status='open'
    ).all()

    return jsonify({
        'positions': [p.to_dict() for p in positions]
    }), 200
