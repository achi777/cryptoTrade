"""Admin Wallet & Withdrawal Management API"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from datetime import datetime

from app.api.admin import admin_bp
from app.api.admin.users import admin_required, log_admin_action
from app import db
from app.models.wallet import Currency, SystemWallet
from app.models.balance import WithdrawalRequest, Transaction, TransactionStatus
from app.models.admin import BlacklistedAddress


@admin_bp.route('/wallets/system', methods=['GET'])
@admin_required
def get_system_wallets():
    """Get system wallet balances"""
    wallets = SystemWallet.query.all()
    return jsonify({
        'wallets': [w.to_dict() for w in wallets]
    }), 200


@admin_bp.route('/wallets/withdrawals/pending', methods=['GET'])
@admin_required
def get_pending_withdrawals():
    """Get pending withdrawal requests"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    withdrawals = WithdrawalRequest.query.filter_by(status='pending').order_by(
        WithdrawalRequest.created_at.asc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'withdrawals': [w.to_dict() for w in withdrawals.items],
        'total': withdrawals.total,
        'pages': withdrawals.pages
    }), 200


@admin_bp.route('/wallets/withdrawals/<int:withdrawal_id>', methods=['GET'])
@admin_required
def get_withdrawal(withdrawal_id):
    """Get withdrawal details"""
    withdrawal = WithdrawalRequest.query.get(withdrawal_id)
    if not withdrawal:
        return jsonify({'error': 'Withdrawal not found'}), 404

    return jsonify({
        'withdrawal': withdrawal.to_dict(),
        'user_email': withdrawal.user.email if withdrawal.user else None
    }), 200


@admin_bp.route('/wallets/withdrawals/<int:withdrawal_id>/approve', methods=['POST'])
@admin_required
def approve_withdrawal(withdrawal_id):
    """Approve withdrawal request"""
    admin_id = get_jwt_identity()
    withdrawal = WithdrawalRequest.query.get(withdrawal_id)

    if not withdrawal:
        return jsonify({'error': 'Withdrawal not found'}), 404

    if withdrawal.status != 'pending':
        return jsonify({'error': 'Can only approve pending withdrawals'}), 400

    data = request.get_json() or {}
    notes = data.get('notes', '')

    old_status = withdrawal.status
    withdrawal.status = 'approved'
    withdrawal.reviewed_by = admin_id
    withdrawal.reviewed_at = datetime.utcnow()

    log_admin_action(
        admin_id=admin_id,
        action='approve_withdrawal',
        entity_type='withdrawal',
        entity_id=withdrawal_id,
        old_value={'status': old_status},
        new_value={'status': 'approved'},
        note=notes
    )

    db.session.commit()

    # In production, this would trigger the actual blockchain transaction
    # For now, just mark as approved

    return jsonify({
        'message': 'Withdrawal approved',
        'withdrawal': withdrawal.to_dict()
    }), 200


@admin_bp.route('/wallets/withdrawals/<int:withdrawal_id>/reject', methods=['POST'])
@admin_required
def reject_withdrawal(withdrawal_id):
    """Reject withdrawal request"""
    admin_id = get_jwt_identity()
    withdrawal = WithdrawalRequest.query.get(withdrawal_id)

    if not withdrawal:
        return jsonify({'error': 'Withdrawal not found'}), 404

    if withdrawal.status != 'pending':
        return jsonify({'error': 'Can only reject pending withdrawals'}), 400

    data = request.get_json()
    reason = data.get('reason', '')

    if not reason:
        return jsonify({'error': 'Rejection reason is required'}), 400

    from app.models.balance import Balance

    # Unlock funds
    balance = Balance.query.filter_by(
        user_id=withdrawal.user_id,
        currency_id=withdrawal.currency_id
    ).first()

    if balance:
        balance.locked -= withdrawal.amount
        balance.available += withdrawal.amount
        balance.update_total()

    old_status = withdrawal.status
    withdrawal.status = 'rejected'
    withdrawal.reviewed_by = admin_id
    withdrawal.reviewed_at = datetime.utcnow()
    withdrawal.rejection_reason = reason

    # Update transaction if exists
    if withdrawal.transaction_id:
        transaction = Transaction.query.get(withdrawal.transaction_id)
        if transaction:
            transaction.status = TransactionStatus.FAILED.value

    log_admin_action(
        admin_id=admin_id,
        action='reject_withdrawal',
        entity_type='withdrawal',
        entity_id=withdrawal_id,
        old_value={'status': old_status},
        new_value={'status': 'rejected'},
        note=reason
    )

    db.session.commit()

    return jsonify({
        'message': 'Withdrawal rejected',
        'withdrawal': withdrawal.to_dict()
    }), 200


