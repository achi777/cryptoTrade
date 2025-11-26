import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from redis import Redis

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO()
mail = Mail()
# NOTE: CSRF protection is handled by JWT bearer tokens (not cookies)
# JWT tokens in Authorization headers are not vulnerable to CSRF attacks
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "200 per minute"],
    headers_enabled=True,
    swallow_errors=True
)
redis_client = None


def validate_security_config(app):
    """
    Validate critical security configuration on startup
    Prevents running with weak/default secrets in production
    """
    # List of weak/default secrets to reject
    WEAK_SECRETS = [
        'dev-secret-key',
        'jwt-secret-key',
        'your-secret-key',
        'change-me',
        'changeme',
        'secret',
        '12345',
        'password'
    ]

    config = app.config
    flask_env = os.getenv('FLASK_ENV', 'production')

    # In production, enforce strong secrets
    if flask_env == 'production':
        # Check SECRET_KEY
        secret_key = config.get('SECRET_KEY', '')
        if not secret_key or len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        if secret_key.lower() in WEAK_SECRETS:
            raise ValueError("SECRET_KEY cannot use default/weak value in production")

        # Check JWT_SECRET_KEY
        jwt_secret = config.get('JWT_SECRET_KEY', '')
        if not jwt_secret or len(jwt_secret) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        if jwt_secret.lower() in WEAK_SECRETS:
            raise ValueError("JWT_SECRET_KEY cannot use default/weak value in production")

        # Check ENCRYPTION_KEY
        encryption_key = config.get('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY must be set in production")
        if len(encryption_key) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters in production")

    # In development, warn about weak secrets
    else:
        secret_key = config.get('SECRET_KEY', '')
        jwt_secret = config.get('JWT_SECRET_KEY', '')

        if secret_key.lower() in WEAK_SECRETS:
            app.logger.warning("⚠️  WARNING: Using weak SECRET_KEY in development. Change for production!")
        if jwt_secret.lower() in WEAK_SECRETS:
            app.logger.warning("⚠️  WARNING: Using weak JWT_SECRET_KEY in development. Change for production!")

        # Warn about missing ENCRYPTION_KEY in development
        if not config.get('ENCRYPTION_KEY'):
            app.logger.warning("⚠️  WARNING: ENCRYPTION_KEY not set. 2FA secret encryption will not work!")


def create_app(config_name=None):
    app = Flask(__name__)

    # Load config
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')

    # CRITICAL: Validate security configuration on startup
    validate_security_config(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Configure allowed origins from environment variable
    allowed_origins = app.config.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

    socketio.init_app(app, cors_allowed_origins=allowed_origins, async_mode='eventlet')
    mail.init_app(app)
    limiter.init_app(app)

    # Swagger API Documentation
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs"
    }

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "CryptoTrade API",
            "description": "Professional Cryptocurrency Trading Platform API",
            "version": "1.0.0",
            "contact": {
                "name": "CryptoTrade Support",
                "email": "support@cryptotrade.com"
            }
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer {token}'"
            }
        },
        "security": [
            {"Bearer": []}
        ],
        "schemes": ["http", "https"],
        "tags": [
            {"name": "Authentication", "description": "User authentication endpoints"},
            {"name": "User", "description": "User profile management"},
            {"name": "Wallet", "description": "Wallet and balance management"},
            {"name": "Trading", "description": "Trading and order management"},
            {"name": "Market", "description": "Market data and prices"},
            {"name": "KYC", "description": "Know Your Customer verification"}
        ]
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    # SECURE CORS configuration - NO wildcards in production
    CORS(app, resources={r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }})

    # Exempt OPTIONS requests from rate limiting
    @app.before_request
    def before_request():
        from flask import request
        if request.method == 'OPTIONS':
            return '', 200

    # Initialize Redis
    global redis_client
    redis_client = Redis.from_url(app.config.get('REDIS_URL', 'redis://localhost:6379/0'))

    # Register blueprints
    from app.api.v1 import api_v1_bp
    from app.api.admin import admin_bp

    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Register error handlers
    register_error_handlers(app)

    # Register JWT callbacks
    register_jwt_callbacks(app)

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'cryptotrade-api'}

    # CLI commands
    @app.cli.command('seed')
    def seed_command():
        """Seed the database with initial data."""
        from app.utils.seed import seed_all
        seed_all()

    return app


def register_error_handlers(app):
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request', 'message': str(error)}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({'error': 'Rate limit exceeded', 'message': 'Too many requests'}), 429

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500


def register_jwt_callbacks(app):
    from app.models.user import User, TokenBlacklist

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        token = db.session.query(TokenBlacklist).filter_by(jti=jti).first()
        return token is not None

    @jwt.user_lookup_loader
    def user_lookup_callback(jwt_header, jwt_payload):
        identity = jwt_payload['sub']
        return User.query.get(identity)
