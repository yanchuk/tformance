"""Tests for custom Django fields."""

from cryptography.fernet import InvalidToken
from django.db import connection
from django.test import TestCase

from apps.integrations.services.encryption import decrypt, encrypt
from apps.utils.fields import EncryptedTextField
from apps.utils.models import BaseModel


class TestModel(BaseModel):
    """Test model for EncryptedTextField testing."""

    secret_token = EncryptedTextField(null=True, blank=True)
    required_secret = EncryptedTextField()

    class Meta:
        app_label = "utils"


class EncryptedTextFieldTest(TestCase):
    """Tests for EncryptedTextField custom field."""

    @classmethod
    def setUpClass(cls):
        """Create the test table for TestModel."""
        super().setUpClass()
        # Try to drop the table first if it exists from a previous run
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS utils_testmodel CASCADE")
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TestModel)

    @classmethod
    def tearDownClass(cls):
        """Drop the test table."""
        super().tearDownClass()
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(TestModel)

    def test_plaintext_value_is_encrypted_in_database(self):
        """Test that saving a plaintext value encrypts it in the database."""
        plaintext = "my-secret-token-12345"
        obj = TestModel.objects.create(required_secret=plaintext)

        # Read directly from database to verify it's encrypted
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT required_secret FROM utils_testmodel WHERE id = %s",
                [obj.id],
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
        obj = TestModel.objects.create(required_secret=plaintext)

        # Refresh from database
        obj.refresh_from_db()

        # Should get back the original plaintext
        self.assertEqual(obj.required_secret, plaintext)

    def test_none_value_handling(self):
        """Test that None values are handled correctly (not encrypted)."""
        obj = TestModel.objects.create(required_secret="something", secret_token=None)

        # Refresh from database
        obj.refresh_from_db()

        # None should stay None
        self.assertIsNone(obj.secret_token)

        # Verify in database it's actually NULL, not encrypted string "None"
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT secret_token FROM utils_testmodel WHERE id = %s",
                [obj.id],
            )
            row = cursor.fetchone()
            stored_value = row[0]

        self.assertIsNone(stored_value)

    def test_empty_string_handling(self):
        """Test that empty strings are handled correctly (not encrypted)."""
        obj = TestModel.objects.create(required_secret="something", secret_token="")

        # Refresh from database
        obj.refresh_from_db()

        # Empty string should stay empty string
        self.assertEqual(obj.secret_token, "")

        # Verify in database it's actually empty string, not encrypted
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT secret_token FROM utils_testmodel WHERE id = %s",
                [obj.id],
            )
            row = cursor.fetchone()
            stored_value = row[0]

        self.assertEqual(stored_value, "")

    def test_idempotency_already_encrypted_value(self):
        """Test that already encrypted values are not double-encrypted."""
        plaintext = "my-secret"
        encrypted_value = encrypt(plaintext)

        # Create object with pre-encrypted value
        obj = TestModel.objects.create(required_secret=encrypted_value)

        # Read from database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT required_secret FROM utils_testmodel WHERE id = %s",
                [obj.id],
            )
            row = cursor.fetchone()
            stored_value = row[0]

        # Should be the same encrypted value, not double-encrypted
        self.assertEqual(stored_value, encrypted_value)

        # Refresh and verify we can still decrypt it to original plaintext
        obj.refresh_from_db()
        self.assertEqual(obj.required_secret, plaintext)

    def test_model_create_operation(self):
        """Test field works with Django model create operation."""
        obj = TestModel.objects.create(
            required_secret="create-test-secret",
            secret_token="optional-token",
        )

        self.assertIsNotNone(obj.id)
        self.assertEqual(obj.required_secret, "create-test-secret")
        self.assertEqual(obj.secret_token, "optional-token")

    def test_model_save_operation(self):
        """Test field works with Django model save operation."""
        obj = TestModel(required_secret="save-test-secret")
        obj.save()

        self.assertIsNotNone(obj.id)
        self.assertEqual(obj.required_secret, "save-test-secret")

    def test_model_update_operation(self):
        """Test field works when updating existing objects."""
        obj = TestModel.objects.create(required_secret="original-value")
        original_id = obj.id

        # Update the value
        obj.required_secret = "updated-value"
        obj.save()

        # Verify update worked
        obj.refresh_from_db()
        self.assertEqual(obj.id, original_id)
        self.assertEqual(obj.required_secret, "updated-value")

    def test_model_filter_operation(self):
        """Test field works with Django ORM filter operations."""
        # Note: Filtering on encrypted fields won't work as expected
        # since the encrypted values are different each time.
        # This test verifies the field doesn't break basic ORM operations.
        obj = TestModel.objects.create(required_secret="filter-test")

        # Should be able to filter by id and access encrypted field
        found = TestModel.objects.filter(id=obj.id).first()
        self.assertIsNotNone(found)
        self.assertEqual(found.required_secret, "filter-test")

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

        obj1 = TestModel.objects.create(required_secret=plaintext)
        obj2 = TestModel.objects.create(required_secret=plaintext)

        # Read raw values from database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT required_secret FROM utils_testmodel WHERE id IN (%s, %s)",
                [obj1.id, obj2.id],
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
        obj = TestModel.objects.create(required_secret="valid-secret")

        # Manually corrupt the encrypted data in database
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE utils_testmodel SET required_secret = %s WHERE id = %s",
                ["corrupted-invalid-base64-data", obj.id],
            )

        # Reading should raise InvalidToken error
        obj_fresh = TestModel.objects.get(id=obj.id)
        with self.assertRaises(InvalidToken):
            _ = obj_fresh.required_secret
