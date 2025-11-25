"""Admin KYC Management API"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from datetime import datetime

from app.api.admin import admin_bp
from app.api.admin.users import admin_required, log_admin_action
from app import db
from app.models.user import User
from app.models.kyc import KYCRequest, KYCDocument, KYCStatus
from app.services.email_service import send_kyc_approved, send_kyc_rejected


@admin_bp.route('/kyc/requests', methods=['GET'])
@admin_required
def get_kyc_requests():
    """Get KYC verification requests"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    level = request.args.get('level', type=int)

    query = KYCRequest.query

    if status:
        query = query.filter_by(status=status)
    if level:
        query = query.filter_by(level=level)

    requests = query.order_by(KYCRequest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'requests': [r.to_dict() for r in requests.items],
        'total': requests.total,
        'pages': requests.pages,
        'current_page': page
    }), 200


@admin_bp.route('/kyc/requests/pending', methods=['GET'])
@admin_required
def get_pending_kyc():
    """Get pending KYC requests"""
    requests = KYCRequest.query.filter_by(status=KYCStatus.PENDING.value).order_by(
        KYCRequest.created_at.asc()
    ).all()

    return jsonify({
        'requests': [r.to_dict() for r in requests],
        'count': len(requests)
    }), 200


@admin_bp.route('/kyc/requests/<int:request_id>', methods=['GET'])
@admin_required
def get_kyc_request(request_id):
    """Get KYC request details"""
    kyc_request = KYCRequest.query.get(request_id)
    if not kyc_request:
        return jsonify({'error': 'KYC request not found'}), 404

    user = User.query.get(kyc_request.user_id)

    return jsonify({
        'request': kyc_request.to_dict(),
        'user': user.to_dict() if user else None,
        'documents': [d.to_dict() for d in kyc_request.documents]
    }), 200


@admin_bp.route('/kyc/requests/<int:request_id>/approve', methods=['POST'])
@admin_required
def approve_kyc(request_id):
    """Approve KYC request"""
    admin_id = get_jwt_identity()
    kyc_request = KYCRequest.query.get(request_id)

    if not kyc_request:
        return jsonify({'error': 'KYC request not found'}), 404

    if kyc_request.status != KYCStatus.PENDING.value:
        return jsonify({'error': 'Can only approve pending requests'}), 400

    data = request.get_json() or {}
    notes = data.get('notes', '')

    # Update KYC request
    old_status = kyc_request.status
    kyc_request.status = KYCStatus.APPROVED.value
    kyc_request.reviewed_by = admin_id
    kyc_request.reviewed_at = datetime.utcnow()
    kyc_request.admin_notes = notes

    # Update user KYC level
    user = User.query.get(kyc_request.user_id)
    old_level = user.kyc_level
    user.kyc_level = kyc_request.level

    # Update user profile with KYC data
    if user.profile:
        if kyc_request.first_name:
            user.profile.first_name = kyc_request.first_name
        if kyc_request.last_name:
            user.profile.last_name = kyc_request.last_name
        if kyc_request.date_of_birth:
            user.profile.date_of_birth = kyc_request.date_of_birth
        if kyc_request.country:
            user.profile.country = kyc_request.country

    log_admin_action(
        admin_id=admin_id,
        action='approve_kyc',
        entity_type='kyc',
        entity_id=request_id,
        old_value={'status': old_status, 'kyc_level': old_level},
        new_value={'status': KYCStatus.APPROVED.value, 'kyc_level': kyc_request.level},
        note=notes
    )

    db.session.commit()

    # Send notification email
    try:
        send_kyc_approved(user.email, kyc_request.level)
    except Exception:
        pass

    return jsonify({
        'message': 'KYC request approved',
        'request': kyc_request.to_dict()
    }), 200


@admin_bp.route('/kyc/requests/<int:request_id>/reject', methods=['POST'])
@admin_required
def reject_kyc(request_id):
    """Reject KYC request"""
    admin_id = get_jwt_identity()
    kyc_request = KYCRequest.query.get(request_id)

    if not kyc_request:
        return jsonify({'error': 'KYC request not found'}), 404

    if kyc_request.status != KYCStatus.PENDING.value:
        return jsonify({'error': 'Can only reject pending requests'}), 400

    data = request.get_json()
    reason = data.get('reason', '')

    if not reason:
        return jsonify({'error': 'Rejection reason is required'}), 400

    old_status = kyc_request.status
    kyc_request.status = KYCStatus.REJECTED.value
    kyc_request.reviewed_by = admin_id
    kyc_request.reviewed_at = datetime.utcnow()
    kyc_request.rejection_reason = reason

    log_admin_action(
        admin_id=admin_id,
        action='reject_kyc',
        entity_type='kyc',
        entity_id=request_id,
        old_value={'status': old_status},
        new_value={'status': KYCStatus.REJECTED.value},
        note=reason
    )

    db.session.commit()

    # Send notification email
    user = User.query.get(kyc_request.user_id)
    try:
        send_kyc_rejected(user.email, reason)
    except Exception:
        pass

    return jsonify({
        'message': 'KYC request rejected',
        'request': kyc_request.to_dict()
    }), 200


@admin_bp.route('/kyc/documents/<int:document_id>', methods=['GET'])
@admin_required
def get_kyc_document(document_id):
    """Get KYC document file"""
    document = KYCDocument.query.get(document_id)
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    # In production, return a signed URL to cloud storage
    # For now, return file path info
    return jsonify({
        'document': document.to_dict(),
        'file_path': document.file_path
    }), 200


@admin_bp.route('/kyc/stats', methods=['GET'])
@admin_required
def get_kyc_stats():
    """Get KYC statistics"""
    pending = KYCRequest.query.filter_by(status=KYCStatus.PENDING.value).count()
    approved = KYCRequest.query.filter_by(status=KYCStatus.APPROVED.value).count()
    rejected = KYCRequest.query.filter_by(status=KYCStatus.REJECTED.value).count()

    # Users by KYC level
    level_0 = User.query.filter_by(kyc_level=0).count()
    level_1 = User.query.filter_by(kyc_level=1).count()
    level_2 = User.query.filter_by(kyc_level=2).count()

    return jsonify({
        'requests': {
            'pending': pending,
            'approved': approved,
            'rejected': rejected
        },
        'users_by_level': {
            'level_0': level_0,
            'level_1': level_1,
            'level_2': level_2
        }
    }), 200
