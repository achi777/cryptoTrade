from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from app.api.v1 import api_v1_bp
from app import db
from app.models.user import User
from app.models.kyc import KYCRequest, KYCDocument
from app.utils.file_validation import validate_file_upload, sanitize_filename, FileValidationError


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
UPLOAD_FOLDER = '/app/uploads/kyc'


def allowed_file(filename):
    """Legacy function - kept for backward compatibility"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_v1_bp.route('/kyc/basic-info', methods=['POST'])
@jwt_required()
def submit_basic_info():
    """
    Submit Level 1 KYC - Basic Information
    ---
    tags:
      - KYC
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - firstName
            - lastName
            - dateOfBirth
            - nationality
          properties:
            firstName:
              type: string
              example: John
            lastName:
              type: string
              example: Doe
            dateOfBirth:
              type: string
              format: date
              example: "1990-01-01"
            nationality:
              type: string
              example: USA
    responses:
      200:
        description: Basic information submitted and auto-approved
        schema:
          type: object
          properties:
            message:
              type: string
            submission:
              type: object
      400:
        description: Level 1 already approved
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()

    # Check if already submitted
    existing = KYCRequest.query.filter_by(
        user_id=user_id,
        level=1
    ).first()

    if existing and existing.status == 'approved':
        return jsonify({'error': 'Level 1 KYC already approved'}), 400

    # Create or update request
    if existing:
        request_obj = existing
        request_obj.status = 'pending'
    else:
        request_obj = KYCRequest(
            user_id=user_id,
            level=1,
            status='pending'
        )
        db.session.add(request_obj)

    # Update request data
    request_obj.first_name = data.get('firstName')
    request_obj.last_name = data.get('lastName')
    request_obj.date_of_birth = datetime.strptime(data.get('dateOfBirth'), '%Y-%m-%d').date() if data.get('dateOfBirth') else None
    request_obj.nationality = data.get('nationality')

    # Auto-approve Level 1 (basic info doesn't need manual review)
    request_obj.status = 'approved'
    request_obj.reviewed_at = datetime.utcnow()
    user.kyc_level = 1

    db.session.commit()

    return jsonify({
        'message': 'Basic information submitted successfully',
        'submission': request_obj.to_dict()
    }), 200


