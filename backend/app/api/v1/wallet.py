from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
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
    """
    Get All User Wallets
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    responses:
      200:
        description: List of all user wallets with addresses
        schema:
          type: object
          properties:
            wallets:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  currency:
                    type: string
                    example: BTC
                  addresses:
                    type: array
                    items:
                      type: object
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    wallets = Wallet.query.filter_by(user_id=user_id).all()

    return jsonify({
        'wallets': [w.to_dict() for w in wallets]
    }), 200


@api_v1_bp.route('/wallets/<currency_symbol>', methods=['GET'])
@jwt_required()
def get_wallet(currency_symbol):
    """
    Get Specific Wallet by Currency
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    parameters:
      - name: currency_symbol
        in: path
        required: true
        type: string
        description: Currency symbol (e.g., BTC, ETH)
        example: BTC
    responses:
      200:
        description: Wallet details with balance
        schema:
          type: object
          properties:
            wallet:
              type: object
            balance:
              type: object
              properties:
                available:
                  type: string
                locked:
                  type: string
                total:
                  type: string
      404:
        description: Currency or wallet not found
      401:
        description: Unauthorized
    """
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
    """
    Get or Generate Deposit Address
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    parameters:
      - name: currency_symbol
        in: path
        required: true
        type: string
        description: Currency symbol (e.g., BTC, ETH)
        example: BTC
    responses:
      200:
        description: Deposit address details
        schema:
          type: object
          properties:
            address:
              type: string
              example: "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
            memo:
              type: string
              nullable: true
            currency:
              type: string
              example: BTC
            network:
              type: string
              example: Bitcoin
            min_deposit:
              type: string
              example: "0.0001"
            confirmations_required:
              type: integer
              example: 3
      404:
        description: Currency not found or inactive
      500:
        description: Failed to generate deposit address
      401:
        description: Unauthorized
    """
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
    """
    Get Deposit History
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 20
        description: Items per page
      - name: currency
        in: query
        type: string
        description: Filter by currency symbol
        example: BTC
    responses:
      200:
        description: Paginated list of deposits
        schema:
          type: object
          properties:
            deposits:
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
@limiter.limit("5/hour;20/day")  # SECURITY: Strict limits on withdrawals
def create_withdrawal():
    """
    Create Withdrawal Request
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - currency
            - address
            - amount
            - totp_code
          properties:
            currency:
              type: string
              example: BTC
            address:
              type: string
              example: "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
            memo:
              type: string
              nullable: true
            amount:
              type: string
              example: "0.01"
            totp_code:
              type: string
              example: "123456"
              description: 2FA code (required)
    responses:
      201:
        description: Withdrawal request created
        schema:
          type: object
          properties:
            message:
              type: string
            withdrawal:
              type: object
            can_process_after:
              type: string
              format: date-time
            requires_approval:
              type: boolean
      400:
        description: Invalid input or insufficient balance
      401:
        description: Invalid 2FA code
      403:
        description: 2FA not enabled or blacklisted address
      404:
        description: Currency not found
      429:
        description: Rate limit exceeded
    """
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

    # Check minimum withdrawal first (before locking)
    if amount < currency.min_withdrawal:
        return jsonify({'error': f'Minimum withdrawal is {currency.min_withdrawal} {currency.symbol}'}), 400

    # Calculate fee
    fee = currency.withdrawal_fee
    net_amount = amount - fee

    if net_amount <= 0:
        return jsonify({'error': 'Amount too small after fee deduction'}), 400

    # Check 2FA if enabled - ENFORCE for all withdrawals
    if not user.two_factor_enabled:
        return jsonify({'error': 'Two-factor authentication must be enabled before making withdrawals'}), 403

    if not totp_code:
        return jsonify({'error': '2FA code required', 'requires_2fa': True}), 401

    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(totp_code):
        return jsonify({'error': 'Invalid 2FA code'}), 401

    # Check KYC level for withdrawal limits
    # (implement withdrawal limits based on KYC level)

    # Lock balance row atomically to prevent race conditions
    from sqlalchemy import select

    balance = db.session.execute(
        select(Balance).filter_by(
            user_id=user_id,
            currency_id=currency.id
        ).with_for_update()
    ).scalar_one_or_none()

    if not balance or balance.available < amount:
        db.session.rollback()
        return jsonify({'error': 'Insufficient balance'}), 400

    # Lock funds atomically
    balance.available -= amount
    balance.locked += amount
    balance.update_total()

    # SECURITY: Determine time-delay and approval requirements
    # Large withdrawals require longer delays and manual approval
    requires_approval = amount > Decimal('1000')  # Threshold for manual approval

    if amount >= Decimal('10000'):
        delay_minutes = 60  # 1 hour for very large withdrawals
    elif amount >= Decimal('1000'):
        delay_minutes = 30  # 30 minutes for large withdrawals
    else:
        delay_minutes = 10  # 10 minutes for normal withdrawals

    can_process_after = datetime.utcnow() + timedelta(minutes=delay_minutes)

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
        requires_manual_approval=requires_approval,
        can_process_after=can_process_after
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

    # Build response message
    message = f'Withdrawal request created. Processing will begin after {delay_minutes} minutes.'
    if requires_approval:
        message += ' Manual approval required for large amounts.'

    return jsonify({
        'message': message,
        'withdrawal': withdrawal.to_dict(),
        'can_process_after': can_process_after.isoformat(),
        'requires_approval': requires_approval
    }), 201


@api_v1_bp.route('/wallets/withdrawals', methods=['GET'])
@jwt_required()
def get_withdrawals():
    """
    Get Withdrawal History
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 20
        description: Items per page
      - name: status
        in: query
        type: string
        description: Filter by status
        enum: [pending, processing, completed, cancelled, rejected]
    responses:
      200:
        description: Paginated list of withdrawals
        schema:
          type: object
          properties:
            withdrawals:
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
    """
    Cancel Pending Withdrawal
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    parameters:
      - name: withdrawal_id
        in: path
        required: true
        type: integer
        description: Withdrawal request ID
    responses:
      200:
        description: Withdrawal cancelled successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Withdrawal cancelled
      404:
        description: Withdrawal not found or cannot be cancelled
      401:
        description: Unauthorized
    """
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
    """
    Get All Supported Currencies
    ---
    tags:
      - Wallet
    responses:
      200:
        description: List of all active currencies
        schema:
          type: object
          properties:
            currencies:
              type: array
              items:
                type: object
                properties:
                  symbol:
                    type: string
                    example: BTC
                  name:
                    type: string
                    example: Bitcoin
                  network:
                    type: string
                  min_deposit:
                    type: string
                  min_withdrawal:
                    type: string
                  withdrawal_fee:
                    type: string
    """
    currencies = Currency.query.filter_by(is_active=True).all()
    return jsonify({
        'currencies': [c.to_dict() for c in currencies]
    }), 200
