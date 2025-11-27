from datetime import datetime
from app import db
import bcrypt
from app.utils.encryption import encrypt_data, decrypt_data


class User(db.Model):
    """User model for authentication and basic info"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    _two_factor_secret_encrypted = db.Column('two_factor_secret', db.String(255), nullable=True)  # Encrypted storage
    kyc_level = db.Column(db.Integer, default=0)  # 0, 1, 2, 3
    verification_token = db.Column(db.String(255), nullable=True)
    verification_expires = db.Column(db.DateTime, nullable=True)
    password_reset_token = db.Column(db.String(255), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    wallets = db.relationship('Wallet', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    balances = db.relationship('Balance', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    kyc_requests = db.relationship('KYCRequest', backref='user', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='KYCRequest.user_id')

    @property
    def two_factor_secret(self):
        """Decrypt and return 2FA secret"""
        if not self._two_factor_secret_encrypted:
            return None
        try:
            return decrypt_data(self._two_factor_secret_encrypted)
        except Exception:
            # If decryption fails (e.g., key changed), return None
            return None

    @two_factor_secret.setter
    def two_factor_secret(self, value):
        """Encrypt and store 2FA secret"""
        if value is None:
            self._two_factor_secret_encrypted = None
        else:
            self._two_factor_secret_encrypted = encrypt_data(value)

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')

    def check_password(self, password):
        """Verify password"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def to_dict(self):
        """Serialize user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'is_admin': self.is_admin,
            'two_factor_enabled': self.two_factor_enabled,
            'kyc_level': self.kyc_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'profile': self.profile.to_dict() if self.profile else None
        }


class UserProfile(db.Model):
    """Extended user profile information"""
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'country': self.country,
            'city': self.city,
            'address': self.address,
            'postal_code': self.postal_code,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None
        }


class TokenBlacklist(db.Model):
    """Blacklisted JWT tokens"""
    __tablename__ = 'token_blacklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
