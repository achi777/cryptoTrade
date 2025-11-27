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
@limiter.limit("3/minute;10/hour")  # SECURITY: Prevent account enumeration
def register():
    """
    Register New User
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
              example: newuser@example.com
            password:
              type: string
              minLength: 8
              example: SecurePassword123
    responses:
      201:
        description: Registration successful
        schema:
          type: object
          properties:
            message:
              type: string
            user:
              type: object
      400:
        description: Invalid input
      409:
        description: Email already registered
    """
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
    user.verification_expires = datetime.utcnow() + timedelta(hours=24)

    db.session.add(user)
    db.session.flush()  # Get user ID

    # Create profile
    profile = UserProfile(user_id=user.id)
    db.session.add(profile)

    # Commit user and profile first
    db.session.commit()

    # Create wallets for all supported currencies after user is committed
    try:
        create_user_wallets(user.id)
    except Exception as e:
        current_app.logger.error(f"Failed to create wallets for user {user.id}: {e}")
        # Don't fail registration if wallet creation fails

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
@limiter.limit("5/minute;20/hour")  # SECURITY: Brute force protection
def login():
    """
    User Login
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: user@example.com
            password:
              type: string
              example: SecurePassword123
            totp_code:
              type: string
              example: "123456"
              description: Required if 2FA is enabled
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
            user:
              type: object
      401:
        description: Invalid credentials or 2FA required
      403:
        description: Account blocked or not verified
    """
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
    """
    Refresh Access Token
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: New access token generated
        schema:
          type: object
          properties:
            access_token:
              type: string
      401:
        description: Invalid or expired refresh token
    """
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200


@api_v1_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout User
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Successfully logged out
        schema:
          type: object
          properties:
            message:
              type: string
              example: Successfully logged out
      401:
        description: Unauthorized
    """
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
    """
    Verify User Email
    ---
    tags:
      - Authentication
    parameters:
      - name: token
        in: path
        required: true
        type: string
        description: Email verification token
    responses:
      200:
        description: Email verified successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Email verified successfully
      400:
        description: Invalid or expired verification token
    """
    user = User.query.filter_by(verification_token=token).first()

    if not user:
        return jsonify({'error': 'Invalid or expired verification token'}), 400

    # Check if token is expired
    if user.verification_expires and datetime.utcnow() > user.verification_expires:
        return jsonify({'error': 'Verification token has expired. Please request a new one.'}), 400

    user.is_verified = True
    user.verification_token = None
    user.verification_expires = None
    db.session.commit()

    return jsonify({'message': 'Email verified successfully'}), 200


@api_v1_bp.route('/auth/resend-verification', methods=['POST'])
@limiter.limit("3/hour")
def resend_verification():
    """
    Resend Verification Email
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              example: user@example.com
    responses:
      200:
        description: Verification link sent if email exists
        schema:
          type: object
          properties:
            message:
              type: string
              example: If the email exists, a verification link has been sent
      400:
        description: Email already verified
      429:
        description: Rate limit exceeded
    """
    data = request.get_json()
    email = data.get('email', '').lower().strip()

    user = User.query.filter_by(email=email).first()

    if not user:
        # Don't reveal if user exists
        return jsonify({'message': 'If the email exists, a verification link has been sent'}), 200

    if user.is_verified:
        return jsonify({'error': 'Email already verified'}), 400

    user.verification_token = secrets.token_urlsafe(32)
    user.verification_expires = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()

    try:
        send_verification_email(user.email, user.verification_token)
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {e}")

    return jsonify({'message': 'If the email exists, a verification link has been sent'}), 200


@api_v1_bp.route('/auth/forgot-password', methods=['POST'])
@limiter.limit("3/hour")
def forgot_password():
    """
    Send Password Reset Email
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              example: user@example.com
    responses:
      200:
        description: Password reset link sent if email exists
        schema:
          type: object
          properties:
            message:
              type: string
              example: If the email exists, a password reset link has been sent
      429:
        description: Rate limit exceeded
    """
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
    """
    Reset Password with Token
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - token
            - password
          properties:
            token:
              type: string
              description: Password reset token
            password:
              type: string
              minLength: 8
              example: NewPassword123
    responses:
      200:
        description: Password reset successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Password reset successfully
      400:
        description: Invalid/expired token or password too short
    """
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
    """
    Generate 2FA Secret and QR Code
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: 2FA setup initiated
        schema:
          type: object
          properties:
            secret:
              type: string
              example: JBSWY3DPEHPK3PXP
              description: Base32 encoded secret
            qr_code:
              type: string
              description: Base64 encoded QR code image
              example: data:image/png;base64,iVBORw0KG...
      400:
        description: 2FA is already enabled
      401:
        description: Unauthorized
    """
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
    """
    Verify and Enable 2FA
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - code
          properties:
            code:
              type: string
              example: "123456"
              description: 6-digit TOTP code
    responses:
      200:
        description: 2FA enabled successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: 2FA enabled successfully
      400:
        description: Code required or 2FA not setup
      401:
        description: Invalid code or unauthorized
    """
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
    """
    Disable 2FA
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - code
            - password
          properties:
            code:
              type: string
              example: "123456"
              description: Current 6-digit TOTP code
            password:
              type: string
              description: User password for confirmation
    responses:
      200:
        description: 2FA disabled successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: 2FA disabled successfully
      400:
        description: Code and password required or 2FA not enabled
      401:
        description: Invalid password or 2FA code
    """
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
