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
from redis import Redis

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    headers_enabled=True,
    swallow_errors=True
)
redis_client = None


def create_app(config_name=None):
    app = Flask(__name__)

    # Load config
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')
    mail.init_app(app)
    limiter.init_app(app)
    CORS(app, resources={r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
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
