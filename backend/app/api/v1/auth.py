from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt
)
from datetime import datetime, timedelta
import secrets
import pyotp
import qrcode
import io
import base64

from app.api.v1 import api_v1_bp
from app import db, limiter
from app.models.user import User, UserProfile, TokenBlacklist
from app.services.email_service import send_verification_email, send_password_reset_email
from app.services.wallet_service import create_user_wallets


@api_v1_bp.route('/auth/register', methods=['POST'])
@limiter.limit("5/minute")
def register():
    """Register a new user"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').lower().strip()
    password = data.get('password', '')

    # Validation
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    # Create user
    user = User(email=email)
    user.set_password(password)
    user.verification_token = secrets.token_urlsafe(32)

    db.session.add(user)
    db.session.flush()  # Get user ID

    # Create profile
    profile = UserProfile(user_id=user.id)
    db.session.add(profile)

    # Create wallets for all supported currencies
    try:
        create_user_wallets(user.id)
    except Exception as e:
        current_app.logger.error(f"Failed to create wallets for user {user.id}: {e}")

    db.session.commit()

    # Send verification email
    try:
        send_verification_email(user.email, user.verification_token)
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {e}")

    return jsonify({
        'message': 'Registration successful. Please check your email to verify your account.',
        'user': user.to_dict()
    }), 201


@api_v1_bp.route('/auth/login', methods=['POST'])
@limiter.limit("5/minute")
def login():
    """Login user and return JWT tokens"""
    data = request.get_json()

    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    totp_code = data.get('totp_code')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if user.is_blocked:
        return jsonify({'error': 'Account is blocked. Please contact support.'}), 403

    if not user.is_verified:
        return jsonify({'error': 'Please verify your email first'}), 403

    # Check 2FA if enabled
    if user.two_factor_enabled:
        if not totp_code:
            return jsonify({'error': '2FA code required', 'requires_2fa': True}), 401

        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(totp_code):
            return jsonify({'error': 'Invalid 2FA code'}), 401

    # Update last login
    user.last_login = datetime.utcnow()
    user.last_login_ip = request.remote_addr
    db.session.commit()

    # Create tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200


@api_v1_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200


@api_v1_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user by blacklisting token"""
    jwt_data = get_jwt()
    jti = jwt_data['jti']
    token_type = jwt_data['type']
    user_id = get_jwt_identity()
    expires = datetime.fromtimestamp(jwt_data['exp'])

    blacklist = TokenBlacklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires_at=expires
    )
    db.session.add(blacklist)
    db.session.commit()

    return jsonify({'message': 'Successfully logged out'}), 200


@api_v1_bp.route('/auth/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """Verify user email"""
    user = User.query.filter_by(verification_token=token).first()

    if not user:
        return jsonify({'error': 'Invalid or expired verification token'}), 400

    user.is_verified = True
    user.verification_token = None
    db.session.commit()

    return jsonify({'message': 'Email verified successfully'}), 200


@api_v1_bp.route('/auth/resend-verification', methods=['POST'])
@limiter.limit("3/hour")
def resend_verification():
    """Resend verification email"""
    data = request.get_json()
    email = data.get('email', '').lower().strip()

    user = User.query.filter_by(email=email).first()

    if not user:
        # Don't reveal if user exists
        return jsonify({'message': 'If the email exists, a verification link has been sent'}), 200

    if user.is_verified:
        return jsonify({'error': 'Email already verified'}), 400

    user.verification_token = secrets.token_urlsafe(32)
    db.session.commit()

    try:
        send_verification_email(user.email, user.verification_token)
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {e}")

    return jsonify({'message': 'If the email exists, a verification link has been sent'}), 200


@api_v1_bp.route('/auth/forgot-password', methods=['POST'])
@limiter.limit("3/hour")
def forgot_password():
    """Send password reset email"""
    data = request.get_json()
    email = data.get('email', '').lower().strip()

    user = User.query.filter_by(email=email).first()

    if user and user.is_verified:
        user.password_reset_token = secrets.token_urlsafe(32)
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        try:
            send_password_reset_email(user.email, user.password_reset_token)
        except Exception as e:
            current_app.logger.error(f"Failed to send password reset email: {e}")

    return jsonify({'message': 'If the email exists, a password reset link has been sent'}), 200


@api_v1_bp.route('/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')

    if not token or not new_password:
        return jsonify({'error': 'Token and password are required'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    user = User.query.filter_by(password_reset_token=token).first()

    if not user or not user.password_reset_expires:
        return jsonify({'error': 'Invalid or expired reset token'}), 400

    if datetime.utcnow() > user.password_reset_expires:
        return jsonify({'error': 'Reset token has expired'}), 400

    user.set_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.session.commit()

    return jsonify({'message': 'Password reset successfully'}), 200


@api_v1_bp.route('/auth/2fa/setup', methods=['POST'])
@jwt_required()
def setup_2fa():
    """Generate 2FA secret and QR code"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if user.two_factor_enabled:
        return jsonify({'error': '2FA is already enabled'}), 400

    # Generate secret
    secret = pyotp.random_base32()
    user.two_factor_secret = secret
    db.session.commit()

    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name='CryptoTrade'
    )

    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({
        'secret': secret,
        'qr_code': f'data:image/png;base64,{qr_base64}'
    }), 200


@api_v1_bp.route('/auth/2fa/verify', methods=['POST'])
@jwt_required()
def verify_2fa():
    """Verify and enable 2FA"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    data = request.get_json()
    code = data.get('code')

    if not code:
        return jsonify({'error': 'Code is required'}), 400

    if not user.two_factor_secret:
        return jsonify({'error': 'Please setup 2FA first'}), 400

    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(code):
        return jsonify({'error': 'Invalid code'}), 400

    user.two_factor_enabled = True
    db.session.commit()

    return jsonify({'message': '2FA enabled successfully'}), 200


@api_v1_bp.route('/auth/2fa/disable', methods=['POST'])
@jwt_required()
def disable_2fa():
    """Disable 2FA"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    data = request.get_json()
    code = data.get('code')
    password = data.get('password')

    if not code or not password:
        return jsonify({'error': 'Code and password are required'}), 400

    if not user.check_password(password):
        return jsonify({'error': 'Invalid password'}), 401

    if not user.two_factor_enabled:
        return jsonify({'error': '2FA is not enabled'}), 400

    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(code):
        return jsonify({'error': 'Invalid 2FA code'}), 401

    user.two_factor_enabled = False
    user.two_factor_secret = None
    db.session.commit()

    return jsonify({'message': '2FA disabled successfully'}), 200
