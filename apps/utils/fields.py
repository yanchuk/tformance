"""Custom Django fields."""

from cryptography.fernet import InvalidToken
from django.db import models

from apps.integrations.services.encryption import decrypt, encrypt


def _is_empty_value(value):
    """Check if a value is None or empty string.

    Args:
        value: The value to check

    Returns:
        bool: True if value is None or empty string, False otherwise
    """
    return value is None or value == ""


class EncryptedValue:
    """Wrapper class to mark a value as already encrypted from the database.

    This wrapper is used internally by EncryptedTextField to distinguish between:
    - Values that came from the database (already encrypted, need decryption on access)
    - Values set by user code (plaintext, need encryption on save)

    Attributes:
        encrypted_data (str): The encrypted ciphertext from the database
    """

    def __init__(self, encrypted_data):
        self.encrypted_data = encrypted_data


class EncryptedFieldDescriptor:
    """Descriptor for EncryptedTextField that handles lazy decryption.

    This descriptor intercepts attribute access on model instances to:
    - Decrypt encrypted values from the database only when accessed (lazy decryption)
    - Return plaintext values as-is when set by user code
    - Handle None and empty string values without encryption/decryption

    Lazy decryption improves performance by avoiding unnecessary decryption of fields
    that may not be accessed, and allows InvalidToken exceptions to be raised at the
    point of access rather than at query time.

    Attributes:
        field (EncryptedTextField): The field instance this descriptor manages
    """

    def __init__(self, field):
        self.field = field

    def __get__(self, instance, owner=None):
        """Get the field value, decrypting if needed.

        Args:
            instance: The model instance, or None when accessed on the class
            owner: The model class

        Returns:
            The decrypted plaintext value, or the class descriptor itself if accessed on the class

        Raises:
            InvalidToken: If the encrypted data is corrupted or encrypted with a different key
        """
        if instance is None:
            return self

        value = instance.__dict__.get(self.field.name)

        if _is_empty_value(value):
            return value

        # Check if this is an EncryptedValue wrapper from the database
        if isinstance(value, EncryptedValue):
            # Decrypt when accessed (this is where InvalidToken can be raised)
            return decrypt(value.encrypted_data)
        else:
            # Value was set by user code, return as-is
            return value

    def __set__(self, instance, value):
        """Set the field value without encryption (encryption happens on save).

        Args:
            instance: The model instance
            value: The value to set (plaintext, EncryptedValue, None, or empty string)
        """
        # Handle EncryptedValue wrapper in case it's being re-assigned
        if isinstance(value, EncryptedValue):
            instance.__dict__[self.field.name] = value
        else:
            # Store the plaintext value as-is
            instance.__dict__[self.field.name] = value


class EncryptedTextField(models.TextField):
    """A TextField that automatically encrypts data before saving and decrypts when reading.

    This field provides transparent encryption for sensitive data stored in the database.
    It handles:
    - Automatic encryption when saving to the database
    - Lazy decryption when accessing field values
    - Idempotency (pre-encrypted values are not double-encrypted)
    - None and empty string values (stored as-is without encryption)

    Usage:
        class MyModel(models.Model):
            oauth_token = EncryptedTextField()
            optional_secret = EncryptedTextField(null=True, blank=True)

    Security:
        - Uses Fernet symmetric encryption (AES-128-CBC with HMAC)
        - Requires INTEGRATION_ENCRYPTION_KEY setting
        - Each encryption includes a random nonce, so identical plaintexts produce different ciphertexts
    """

    def contribute_to_class(self, cls, name, *args, **kwargs):
        """Override to install custom descriptor for lazy decryption.

        Args:
            cls: The model class this field is being added to
            name: The name of the field
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        super().contribute_to_class(cls, name, *args, **kwargs)
        # Replace the default descriptor with our custom one
        setattr(cls, name, EncryptedFieldDescriptor(self))

    def get_prep_value(self, value):
        """Encrypt plaintext value before saving to database.

        This method is called by Django when preparing a value to be saved to the database.
        It handles idempotency by checking if the value is already encrypted before encrypting.

        Args:
            value: The value to prepare (plaintext, EncryptedValue, None, or empty string)

        Returns:
            str or None: The encrypted ciphertext, or None/empty string for empty values

        Raises:
            ValueError: If encryption key is not configured
        """
        # Handle EncryptedValue wrapper (already encrypted from DB)
        if isinstance(value, EncryptedValue):
            return value.encrypted_data

        if _is_empty_value(value):
            return value

        # Check if already encrypted (idempotency)
        try:
            decrypt(value)
            return value  # Already encrypted, return as-is
        except (InvalidToken, ValueError, TypeError, AttributeError):
            # Not encrypted or invalid format, encrypt it
            # InvalidToken: not valid Fernet ciphertext
            # ValueError: not valid base64
            # TypeError/AttributeError: value doesn't support string operations
            return encrypt(value)

    def from_db_value(self, value, expression, connection):
        """Wrap encrypted value from database for lazy decryption.

        This method is called by Django when loading a value from the database.
        It wraps the encrypted value in an EncryptedValue marker so the descriptor
        knows to decrypt it when accessed.

        Args:
            value: The raw value from the database
            expression: The query expression (unused)
            connection: The database connection (unused)

        Returns:
            EncryptedValue or None or str: Wrapped encrypted value, or None/empty string for empty values
        """
        if _is_empty_value(value):
            return value

        # Wrap the encrypted value so we can identify it in the descriptor
        return EncryptedValue(value)
