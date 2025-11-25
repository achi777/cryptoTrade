from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from app.api.v1 import api_v1_bp
from app import db
from app.models.user import User, UserProfile
from app.models.kyc import KYCRequest, KYCDocument, KYCStatus
from app.models.balance import Balance


@api_v1_bp.route('/user/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user.to_dict()}), 200


@api_v1_bp.route('/user/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if not user.profile:
        user.profile = UserProfile(user_id=user.id)

    profile = user.profile

    # Update allowed fields
    allowed_fields = ['first_name', 'last_name', 'phone', 'country', 'city', 'address', 'postal_code']
    for field in allowed_fields:
        if field in data:
            setattr(profile, field, data[field])

    if 'date_of_birth' in data and data['date_of_birth']:
        try:
            profile.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    db.session.commit()

    return jsonify({'user': user.to_dict()}), 200


@api_v1_bp.route('/user/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password are required'}), 400

    if not user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401

    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'message': 'Password changed successfully'}), 200


@api_v1_bp.route('/user/balances', methods=['GET'])
@jwt_required()
def get_balances():
    """Get user balances for all currencies"""
    user_id = get_jwt_identity()
    balances = Balance.query.filter_by(user_id=user_id).all()

    return jsonify({
        'balances': [b.to_dict() for b in balances]
    }), 200


@api_v1_bp.route('/user/kyc', methods=['GET'])
@jwt_required()
def get_user_kyc_status():
    """Get current KYC status"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    latest_request = KYCRequest.query.filter_by(user_id=user_id).order_by(KYCRequest.created_at.desc()).first()

    return jsonify({
        'kyc_level': user.kyc_level,
        'latest_request': latest_request.to_dict() if latest_request else None
    }), 200


@api_v1_bp.route('/user/kyc/submit', methods=['POST'])
@jwt_required()
def submit_kyc():
    """Submit KYC verification request"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # Check if there's a pending request
    pending = KYCRequest.query.filter_by(
        user_id=user_id,
        status=KYCStatus.PENDING.value
    ).first()

    if pending:
        return jsonify({'error': 'You already have a pending KYC request'}), 400

    data = request.form.to_dict()
    target_level = int(data.get('level', user.kyc_level + 1))

    if target_level <= user.kyc_level:
        return jsonify({'error': 'Cannot request verification for current or lower level'}), 400

    # Create KYC request
    kyc_request = KYCRequest(
        user_id=user_id,
        level=target_level,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
        nationality=data.get('nationality'),
        document_number=data.get('document_number'),
        address=data.get('address'),
        city=data.get('city'),
        country=data.get('country'),
        postal_code=data.get('postal_code')
    )

    db.session.add(kyc_request)
    db.session.flush()

    # Handle document uploads
    files = request.files
    for key, file in files.items():
        if file and file.filename:
            # In production, upload to S3/cloud storage
            # For now, save locally
            import os
            upload_dir = f'uploads/kyc/{user_id}'
            os.makedirs(upload_dir, exist_ok=True)
            filename = f'{kyc_request.id}_{key}_{file.filename}'
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)

            doc = KYCDocument(
                kyc_request_id=kyc_request.id,
                document_type=key,
                file_path=file_path,
                file_name=file.filename,
                mime_type=file.content_type
            )
            db.session.add(doc)

    db.session.commit()

    return jsonify({
        'message': 'KYC request submitted successfully',
        'request': kyc_request.to_dict()
    }), 201


@api_v1_bp.route('/user/activity', methods=['GET'])
@jwt_required()
def get_activity():
    """Get user activity/login history"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # In a full implementation, you'd have a login_history table
    return jsonify({
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'last_login_ip': user.last_login_ip
    }), 200
