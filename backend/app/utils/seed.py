"""
Database seed script - Initialize default data.
"""

from decimal import Decimal
from app import db
from app.models.wallet import Currency
from app.models.trading import TradingPair
from app.models.admin import SystemSetting, FeeConfig
from app.models.user import User


def seed_currencies():
    """Seed default currencies"""
    currencies = [
        {
            'symbol': 'BTC',
            'name': 'Bitcoin',
            'network': 'btc_mainnet',
            'decimals': 8,
            'is_token': False,
            'min_deposit': Decimal('0.0001'),
            'min_withdrawal': Decimal('0.001'),
            'withdrawal_fee': Decimal('0.0001'),
            'confirmations_required': 3
        },
        {
            'symbol': 'ETH',
            'name': 'Ethereum',
            'network': 'eth_mainnet',
            'decimals': 18,
            'is_token': False,
            'min_deposit': Decimal('0.001'),
            'min_withdrawal': Decimal('0.01'),
            'withdrawal_fee': Decimal('0.002'),
            'confirmations_required': 12
        },
        {
            'symbol': 'USDT',
            'name': 'Tether USD',
            'network': 'trx_mainnet',
            'contract_address': 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t',
            'decimals': 6,
            'is_token': True,
            'min_deposit': Decimal('1'),
            'min_withdrawal': Decimal('10'),
            'withdrawal_fee': Decimal('1'),
            'confirmations_required': 19
        },
        {
            'symbol': 'TRX',
            'name': 'Tron',
            'network': 'trx_mainnet',
            'decimals': 6,
            'is_token': False,
            'min_deposit': Decimal('1'),
            'min_withdrawal': Decimal('10'),
            'withdrawal_fee': Decimal('1'),
            'confirmations_required': 19
        },
        {
            'symbol': 'SOL',
            'name': 'Solana',
            'network': 'sol_mainnet',
            'decimals': 9,
            'is_token': False,
            'min_deposit': Decimal('0.01'),
            'min_withdrawal': Decimal('0.1'),
            'withdrawal_fee': Decimal('0.01'),
            'confirmations_required': 32
        },
        {
            'symbol': 'LTC',
            'name': 'Litecoin',
            'network': 'ltc_mainnet',
            'decimals': 8,
            'is_token': False,
            'min_deposit': Decimal('0.001'),
            'min_withdrawal': Decimal('0.01'),
            'withdrawal_fee': Decimal('0.001'),
            'confirmations_required': 6
        },
        {
            'symbol': 'DOGE',
            'name': 'Dogecoin',
            'network': 'doge_mainnet',
            'decimals': 8,
            'is_token': False,
            'min_deposit': Decimal('1'),
            'min_withdrawal': Decimal('10'),
            'withdrawal_fee': Decimal('1'),
            'confirmations_required': 6
        },
        {
            'symbol': 'XLM',
            'name': 'Stellar',
            'network': 'xlm_mainnet',
            'decimals': 7,
            'is_token': False,
            'min_deposit': Decimal('1'),
            'min_withdrawal': Decimal('10'),
            'withdrawal_fee': Decimal('0.1'),
            'confirmations_required': 1
        }
    ]

    for cur_data in currencies:
        existing = Currency.query.filter_by(symbol=cur_data['symbol']).first()
        if not existing:
            currency = Currency(**cur_data)
            db.session.add(currency)

    db.session.commit()
    print("Currencies seeded successfully")


def seed_trading_pairs():
    """Seed default trading pairs"""
    pairs = [
        ('BTC', 'USDT'),
        ('ETH', 'USDT'),
        ('SOL', 'USDT'),
        ('LTC', 'USDT'),
        ('DOGE', 'USDT'),
        ('XLM', 'USDT'),
        ('TRX', 'USDT'),
        ('ETH', 'BTC'),
        ('SOL', 'BTC'),
        ('LTC', 'BTC'),
    ]

    for base_symbol, quote_symbol in pairs:
        base = Currency.query.filter_by(symbol=base_symbol).first()
        quote = Currency.query.filter_by(symbol=quote_symbol).first()

        if not base or not quote:
            continue

        symbol = f'{base_symbol}_{quote_symbol}'
        existing = TradingPair.query.filter_by(symbol=symbol).first()

        if not existing:
            pair = TradingPair(
                symbol=symbol,
                base_currency_id=base.id,
                quote_currency_id=quote.id,
                is_active=True,
                min_order_size=Decimal('0.0001'),
                max_order_size=Decimal('1000000'),
                price_precision=8,
                amount_precision=8
            )
            db.session.add(pair)

    db.session.commit()
    print("Trading pairs seeded successfully")


def seed_fee_configs():
    """Seed default fee configurations"""
    fees = [
        {'fee_type': 'maker', 'value': Decimal('0.1'), 'is_percentage': True},
        {'fee_type': 'taker', 'value': Decimal('0.2'), 'is_percentage': True},
    ]

    for fee_data in fees:
        existing = FeeConfig.query.filter_by(
            fee_type=fee_data['fee_type'],
            currency_id=None,
            trading_pair_id=None
        ).first()

        if not existing:
            fee = FeeConfig(**fee_data, is_active=True)
            db.session.add(fee)

    db.session.commit()
    print("Fee configurations seeded successfully")


def seed_system_settings():
    """Seed default system settings"""
    settings = [
        {'key': 'maintenance_mode', 'value': 'false', 'value_type': 'bool', 'description': 'Enable maintenance mode'},
        {'key': 'registration_enabled', 'value': 'true', 'value_type': 'bool', 'description': 'Allow new user registration'},
        {'key': 'trading_enabled', 'value': 'true', 'value_type': 'bool', 'description': 'Enable trading'},
        {'key': 'withdrawals_enabled', 'value': 'true', 'value_type': 'bool', 'description': 'Enable withdrawals'},
        {'key': 'deposits_enabled', 'value': 'true', 'value_type': 'bool', 'description': 'Enable deposits'},
        {'key': 'kyc_required_for_withdrawal', 'value': 'true', 'value_type': 'bool', 'description': 'Require KYC for withdrawals'},
        {'key': 'min_withdrawal_kyc_level', 'value': '1', 'value_type': 'int', 'description': 'Minimum KYC level for withdrawal'},
        {'key': 'max_withdrawal_no_kyc', 'value': '100', 'value_type': 'float', 'description': 'Max withdrawal without KYC (USDT)'},
        {'key': 'platform_name', 'value': 'CryptoTrade', 'value_type': 'string', 'description': 'Platform name', 'is_public': True},
    ]

    for setting_data in settings:
        existing = SystemSetting.query.filter_by(key=setting_data['key']).first()
        if not existing:
            setting = SystemSetting(**setting_data)
            db.session.add(setting)

    db.session.commit()
    print("System settings seeded successfully")


def seed_admin_user():
    """Create default admin user"""
    admin_email = 'admin@cryptotrade.com'
    existing = User.query.filter_by(email=admin_email).first()

    if not existing:
        admin = User(
            email=admin_email,
            is_active=True,
            is_verified=True,
            is_admin=True,
            kyc_level=3
        )
        admin.set_password('admin123!@#')  # Change in production!
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {admin_email}")
    else:
        print("Admin user already exists")


def seed_all():
    """Run all seed functions"""
    print("Starting database seed...")
    seed_currencies()
    seed_trading_pairs()
    seed_fee_configs()
    seed_system_settings()
    seed_admin_user()
    print("Database seed completed!")


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_all()
