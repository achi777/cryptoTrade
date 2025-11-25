from datetime import datetime
from app import db


class AuditLog(db.Model):
    """Audit log for important admin actions"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)  # user, kyc, balance, withdrawal, fee
    entity_id = db.Column(db.Integer, nullable=True)
    old_value = db.Column(db.JSON, nullable=True)
    new_value = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    admin = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'admin_email': self.admin.email if self.admin else None,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'ip_address': self.ip_address,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemSetting(db.Model):
    """Global system settings"""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, default=False)  # Can be fetched by frontend
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def get_value(self):
        """Get typed value"""
        if self.value is None:
            return None
        if self.value_type == 'int':
            return int(self.value)
        if self.value_type == 'float':
            return float(self.value)
        if self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes')
        if self.value_type == 'json':
            import json
            return json.loads(self.value)
        return self.value

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.get_value(),
            'description': self.description
        }


class FeeConfig(db.Model):
    """Fee configuration"""
    __tablename__ = 'fee_configs'

    id = db.Column(db.Integer, primary_key=True)
    fee_type = db.Column(db.String(50), nullable=False)  # maker, taker, withdrawal
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=True)  # Null for global
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pairs.id'), nullable=True)
    value = db.Column(db.Numeric(10, 6), nullable=False)  # Percentage or fixed amount
    is_percentage = db.Column(db.Boolean, default=True)
    min_amount = db.Column(db.Numeric(36, 18), nullable=True)
    max_amount = db.Column(db.Numeric(36, 18), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    currency = db.relationship('Currency')
    trading_pair = db.relationship('TradingPair')

    def to_dict(self):
        return {
            'id': self.id,
            'fee_type': self.fee_type,
            'currency': self.currency.symbol if self.currency else None,
            'trading_pair': self.trading_pair.symbol if self.trading_pair else None,
            'value': str(self.value),
            'is_percentage': self.is_percentage,
            'is_active': self.is_active
        }


class BlacklistedAddress(db.Model):
    """Blacklisted blockchain addresses for AML"""
    __tablename__ = 'blacklisted_addresses'

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), unique=True, nullable=False, index=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(100), nullable=True)  # OFAC, internal, reported
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    currency = db.relationship('Currency')

    def to_dict(self):
        return {
            'id': self.id,
            'address': self.address,
            'currency': self.currency.symbol if self.currency else None,
            'reason': self.reason,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
