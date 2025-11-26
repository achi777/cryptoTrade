"""Admin User Management API"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from decimal import Decimal, InvalidOperation

from app.api.admin import admin_bp
from app import db
from app.models.user import User, UserProfile
from app.models.balance import Balance, Transaction, TransactionType, TransactionStatus
from app.models.trading import Order, Trade
from app.models.admin import AuditLog
from app.utils.security import sanitize_sql_like_pattern


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def log_admin_action(admin_id: int, action: str, entity_type: str, entity_id: int = None,
                     old_value: dict = None, new_value: dict = None, note: str = None):
    """Log admin action for audit"""
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:500] if request.user_agent else None,
        note=note
    )
    db.session.add(log)


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users with filters"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    kyc_level = request.args.get('kyc_level', type=int)
    is_blocked = request.args.get('is_blocked')

    query = User.query

    if search:
        # SECURITY: Sanitize search input to prevent SQL injection
        sanitized_search = sanitize_sql_like_pattern(search)
        query = query.filter(User.email.ilike(f'%{sanitized_search}%'))
    if kyc_level is not None:
        query = query.filter_by(kyc_level=kyc_level)
    if is_blocked is not None:
        query = query.filter_by(is_blocked=is_blocked.lower() == 'true')

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'users': [u.to_dict() for u in users.items],
        'total': users.total,
        'pages': users.pages,
        'current_page': page
    }), 200


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """Get user details"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    balances = Balance.query.filter_by(user_id=user_id).all()
    recent_orders = Order.query.filter_by(user_id=user_id).order_by(
        Order.created_at.desc()
    ).limit(10).all()
    recent_transactions = Transaction.query.filter_by(user_id=user_id).order_by(
        Transaction.created_at.desc()
    ).limit(10).all()

    return jsonify({
        'user': user.to_dict(),
        'balances': [b.to_dict() for b in balances],
        'recent_orders': [o.to_dict() for o in recent_orders],
        'recent_transactions': [t.to_dict() for t in recent_transactions]
    }), 200


@admin_bp.route('/users/<int:user_id>/block', methods=['POST'])
@admin_required
def block_user(user_id):
    """Block a user"""
    admin_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.is_admin:
        return jsonify({'error': 'Cannot block admin users'}), 400

    data = request.get_json()
    reason = data.get('reason', '')

    old_status = user.is_blocked
    user.is_blocked = True

    log_admin_action(
        admin_id=admin_id,
        action='block_user',
        entity_type='user',
        entity_id=user_id,
        old_value={'is_blocked': old_status},
        new_value={'is_blocked': True},
        note=reason
    )

    db.session.commit()

    return jsonify({'message': 'User blocked successfully'}), 200


@admin_bp.route('/users/<int:user_id>/unblock', methods=['POST'])
@admin_required
def unblock_user(user_id):
    """Unblock a user"""
    admin_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    old_status = user.is_blocked
    user.is_blocked = False

    log_admin_action(
        admin_id=admin_id,
        action='unblock_user',
        entity_type='user',
        entity_id=user_id,
        old_value={'is_blocked': old_status},
        new_value={'is_blocked': False}
    )

    db.session.commit()

    return jsonify({'message': 'User unblocked successfully'}), 200


@admin_bp.route('/users/<int:user_id>/balance/adjust', methods=['POST'])
@admin_required
def adjust_balance(user_id):
    """Manually adjust user balance (with audit log)"""
    admin_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    currency_symbol = data.get('currency', '').upper()
    adjustment_type = data.get('type')  # 'credit' or 'debit'
    reason = data.get('reason', '')

    try:
        amount = Decimal(str(data.get('amount', 0)))
    except (InvalidOperation, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400

    if adjustment_type not in ['credit', 'debit']:
        return jsonify({'error': 'Type must be credit or debit'}), 400

    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    from app.models.wallet import Currency
    currency = Currency.query.filter_by(symbol=currency_symbol).first()
    if not currency:
        return jsonify({'error': 'Currency not found'}), 404

    balance = Balance.query.filter_by(user_id=user_id, currency_id=currency.id).first()
    if not balance:
        balance = Balance(
            user_id=user_id,
            currency_id=currency.id,
            available=Decimal('0'),
            locked=Decimal('0'),
            total=Decimal('0')
        )
        db.session.add(balance)

    old_balance = {
        'available': str(balance.available),
        'locked': str(balance.locked),
        'total': str(balance.total)
    }

    if adjustment_type == 'credit':
        balance.available += amount
    else:
        if balance.available < amount:
            return jsonify({'error': 'Insufficient balance for debit'}), 400
        balance.available -= amount

    balance.update_total()

    new_balance = {
        'available': str(balance.available),
        'locked': str(balance.locked),
        'total': str(balance.total)
    }

    # Create transaction record
    transaction = Transaction(
        user_id=user_id,
        currency_id=currency.id,
        type=TransactionType.ADJUSTMENT.value,
        status=TransactionStatus.COMPLETED.value,
        amount=amount if adjustment_type == 'credit' else -amount,
        fee=Decimal('0'),
        net_amount=amount if adjustment_type == 'credit' else -amount,
        balance_before=Decimal(old_balance['available']),
        balance_after=balance.available,
        admin_id=admin_id,
        note=reason
    )
    db.session.add(transaction)

    log_admin_action(
        admin_id=admin_id,
        action='balance_adjustment',
        entity_type='balance',
        entity_id=balance.id,
        old_value=old_balance,
        new_value=new_balance,
        note=f"{adjustment_type}: {amount} {currency_symbol}. Reason: {reason}"
    )

    db.session.commit()

    return jsonify({
        'message': 'Balance adjusted successfully',
        'balance': balance.to_dict()
    }), 200


@admin_bp.route('/users/<int:user_id>/orders', methods=['GET'])
@admin_required
def get_user_orders(user_id):
    """Get user's order history"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    orders = Order.query.filter_by(user_id=user_id).order_by(
        Order.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'orders': [o.to_dict() for o in orders.items],
        'total': orders.total,
        'pages': orders.pages
    }), 200


@admin_bp.route('/users/<int:user_id>/trades', methods=['GET'])
@admin_required
def get_user_trades(user_id):
    """Get user's trade history"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    trades = Trade.query.filter(
        (Trade.buyer_id == user_id) | (Trade.seller_id == user_id)
    ).order_by(Trade.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'trades': [t.to_dict() for t in trades.items],
        'total': trades.total,
        'pages': trades.pages
    }), 200


@admin_bp.route('/users/<int:user_id>/transactions', methods=['GET'])
@admin_required
def get_user_transactions(user_id):
    """Get user's transaction history"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    tx_type = request.args.get('type')

    query = Transaction.query.filter_by(user_id=user_id)

    if tx_type:
        query = query.filter_by(type=tx_type)

    transactions = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'transactions': [t.to_dict() for t in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages
    }), 200

@admin_bp.route('/users/<int:user_id>/verify-email', methods=['POST'])
@admin_required
def verify_user_email(user_id):
    """Manually verify user's email"""
    user = User.query.get_or_404(user_id)
    
    if user.is_verified:
        return jsonify({'message': 'User already verified'}), 200
    
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    
    return jsonify({'message': 'User email verified successfully'}), 200


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    return jsonify({
        'message': f'User {status} successfully',
        'is_active': user.is_active
    }), 200
