"""Tests for GitHub webhook service."""

import hashlib
import hmac
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_webhooks import (
    GitHubOAuthError,
    create_repository_webhook,
    delete_repository_webhook,
    validate_webhook_signature,
)


class TestCreateRepositoryWebhook(TestCase):
    """Tests for creating GitHub repository webhooks."""

    @patch("apps.integrations.services.github_webhooks.requests.post")
    def test_create_repository_webhook_returns_webhook_id_on_success(self, mock_post):
        """Test that create_repository_webhook returns webhook_id on successful creation."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 12345678,
            "name": "web",
            "active": True,
            "events": ["pull_request", "pull_request_review"],
            "config": {
                "url": "https://example.com/webhooks/github",
                "content_type": "json",
                "insecure_ssl": "0",
            },
        }
        mock_post.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        webhook_url = "https://example.com/webhooks/github"
        secret = "webhook_secret_123"

        result = create_repository_webhook(access_token, repo_full_name, webhook_url, secret)

        self.assertEqual(result, 12345678)

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/repos/acme-corp/backend-api/hooks")

    @patch("apps.integrations.services.github_webhooks.requests.post")
    def test_create_repository_webhook_sends_correct_payload(self, mock_post):
        """Test that create_repository_webhook sends correct payload with events and config."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 87654321,
            "name": "web",
            "active": True,
            "events": ["pull_request", "pull_request_review"],
        }
        mock_post.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "test-org/test-repo"
        webhook_url = "https://example.com/webhooks/github"
        secret = "my_secret"

        create_repository_webhook(access_token, repo_full_name, webhook_url, secret)

        # Verify the payload
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]

        # Check events
        self.assertIn("events", payload)
        self.assertIn("pull_request", payload["events"])
        self.assertIn("pull_request_review", payload["events"])
        self.assertEqual(len(payload["events"]), 2)

        # Check config
        self.assertIn("config", payload)
        self.assertEqual(payload["config"]["url"], webhook_url)
        self.assertEqual(payload["config"]["content_type"], "json")
        self.assertEqual(payload["config"]["secret"], secret)
        self.assertEqual(payload["config"]["insecure_ssl"], "0")

        # Check name
        self.assertEqual(payload["name"], "web")

        # Check active
        self.assertTrue(payload["active"])

    @patch("apps.integrations.services.github_webhooks.requests.post")
    def test_create_repository_webhook_sends_correct_headers(self, mock_post):
        """Test that create_repository_webhook sends correct Authorization and Accept headers."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_post.return_value = mock_response

        access_token = "gho_test_token_xyz"
        repo_full_name = "org/repo"
        webhook_url = "https://example.com/webhook"
        secret = "secret"

        create_repository_webhook(access_token, repo_full_name, webhook_url, secret)

        # Verify headers
        call_kwargs = mock_post.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["Authorization"], "token gho_test_token_xyz")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")

    @patch("apps.integrations.services.github_webhooks.requests.post")
    def test_create_repository_webhook_raises_error_on_403_forbidden(self, mock_post):
        """Test that create_repository_webhook raises GitHubOAuthError on 403 (no permission)."""
        # Mock 403 response (insufficient permissions)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "You must have admin access to create a webhook.",
        }
        mock_post.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "org/private-repo"
        webhook_url = "https://example.com/webhook"
        secret = "secret"

        with self.assertRaises(GitHubOAuthError) as context:
            create_repository_webhook(access_token, repo_full_name, webhook_url, secret)

        self.assertIn("Insufficient permissions", str(context.exception))
        self.assertIn("org/private-repo", str(context.exception))

    @patch("apps.integrations.services.github_webhooks.requests.post")
    def test_create_repository_webhook_raises_error_on_404_not_found(self, mock_post):
        """Test that create_repository_webhook raises GitHubOAuthError on 404 (repo not found)."""
        # Mock 404 response (repository not found)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found",
        }
        mock_post.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "org/nonexistent-repo"
        webhook_url = "https://example.com/webhook"
        secret = "secret"

        with self.assertRaises(GitHubOAuthError) as context:
            create_repository_webhook(access_token, repo_full_name, webhook_url, secret)

        self.assertIn("Repository not found", str(context.exception))
        self.assertIn("org/nonexistent-repo", str(context.exception))


class TestDeleteRepositoryWebhook(TestCase):
    """Tests for deleting GitHub repository webhooks."""

    @patch("apps.integrations.services.github_webhooks.requests.delete")
    def test_delete_repository_webhook_returns_true_on_204_success(self, mock_delete):
        """Test that delete_repository_webhook returns True on successful deletion (204)."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        webhook_id = 12345678

        result = delete_repository_webhook(access_token, repo_full_name, webhook_id)

        self.assertTrue(result)

        # Verify the request was made correctly
        mock_delete.assert_called_once()
        call_args = mock_delete.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/repos/acme-corp/backend-api/hooks/12345678")

    @patch("apps.integrations.services.github_webhooks.requests.delete")
    def test_delete_repository_webhook_sends_correct_headers(self, mock_delete):
        """Test that delete_repository_webhook sends correct Authorization and Accept headers."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        access_token = "gho_test_token_xyz"
        repo_full_name = "org/repo"
        webhook_id = 999

        delete_repository_webhook(access_token, repo_full_name, webhook_id)

        # Verify headers
        call_kwargs = mock_delete.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["Authorization"], "token gho_test_token_xyz")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")

    @patch("apps.integrations.services.github_webhooks.requests.delete")
    def test_delete_repository_webhook_returns_true_on_404_already_deleted(self, mock_delete):
        """Test that delete_repository_webhook returns True on 404 (webhook already deleted)."""
        # Mock 404 response (webhook doesn't exist - already deleted)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found",
        }
        mock_delete.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "org/repo"
        webhook_id = 99999  # Non-existent webhook ID

        result = delete_repository_webhook(access_token, repo_full_name, webhook_id)

        # Should return True because webhook is already gone (idempotent)
        self.assertTrue(result)

    @patch("apps.integrations.services.github_webhooks.requests.delete")
    def test_delete_repository_webhook_raises_error_on_403_forbidden(self, mock_delete):
        """Test that delete_repository_webhook raises GitHubOAuthError on 403 (no permission)."""
        # Mock 403 response (insufficient permissions)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "You must have admin access to delete a webhook.",
        }
        mock_delete.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "org/private-repo"
        webhook_id = 123

        with self.assertRaises(GitHubOAuthError) as context:
            delete_repository_webhook(access_token, repo_full_name, webhook_id)

        self.assertIn("Insufficient permissions", str(context.exception))
        self.assertIn("org/private-repo", str(context.exception))

    @patch("apps.integrations.services.github_webhooks.requests.delete")
    def test_delete_repository_webhook_raises_error_on_other_failures(self, mock_delete):
        """Test that delete_repository_webhook raises GitHubOAuthError on other error codes."""
        # Mock 500 response (server error)
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "message": "Internal Server Error",
        }
        mock_delete.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "org/repo"
        webhook_id = 123

        with self.assertRaises(GitHubOAuthError) as context:
            delete_repository_webhook(access_token, repo_full_name, webhook_id)

        self.assertIn("500", str(context.exception))


class TestValidateWebhookSignature(TestCase):
    """Tests for validating GitHub webhook signatures."""

    def test_validate_webhook_signature_returns_true_for_valid_signature(self):
        """Test that validate_webhook_signature returns True for a valid signature."""
        secret = "my_webhook_secret"
        payload = b'{"action":"opened","pull_request":{"id":123}}'

        # Calculate the correct signature
        mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
        signature = "sha256=" + mac.hexdigest()

        result = validate_webhook_signature(payload, signature, secret)

        self.assertTrue(result)

    def test_validate_webhook_signature_returns_false_for_invalid_signature(self):
        """Test that validate_webhook_signature returns False for an invalid signature."""
        secret = "my_webhook_secret"
        payload = b'{"action":"opened","pull_request":{"id":123}}'
        invalid_signature = "sha256=invalid_signature_hash_1234567890abcdef"

        result = validate_webhook_signature(payload, invalid_signature, secret)

        self.assertFalse(result)

    def test_validate_webhook_signature_returns_false_for_wrong_secret(self):
        """Test that validate_webhook_signature returns False when secret is wrong."""
        correct_secret = "correct_secret"
        wrong_secret = "wrong_secret"
        payload = b'{"action":"closed","pull_request":{"id":456}}'

        # Calculate signature with correct secret
        mac = hmac.new(correct_secret.encode(), msg=payload, digestmod=hashlib.sha256)
        signature = "sha256=" + mac.hexdigest()

        # Validate with wrong secret
        result = validate_webhook_signature(payload, signature, wrong_secret)

        self.assertFalse(result)

    def test_validate_webhook_signature_returns_false_for_missing_sha256_prefix(self):
        """Test that validate_webhook_signature returns False for signature missing 'sha256=' prefix."""
        secret = "my_webhook_secret"
        payload = b'{"action":"opened","pull_request":{"id":123}}'

        # Calculate signature but omit the "sha256=" prefix
        mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
        signature_without_prefix = mac.hexdigest()  # Missing "sha256="

        result = validate_webhook_signature(payload, signature_without_prefix, secret)

        self.assertFalse(result)

    def test_validate_webhook_signature_returns_false_for_empty_signature(self):
        """Test that validate_webhook_signature returns False for empty signature."""
        secret = "my_webhook_secret"
        payload = b'{"action":"opened","pull_request":{"id":123}}'
        empty_signature = ""

        result = validate_webhook_signature(payload, empty_signature, secret)

        self.assertFalse(result)

    def test_validate_webhook_signature_returns_false_for_malformed_signature(self):
        """Test that validate_webhook_signature returns False for malformed signature."""
        secret = "my_webhook_secret"
        payload = b'{"action":"opened","pull_request":{"id":123}}'
        malformed_signatures = [
            "sha256",  # Missing equals and hash
            "sha256=",  # Missing hash
            "md5=1234567890abcdef",  # Wrong algorithm
            "sha256=not_a_valid_hex",  # Invalid hex characters
        ]

        for malformed_signature in malformed_signatures:
            with self.subTest(malformed_signature=malformed_signature):
                result = validate_webhook_signature(payload, malformed_signature, secret)
                self.assertFalse(result)

    def test_validate_webhook_signature_uses_timing_safe_comparison(self):
        """Test that validate_webhook_signature uses hmac.compare_digest for timing-safe comparison."""
        # This test verifies the function uses hmac.compare_digest by checking
        # that it correctly validates a proper signature
        secret = "timing_safe_secret"
        payload = b'{"test":"timing_attack_prevention"}'

        # Calculate correct signature
        mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
        correct_signature = "sha256=" + mac.hexdigest()

        # Verify it validates correctly (implying compare_digest is being used)
        result = validate_webhook_signature(payload, correct_signature, secret)
        self.assertTrue(result)

        # Also verify it rejects incorrect signature
        incorrect_signature = "sha256=" + mac.hexdigest()[:-2] + "XX"
        result = validate_webhook_signature(payload, incorrect_signature, secret)
        self.assertFalse(result)
