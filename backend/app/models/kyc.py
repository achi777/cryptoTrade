from datetime import datetime
from enum import Enum
from app import db


class KYCStatus(str, Enum):
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class DocumentType(str, Enum):
    PASSPORT = 'passport'
    ID_CARD = 'id_card'
    DRIVERS_LICENSE = 'drivers_license'
    SELFIE = 'selfie'
    PROOF_OF_ADDRESS = 'proof_of_address'


class KYCRequest(db.Model):
    """KYC verification request"""
    __tablename__ = 'kyc_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # Target KYC level (1, 2, 3)
    status = db.Column(db.String(20), default=KYCStatus.PENDING.value)

    # Personal info submitted
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    nationality = db.Column(db.String(100), nullable=True)
    document_number = db.Column(db.String(100), nullable=True)
    document_expiry = db.Column(db.Date, nullable=True)

    # Address info
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)

    # Admin review
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = db.relationship('KYCDocument', backref='kyc_request', lazy='dynamic', cascade='all, delete-orphan')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'level': self.level,
            'status': self.status,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'nationality': self.nationality,
            'document_number': self.document_number,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'documents': [doc.to_dict() for doc in self.documents]
        }


class KYCDocument(db.Model):
    """KYC document uploads"""
    __tablename__ = 'kyc_documents'

    id = db.Column(db.Integer, primary_key=True)
    kyc_request_id = db.Column(db.Integer, db.ForeignKey('kyc_requests.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'document_type': self.document_type,
            'file_name': self.file_name,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