@api_v1_bp.route('/kyc/id-verification', methods=['POST'])
@jwt_required()
def submit_id_verification():
    """
    Submit Level 2 KYC - ID Verification
    ---
    tags:
      - KYC
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: id_type
        in: formData
        type: string
        required: true
        description: Type of ID document
        example: passport
      - name: id_number
        in: formData
        type: string
        required: true
        description: ID document number
        example: A12345678
      - name: id_front
        in: formData
        type: file
        required: true
        description: Front side of ID document
      - name: id_back
        in: formData
        type: file
        description: Back side of ID document (if applicable)
      - name: selfie
        in: formData
        type: file
        description: Selfie with ID document
    responses:
      200:
        description: ID verification submitted for review
        schema:
          type: object
          properties:
            message:
              type: string
            submission:
              type: object
            files_uploaded:
              type: array
              items:
                type: string
      400:
        description: Level 1 not completed, already approved, or invalid files
      401:
        description: Unauthorized
      500:
        description: File processing error
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if user.kyc_level < 1:
        return jsonify({'error': 'Please complete Level 1 KYC first'}), 400

    # Get form data
    id_type = request.form.get('id_type')
    id_number = request.form.get('id_number')

    if not id_type or not id_number:
        return jsonify({'error': 'ID type and number are required'}), 400

    # Check if already submitted
    existing = KYCRequest.query.filter_by(
        user_id=user_id,
        level=2
    ).first()

    if existing and existing.status == 'approved':
        return jsonify({'error': 'Level 2 KYC already approved'}), 400

    # Create upload folder if not exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Create or update request
    if existing:
        request_obj = existing
        request_obj.status = 'pending'
    else:
        request_obj = KYCRequest(
            user_id=user_id,
            level=2,
            status='pending'
        )
        db.session.add(request_obj)

    request_obj.document_number = id_number

    # Commit to get request_obj.id before creating documents
    db.session.commit()

    # Handle file uploads
    files_uploaded = []

    if 'id_front' in request.files:
        file = request.files['id_front']
        if file and file.filename:
            try:
                # SECURITY: Comprehensive file validation
                validation_result = validate_file_upload(file, 'id')
                filename = sanitize_filename(file.filename, user_id, 'id_front')
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)

                doc = KYCDocument(
                    kyc_request_id=request_obj.id,
                    document_type='id_front',
                    file_path=filepath,
                    file_name=filename
                )
                db.session.add(doc)
                files_uploaded.append('id_front')
            except FileValidationError as e:
                return jsonify({'error': f'ID front validation failed: {str(e)}'}), 400
            except Exception as e:
                current_app.logger.error(f"File upload error: {e}")
                return jsonify({'error': 'Failed to process ID front image'}), 500

    if 'id_back' in request.files:
        file = request.files['id_back']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{user_id}_id_back_{datetime.utcnow().timestamp()}.{file.filename.rsplit('.', 1)[1]}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            doc = KYCDocument(
                kyc_request_id=request_obj.id,
                document_type='id_back',
                file_path=filepath,
                file_name=filename
            )
            db.session.add(doc)
            files_uploaded.append('id_back')

    if 'selfie' in request.files:
        file = request.files['selfie']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{user_id}_selfie_{datetime.utcnow().timestamp()}.{file.filename.rsplit('.', 1)[1]}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            doc = KYCDocument(
                kyc_request_id=request_obj.id,
                document_type='selfie',
                file_path=filepath,
                file_name=filename
            )
            db.session.add(doc)
            files_uploaded.append('selfie')

    if not files_uploaded:
        return jsonify({'error': 'No valid files uploaded'}), 400

    db.session.commit()

    return jsonify({
        'message': 'ID verification submitted for review',
        'submission': request_obj.to_dict(),
        'files_uploaded': files_uploaded
    }), 200


@api_v1_bp.route('/kyc/address-verification', methods=['POST'])
@jwt_required()
def submit_address_verification():
    """
    Submit Level 3 KYC - Address Verification
    ---
    tags:
      - KYC
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: address
        in: formData
        type: string
        required: true
        example: "123 Main Street"
      - name: city
        in: formData
        type: string
        required: true
        example: "New York"
      - name: postal_code
        in: formData
        type: string
        required: true
        example: "10001"
      - name: country
        in: formData
        type: string
        required: true
        example: USA
      - name: proof_document
        in: formData
        type: file
        required: true
        description: Proof of address document (utility bill, bank statement, etc.)
    responses:
      200:
        description: Address verification submitted for review
        schema:
          type: object
          properties:
            message:
              type: string
            submission:
              type: object
      400:
        description: Level 2 not completed, already approved, or missing fields
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if user.kyc_level < 2:
        return jsonify({'error': 'Please complete Level 2 KYC first'}), 400

    # Get form data
    address = request.form.get('address')
    city = request.form.get('city')
    postal_code = request.form.get('postal_code')
    country = request.form.get('country')

    if not all([address, city, postal_code, country]):
        return jsonify({'error': 'All address fields are required'}), 400

    # Check if already submitted
    existing = KYCRequest.query.filter_by(
        user_id=user_id,
        level=3
    ).first()

    if existing and existing.status == 'approved':
        return jsonify({'error': 'Level 3 KYC already approved'}), 400

    # Create upload folder if not exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Create or update request
    if existing:
        request_obj = existing
        request_obj.status = 'pending'
    else:
        request_obj = KYCRequest(
            user_id=user_id,
            level=3,
            status='pending'
        )
        db.session.add(request_obj)

    request_obj.address = address
    request_obj.city = city
    request_obj.postal_code = postal_code
    request_obj.country = country

    # Commit to get request_obj.id before creating documents
    db.session.commit()

    # Handle proof document upload
    if 'proof_document' not in request.files:
        return jsonify({'error': 'Proof of address document is required'}), 400

    file = request.files['proof_document']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format'}), 400

    filename = secure_filename(f"{user_id}_address_proof_{datetime.utcnow().timestamp()}.{file.filename.rsplit('.', 1)[1]}")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    doc = KYCDocument(
        kyc_request_id=request_obj.id,
        document_type='address_proof',
        file_path=filepath,
        file_name=filename
    )
    db.session.add(doc)

    db.session.commit()

    return jsonify({
        'message': 'Address verification submitted for review',
        'submission': request_obj.to_dict()
    }), 200


@api_v1_bp.route('/kyc/status', methods=['GET'])
@jwt_required()
def get_kyc_status():
    """
    Get User's KYC Status
    ---
    tags:
      - KYC
    security:
      - Bearer: []
    responses:
      200:
        description: User's KYC status and requests
        schema:
          type: object
          properties:
            current_level:
              type: integer
              example: 1
              description: Current KYC level (0-3)
            requests:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  level:
                    type: integer
                  status:
                    type: string
                    enum: [pending, approved, rejected]
                  created_at:
                    type: string
                    format: date-time
                  reviewed_at:
                    type: string
                    format: date-time
                    nullable: true
      401:
        description: Unauthorized
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    requests = KYCRequest.query.filter_by(user_id=user_id).all()

    return jsonify({
        'current_level': user.kyc_level,
        'requests': [r.to_dict() for r in requests]
    }), 200
