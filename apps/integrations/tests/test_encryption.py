"""Tests for encryption service."""

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.test import TestCase, override_settings

from apps.integrations.services.encryption import _reset_fernet_cache, decrypt, encrypt


class TestEncryptionService(TestCase):
    """Tests for encryption and decryption functionality."""

    def setUp(self):
        """Reset the cached Fernet instance before each test."""
        _reset_fernet_cache()

    def tearDown(self):
        """Reset the cached Fernet instance after each test."""
        _reset_fernet_cache()

    def test_encrypt_returns_different_value_than_plaintext(self):
        """Test that encrypted output is different from plaintext."""
        plaintext = "my_secret_token_123"
        ciphertext = encrypt(plaintext)

        self.assertNotEqual(ciphertext, plaintext)
        self.assertIsInstance(ciphertext, str)

    def test_decrypt_reverses_encrypt(self):
        """Test that decrypt(encrypt(text)) returns original text."""
        plaintext = "test_secret_value"
        ciphertext = encrypt(plaintext)
        decrypted = decrypt(ciphertext)

        self.assertEqual(decrypted, plaintext)

    def test_encrypt_decrypt_roundtrip_with_various_inputs(self):
        """Test encryption/decryption roundtrip with various string inputs."""
        test_cases = [
            "simple",
            "with spaces and punctuation!",
            "UPPERCASE",
            "MixedCase123",
            "special@#$%^&*()chars",
            "very" * 100,  # Long string
            "12345",  # Numbers as string
            "tab\there",  # Tab character
            "new\nline",  # Newline character
        ]

        for plaintext in test_cases:
            with self.subTest(plaintext=plaintext):
                ciphertext = encrypt(plaintext)
                decrypted = decrypt(ciphertext)
                self.assertEqual(decrypted, plaintext)

    def test_encrypt_unicode_and_special_characters(self):
        """Test that encryption handles unicode and special characters correctly."""
        test_cases = [
            "Hello 世界",  # Chinese characters
            "Привет мир",  # Cyrillic
            "مرحبا العالم",  # Arabic
            "🔒🔑💻",  # Emojis
            "café",  # Accented characters
            "Ñoño",  # Spanish special chars
        ]

        for plaintext in test_cases:
            with self.subTest(plaintext=plaintext):
                ciphertext = encrypt(plaintext)
                decrypted = decrypt(ciphertext)
                self.assertEqual(decrypted, plaintext)
                self.assertNotEqual(ciphertext, plaintext)

    def test_encrypt_empty_string(self):
        """Test that empty string can be encrypted and decrypted."""
        plaintext = ""
        ciphertext = encrypt(plaintext)
        decrypted = decrypt(ciphertext)

        self.assertEqual(decrypted, plaintext)
        self.assertEqual(decrypted, "")
        self.assertNotEqual(ciphertext, "")  # Encrypted empty string is not empty

    def test_encrypt_returns_base64_encoded_string(self):
        """Test that encrypt returns a base64-encoded string."""
        import base64

        plaintext = "test_token"
        ciphertext = encrypt(plaintext)

        # Should be able to decode as base64 without errors
        try:
            decoded = base64.b64decode(ciphertext)
            self.assertIsInstance(decoded, bytes)
        except Exception as e:
            self.fail(f"Ciphertext is not valid base64: {e}")

    def test_different_encryptions_of_same_plaintext_are_different(self):
        """Test that encrypting the same plaintext twice produces different ciphertexts.

        This verifies that Fernet uses a timestamp/nonce in encryption.
        """
        plaintext = "same_value"
        ciphertext1 = encrypt(plaintext)
        ciphertext2 = encrypt(plaintext)

        # Different ciphertexts
        self.assertNotEqual(ciphertext1, ciphertext2)

        # But both decrypt to same plaintext
        self.assertEqual(decrypt(ciphertext1), plaintext)
        self.assertEqual(decrypt(ciphertext2), plaintext)

    def test_decrypt_with_invalid_ciphertext_raises_error(self):
        """Test that decrypting invalid ciphertext raises InvalidToken error."""
        invalid_ciphertexts = [
            "not_a_valid_token",
            "YWJjMTIz",  # Valid base64 but not encrypted with our key
            "!!!invalid!!!",
            "",  # Empty string
        ]

        for invalid_ciphertext in invalid_ciphertexts:
            with self.subTest(invalid_ciphertext=invalid_ciphertext), self.assertRaises((InvalidToken, Exception)):
                decrypt(invalid_ciphertext)

    def test_decrypt_with_wrong_key_raises_error(self):
        """Test that decrypting with wrong key raises InvalidToken error."""
        from cryptography.fernet import Fernet

        # Encrypt with current key
        plaintext = "secret_data"
        ciphertext = encrypt(plaintext)

        # Reset cache and try to decrypt with a different key
        _reset_fernet_cache()
        wrong_key = Fernet.generate_key().decode()
        with override_settings(INTEGRATION_ENCRYPTION_KEY=wrong_key), self.assertRaises(InvalidToken):
            decrypt(ciphertext)

    @override_settings(INTEGRATION_ENCRYPTION_KEY=None)
    def test_encrypt_raises_value_error_when_key_not_configured(self):
        """Test that encrypt raises ValueError when INTEGRATION_ENCRYPTION_KEY is not set."""
        with self.assertRaises(ValueError) as context:
            encrypt("some_data")

        self.assertIn("INTEGRATION_ENCRYPTION_KEY", str(context.exception))

    @override_settings(INTEGRATION_ENCRYPTION_KEY="")
    def test_encrypt_raises_value_error_when_key_is_empty(self):
        """Test that encrypt raises ValueError when INTEGRATION_ENCRYPTION_KEY is empty."""
        with self.assertRaises(ValueError) as context:
            encrypt("some_data")

        self.assertIn("INTEGRATION_ENCRYPTION_KEY", str(context.exception))

    @override_settings(INTEGRATION_ENCRYPTION_KEY=None)
    def test_decrypt_raises_value_error_when_key_not_configured(self):
        """Test that decrypt raises ValueError when INTEGRATION_ENCRYPTION_KEY is not set."""
        with self.assertRaises(ValueError) as context:
            decrypt("some_ciphertext")

        self.assertIn("INTEGRATION_ENCRYPTION_KEY", str(context.exception))

    def test_encrypt_with_none_value_raises_error(self):
        """Test that passing None to encrypt raises an appropriate error."""
        with self.assertRaises((TypeError, AttributeError)):
            encrypt(None)

    def test_decrypt_with_none_value_raises_error(self):
        """Test that passing None to decrypt raises an appropriate error."""
        with self.assertRaises((TypeError, AttributeError)):
            decrypt(None)

    def test_encrypt_returns_string_type(self):
        """Test that encrypt always returns a string."""
        result = encrypt("test")
        self.assertIsInstance(result, str)

    def test_decrypt_returns_string_type(self):
        """Test that decrypt always returns a string."""
        ciphertext = encrypt("test")
        result = decrypt(ciphertext)
        self.assertIsInstance(result, str)

    def test_encryption_key_loaded_from_settings(self):
        """Test that encryption functions use the key from Django settings."""
        # This test verifies the key is actually loaded from settings
        self.assertTrue(hasattr(settings, "INTEGRATION_ENCRYPTION_KEY"))
        self.assertIsNotNone(settings.INTEGRATION_ENCRYPTION_KEY)
        self.assertNotEqual(settings.INTEGRATION_ENCRYPTION_KEY, "")

        # Should work with the configured key
        plaintext = "test_with_settings_key"
        ciphertext = encrypt(plaintext)
        decrypted = decrypt(ciphertext)
        self.assertEqual(decrypted, plaintext)

    def test_long_plaintext_encryption(self):
        """Test encryption and decryption of long strings."""
        # Test with a very long plaintext (10KB)
        long_text = "A" * 10240
        ciphertext = encrypt(long_text)
        decrypted = decrypt(ciphertext)

        self.assertEqual(decrypted, long_text)
        self.assertNotEqual(ciphertext, long_text)

    def test_ciphertext_is_safe_for_storage(self):
        """Test that ciphertext only contains safe characters for database storage."""
        plaintext = "test_token_with_special_chars!@#$%"
        ciphertext = encrypt(plaintext)

        # Base64 encoded strings should only contain alphanumeric, +, /, and =
        import re

        self.assertTrue(re.match(r"^[A-Za-z0-9+/=]+$", ciphertext))
