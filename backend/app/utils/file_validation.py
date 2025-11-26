"""
File upload validation utilities
"""
import os
try:
    import magic  # python-magic for MIME type detection
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
from PIL import Image
from werkzeug.datastructures import FileStorage


# Allowed file types
ALLOWED_IMAGE_MIME_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png'
}

ALLOWED_DOCUMENT_MIME_TYPES = {
    'application/pdf'
}

ALLOWED_MIME_TYPES = ALLOWED_IMAGE_MIME_TYPES | ALLOWED_DOCUMENT_MIME_TYPES

# File size limits (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PDF_SIZE = 15 * 1024 * 1024    # 15 MB

# Image dimension limits
MAX_IMAGE_WIDTH = 8000
MAX_IMAGE_HEIGHT = 8000
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 200


class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    pass


def validate_file_upload(file: FileStorage, file_purpose: str = 'document') -> dict:
    """
    Comprehensive file validation for uploads

    Args:
        file: The uploaded file object
        file_purpose: Purpose of file ('document', 'id', 'selfie', 'address_proof')

    Returns:
        dict with validation results

    Raises:
        FileValidationError: If file is invalid
    """
    if not file or not file.filename:
        raise FileValidationError("No file provided")

    # 1. Check filename
    if len(file.filename) > 255:
        raise FileValidationError("Filename too long")

    filename = file.filename.lower()

    # 2. Check file extension
    if '.' not in filename:
        raise FileValidationError("File must have an extension")

    extension = filename.rsplit('.', 1)[1]
    allowed_extensions = {'jpg', 'jpeg', 'png', 'pdf'}

    if extension not in allowed_extensions:
        raise FileValidationError(f"File extension '{extension}' not allowed. Allowed: {', '.join(allowed_extensions)}")

    # 3. Check file size before reading
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size == 0:
        raise FileValidationError("File is empty")

    max_size = MAX_PDF_SIZE if extension == 'pdf' else MAX_IMAGE_SIZE

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise FileValidationError(f"File too large. Maximum size: {max_mb}MB")

    # 4. Verify MIME type (prevents extension spoofing)
    if HAS_MAGIC:
        try:
            file_content = file.read(2048)  # Read first 2KB for MIME detection
            file.seek(0)  # Reset

            mime = magic.from_buffer(file_content, mime=True)

            if mime not in ALLOWED_MIME_TYPES:
                raise FileValidationError(f"File type '{mime}' not allowed")

            # Verify MIME matches extension
            if extension in ['jpg', 'jpeg']:
                if mime not in ['image/jpeg', 'image/jpg']:
                    raise FileValidationError("File extension doesn't match file content")
            elif extension == 'png':
                if mime != 'image/png':
                    raise FileValidationError("File extension doesn't match file content")
            elif extension == 'pdf':
                if mime != 'application/pdf':
                    raise FileValidationError("File extension doesn't match file content")

        except Exception as e:
            raise FileValidationError(f"Failed to detect file type: {str(e)}")
    else:
        # Fallback when python-magic is not available
        mime = f'image/{extension}' if extension in ['jpg', 'jpeg', 'png'] else 'application/pdf'

    # 5. Additional validation for images
    if extension in ['jpg', 'jpeg', 'png']:
        try:
            file.seek(0)
            img = Image.open(file)

            # Verify it's actually a valid image
            img.verify()

            # Re-open after verify (verify closes the image)
            file.seek(0)
            img = Image.open(file)

            width, height = img.size

            # Check dimensions
            if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
                raise FileValidationError(f"Image too large. Maximum dimensions: {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}")

            if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                raise FileValidationError(f"Image too small. Minimum dimensions: {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}")

            # Check for suspicious metadata that could indicate steganography
            # (basic check - more advanced checks would require specialized libraries)
            if hasattr(img, '_getexif') and img._getexif():
                exif_data = img._getexif()
                # Basic validation - could be extended
                if len(str(exif_data)) > 10000:  # Unusually large EXIF
                    raise FileValidationError("Image metadata appears suspicious")

            file.seek(0)  # Reset for actual save

            return {
                'valid': True,
                'mime_type': mime,
                'extension': extension,
                'size': file_size,
                'dimensions': (width, height)
            }

        except FileValidationError:
            raise
        except Exception as e:
            raise FileValidationError(f"Invalid image file: {str(e)}")

    # 6. Additional validation for PDFs
    elif extension == 'pdf':
        file.seek(0)
        # Basic PDF validation - check magic bytes
        header = file.read(5)
        file.seek(0)

        if header != b'%PDF-':
            raise FileValidationError("Invalid PDF file")

        return {
            'valid': True,
            'mime_type': mime,
            'extension': extension,
            'size': file_size
        }

    return {
        'valid': True,
        'mime_type': mime,
        'extension': extension,
        'size': file_size
    }


def sanitize_filename(filename: str, user_id: int, purpose: str) -> str:
    """
    Generate a safe, unique filename

    Args:
        filename: Original filename
        user_id: User ID
        purpose: File purpose (e.g., 'id_front', 'selfie')

    Returns:
        Sanitized filename
    """
    from datetime import datetime
    import secrets

    # Extract extension
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    # Generate safe filename with timestamp and random token
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    random_token = secrets.token_hex(8)

    safe_filename = f"{user_id}_{purpose}_{timestamp}_{random_token}.{extension}"

    return safe_filename
