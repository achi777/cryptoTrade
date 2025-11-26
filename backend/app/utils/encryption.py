"""
Encryption utilities for sensitive data
"""
from cryptography.fernet import Fernet
from flask import current_app


def get_fernet():
    """Get Fernet instance with encryption key from config"""
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        # In development, generate a temporary key (WARNING: not persistent!)
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        current_app.logger.warning("⚠️  WARNING: Using temporary ENCRYPTION_KEY. Set ENCRYPTION_KEY in .env!")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_data(plaintext: str) -> str:
    """
    Encrypt plaintext data using Fernet symmetric encryption

    Args:
        plaintext: String to encrypt

    Returns:
        Base64-encoded encrypted string
    """
    if not plaintext:
        return None

    f = get_fernet()
    encrypted = f.encrypt(plaintext.encode())
    return encrypted.decode()


def decrypt_data(ciphertext: str) -> str:
    """
    Decrypt ciphertext data using Fernet symmetric encryption

    Args:
        ciphertext: Base64-encoded encrypted string

    Returns:
        Decrypted plaintext string
    """
    if not ciphertext:
        return None

    f = get_fernet()
    decrypted = f.decrypt(ciphertext.encode())
    return decrypted.decode()
