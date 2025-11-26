from datetime import datetime
from enum import Enum
from app import db
from decimal import Decimal


class TransactionType(str, Enum):
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    TRADE_BUY = 'trade_buy'
    TRADE_SELL = 'trade_sell'
    FEE = 'fee'
    FEE_COLLECTION = 'fee_collection'
    TRANSFER_IN = 'transfer_in'
    TRANSFER_OUT = 'transfer_out'
    MARGIN_TRANSFER_IN = 'margin_transfer_in'
    MARGIN_TRANSFER_OUT = 'margin_transfer_out'
    LIQUIDATION = 'liquidation'
    ADJUSTMENT = 'adjustment'  # Admin manual adjustment


class TransactionStatus(str, Enum):
    PENDING = 'pending'
    CONFIRMING = 'confirming'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class Balance(db.Model):
    """User balance per currency (double-entry ledger style)"""
    __tablename__ = 'balances'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    available = db.Column(db.Numeric(36, 18), default=Decimal('0'))  # Available for trading/withdrawal
    locked = db.Column(db.Numeric(36, 18), default=Decimal('0'))  # Locked in open orders
    total = db.Column(db.Numeric(36, 18), default=Decimal('0'))  # available + locked
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    currency = db.relationship('Currency')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'currency_id', name='unique_user_balance'),
        db.CheckConstraint('available >= 0', name='check_available_positive'),
        db.CheckConstraint('locked >= 0', name='check_locked_positive'),
    )

    def to_dict(self):
        return {
            'currency': self.currency.symbol if self.currency else None,
            'available': str(self.available),
            'locked': str(self.locked),
            'total': str(self.total)
        }

    def update_total(self):
        self.total = self.available + self.locked


class Transaction(db.Model):
    """Transaction ledger for all balance changes"""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default=TransactionStatus.PENDING.value)

    # Amount details
    amount = db.Column(db.Numeric(36, 18), nullable=False)
    fee = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    net_amount = db.Column(db.Numeric(36, 18), nullable=False)  # amount - fee

    # Balance snapshot after transaction
    balance_before = db.Column(db.Numeric(36, 18), nullable=True)
    balance_after = db.Column(db.Numeric(36, 18), nullable=True)

    # Blockchain details (for deposits/withdrawals)
    tx_hash = db.Column(db.String(255), nullable=True, index=True)
    from_address = db.Column(db.String(255), nullable=True)
    to_address = db.Column(db.String(255), nullable=True)
    confirmations = db.Column(db.Integer, default=0)
    block_number = db.Column(db.BigInteger, nullable=True)

    # Related entities
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    trade_id = db.Column(db.Integer, db.ForeignKey('trades.id'), nullable=True)

    # Metadata
    note = db.Column(db.Text, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # For manual adjustments

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    currency = db.relationship('Currency')
    user = db.relationship('User', foreign_keys=[user_id])
    admin = db.relationship('User', foreign_keys=[admin_id])

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'status': self.status,
            'currency': self.currency.symbol if self.currency else None,
            'amount': str(self.amount),
            'fee': str(self.fee),
            'net_amount': str(self.net_amount),
            'tx_hash': self.tx_hash,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'confirmations': self.confirmations,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class WithdrawalRequest(db.Model):
    """Pending withdrawal requests"""
    __tablename__ = 'withdrawal_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)

    amount = db.Column(db.Numeric(36, 18), nullable=False)
    fee = db.Column(db.Numeric(36, 18), nullable=False)
    net_amount = db.Column(db.Numeric(36, 18), nullable=False)
    to_address = db.Column(db.String(255), nullable=False)
    memo = db.Column(db.String(100), nullable=True)

    status = db.Column(db.String(20), default='pending')  # pending, approved, processing, completed, rejected
    requires_manual_approval = db.Column(db.Boolean, default=False)

    # Risk checks
    risk_score = db.Column(db.Integer, default=0)
    risk_flags = db.Column(db.JSON, nullable=True)
    is_blacklisted_address = db.Column(db.Boolean, default=False)

    # 2FA verification
    two_factor_verified = db.Column(db.Boolean, default=False)

    # Admin review
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    currency = db.relationship('Currency')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            'id': self.id,
            'currency': self.currency.symbol if self.currency else None,
            'amount': str(self.amount),
            'fee': str(self.fee),
            'net_amount': str(self.net_amount),
            'to_address': self.to_address,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