@admin_bp.route('/wallets/blacklist', methods=['GET'])
@admin_required
def get_blacklisted_addresses():
    """Get blacklisted addresses"""
    addresses = BlacklistedAddress.query.all()
    return jsonify({
        'addresses': [a.to_dict() for a in addresses]
    }), 200


@admin_bp.route('/wallets/blacklist', methods=['POST'])
@admin_required
def add_blacklisted_address():
    """Add address to blacklist"""
    admin_id = get_jwt_identity()
    data = request.get_json()

    address = data.get('address', '').strip()
    reason = data.get('reason', '')
    source = data.get('source', 'internal')

    if not address:
        return jsonify({'error': 'Address is required'}), 400

    existing = BlacklistedAddress.query.filter_by(address=address).first()
    if existing:
        return jsonify({'error': 'Address already blacklisted'}), 400

    blacklist = BlacklistedAddress(
        address=address,
        reason=reason,
        source=source,
        added_by=admin_id
    )
    db.session.add(blacklist)

    log_admin_action(
        admin_id=admin_id,
        action='add_blacklist',
        entity_type='blacklist',
        new_value={'address': address, 'reason': reason}
    )

    db.session.commit()

    return jsonify({
        'message': 'Address added to blacklist',
        'address': blacklist.to_dict()
    }), 201


@admin_bp.route('/wallets/blacklist/<int:address_id>', methods=['DELETE'])
@admin_required
def remove_blacklisted_address(address_id):
    """Remove address from blacklist"""
    admin_id = get_jwt_identity()
    blacklist = BlacklistedAddress.query.get(address_id)

    if not blacklist:
        return jsonify({'error': 'Address not found'}), 404

    log_admin_action(
        admin_id=admin_id,
        action='remove_blacklist',
        entity_type='blacklist',
        entity_id=address_id,
        old_value={'address': blacklist.address}
    )

    db.session.delete(blacklist)
    db.session.commit()

    return jsonify({'message': 'Address removed from blacklist'}), 200


@admin_bp.route('/wallets/currencies', methods=['GET'])
@admin_required
def get_currencies():
    """Get all currencies"""
    currencies = Currency.query.all()
    return jsonify({
        'currencies': [c.to_dict() for c in currencies]
    }), 200


@admin_bp.route('/wallets/currencies/<int:currency_id>', methods=['PUT'])
@admin_required
def update_currency(currency_id):
    """Update currency settings"""
    admin_id = get_jwt_identity()
    currency = Currency.query.get(currency_id)

    if not currency:
        return jsonify({'error': 'Currency not found'}), 404

    data = request.get_json()
    old_values = currency.to_dict()

    # Update allowed fields
    if 'is_active' in data:
        currency.is_active = data['is_active']
    if 'min_deposit' in data:
        currency.min_deposit = data['min_deposit']
    if 'min_withdrawal' in data:
        currency.min_withdrawal = data['min_withdrawal']
    if 'withdrawal_fee' in data:
        currency.withdrawal_fee = data['withdrawal_fee']
    if 'confirmations_required' in data:
        currency.confirmations_required = data['confirmations_required']

    log_admin_action(
        admin_id=admin_id,
        action='update_currency',
        entity_type='currency',
        entity_id=currency_id,
        old_value=old_values,
        new_value=currency.to_dict()
    )

    db.session.commit()

    return jsonify({
        'message': 'Currency updated',
        'currency': currency.to_dict()
    }), 200
