"""Tests for custom Django fields."""

from cryptography.fernet import InvalidToken
from django.db import connection
from django.test import TestCase

from apps.integrations.factories import IntegrationCredentialFactory
from apps.integrations.models import IntegrationCredential
from apps.integrations.services.encryption import decrypt, encrypt
from apps.utils.fields import EncryptedTextField


class EncryptedTextFieldTest(TestCase):
    """Tests for EncryptedTextField custom field.

    Uses IntegrationCredential model which has EncryptedTextField for access_token
    and refresh_token. This avoids creating/dropping tables during tests which
    would break parallel test execution.
    """

    def test_plaintext_value_is_encrypted_in_database(self):
        """Test that saving a plaintext value encrypts it in the database."""
        plaintext = "my-secret-token-12345"
        credential = IntegrationCredentialFactory(access_token=plaintext)

        # Read directly from database to verify it's encrypted
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT access_token FROM integrations_integrationcredential WHERE id = %s",
                [credential.id],
            )
            row = cursor.fetchone()
            stored_value = row[0]

        # Stored value should be different from plaintext (encrypted)
        self.assertNotEqual(stored_value, plaintext)

        # Stored value should be valid encrypted data (can be decrypted)
        decrypted = decrypt(stored_value)
        self.assertEqual(decrypted, plaintext)

    def test_reading_value_returns_decrypted_plaintext(self):
        """Test that reading a value from database returns decrypted plaintext."""
        plaintext = "another-secret-value"
        credential = IntegrationCredentialFactory(access_token=plaintext)

        # Refresh from database
        credential.refresh_from_db()

        # Should get back the original plaintext
        self.assertEqual(credential.access_token, plaintext)

    def test_empty_string_handling(self):
        """Test that empty strings are handled correctly.

        Note: IntegrationCredential.refresh_token allows blank=True.
        """
        credential = IntegrationCredentialFactory(access_token="valid-token", refresh_token="")

        # Refresh from database
        credential.refresh_from_db()

        # Empty string should stay empty string
        self.assertEqual(credential.refresh_token, "")

        # Verify in database it's actually empty string, not encrypted
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT refresh_token FROM integrations_integrationcredential WHERE id = %s",
                [credential.id],
            )
            row = cursor.fetchone()
            stored_value = row[0]

        self.assertEqual(stored_value, "")

    def test_idempotency_already_encrypted_value(self):
        """Test that already encrypted values are not double-encrypted."""
        plaintext = "my-secret"
        encrypted_value = encrypt(plaintext)

        # Create credential with pre-encrypted value
        credential = IntegrationCredentialFactory(access_token=encrypted_value)

        # Read from database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT access_token FROM integrations_integrationcredential WHERE id = %s",
                [credential.id],
            )
            row = cursor.fetchone()
            stored_value = row[0]

        # Should be the same encrypted value, not double-encrypted
        self.assertEqual(stored_value, encrypted_value)

        # Refresh and verify we can still decrypt it to original plaintext
        credential.refresh_from_db()
        self.assertEqual(credential.access_token, plaintext)

    def test_model_create_operation(self):
        """Test field works with Django model create operation."""
        credential = IntegrationCredentialFactory(
            access_token="create-test-secret",
            refresh_token="optional-refresh-token",
        )

        self.assertIsNotNone(credential.id)
        self.assertEqual(credential.access_token, "create-test-secret")
        self.assertEqual(credential.refresh_token, "optional-refresh-token")

    def test_model_update_operation(self):
        """Test field works when updating existing objects."""
        credential = IntegrationCredentialFactory(access_token="original-value")
        original_id = credential.id

        # Update the value
        credential.access_token = "updated-value"
        credential.save()

        # Verify update worked
        credential.refresh_from_db()
        self.assertEqual(credential.id, original_id)
        self.assertEqual(credential.access_token, "updated-value")

    def test_model_filter_operation(self):
        """Test field works with Django ORM filter operations."""
        # Note: Filtering on encrypted fields won't work as expected
        # since the encrypted values are different each time.
        # This test verifies the field doesn't break basic ORM operations.
        credential = IntegrationCredentialFactory(access_token="filter-test")

        # Should be able to filter by id and access encrypted field
        found = IntegrationCredential.objects.filter(id=credential.id).first()
        self.assertIsNotNone(found)
        self.assertEqual(found.access_token, "filter-test")

    def test_field_deconstruct_for_migrations(self):
        """Test field's deconstruct() method for Django migrations."""
        field = EncryptedTextField(null=True, blank=True, max_length=500)
        name, path, args, kwargs = field.deconstruct()

        # Path should point to our custom field
        self.assertEqual(path, "apps.utils.fields.EncryptedTextField")

        # Should preserve field options
        self.assertTrue(kwargs.get("null"))
        self.assertTrue(kwargs.get("blank"))

    def test_multiple_objects_with_same_plaintext_have_different_ciphertext(self):
        """Test that same plaintext encrypts to different ciphertext (due to Fernet nonce)."""
        plaintext = "shared-secret"

        cred1 = IntegrationCredentialFactory(access_token=plaintext)
        cred2 = IntegrationCredentialFactory(access_token=plaintext)

        # Read raw values from database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT access_token FROM integrations_integrationcredential WHERE id IN (%s, %s)",
                [cred1.id, cred2.id],
            )
            rows = cursor.fetchall()
            stored_value1 = rows[0][0]
            stored_value2 = rows[1][0]

        # Encrypted values should be different (Fernet uses random nonce)
        self.assertNotEqual(stored_value1, stored_value2)

        # But both should decrypt to same plaintext
        self.assertEqual(decrypt(stored_value1), plaintext)
        self.assertEqual(decrypt(stored_value2), plaintext)

    def test_invalid_encrypted_data_raises_error_on_read(self):
        """Test that corrupted encrypted data raises an error when reading."""
        credential = IntegrationCredentialFactory(access_token="valid-secret")

        # Manually corrupt the encrypted data in database
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE integrations_integrationcredential SET access_token = %s WHERE id = %s",
                ["corrupted-invalid-base64-data", credential.id],
            )

        # Reading should raise InvalidToken error
        cred_fresh = IntegrationCredential.objects.get(id=credential.id)
        with self.assertRaises(InvalidToken):
            _ = cred_fresh.access_token
