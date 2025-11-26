"""Admin Trading Management API"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from decimal import Decimal, InvalidOperation

from app.api.admin import admin_bp
from app.api.admin.users import admin_required, log_admin_action
from app import db
from app.models.trading import TradingPair, Order, Trade
from app.models.admin import FeeConfig


@admin_bp.route('/trading/pairs', methods=['GET'])
@admin_required
def get_trading_pairs():
    """Get all trading pairs"""
    pairs = TradingPair.query.all()
    return jsonify({
        'pairs': [p.to_dict() for p in pairs]
    }), 200


@admin_bp.route('/trading/pairs/<int:pair_id>', methods=['PUT', 'PATCH'])
@admin_required
def update_trading_pair(pair_id):
    """Update trading pair configuration"""
    admin_id = get_jwt_identity()
    pair = TradingPair.query.get(pair_id)

    if not pair:
        return jsonify({'error': 'Trading pair not found'}), 404

    data = request.get_json()
    old_values = pair.to_dict()

    # Update allowed fields
    if 'is_active' in data:
        pair.is_active = data['is_active']
    if 'is_margin_enabled' in data:
        pair.is_margin_enabled = data['is_margin_enabled']
    if 'min_order_size' in data:
        pair.min_order_size = Decimal(str(data['min_order_size']))
    if 'max_order_size' in data:
        pair.max_order_size = Decimal(str(data['max_order_size']))
    if 'price_precision' in data:
        pair.price_precision = int(data['price_precision'])
    if 'amount_precision' in data:
        pair.amount_precision = int(data['amount_precision'])
    if 'maker_fee' in data:
        pair.maker_fee = Decimal(str(data['maker_fee'])) if data['maker_fee'] else None
    if 'taker_fee' in data:
        pair.taker_fee = Decimal(str(data['taker_fee'])) if data['taker_fee'] else None

    log_admin_action(
        admin_id=admin_id,
        action='update_trading_pair',
        entity_type='trading_pair',
        entity_id=pair_id,
        old_value=old_values,
        new_value=pair.to_dict()
    )

    db.session.commit()

    return jsonify({
        'message': 'Trading pair updated',
        'pair': pair.to_dict()
    }), 200


@admin_bp.route('/trading/pairs', methods=['POST'])
@admin_required
def create_trading_pair():
    """Create new trading pair"""
    admin_id = get_jwt_identity()
    data = request.get_json()

    from app.models.wallet import Currency

    base_symbol = data.get('base_currency', '').upper()
    quote_symbol = data.get('quote_currency', '').upper()

    base_currency = Currency.query.filter_by(symbol=base_symbol).first()
    quote_currency = Currency.query.filter_by(symbol=quote_symbol).first()

    if not base_currency or not quote_currency:
        return jsonify({'error': 'Currency not found'}), 404

    symbol = f"{base_symbol}_{quote_symbol}"

    existing = TradingPair.query.filter_by(symbol=symbol).first()
    if existing:
        return jsonify({'error': 'Trading pair already exists'}), 400

    pair = TradingPair(
        symbol=symbol,
        base_currency_id=base_currency.id,
        quote_currency_id=quote_currency.id,
        is_active=data.get('is_active', True),
        min_order_size=Decimal(str(data.get('min_order_size', '0.0001'))),
        max_order_size=Decimal(str(data.get('max_order_size', '1000000'))),
        price_precision=data.get('price_precision', 8),
        amount_precision=data.get('amount_precision', 8)
    )

    db.session.add(pair)

    log_admin_action(
        admin_id=admin_id,
        action='create_trading_pair',
        entity_type='trading_pair',
        new_value={'symbol': symbol}
    )

    db.session.commit()

    return jsonify({
        'message': 'Trading pair created',
        'pair': pair.to_dict()
    }), 201


@admin_bp.route('/trading/fees', methods=['GET'])
@admin_required
def get_fee_configs():
    """Get fee configurations"""
    fees = FeeConfig.query.all()
    return jsonify({
        'fees': [f.to_dict() for f in fees]
    }), 200


@admin_bp.route('/trading/fees', methods=['POST'])
@admin_required
def create_fee_config():
    """Create fee configuration"""
    admin_id = get_jwt_identity()
    data = request.get_json()

    fee_type = data.get('fee_type')
    if fee_type not in ['maker', 'taker', 'withdrawal']:
        return jsonify({'error': 'Invalid fee type'}), 400

    try:
        value = Decimal(str(data.get('value', 0)))
    except (InvalidOperation, TypeError):
        return jsonify({'error': 'Invalid value'}), 400

    fee = FeeConfig(
        fee_type=fee_type,
        currency_id=data.get('currency_id'),
        trading_pair_id=data.get('trading_pair_id'),
        value=value,
        is_percentage=data.get('is_percentage', True),
        is_active=data.get('is_active', True)
    )

    db.session.add(fee)

    log_admin_action(
        admin_id=admin_id,
        action='create_fee_config',
        entity_type='fee',
        new_value={'fee_type': fee_type, 'value': str(value)}
    )

    db.session.commit()

    return jsonify({
        'message': 'Fee configuration created',
        'fee': fee.to_dict()
    }), 201


@admin_bp.route('/trading/fees/<int:fee_id>', methods=['PUT'])
@admin_required
def update_fee_config(fee_id):
    """Update fee configuration"""
    admin_id = get_jwt_identity()
    fee = FeeConfig.query.get(fee_id)

    if not fee:
        return jsonify({'error': 'Fee configuration not found'}), 404

    data = request.get_json()
    old_values = fee.to_dict()

    if 'value' in data:
        fee.value = Decimal(str(data['value']))
    if 'is_percentage' in data:
        fee.is_percentage = data['is_percentage']
    if 'is_active' in data:
        fee.is_active = data['is_active']

    log_admin_action(
        admin_id=admin_id,
        action='update_fee_config',
        entity_type='fee',
        entity_id=fee_id,
        old_value=old_values,
        new_value=fee.to_dict()
    )

    db.session.commit()

    return jsonify({
        'message': 'Fee configuration updated',
        'fee': fee.to_dict()
    }), 200


@admin_bp.route('/trading/orders', methods=['GET'])
@admin_required
def get_all_orders():
    """Get all orders with filters"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    pair = request.args.get('pair')

    query = Order.query

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
        'pages': orders.pages
    }), 200


@admin_bp.route('/trading/trades', methods=['GET'])
@admin_required
def get_all_trades():
    """Get all trades"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pair = request.args.get('pair')

    query = Trade.query

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
        'pages': trades.pages
    }), 200


@admin_bp.route('/trading/stats', methods=['GET'])
@admin_required
def get_trading_stats():
    """Get trading statistics"""
    from datetime import datetime, timedelta

    day_ago = datetime.utcnow() - timedelta(days=1)
    week_ago = datetime.utcnow() - timedelta(days=7)

    # 24h stats
    trades_24h = Trade.query.filter(Trade.created_at >= day_ago).count()
    orders_24h = Order.query.filter(Order.created_at >= day_ago).count()

    # Volume 24h (sum of all trade totals)
    from sqlalchemy import func
    volume_24h = db.session.query(func.sum(Trade.total)).filter(
        Trade.created_at >= day_ago
    ).scalar() or 0

    # Active trading pairs
    active_pairs = TradingPair.query.filter_by(is_active=True).count()

    return jsonify({
        'trades_24h': trades_24h,
        'orders_24h': orders_24h,
        'volume_24h': str(volume_24h),
        'active_pairs': active_pairs
    }), 200
