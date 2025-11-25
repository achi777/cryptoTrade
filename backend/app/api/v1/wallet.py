from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal, InvalidOperation
import pyotp

from app.api.v1 import api_v1_bp
from app import db, limiter
from app.models.user import User
from app.models.wallet import Wallet, WalletAddress, Currency
from app.models.balance import Balance, Transaction, TransactionType, TransactionStatus, WithdrawalRequest
from app.models.admin import BlacklistedAddress
from app.services.wallet_service import generate_deposit_address
from app.services.blockchain_service import validate_address, estimate_withdrawal_fee


@api_v1_bp.route('/wallets', methods=['GET'])
@jwt_required()
def get_wallets():
    """Get all user wallets with addresses"""
    user_id = get_jwt_identity()
    wallets = Wallet.query.filter_by(user_id=user_id).all()

    return jsonify({
        'wallets': [w.to_dict() for w in wallets]
    }), 200


@api_v1_bp.route('/wallets/<currency_symbol>', methods=['GET'])
@jwt_required()
def get_wallet(currency_symbol):
    """Get specific wallet by currency"""
    user_id = get_jwt_identity()

    currency = Currency.query.filter_by(symbol=currency_symbol.upper()).first()
    if not currency:
        return jsonify({'error': 'Currency not found'}), 404

    wallet = Wallet.query.filter_by(user_id=user_id, currency_id=currency.id).first()
    if not wallet:
        return jsonify({'error': 'Wallet not found'}), 404

    balance = Balance.query.filter_by(user_id=user_id, currency_id=currency.id).first()

    return jsonify({
        'wallet': wallet.to_dict(),
        'balance': balance.to_dict() if balance else None
    }), 200


@api_v1_bp.route('/wallets/<currency_symbol>/address', methods=['GET'])
@jwt_required()
def get_deposit_address(currency_symbol):
    """Get or generate deposit address for a currency"""
    user_id = get_jwt_identity()

    currency = Currency.query.filter_by(symbol=currency_symbol.upper(), is_active=True).first()
    if not currency:
        return jsonify({'error': 'Currency not found or inactive'}), 404

    wallet = Wallet.query.filter_by(user_id=user_id, currency_id=currency.id).first()
    if not wallet:
        return jsonify({'error': 'Wallet not found'}), 404

    # Get existing address or generate new one
    address = WalletAddress.query.filter_by(wallet_id=wallet.id, is_active=True).first()

    if not address:
        try:
            address = generate_deposit_address(wallet)
        except Exception as e:
            current_app.logger.error(f"Failed to generate address: {e}")
            return jsonify({'error': 'Failed to generate deposit address'}), 500

    return jsonify({
        'address': address.address,
        'memo': address.memo,
        'currency': currency.symbol,
        'network': currency.network,
        'min_deposit': str(currency.min_deposit),
        'confirmations_required': currency.confirmations_required
    }), 200


@api_v1_bp.route('/wallets/deposits', methods=['GET'])
@jwt_required()
def get_deposits():
    """Get deposit history"""
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    currency = request.args.get('currency')

    query = Transaction.query.filter_by(
        user_id=user_id,
        type=TransactionType.DEPOSIT.value
    )

    if currency:
        cur = Currency.query.filter_by(symbol=currency.upper()).first()
        if cur:
            query = query.filter_by(currency_id=cur.id)

    deposits = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'deposits': [d.to_dict() for d in deposits.items],
        'total': deposits.total,
        'pages': deposits.pages,
        'current_page': page
    }), 200


