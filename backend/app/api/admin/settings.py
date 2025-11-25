"""Admin Settings & Audit Logs API"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.api.admin import admin_bp
from app.api.admin.users import admin_required, log_admin_action
from app import db
from app.models.admin import SystemSetting, AuditLog


@admin_bp.route('/settings', methods=['GET'])
@admin_required
def get_settings():
    """Get all system settings"""
    settings = SystemSetting.query.all()
    return jsonify({
        'settings': [s.to_dict() for s in settings]
    }), 200


@admin_bp.route('/settings/<key>', methods=['GET'])
@admin_required
def get_setting(key):
    """Get specific setting"""
    setting = SystemSetting.query.filter_by(key=key).first()
    if not setting:
        return jsonify({'error': 'Setting not found'}), 404

    return jsonify({'setting': setting.to_dict()}), 200


@admin_bp.route('/settings/<key>', methods=['PUT'])
@admin_required
def update_setting(key):
    """Update system setting"""
    admin_id = get_jwt_identity()
    data = request.get_json()

    setting = SystemSetting.query.filter_by(key=key).first()

    if not setting:
        # Create new setting
        setting = SystemSetting(
            key=key,
            value=str(data.get('value', '')),
            value_type=data.get('value_type', 'string'),
            description=data.get('description'),
            is_public=data.get('is_public', False)
        )
        db.session.add(setting)
        old_value = None
    else:
        old_value = setting.get_value()
        setting.value = str(data.get('value', ''))
        if 'description' in data:
            setting.description = data['description']
        if 'is_public' in data:
            setting.is_public = data['is_public']

    setting.updated_by = admin_id

    log_admin_action(
        admin_id=admin_id,
        action='update_setting',
        entity_type='setting',
        old_value={'value': old_value},
        new_value={'value': setting.get_value()},
        note=f"Setting: {key}"
    )

    db.session.commit()

    return jsonify({
        'message': 'Setting updated',
        'setting': setting.to_dict()
    }), 200


@admin_bp.route('/settings/bulk', methods=['POST'])
@admin_required
def update_settings_bulk():
    """Update multiple settings at once"""
    admin_id = get_jwt_identity()
    data = request.get_json()

    settings_data = data.get('settings', [])

    for item in settings_data:
        key = item.get('key')
        value = item.get('value')

        if not key:
            continue

        setting = SystemSetting.query.filter_by(key=key).first()
        if setting:
            old_value = setting.get_value()
            setting.value = str(value)
            setting.updated_by = admin_id

            log_admin_action(
                admin_id=admin_id,
                action='update_setting',
                entity_type='setting',
                old_value={'value': old_value},
                new_value={'value': value},
                note=f"Setting: {key}"
            )

    db.session.commit()

    return jsonify({'message': 'Settings updated'}), 200


@admin_bp.route('/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    """Get audit logs"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action = request.args.get('action')
    entity_type = request.args.get('entity_type')
    admin_id = request.args.get('admin_id', type=int)

    query = AuditLog.query

    if action:
        query = query.filter_by(action=action)
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if admin_id:
        query = query.filter_by(admin_id=admin_id)

    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'logs': [l.to_dict() for l in logs.items],
        'total': logs.total,
        'pages': logs.pages,
        'current_page': page
    }), 200


@admin_bp.route('/audit-logs/<int:log_id>', methods=['GET'])
@admin_required
def get_audit_log(log_id):
    """Get specific audit log entry"""
    log = AuditLog.query.get(log_id)
    if not log:
        return jsonify({'error': 'Log not found'}), 404

    return jsonify({'log': log.to_dict()}), 200


@admin_bp.route('/dashboard/stats', methods=['GET'])
@admin_required
def get_dashboard_stats():
    """Get dashboard statistics for admin panel"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.user import User
    from app.models.trading import Order, Trade, TradingPair
    from app.models.balance import Transaction, WithdrawalRequest
    from app.models.kyc import KYCRequest, KYCStatus

    day_ago = datetime.utcnow() - timedelta(days=1)
    week_ago = datetime.utcnow() - timedelta(days=7)

    # User stats
    total_users = User.query.count()
    new_users_24h = User.query.filter(User.created_at >= day_ago).count()
    verified_users = User.query.filter_by(is_verified=True).count()

    # Trading stats
    trades_24h = Trade.query.filter(Trade.created_at >= day_ago).count()
    volume_24h = db.session.query(func.sum(Trade.total)).filter(
        Trade.created_at >= day_ago
    ).scalar() or 0

    # Pending items
    pending_kyc = KYCRequest.query.filter_by(status=KYCStatus.PENDING.value).count()
    pending_withdrawals = WithdrawalRequest.query.filter_by(status='pending').count()

    # Revenue (fees collected)
    fees_24h = db.session.query(func.sum(Trade.buyer_fee + Trade.seller_fee)).filter(
        Trade.created_at >= day_ago
    ).scalar() or 0

    return jsonify({
        'users': {
            'total': total_users,
            'new_24h': new_users_24h,
            'verified': verified_users
        },
        'trading': {
            'trades_24h': trades_24h,
            'volume_24h': str(volume_24h)
        },
        'pending': {
            'kyc': pending_kyc,
            'withdrawals': pending_withdrawals
        },
        'revenue': {
            'fees_24h': str(fees_24h)
        }
    }), 200


# Default system settings to initialize
DEFAULT_SETTINGS = [
    {'key': 'maintenance_mode', 'value': 'false', 'value_type': 'bool', 'description': 'Enable maintenance mode'},
    {'key': 'registration_enabled', 'value': 'true', 'value_type': 'bool', 'description': 'Allow new user registration'},
    {'key': 'trading_enabled', 'value': 'true', 'value_type': 'bool', 'description': 'Enable trading'},
    {'key': 'withdrawals_enabled', 'value': 'true', 'value_type': 'bool', 'description': 'Enable withdrawals'},
    {'key': 'deposits_enabled', 'value': 'true', 'value_type': 'bool', 'description': 'Enable deposits'},
    {'key': 'kyc_required_for_withdrawal', 'value': 'true', 'value_type': 'bool', 'description': 'Require KYC for withdrawals'},
    {'key': 'min_withdrawal_kyc_level', 'value': '1', 'value_type': 'int', 'description': 'Minimum KYC level for withdrawal'},
    {'key': 'max_withdrawal_no_kyc', 'value': '100', 'value_type': 'float', 'description': 'Max withdrawal without KYC (USDT)'},
]


def init_default_settings():
    """Initialize default system settings"""
    for setting_data in DEFAULT_SETTINGS:
        existing = SystemSetting.query.filter_by(key=setting_data['key']).first()
        if not existing:
            setting = SystemSetting(**setting_data)
            db.session.add(setting)
    db.session.commit()
