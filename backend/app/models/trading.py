from datetime import datetime
from enum import Enum
from app import db
from decimal import Decimal


class OrderType(str, Enum):
    MARKET = 'market'
    LIMIT = 'limit'
    STOP_LIMIT = 'stop_limit'


class OrderSide(str, Enum):
    BUY = 'buy'
    SELL = 'sell'


class OrderStatus(str, Enum):
    PENDING = 'pending'
    OPEN = 'open'
    PARTIALLY_FILLED = 'partially_filled'
    FILLED = 'filled'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'


class TradingPair(db.Model):
    """Trading pairs configuration"""
    __tablename__ = 'trading_pairs'

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False, index=True)  # BTC_USDT
    base_currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    quote_currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    is_margin_enabled = db.Column(db.Boolean, default=False)

    # Trading limits
    min_order_size = db.Column(db.Numeric(36, 18), default=Decimal('0.0001'))
    max_order_size = db.Column(db.Numeric(36, 18), default=Decimal('1000000'))
    min_price = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    max_price = db.Column(db.Numeric(36, 18), default=Decimal('999999999'))

    # Precision
    price_precision = db.Column(db.Integer, default=8)
    amount_precision = db.Column(db.Integer, default=8)

    # Fees (override global if set)
    maker_fee = db.Column(db.Numeric(10, 6), nullable=True)
    taker_fee = db.Column(db.Numeric(10, 6), nullable=True)

    # Market data cache
    last_price = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    price_change_24h = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    high_24h = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    low_24h = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    volume_24h = db.Column(db.Numeric(36, 18), default=Decimal('0'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    base_currency = db.relationship('Currency', foreign_keys=[base_currency_id])
    quote_currency = db.relationship('Currency', foreign_keys=[quote_currency_id])

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'base_currency': self.base_currency.symbol if self.base_currency else None,
            'quote_currency': self.quote_currency.symbol if self.quote_currency else None,
            'is_active': self.is_active,
            'is_margin_enabled': self.is_margin_enabled,
            'min_order_size': str(self.min_order_size),
            'max_order_size': str(self.max_order_size),
            'price_precision': self.price_precision,
            'amount_precision': self.amount_precision,
            'maker_fee': str(self.maker_fee) if self.maker_fee else None,
            'taker_fee': str(self.taker_fee) if self.taker_fee else None,
            'last_price': str(self.last_price),
            'price_change_24h': str(self.price_change_24h),
            'high_24h': str(self.high_24h),
            'low_24h': str(self.low_24h),
            'volume_24h': str(self.volume_24h)
        }


class Order(db.Model):
    """Trading orders"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pairs.id'), nullable=False)

    order_type = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default=OrderStatus.PENDING.value, index=True)

    # Prices
    price = db.Column(db.Numeric(36, 18), nullable=True)  # Null for market orders
    stop_price = db.Column(db.Numeric(36, 18), nullable=True)  # For stop-limit orders
    avg_fill_price = db.Column(db.Numeric(36, 18), default=Decimal('0'))

    # Amounts
    amount = db.Column(db.Numeric(36, 18), nullable=False)  # Original amount
    filled_amount = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    remaining_amount = db.Column(db.Numeric(36, 18), nullable=False)

    # Fees
    fee = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    fee_currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=True)

    # Margin trading
    is_margin = db.Column(db.Boolean, default=False)
    leverage = db.Column(db.Integer, default=1)
    margin_account_id = db.Column(db.Integer, db.ForeignKey('margin_accounts.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    filled_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Client order id (optional)
    client_order_id = db.Column(db.String(100), nullable=True)

    # Relationships
    trading_pair = db.relationship('TradingPair')
    trades = db.relationship('Trade', backref='order', lazy='dynamic',
                            foreign_keys='Trade.order_id')

    def to_dict(self):
        return {
            'id': self.id,
            'trading_pair': self.trading_pair.symbol if self.trading_pair else None,
            'order_type': self.order_type,
            'side': self.side,
            'status': self.status,
            'price': str(self.price) if self.price else None,
            'amount': str(self.amount),
            'filled_amount': str(self.filled_amount),
            'remaining_amount': str(self.remaining_amount),
            'avg_fill_price': str(self.avg_fill_price),
            'fee': str(self.fee),
            'is_margin': self.is_margin,
            'leverage': self.leverage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None
        }


class Trade(db.Model):
    """Executed trades"""
    __tablename__ = 'trades'

    id = db.Column(db.Integer, primary_key=True)
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pairs.id'), nullable=False, index=True)

    # Orders involved
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    counter_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)

    # Users
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Trade details
    price = db.Column(db.Numeric(36, 18), nullable=False)
    amount = db.Column(db.Numeric(36, 18), nullable=False)
    total = db.Column(db.Numeric(36, 18), nullable=False)  # price * amount

    # Fees
    buyer_fee = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    seller_fee = db.Column(db.Numeric(36, 18), default=Decimal('0'))

    # Who was maker/taker
    maker_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    taker_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    trading_pair = db.relationship('TradingPair')
    buyer = db.relationship('User', foreign_keys=[buyer_id])
    seller = db.relationship('User', foreign_keys=[seller_id])

    def to_dict(self):
        return {
            'id': self.id,
            'trading_pair': self.trading_pair.symbol if self.trading_pair else None,
            'price': str(self.price),
            'amount': str(self.amount),
            'total': str(self.total),
            'buyer_fee': str(self.buyer_fee),
            'seller_fee': str(self.seller_fee),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class MarginAccount(db.Model):
    """Margin trading account"""
    __tablename__ = 'margin_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # Collateral
    collateral = db.Column(db.Numeric(36, 18), default=Decimal('0'))  # In quote currency (USDT)
    borrowed = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    interest_accrued = db.Column(db.Numeric(36, 18), default=Decimal('0'))

    # Risk metrics
    margin_ratio = db.Column(db.Numeric(10, 6), default=Decimal('0'))  # collateral / borrowed
    liquidation_price = db.Column(db.Numeric(36, 18), nullable=True)

    # Settings
    max_leverage = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='margin_account')
    positions = db.relationship('MarginPosition', backref='margin_account', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'collateral': str(self.collateral),
            'borrowed': str(self.borrowed),
            'interest_accrued': str(self.interest_accrued),
            'margin_ratio': str(self.margin_ratio),
            'liquidation_price': str(self.liquidation_price) if self.liquidation_price else None,
            'max_leverage': self.max_leverage,
            'is_active': self.is_active
        }


class MarginPosition(db.Model):
    """Open margin positions"""
    __tablename__ = 'margin_positions'

    id = db.Column(db.Integer, primary_key=True)
    margin_account_id = db.Column(db.Integer, db.ForeignKey('margin_accounts.id'), nullable=False)
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pairs.id'), nullable=False)

    side = db.Column(db.String(10), nullable=False)  # long, short
    entry_price = db.Column(db.Numeric(36, 18), nullable=False)
    current_price = db.Column(db.Numeric(36, 18), nullable=False)
    amount = db.Column(db.Numeric(36, 18), nullable=False)
    leverage = db.Column(db.Integer, default=1)

    # PnL
    unrealized_pnl = db.Column(db.Numeric(36, 18), default=Decimal('0'))
    realized_pnl = db.Column(db.Numeric(36, 18), default=Decimal('0'))

    # Liquidation
    liquidation_price = db.Column(db.Numeric(36, 18), nullable=False)
    is_liquidated = db.Column(db.Boolean, default=False)

    status = db.Column(db.String(20), default='open')  # open, closed, liquidated

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    trading_pair = db.relationship('TradingPair')

    def to_dict(self):
        return {
            'id': self.id,
            'trading_pair': self.trading_pair.symbol if self.trading_pair else None,
            'side': self.side,
            'entry_price': str(self.entry_price),
            'current_price': str(self.current_price),
            'amount': str(self.amount),
            'leverage': self.leverage,
            'unrealized_pnl': str(self.unrealized_pnl),
            'liquidation_price': str(self.liquidation_price),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Candle(db.Model):
    """OHLCV candlestick data"""
    __tablename__ = 'candles'

    id = db.Column(db.Integer, primary_key=True)
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pairs.id'), nullable=False)
    timeframe = db.Column(db.String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    timestamp = db.Column(db.DateTime, nullable=False)

    open = db.Column(db.Numeric(36, 18), nullable=False)
    high = db.Column(db.Numeric(36, 18), nullable=False)
    low = db.Column(db.Numeric(36, 18), nullable=False)
    close = db.Column(db.Numeric(36, 18), nullable=False)
    volume = db.Column(db.Numeric(36, 18), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('trading_pair_id', 'timeframe', 'timestamp', name='unique_candle'),
        db.Index('idx_candle_lookup', 'trading_pair_id', 'timeframe', 'timestamp'),
    )

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'open': str(self.open),
            'high': str(self.high),
            'low': str(self.low),
            'close': str(self.close),
            'volume': str(self.volume)
        }