@api_v1_bp.route('/wallets/withdraw', methods=['POST'])
@jwt_required()
@limiter.limit("10/hour")
def create_withdrawal():
    """Create withdrawal request"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()

    currency_symbol = data.get('currency', '').upper()
    to_address = data.get('address', '').strip()
    memo = data.get('memo')
    totp_code = data.get('totp_code')

    try:
        amount = Decimal(str(data.get('amount', 0)))
    except (InvalidOperation, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400

    # Validate currency
    currency = Currency.query.filter_by(symbol=currency_symbol, is_active=True).first()
    if not currency:
        return jsonify({'error': 'Currency not found or inactive'}), 404

    # Validate address
    if not validate_address(currency.network, to_address):
        return jsonify({'error': 'Invalid withdrawal address'}), 400

    # Check blacklist
    if BlacklistedAddress.query.filter_by(address=to_address).first():
        return jsonify({'error': 'This address is not allowed'}), 403

    # Check balance
    balance = Balance.query.filter_by(user_id=user_id, currency_id=currency.id).first()
    if not balance or balance.available < amount:
        return jsonify({'error': 'Insufficient balance'}), 400

    # Check minimum withdrawal
    if amount < currency.min_withdrawal:
        return jsonify({'error': f'Minimum withdrawal is {currency.min_withdrawal} {currency.symbol}'}), 400

    # Calculate fee
    fee = currency.withdrawal_fee
    net_amount = amount - fee

    if net_amount <= 0:
        return jsonify({'error': 'Amount too small after fee deduction'}), 400

    # Check 2FA if enabled
    if user.two_factor_enabled:
        if not totp_code:
            return jsonify({'error': '2FA code required', 'requires_2fa': True}), 401

        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(totp_code):
            return jsonify({'error': 'Invalid 2FA code'}), 401

    # Check KYC level for withdrawal limits
    # (implement withdrawal limits based on KYC level)

    # Lock funds
    balance.available -= amount
    balance.locked += amount
    balance.update_total()

    # Create withdrawal request
    withdrawal = WithdrawalRequest(
        user_id=user_id,
        currency_id=currency.id,
        amount=amount,
        fee=fee,
        net_amount=net_amount,
        to_address=to_address,
        memo=memo,
        two_factor_verified=user.two_factor_enabled,
        requires_manual_approval=amount > Decimal('1000')  # Example threshold
    )

    # Create transaction record
    transaction = Transaction(
        user_id=user_id,
        currency_id=currency.id,
        type=TransactionType.WITHDRAWAL.value,
        status=TransactionStatus.PENDING.value,
        amount=amount,
        fee=fee,
        net_amount=net_amount,
        to_address=to_address,
        balance_before=balance.available + amount,
        balance_after=balance.available
    )

    db.session.add(withdrawal)
    db.session.add(transaction)
    db.session.commit()

    withdrawal.transaction_id = transaction.id
    db.session.commit()

    return jsonify({
        'message': 'Withdrawal request created',
        'withdrawal': withdrawal.to_dict()
    }), 201


@api_v1_bp.route('/wallets/withdrawals', methods=['GET'])
@jwt_required()
def get_withdrawals():
    """Get withdrawal history"""
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    query = WithdrawalRequest.query.filter_by(user_id=user_id)

    if status:
        query = query.filter_by(status=status)

    withdrawals = query.order_by(WithdrawalRequest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'withdrawals': [w.to_dict() for w in withdrawals.items],
        'total': withdrawals.total,
        'pages': withdrawals.pages,
        'current_page': page
    }), 200


@api_v1_bp.route('/wallets/withdrawals/<int:withdrawal_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_withdrawal(withdrawal_id):
    """Cancel pending withdrawal"""
    user_id = get_jwt_identity()

    withdrawal = WithdrawalRequest.query.filter_by(
        id=withdrawal_id,
        user_id=user_id,
        status='pending'
    ).first()

    if not withdrawal:
        return jsonify({'error': 'Withdrawal not found or cannot be cancelled'}), 404

    # Unlock funds
    balance = Balance.query.filter_by(
        user_id=user_id,
        currency_id=withdrawal.currency_id
    ).first()

    if balance:
        balance.locked -= withdrawal.amount
        balance.available += withdrawal.amount
        balance.update_total()

    withdrawal.status = 'cancelled'

    # Update transaction
    if withdrawal.transaction_id:
        transaction = Transaction.query.get(withdrawal.transaction_id)
        if transaction:
            transaction.status = TransactionStatus.CANCELLED.value

    db.session.commit()

    return jsonify({'message': 'Withdrawal cancelled'}), 200


@api_v1_bp.route('/currencies', methods=['GET'])
def get_currencies():
    """Get all supported currencies"""
    currencies = Currency.query.filter_by(is_active=True).all()
    return jsonify({
        'currencies': [c.to_dict() for c in currencies]
    }), 200
