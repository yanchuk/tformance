"""Tests for GitHub webhook endpoint."""

import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory


class TestGitHubWebhook(TestCase):
    """Tests for GitHub webhook endpoint at /webhooks/github/."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.github_integration = GitHubIntegrationFactory(webhook_secret="test_webhook_secret_12345")
        self.tracked_repo = TrackedRepositoryFactory(
            integration=self.github_integration,
            github_repo_id=98765,
            full_name="acme/repo",
        )
        self.webhook_url = reverse("web:github_webhook")

    def _create_valid_signature(self, payload_bytes, secret):
        """Create a valid HMAC-SHA256 signature for webhook payload."""
        mac = hmac.new(secret.encode(), msg=payload_bytes, digestmod=hashlib.sha256)
        return f"sha256={mac.hexdigest()}"

    def _create_webhook_payload(self, action="opened", repo_id=98765, repo_name="acme/repo"):
        """Create a GitHub webhook payload."""
        return {
            "action": action,
            "repository": {
                "id": repo_id,
                "full_name": repo_name,
            },
            "pull_request": {
                "number": 123,
                "title": "Test PR",
            },
        }

    def test_endpoint_returns_405_for_get_request(self):
        """Test that GET requests to webhook endpoint return 405 Method Not Allowed."""
        response = self.client.get(self.webhook_url)
        self.assertEqual(response.status_code, 405)

    def test_endpoint_returns_401_for_missing_signature_header(self):
        """Test that webhook rejects requests without X-Hub-Signature-256 header."""
        payload = self._create_webhook_payload()
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("signature", response.json().get("error", "").lower())

    def test_endpoint_returns_401_for_invalid_signature(self):
        """Test that webhook rejects requests with invalid signature."""
        payload = self._create_webhook_payload()
        payload_bytes = json.dumps(payload).encode()

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalid_signature_here",
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("signature", response.json().get("error", "").lower())

    @patch("apps.metrics.processors.handle_pull_request_event")
    def test_endpoint_returns_200_for_valid_payload_with_valid_signature(self, mock_handler):
        """Test that webhook accepts valid payload with correct signature."""
        payload = self._create_webhook_payload()
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.metrics.processors.handle_pull_request_review_event")
    @patch("apps.metrics.processors.handle_pull_request_event")
    def test_endpoint_extracts_event_type_from_header(self, mock_pr_handler, mock_review_handler):
        """Test that webhook extracts event type from X-GitHub-Event header."""
        payload = self._create_webhook_payload()
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)

        # Test with different event types (each needs unique delivery ID for replay protection)
        for i, event_type in enumerate(["pull_request", "push", "pull_request_review"]):
            with self.subTest(event_type=event_type):
                response = self.client.post(
                    self.webhook_url,
                    data=payload_bytes,
                    content_type="application/json",
                    HTTP_X_GITHUB_EVENT=event_type,
                    HTTP_X_GITHUB_DELIVERY=f"72d3162e-cc78-11e3-81ab-4c9367dc095{i}",
                    HTTP_X_HUB_SIGNATURE_256=signature,
                )
                self.assertEqual(response.status_code, 200)
                # The response should acknowledge the event was processed
                response_data = response.json()
                self.assertEqual(response_data.get("event"), event_type)

    @patch("apps.metrics.processors.handle_pull_request_event")
    def test_endpoint_looks_up_team_from_repository_in_payload(self, mock_handler):
        """Test that webhook identifies team from repository in payload."""
        payload = self._create_webhook_payload()
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response.status_code, 200)
        # Verify response is minimal (no internal IDs leaked for security)
        response_data = response.json()
        self.assertEqual(response_data.get("status"), "processed")
        self.assertNotIn("team_id", response_data)  # Security: no internal IDs
        # Verify handler was called with correct team
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        self.assertEqual(call_args[0][0], self.github_integration.team)

    def test_endpoint_returns_400_for_missing_delivery_id(self):
        """Test that webhook rejects requests without X-GitHub-Delivery header."""
        payload = self._create_webhook_payload()
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request",
            HTTP_X_HUB_SIGNATURE_256=signature,
            # Missing HTTP_X_GITHUB_DELIVERY
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("delivery", response.json().get("error", "").lower())

    @patch("apps.metrics.processors.handle_pull_request_event")
    def test_replay_protection_rejects_duplicate_delivery(self, mock_handler):
        """Test that webhook rejects duplicate deliveries (replay protection)."""
        from django.test import override_settings

        # Use LocMemCache for this test since default may be DummyCache
        with override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}):
            from django.core.cache import cache

            cache.clear()  # Clear any existing cache

            payload = self._create_webhook_payload()
            payload_bytes = json.dumps(payload).encode()
            signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)
            delivery_id = "unique-delivery-id-123"

            # First request should succeed
            response1 = self.client.post(
                self.webhook_url,
                data=payload_bytes,
                content_type="application/json",
                HTTP_X_GITHUB_EVENT="pull_request",
                HTTP_X_GITHUB_DELIVERY=delivery_id,
                HTTP_X_HUB_SIGNATURE_256=signature,
            )
            self.assertEqual(response1.status_code, 200)

            # Second request with same delivery ID should be rejected
            response2 = self.client.post(
                self.webhook_url,
                data=payload_bytes,
                content_type="application/json",
                HTTP_X_GITHUB_EVENT="pull_request",
                HTTP_X_GITHUB_DELIVERY=delivery_id,
                HTTP_X_HUB_SIGNATURE_256=signature,
            )
            self.assertEqual(response2.status_code, 409)  # Conflict
            self.assertIn("duplicate", response2.json().get("error", "").lower())

    def test_endpoint_returns_404_if_repository_not_tracked(self):
        """Test that webhook returns 404 if repository is not in TrackedRepository."""
        # Create payload for a repository that is not tracked
        payload = self._create_webhook_payload(repo_id=99999, repo_name="unknown/repo")
        payload_bytes = json.dumps(payload).encode()

        # We still need a valid signature, but we need to determine which secret to use
        # Since the repo isn't tracked, we can't know the secret, so this test
        # needs to assume the webhook tries to look up the repo first
        # For now, let's use any valid signature to test the lookup logic
        signature = self._create_valid_signature(payload_bytes, "any_secret")

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertIn("repository", response_data.get("error", "").lower())


class TestGitHubWebhookEventDispatch(TestCase):
    """Tests for webhook event dispatching to correct handlers."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.github_integration = GitHubIntegrationFactory(webhook_secret="test_webhook_secret_12345")
        self.tracked_repo = TrackedRepositoryFactory(
            integration=self.github_integration,
            github_repo_id=98765,
            full_name="acme/repo",
        )
        self.webhook_url = reverse("web:github_webhook")

    def _create_valid_signature(self, payload_bytes, secret):
        """Create a valid HMAC-SHA256 signature for webhook payload."""
        mac = hmac.new(secret.encode(), msg=payload_bytes, digestmod=hashlib.sha256)
        return f"sha256={mac.hexdigest()}"

    def _create_webhook_payload(self, action="opened", repo_id=98765, repo_name="acme/repo"):
        """Create a GitHub webhook payload."""
        return {
            "action": action,
            "repository": {
                "id": repo_id,
                "full_name": repo_name,
            },
            "pull_request": {
                "number": 123,
                "title": "Test PR",
            },
        }

    @patch("apps.metrics.processors.handle_pull_request_event")
    def test_pull_request_event_calls_handler(self, mock_handler):
        """Test that pull_request event dispatches to handle_pull_request_event."""
        payload = self._create_webhook_payload()
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

        self.assertEqual(response.status_code, 200)
        # Verify handler was called with team and payload
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        self.assertEqual(call_args[0][0], self.github_integration.team)  # team argument
        self.assertEqual(call_args[0][1], payload)  # payload argument

    @patch("apps.metrics.processors.handle_pull_request_review_event")
    def test_pull_request_review_event_calls_handler(self, mock_handler):
        """Test that pull_request_review event dispatches to handle_pull_request_review_event."""
        payload = {
            "action": "submitted",
            "repository": {
                "id": 98765,
                "full_name": "acme/repo",
            },
            "pull_request": {
                "number": 123,
                "title": "Test PR",
            },
            "review": {
                "id": 456,
                "state": "approved",
            },
        }
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request_review",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

        self.assertEqual(response.status_code, 200)
        # Verify handler was called with team and payload
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        self.assertEqual(call_args[0][0], self.github_integration.team)  # team argument
        self.assertEqual(call_args[0][1], payload)  # payload argument

    @patch("apps.metrics.processors.handle_pull_request_review_event")
    @patch("apps.metrics.processors.handle_pull_request_event")
    def test_unknown_event_type_returns_200_without_calling_handlers(self, mock_pr_handler, mock_review_handler):
        """Test that unknown event types return 200 OK but don't call any handlers."""
        payload = self._create_webhook_payload()
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="unknown_event",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

        self.assertEqual(response.status_code, 200)
        # Verify handlers were NOT called
        mock_pr_handler.assert_not_called()
        mock_review_handler.assert_not_called()

    @patch("apps.metrics.processors.handle_pull_request_review_event")
    @patch("apps.metrics.processors.handle_pull_request_event")
    def test_push_event_is_ignored(self, mock_pr_handler, mock_review_handler):
        """Test that push events return 200 OK but don't call any handlers."""
        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "id": 98765,
                "full_name": "acme/repo",
            },
            "commits": [
                {
                    "id": "abc123",
                    "message": "Test commit",
                }
            ],
        }
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_valid_signature(payload_bytes, self.github_integration.webhook_secret)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="push",
            HTTP_X_GITHUB_DELIVERY="72d3162e-cc78-11e3-81ab-4c9367dc0958",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

        self.assertEqual(response.status_code, 200)
        # Verify handlers were NOT called
        mock_pr_handler.assert_not_called()
        mock_review_handler.assert_not_called()
