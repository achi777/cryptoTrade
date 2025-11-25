import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"postgresql://{os.getenv('DB_USER', 'cryptotrade')}:{os.getenv('DB_PASSWORD', 'cryptotrade_secret')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'cryptotrade')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000)))
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@cryptotrade.com')

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    RATELIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '100/hour')

    # Security
    BCRYPT_LOG_ROUNDS = int(os.getenv('BCRYPT_LOG_ROUNDS', 12))

    # Platform fees
    MAKER_FEE_PERCENT = float(os.getenv('MAKER_FEE_PERCENT', 0.1))
    TAKER_FEE_PERCENT = float(os.getenv('TAKER_FEE_PERCENT', 0.2))

    # Blockchain providers
    BTC_NODE_URL = os.getenv('BTC_NODE_URL', 'https://blockstream.info/api')
    ETH_NODE_URL = os.getenv('ETH_NODE_URL')
    TRX_NODE_URL = os.getenv('TRX_NODE_URL', 'https://api.trongrid.io')
    SOL_NODE_URL = os.getenv('SOL_NODE_URL', 'https://api.mainnet-beta.solana.com')
    LTC_NODE_URL = os.getenv('LTC_NODE_URL')
    DOGE_NODE_URL = os.getenv('DOGE_NODE_URL')
    XLM_NODE_URL = os.getenv('XLM_NODE_URL', 'https://horizon.stellar.org')


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

    # Stricter security in production
    JWT_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True


class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)
