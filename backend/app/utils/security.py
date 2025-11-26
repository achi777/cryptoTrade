"""
Security utility functions
"""
import re


def sanitize_sql_like_pattern(pattern: str, max_length: int = 100) -> str:
    """
    Sanitize user input for SQL LIKE/ILIKE queries to prevent injection

    Args:
        pattern: User-provided search pattern
        max_length: Maximum allowed pattern length

    Returns:
        Sanitized pattern safe for SQL LIKE/ILIKE

    Example:
        >>> sanitize_sql_like_pattern("user@example.com")
        'user@example.com'
        >>> sanitize_sql_like_pattern("test%_\\")  # Escapes special chars
        'test\\%\\_\\\\'
    """
    if not pattern:
        return ""

    # Truncate to max length
    pattern = pattern[:max_length]

    # Escape SQL LIKE special characters
    # % = any sequence of characters
    # _ = any single character
    # \ = escape character (backslash itself needs escaping)
    pattern = pattern.replace('\\', '\\\\')  # Escape backslash first
    pattern = pattern.replace('%', '\\%')    # Escape percent
    pattern = pattern.replace('_', '\\_')    # Escape underscore

    # Only allow alphanumeric, spaces, and common safe characters
    # This prevents injection of other SQL special characters
    pattern = re.sub(r'[^a-zA-Z0-9@.\-_ ]', '', pattern)

    return pattern


def validate_sql_order_by(field: str, allowed_fields: list) -> str:
    """
    Validate ORDER BY field to prevent SQL injection

    Args:
        field: The field name to order by
        allowed_fields: List of allowed field names

    Returns:
        Validated field name

    Raises:
        ValueError: If field is not in allowed_fields
    """
    if field not in allowed_fields:
        raise ValueError(f"Invalid order field: {field}")
    return field


def sanitize_input(value: str, max_length: int = 255, allow_special: bool = False) -> str:
    """
    General input sanitization

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        allow_special: Whether to allow special characters

    Returns:
        Sanitized string
    """
    if not value:
        return ""

    # Truncate
    value = value[:max_length]

    # Strip leading/trailing whitespace
    value = value.strip()

    if not allow_special:
        # Remove potentially dangerous characters
        value = re.sub(r'[<>"\';\\]', '', value)

    return value
