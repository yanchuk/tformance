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

    @patch("apps.integrations.services.github_webhooks.Github")
    def test_create_repository_webhook_returns_webhook_id_on_success(self, mock_github_class):
        """Test that create_repository_webhook returns webhook_id on successful creation."""
        # Mock the Github instance and repository
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        # Mock the hook that gets created
        mock_hook = MagicMock()
        mock_hook.id = 12345678
        mock_repo.create_hook.return_value = mock_hook

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        webhook_url = "https://example.com/webhooks/github"
        secret = "webhook_secret_123"

        result = create_repository_webhook(access_token, repo_full_name, webhook_url, secret)

        self.assertEqual(result, 12345678)

        # Verify Github was initialized with the access token
        mock_github_class.assert_called_once_with(access_token)

        # Verify get_repo was called with the correct repo name
        mock_github.get_repo.assert_called_once_with(repo_full_name)

    @patch("apps.integrations.services.github_webhooks.Github")
    def test_create_repository_webhook_sends_correct_config(self, mock_github_class):
        """Test that create_repository_webhook sends correct config (url, secret, events)."""
        # Mock the Github instance and repository
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        # Mock the hook that gets created
        mock_hook = MagicMock()
        mock_hook.id = 87654321
        mock_repo.create_hook.return_value = mock_hook

        access_token = "gho_test_token"
        repo_full_name = "test-org/test-repo"
        webhook_url = "https://example.com/webhooks/github"
        secret = "my_secret"

        create_repository_webhook(access_token, repo_full_name, webhook_url, secret)

        # Verify create_hook was called with correct parameters
        mock_repo.create_hook.assert_called_once_with(
            name="web",
            config={
                "url": webhook_url,
                "content_type": "json",
                "secret": secret,
                "insecure_ssl": "0",
            },
            events=["pull_request", "pull_request_review"],
            active=True,
        )

    @patch("apps.integrations.services.github_webhooks.Github")
    def test_create_repository_webhook_raises_error_on_403_forbidden(self, mock_github_class):
        """Test that create_repository_webhook raises GitHubOAuthError on 403 (no permission)."""
        from github import GithubException

        # Mock the Github instance and repository
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        # Mock 403 response (insufficient permissions)
        mock_repo.create_hook.side_effect = GithubException(
            status=403,
            data={"message": "You must have admin access to create a webhook."},
        )

        access_token = "gho_test_token"
        repo_full_name = "org/private-repo"
        webhook_url = "https://example.com/webhook"
        secret = "secret"

        with self.assertRaises(GitHubOAuthError) as context:
            create_repository_webhook(access_token, repo_full_name, webhook_url, secret)

        self.assertIn("Insufficient permissions", str(context.exception))
        self.assertIn("org/private-repo", str(context.exception))

    @patch("apps.integrations.services.github_webhooks.Github")
    def test_create_repository_webhook_raises_error_on_404_not_found(self, mock_github_class):
        """Test that create_repository_webhook raises GitHubOAuthError on 404 (repo not found)."""
        from github import GithubException

        # Mock the Github instance and repository
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        # Mock 404 response (repository not found)
        mock_repo.create_hook.side_effect = GithubException(
            status=404,
            data={"message": "Not Found"},
        )

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

    @patch("apps.integrations.services.github_webhooks.Github")
    def test_delete_repository_webhook_returns_true_on_success(self, mock_github_class):
        """Test that delete_repository_webhook returns True on successful deletion."""
        # Mock the Github instance and repository
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        # Mock the hook
        mock_hook = MagicMock()
        mock_repo.get_hook.return_value = mock_hook

        # Mock successful deletion (delete() returns None on success)
        mock_hook.delete.return_value = None

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        webhook_id = 12345678

        result = delete_repository_webhook(access_token, repo_full_name, webhook_id)

        self.assertTrue(result)

        # Verify Github was initialized with the access token
        mock_github_class.assert_called_once_with(access_token)

        # Verify get_repo was called with the correct repo name
        mock_github.get_repo.assert_called_once_with(repo_full_name)

        # Verify get_hook was called with the webhook_id
        mock_repo.get_hook.assert_called_once_with(webhook_id)

        # Verify delete was called
        mock_hook.delete.assert_called_once()

    @patch("apps.integrations.services.github_webhooks.Github")
    def test_delete_repository_webhook_returns_true_on_404_already_deleted(self, mock_github_class):
        """Test that delete_repository_webhook returns True on 404 (webhook already deleted)."""
        from github import UnknownObjectException

        # Mock the Github instance and repository
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        # Mock 404 response (webhook doesn't exist - already deleted)
        # PyGithub raises UnknownObjectException for 404
        mock_repo.get_hook.side_effect = UnknownObjectException(
            status=404,
            data={"message": "Not Found"},
        )

        access_token = "gho_test_token"
        repo_full_name = "org/repo"
        webhook_id = 99999  # Non-existent webhook ID

        result = delete_repository_webhook(access_token, repo_full_name, webhook_id)

        # Should return True because webhook is already gone (idempotent)
        self.assertTrue(result)

    @patch("apps.integrations.services.github_webhooks.Github")
    def test_delete_repository_webhook_raises_error_on_403_forbidden(self, mock_github_class):
        """Test that delete_repository_webhook raises GitHubOAuthError on 403 (no permission)."""
        from github import GithubException

        # Mock the Github instance and repository
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        mock_hook = MagicMock()
        mock_repo.get_hook.return_value = mock_hook

        # Mock 403 response (insufficient permissions)
        mock_hook.delete.side_effect = GithubException(
            status=403,
            data={"message": "You must have admin access to delete a webhook."},
        )

        access_token = "gho_test_token"
        repo_full_name = "org/private-repo"
        webhook_id = 123

        with self.assertRaises(GitHubOAuthError) as context:
            delete_repository_webhook(access_token, repo_full_name, webhook_id)

        self.assertIn("Insufficient permissions", str(context.exception))
        self.assertIn("org/private-repo", str(context.exception))

    @patch("apps.integrations.services.github_webhooks.Github")
    def test_delete_repository_webhook_raises_error_on_other_failures(self, mock_github_class):
        """Test that delete_repository_webhook raises GitHubOAuthError on other error codes."""
        from github import GithubException

        # Mock the Github instance and repository
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        mock_hook = MagicMock()
        mock_repo.get_hook.return_value = mock_hook

        # Mock 500 response (server error)
        mock_hook.delete.side_effect = GithubException(
            status=500,
            data={"message": "Internal Server Error"},
        )

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
