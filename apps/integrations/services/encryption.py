"""Encryption service for securing OAuth tokens and other sensitive data."""

from cryptography.fernet import Fernet
from django.conf import settings


def _get_fernet() -> Fernet:
    """Get a Fernet instance using the configured encryption key.

    Returns:
        Fernet: Configured Fernet cipher instance

    Raises:
        ValueError: If INTEGRATION_ENCRYPTION_KEY is not configured or empty
    """
    key = settings.INTEGRATION_ENCRYPTION_KEY

    if not key:
        raise ValueError("INTEGRATION_ENCRYPTION_KEY is not configured")

    return Fernet(key.encode())


def _to_standard_base64(urlsafe_base64: str) -> str:
    """Convert URL-safe base64 to standard base64.

    Args:
        urlsafe_base64: URL-safe base64 string (using - and _ instead of + and /)

    Returns:
        Standard base64 string (using + and /)
    """
    return urlsafe_base64.replace("-", "+").replace("_", "/")


def _to_urlsafe_base64(standard_base64: str) -> str:
    """Convert standard base64 to URL-safe base64.

    Args:
        standard_base64: Standard base64 string (using + and /)

    Returns:
        URL-safe base64 string (using - and _ instead of + and /)
    """
    return standard_base64.replace("+", "-").replace("/", "_")


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string and return base64-encoded ciphertext.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded encrypted string (standard base64, not URL-safe)

    Raises:
        ValueError: If INTEGRATION_ENCRYPTION_KEY is not configured or empty
        TypeError: If plaintext is None
        AttributeError: If plaintext is None
    """
    fernet = _get_fernet()
    ciphertext_bytes = fernet.encrypt(plaintext.encode())
    # Fernet returns URL-safe base64, convert to standard base64 for database storage
    urlsafe_ciphertext = ciphertext_bytes.decode()
    return _to_standard_base64(urlsafe_ciphertext)


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext and return plaintext.

    Args:
        ciphertext: Base64-encoded encrypted string (standard base64, not URL-safe)

    Returns:
        Decrypted plaintext string

    Raises:
        ValueError: If INTEGRATION_ENCRYPTION_KEY is not configured or empty
        InvalidToken: If ciphertext is invalid or encrypted with wrong key
        TypeError: If ciphertext is None
        AttributeError: If ciphertext is None
    """
    fernet = _get_fernet()
    # Convert standard base64 back to URL-safe base64 for Fernet
    urlsafe_ciphertext = _to_urlsafe_base64(ciphertext)
    plaintext_bytes = fernet.decrypt(urlsafe_ciphertext.encode())
    return plaintext_bytes.decode()
