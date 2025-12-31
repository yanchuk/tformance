"""Tests for error sanitization utility.

These tests verify that internal exception details are not exposed to users,
while still providing helpful error messages for debugging.
"""

from unittest.mock import MagicMock

import requests
from django.test import TestCase

from apps.utils.errors import sanitize_error


class TestSanitizeError(TestCase):
    """Tests for sanitize_error() function."""

    def test_connection_error_returns_user_safe_message(self):
        """Test that ConnectionError returns a generic connection failure message."""
        exc = requests.exceptions.ConnectionError(
            "HTTPConnectionPool(host='internal-api.example.com', port=8080): "
            "Max retries exceeded with url: /api/v1/secret-endpoint"
        )

        result = sanitize_error(exc)

        self.assertEqual(result, "Connection failed. Please try again later.")
        # Internal details should NOT be in the message
        self.assertNotIn("internal-api.example.com", result)
        self.assertNotIn("8080", result)
        self.assertNotIn("secret-endpoint", result)

    def test_timeout_error_returns_user_safe_message(self):
        """Test that Timeout errors return a timeout-specific message."""
        exc = requests.exceptions.Timeout("Read timed out. (read timeout=30)")

        result = sanitize_error(exc)

        self.assertEqual(result, "Request timed out. Please try again later.")
        self.assertNotIn("30", result)

    def test_read_timeout_returns_user_safe_message(self):
        """Test that ReadTimeout specifically is handled."""
        exc = requests.exceptions.ReadTimeout(
            "HTTPSConnectionPool(host='api.github.com', port=443): Read timed out. (read timeout=60)"
        )

        result = sanitize_error(exc)

        self.assertEqual(result, "Request timed out. Please try again later.")
        self.assertNotIn("github.com", result)

    def test_http_401_error_returns_auth_failure_message(self):
        """Test that HTTP 401 errors return an authentication failure message."""
        response = MagicMock()
        response.status_code = 401
        response.reason = "Unauthorized"
        response.url = "https://api.github.com/repos/secret-org/private-repo"

        exc = requests.exceptions.HTTPError(response=response)

        result = sanitize_error(exc)

        self.assertEqual(result, "Authentication failed. Please reconnect your integration.")
        self.assertNotIn("secret-org", result)
        self.assertNotIn("private-repo", result)

    def test_http_403_error_returns_permission_message(self):
        """Test that HTTP 403 errors return a permission denied message."""
        response = MagicMock()
        response.status_code = 403
        response.reason = "Forbidden"
        response.url = "https://api.github.com/orgs/acme-corp/members"

        exc = requests.exceptions.HTTPError(response=response)

        result = sanitize_error(exc)

        self.assertEqual(result, "Permission denied. Check your integration permissions.")
        self.assertNotIn("acme-corp", result)

    def test_http_404_error_returns_not_found_message(self):
        """Test that HTTP 404 errors return a resource not found message."""
        response = MagicMock()
        response.status_code = 404
        response.reason = "Not Found"
        response.url = "https://api.jira.com/rest/api/3/issue/SECRET-123"

        exc = requests.exceptions.HTTPError(response=response)

        result = sanitize_error(exc)

        self.assertEqual(result, "Resource not found. It may have been deleted.")
        self.assertNotIn("SECRET-123", result)

    def test_http_429_error_returns_rate_limit_message(self):
        """Test that HTTP 429 errors return a rate limit message."""
        response = MagicMock()
        response.status_code = 429
        response.reason = "Too Many Requests"
        response.url = "https://api.github.com/graphql"

        exc = requests.exceptions.HTTPError(response=response)

        result = sanitize_error(exc)

        self.assertEqual(result, "Rate limit exceeded. Please wait and try again.")

    def test_http_500_error_returns_server_error_message(self):
        """Test that HTTP 5xx errors return a server error message."""
        response = MagicMock()
        response.status_code = 500
        response.reason = "Internal Server Error"
        response.url = "https://api.slack.com/api/chat.postMessage"
        response.text = "Traceback: some internal error details..."

        exc = requests.exceptions.HTTPError(response=response)

        result = sanitize_error(exc)

        self.assertEqual(result, "External service error. Please try again later.")
        self.assertNotIn("Traceback", result)
        self.assertNotIn("internal error", result)

    def test_http_502_error_returns_server_error_message(self):
        """Test that HTTP 502 errors also return server error message."""
        response = MagicMock()
        response.status_code = 502
        response.reason = "Bad Gateway"

        exc = requests.exceptions.HTTPError(response=response)

        result = sanitize_error(exc)

        self.assertEqual(result, "External service error. Please try again later.")

    def test_http_503_error_returns_server_error_message(self):
        """Test that HTTP 503 errors also return server error message."""
        response = MagicMock()
        response.status_code = 503
        response.reason = "Service Unavailable"

        exc = requests.exceptions.HTTPError(response=response)

        result = sanitize_error(exc)

        self.assertEqual(result, "External service error. Please try again later.")

    def test_ssl_error_returns_connection_message(self):
        """Test that SSL errors return a connection failure message."""
        exc = requests.exceptions.SSLError("SSL: CERTIFICATE_VERIFY_FAILED certificate verify failed")

        result = sanitize_error(exc)

        self.assertEqual(result, "Connection failed. Please try again later.")
        self.assertNotIn("CERTIFICATE", result)

    def test_unknown_exception_returns_generic_message(self):
        """Test that unknown exceptions return a generic error message."""
        exc = Exception("Some internal error with sensitive data: API_KEY=abc123")

        result = sanitize_error(exc)

        self.assertEqual(result, "An error occurred. Please try again or contact support.")
        self.assertNotIn("API_KEY", result)
        self.assertNotIn("abc123", result)

    def test_value_error_returns_generic_message(self):
        """Test that ValueError returns a generic message."""
        exc = ValueError("Invalid token format: ghp_xxxxxxxxxxxx")

        result = sanitize_error(exc)

        self.assertEqual(result, "An error occurred. Please try again or contact support.")
        self.assertNotIn("ghp_", result)

    def test_key_error_returns_generic_message(self):
        """Test that KeyError returns a generic message."""
        exc = KeyError("secret_field_name")

        result = sanitize_error(exc)

        self.assertEqual(result, "An error occurred. Please try again or contact support.")
        self.assertNotIn("secret_field", result)

    def test_json_decode_error_returns_parse_message(self):
        """Test that JSON decode errors return a parsing message."""
        import json

        try:
            json.loads("not valid json {{{")
        except json.JSONDecodeError as exc:
            result = sanitize_error(exc)

        self.assertEqual(result, "Invalid response received. Please try again later.")

    def test_request_exception_returns_generic_connection_message(self):
        """Test that generic RequestException returns connection message."""
        exc = requests.exceptions.RequestException("Some complex error with internal details")

        result = sanitize_error(exc)

        self.assertEqual(result, "Connection failed. Please try again later.")
        self.assertNotIn("internal details", result)
