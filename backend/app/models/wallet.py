from datetime import datetime
from enum import Enum
from app import db


class NetworkType(str, Enum):
    BTC_MAINNET = 'btc_mainnet'
    ETH_MAINNET = 'eth_mainnet'
    TRX_MAINNET = 'trx_mainnet'
    SOL_MAINNET = 'sol_mainnet'
    LTC_MAINNET = 'ltc_mainnet'
    DOGE_MAINNET = 'doge_mainnet'
    XLM_MAINNET = 'xlm_mainnet'


class Currency(db.Model):
    """Supported currencies/tokens"""
    __tablename__ = 'currencies'

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False, index=True)  # BTC, ETH, USDT
    name = db.Column(db.String(100), nullable=False)  # Bitcoin, Ethereum
    network = db.Column(db.String(50), nullable=False)  # btc_mainnet, eth_mainnet, trx_mainnet
    contract_address = db.Column(db.String(100), nullable=True)  # For tokens like USDT
    decimals = db.Column(db.Integer, default=8)
    is_token = db.Column(db.Boolean, default=False)  # True for USDT, etc.
    is_active = db.Column(db.Boolean, default=True)
    min_deposit = db.Column(db.Numeric(36, 18), default=0)
    min_withdrawal = db.Column(db.Numeric(36, 18), default=0)
    withdrawal_fee = db.Column(db.Numeric(36, 18), default=0)
    confirmations_required = db.Column(db.Integer, default=3)
    icon_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'network': self.network,
            'decimals': self.decimals,
            'is_token': self.is_token,
            'is_active': self.is_active,
            'min_deposit': str(self.min_deposit),
            'min_withdrawal': str(self.min_withdrawal),
            'withdrawal_fee': str(self.withdrawal_fee),
            'confirmations_required': self.confirmations_required,
            'icon_url': self.icon_url
        }


class Wallet(db.Model):
    """User wallet per currency"""
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    currency = db.relationship('Currency', backref='wallets')
    addresses = db.relationship('WalletAddress', backref='wallet', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'currency_id', name='unique_user_currency'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'currency': self.currency.to_dict() if self.currency else None,
            'is_active': self.is_active,
            'addresses': [addr.to_dict() for addr in self.addresses]
        }


class WalletAddress(db.Model):
    """Deposit addresses for user wallets"""
    __tablename__ = 'wallet_addresses'

    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id'), nullable=False)
    address = db.Column(db.String(255), nullable=False, unique=True, index=True)
    memo = db.Column(db.String(100), nullable=True)  # For XLM, etc.
    derivation_index = db.Column(db.Integer, nullable=True)  # HD wallet index
    is_active = db.Column(db.Boolean, default=True)
    label = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'address': self.address,
            'memo': self.memo,
            'is_active': self.is_active,
            'label': self.label,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemWallet(db.Model):
    """Platform hot/cold wallets"""
    __tablename__ = 'system_wallets'

    id = db.Column(db.Integer, primary_key=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    wallet_type = db.Column(db.String(20), nullable=False)  # 'hot', 'cold', 'fee'
    address = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Numeric(36, 18), default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    currency = db.relationship('Currency')

    def to_dict(self):
        return {
            'id': self.id,
            'currency': self.currency.symbol if self.currency else None,
            'wallet_type': self.wallet_type,
            'address': self.address,
            'balance': str(self.balance),
            'is_active': self.is_active
        }
