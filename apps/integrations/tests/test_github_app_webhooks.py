"""Tests for GitHub App webhook handlers and endpoint.

RED phase: These tests are written BEFORE the handlers exist.
They should all FAIL until the implementation is complete.

Tests cover:
1. Webhook handlers for installation events
2. Webhook handlers for installation_repositories events
3. Webhook endpoint signature validation and routing
"""

import hashlib
import hmac
import json
import logging
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.integrations.factories import GitHubAppInstallationFactory
from apps.metrics.factories import TeamFactory
from apps.teams.context import unset_current_team


class TestHandleInstallationEvent(TestCase):
    """Tests for handle_installation_event webhook handler."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_handle_installation_created_creates_installation_record(self):
        """Test that action=created creates a new GitHubAppInstallation record."""
        from apps.integrations.models import GitHubAppInstallation
        from apps.integrations.webhooks.github_app import handle_installation_event

        payload = {
            "action": "created",
            "installation": {
                "id": 12345678,
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,
                },
                "permissions": {
                    "contents": "read",
                    "pull_requests": "write",
                    "metadata": "read",
                },
                "events": ["pull_request", "push"],
                "repository_selection": "selected",
            },
            "sender": {"login": "admin-user", "id": 11111111},
        }

        handle_installation_event(payload)

        # Verify installation was created
        installation = GitHubAppInstallation.objects.get(installation_id=12345678)
        self.assertEqual(installation.account_type, "Organization")
        self.assertEqual(installation.account_login, "acme-corp")
        self.assertEqual(installation.account_id, 87654321)
        self.assertTrue(installation.is_active)
        self.assertIsNone(installation.suspended_at)
        self.assertEqual(installation.permissions, {"contents": "read", "pull_requests": "write", "metadata": "read"})
        self.assertEqual(installation.events, ["pull_request", "push"])
        self.assertEqual(installation.repository_selection, "selected")

    def test_handle_installation_deleted_marks_installation_inactive(self):
        """Test that action=deleted marks the installation as inactive."""
        from apps.integrations.webhooks.github_app import handle_installation_event

        # Create an active installation
        installation = GitHubAppInstallationFactory(
            team=self.team,
            installation_id=12345678,
            account_login="acme-corp",
            is_active=True,
        )

        payload = {
            "action": "deleted",
            "installation": {
                "id": 12345678,
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,
                },
            },
            "sender": {"login": "admin-user", "id": 11111111},
        }

        handle_installation_event(payload)

        # Verify installation was marked inactive
        installation.refresh_from_db()
        self.assertFalse(installation.is_active)

    def test_handle_installation_suspended_sets_suspended_at(self):
        """Test that action=suspended sets is_active=False and suspended_at timestamp."""
        from apps.integrations.webhooks.github_app import handle_installation_event

        # Create an active installation
        installation = GitHubAppInstallationFactory(
            team=self.team,
            installation_id=12345678,
            account_login="acme-corp",
            is_active=True,
            suspended_at=None,
        )

        payload = {
            "action": "suspended",
            "installation": {
                "id": 12345678,
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,
                },
                "suspended_at": "2024-01-15T10:30:00Z",
                "suspended_by": {"login": "github-admin", "id": 22222222},
            },
            "sender": {"login": "github-admin", "id": 22222222},
        }

        handle_installation_event(payload)

        # Verify installation was suspended
        installation.refresh_from_db()
        self.assertFalse(installation.is_active)
        self.assertIsNotNone(installation.suspended_at)

    def test_handle_installation_unsuspended_clears_suspended_at(self):
        """Test that action=unsuspended sets is_active=True and clears suspended_at."""
        from apps.integrations.webhooks.github_app import handle_installation_event

        # Create a suspended installation
        suspended_time = timezone.now()
        installation = GitHubAppInstallationFactory(
            team=self.team,
            installation_id=12345678,
            account_login="acme-corp",
            is_active=False,
            suspended_at=suspended_time,
        )

        payload = {
            "action": "unsuspended",
            "installation": {
                "id": 12345678,
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,
                },
            },
            "sender": {"login": "github-admin", "id": 22222222},
        }

        handle_installation_event(payload)

        # Verify installation was unsuspended
        installation.refresh_from_db()
        self.assertTrue(installation.is_active)
        self.assertIsNone(installation.suspended_at)

    def test_handle_installation_unknown_action_is_ignored(self):
        """Test that unknown actions are ignored without raising errors."""
        from apps.integrations.webhooks.github_app import handle_installation_event

        payload = {
            "action": "unknown_action",
            "installation": {
                "id": 99999999,
                "account": {
                    "type": "Organization",
                    "login": "some-org",
                    "id": 11111111,
                },
            },
        }

        # Should not raise an exception
        handle_installation_event(payload)

    def test_handle_installation_created_handles_duplicate_webhook(self):
        """EC-11: Duplicate webhook should update, not crash with unique constraint.

        When GitHub retries a webhook or user cancels/retries the install flow,
        we may receive "created" event for an installation_id that already exists.
        This should gracefully update the existing record.
        """
        from apps.integrations.models import GitHubAppInstallation
        from apps.integrations.webhooks.github_app import handle_installation_event

        # Create an installation that might exist from previous attempt
        GitHubAppInstallationFactory(
            team=None,  # Orphaned from abandoned flow
            installation_id=12345678,
            account_login="acme-corp-old",  # Old name
            account_id=87654321,
            is_active=False,  # Might be marked inactive
        )

        payload = {
            "action": "created",
            "installation": {
                "id": 12345678,  # Same installation_id
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",  # Updated name
                    "id": 87654321,
                },
                "permissions": {"pull_requests": "read"},
                "events": ["pull_request"],
                "repository_selection": "all",
            },
        }

        # Should NOT raise IntegrityError
        handle_installation_event(payload)

        # Should have only one installation with this ID
        installations = GitHubAppInstallation.objects.filter(installation_id=12345678)
        self.assertEqual(installations.count(), 1)

        # Should be updated with new data
        installation = installations.first()
        self.assertEqual(installation.account_login, "acme-corp")
        self.assertTrue(installation.is_active)
        self.assertEqual(installation.permissions, {"pull_requests": "read"})
        self.assertEqual(installation.repository_selection, "all")

    def test_handle_installation_created_logs_warning_on_account_type_change(self):
        """EC-13: Should log warning when account type changes (User→Org).

        This can happen when a GitHub user converts their account to an organization.
        """
        from apps.integrations.webhooks.github_app import handle_installation_event

        # Create an installation with User account type
        GitHubAppInstallationFactory(
            team=self.team,
            installation_id=12345678,
            account_type="User",
            account_login="developer",
            account_id=87654321,
        )

        # Webhook with Organization type (account was converted)
        payload = {
            "action": "created",
            "installation": {
                "id": 12345678,
                "account": {
                    "type": "Organization",  # Changed from User
                    "login": "developer",
                    "id": 87654321,
                },
                "permissions": {},
                "events": [],
                "repository_selection": "all",
            },
        }

        with self.assertLogs("apps.integrations.webhooks.github_app", level="WARNING") as log_cm:
            handle_installation_event(payload)

        # Verify warning was logged
        self.assertTrue(
            any("Account type changed" in msg for msg in log_cm.output),
            f"Expected warning about account type change. Got: {log_cm.output}",
        )
        self.assertTrue(
            any("User" in msg and "Organization" in msg for msg in log_cm.output),
            f"Warning should mention both old and new types. Got: {log_cm.output}",
        )


class TestHandleInstallationRepositoriesEvent(TestCase):
    """Tests for handle_installation_repositories_event webhook handler."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.installation = GitHubAppInstallationFactory(
            team=self.team,
            installation_id=12345678,
            account_login="acme-corp",
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_handle_installation_repositories_added_logs_repos(self):
        """Test that action=added logs the repositories that were added."""
        from apps.integrations.webhooks.github_app import handle_installation_repositories_event

        payload = {
            "action": "added",
            "installation": {
                "id": 12345678,
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,
                },
            },
            "repositories_added": [
                {"id": 100001, "name": "backend-api", "full_name": "acme-corp/backend-api"},
                {"id": 100002, "name": "frontend-web", "full_name": "acme-corp/frontend-web"},
            ],
            "repositories_removed": [],
            "sender": {"login": "admin-user", "id": 11111111},
        }

        with self.assertLogs("apps.integrations.webhooks.github_app", level=logging.INFO) as log_context:
            handle_installation_repositories_event(payload)

        # Verify repos were logged
        log_output = "\n".join(log_context.output)
        self.assertIn("acme-corp/backend-api", log_output)
        self.assertIn("acme-corp/frontend-web", log_output)
        self.assertIn("added", log_output.lower())

    def test_handle_installation_repositories_removed_logs_repos(self):
        """Test that action=removed logs the repositories that were removed."""
        from apps.integrations.webhooks.github_app import handle_installation_repositories_event

        payload = {
            "action": "removed",
            "installation": {
                "id": 12345678,
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,
                },
            },
            "repositories_added": [],
            "repositories_removed": [
                {"id": 100003, "name": "deprecated-service", "full_name": "acme-corp/deprecated-service"},
            ],
            "sender": {"login": "admin-user", "id": 11111111},
        }

        with self.assertLogs("apps.integrations.webhooks.github_app", level=logging.INFO) as log_context:
            handle_installation_repositories_event(payload)

        # Verify repos were logged
        log_output = "\n".join(log_context.output)
        self.assertIn("acme-corp/deprecated-service", log_output)
        self.assertIn("removed", log_output.lower())


class TestGitHubAppWebhookEndpoint(TestCase):
    """Tests for the github_app_webhook view endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.webhook_secret = "test_webhook_secret_12345"
        self.team = TeamFactory()
        self.installation = GitHubAppInstallationFactory(
            team=self.team,
            installation_id=12345678,
            account_login="acme-corp",
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def _create_signature(self, payload_bytes: bytes, secret: str) -> str:
        """Create a valid HMAC-SHA256 signature for a payload."""
        mac = hmac.new(secret.encode(), msg=payload_bytes, digestmod=hashlib.sha256)
        return f"sha256={mac.hexdigest()}"

    def _get_webhook_url(self) -> str:
        """Get the GitHub App webhook endpoint URL."""
        return reverse("web:github_app_webhook")

    @patch.dict("os.environ", {"GITHUB_APP_WEBHOOK_SECRET": "test_webhook_secret_12345"})
    def test_webhook_valid_signature_returns_200(self):
        """Test that a valid webhook signature returns 200 OK."""
        payload = {
            "action": "created",
            "installation": {
                "id": 99999999,
                "account": {"type": "Organization", "login": "new-org", "id": 88888888},
                "permissions": {},
                "events": [],
                "repository_selection": "all",
            },
        }
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_signature(payload_bytes, self.webhook_secret)

        response = self.client.post(
            self._get_webhook_url(),
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
            HTTP_X_GITHUB_EVENT="installation",
            HTTP_X_GITHUB_DELIVERY="test-delivery-id-123",
        )

        self.assertEqual(response.status_code, 200)

    @patch.dict("os.environ", {"GITHUB_APP_WEBHOOK_SECRET": "test_webhook_secret_12345"})
    def test_webhook_invalid_signature_returns_403(self):
        """Test that an invalid webhook signature returns 403 Forbidden."""
        payload = {
            "action": "created",
            "installation": {
                "id": 12345678,
                "account": {"type": "Organization", "login": "acme-corp", "id": 87654321},
            },
        }
        payload_bytes = json.dumps(payload).encode()
        invalid_signature = "sha256=invalid_signature_0000000000000000000000000000000000000000"

        response = self.client.post(
            self._get_webhook_url(),
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=invalid_signature,
            HTTP_X_GITHUB_EVENT="installation",
            HTTP_X_GITHUB_DELIVERY="test-delivery-id-456",
        )

        self.assertEqual(response.status_code, 403)

    @patch.dict("os.environ", {"GITHUB_APP_WEBHOOK_SECRET": "test_webhook_secret_12345"})
    def test_webhook_missing_signature_returns_403(self):
        """Test that a missing signature header returns 403 Forbidden."""
        payload = {
            "action": "created",
            "installation": {
                "id": 12345678,
                "account": {"type": "Organization", "login": "acme-corp", "id": 87654321},
            },
        }
        payload_bytes = json.dumps(payload).encode()

        response = self.client.post(
            self._get_webhook_url(),
            data=payload_bytes,
            content_type="application/json",
            # No HTTP_X_HUB_SIGNATURE_256 header
            HTTP_X_GITHUB_EVENT="installation",
            HTTP_X_GITHUB_DELIVERY="test-delivery-id-789",
        )

        self.assertIn(response.status_code, [401, 403])

    @patch.dict("os.environ", {"GITHUB_APP_WEBHOOK_SECRET": "test_webhook_secret_12345"})
    @patch("apps.web.views.handle_installation_event")
    def test_webhook_routes_installation_event(self, mock_handler):
        """Test that installation events are routed to handle_installation_event."""
        payload = {
            "action": "created",
            "installation": {
                "id": 12345678,
                "account": {"type": "Organization", "login": "acme-corp", "id": 87654321},
                "permissions": {},
                "events": [],
                "repository_selection": "all",
            },
        }
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_signature(payload_bytes, self.webhook_secret)

        response = self.client.post(
            self._get_webhook_url(),
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
            HTTP_X_GITHUB_EVENT="installation",
            HTTP_X_GITHUB_DELIVERY="test-delivery-id-route-1",
        )

        self.assertEqual(response.status_code, 200)
        mock_handler.assert_called_once_with(payload)

    @patch.dict("os.environ", {"GITHUB_APP_WEBHOOK_SECRET": "test_webhook_secret_12345"})
    @patch("apps.web.views.handle_installation_repositories_event")
    def test_webhook_routes_installation_repositories_event(self, mock_handler):
        """Test that installation_repositories events are routed to handle_installation_repositories_event."""
        payload = {
            "action": "added",
            "installation": {
                "id": 12345678,
                "account": {"type": "Organization", "login": "acme-corp", "id": 87654321},
            },
            "repositories_added": [
                {"id": 100001, "name": "repo1", "full_name": "acme-corp/repo1"},
            ],
            "repositories_removed": [],
        }
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_signature(payload_bytes, self.webhook_secret)

        response = self.client.post(
            self._get_webhook_url(),
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
            HTTP_X_GITHUB_EVENT="installation_repositories",
            HTTP_X_GITHUB_DELIVERY="test-delivery-id-route-2",
        )

        self.assertEqual(response.status_code, 200)
        mock_handler.assert_called_once_with(payload)

    @patch.dict("os.environ", {"GITHUB_APP_WEBHOOK_SECRET": "test_webhook_secret_12345"})
    def test_webhook_unknown_event_returns_200(self):
        """Test that unknown events return 200 (ignored gracefully)."""
        payload = {
            "action": "opened",
            "issue": {"id": 12345, "title": "Some issue"},
        }
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_signature(payload_bytes, self.webhook_secret)

        response = self.client.post(
            self._get_webhook_url(),
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
            HTTP_X_GITHUB_EVENT="issues",  # Not a handled event type
            HTTP_X_GITHUB_DELIVERY="test-delivery-id-unknown",
        )

        # Unknown events should be acknowledged but not processed
        self.assertEqual(response.status_code, 200)

    @patch.dict("os.environ", {"GITHUB_APP_WEBHOOK_SECRET": "test_webhook_secret_12345"})
    def test_webhook_post_only(self):
        """Test that the webhook endpoint only accepts POST requests."""
        response = self.client.get(self._get_webhook_url())
        self.assertEqual(response.status_code, 405)

        response = self.client.put(
            self._get_webhook_url(),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)

    @patch.dict("os.environ", {"GITHUB_APP_WEBHOOK_SECRET": "test_webhook_secret_12345"})
    def test_webhook_invalid_json_returns_400(self):
        """Test that invalid JSON payload returns 400 Bad Request."""
        payload_bytes = b"not valid json {"
        signature = self._create_signature(payload_bytes, self.webhook_secret)

        response = self.client.post(
            self._get_webhook_url(),
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
            HTTP_X_GITHUB_EVENT="installation",
            HTTP_X_GITHUB_DELIVERY="test-delivery-id-invalid-json",
        )

        self.assertEqual(response.status_code, 400)


class TestReinstallMigration(TestCase):
    """Tests for EC-6: User reinstalls App (new installation ID).

    When a user uninstalls and reinstalls the GitHub App, the new installation
    should:
    1. Migrate TrackedRepository records from the old installation
    2. Inherit the team from the old installation
    3. Old installation should be marked as inactive
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.factories import TrackedRepositoryFactory

        self.team = TeamFactory()

        # Create an old installation that was deleted/inactive
        self.old_installation = GitHubAppInstallationFactory(
            team=self.team,
            installation_id=11111111,  # Old installation ID
            account_id=87654321,  # Same account ID
            account_login="acme-corp",
            account_type="Organization",
            is_active=False,  # Marked inactive after deletion
        )

        # Create TrackedRepository records pointing to old installation
        # Note: integration=None to avoid creating GitHubIntegration (deprecated)
        self.tracked_repo1 = TrackedRepositoryFactory(
            team=self.team,
            integration=None,  # App-based, no OAuth integration
            app_installation=self.old_installation,
            full_name="acme-corp/backend",
            github_repo_id=100001,
        )
        self.tracked_repo2 = TrackedRepositoryFactory(
            team=self.team,
            integration=None,  # App-based, no OAuth integration
            app_installation=self.old_installation,
            full_name="acme-corp/frontend",
            github_repo_id=100002,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_reinstall_migrates_tracked_repos(self):
        """Test that TrackedRepository records are migrated to new installation."""
        from apps.integrations.models import GitHubAppInstallation
        from apps.integrations.webhooks.github_app import handle_installation_event

        # Simulate user reinstalling the App (new installation ID, same account)
        payload = {
            "action": "created",
            "installation": {
                "id": 22222222,  # New installation ID
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,  # Same account ID as old installation
                },
                "permissions": {"pull_requests": "read", "metadata": "read"},
                "events": ["pull_request"],
                "repository_selection": "selected",
            },
            "sender": {"login": "admin-user", "id": 11111111},
        }

        handle_installation_event(payload)

        # Verify new installation was created
        new_installation = GitHubAppInstallation.objects.get(installation_id=22222222)
        self.assertTrue(new_installation.is_active)

        # Verify TrackedRepository records were migrated to new installation
        self.tracked_repo1.refresh_from_db()
        self.tracked_repo2.refresh_from_db()

        self.assertEqual(
            self.tracked_repo1.app_installation_id,
            new_installation.id,
            "TrackedRepository should be migrated to new installation",
        )
        self.assertEqual(
            self.tracked_repo2.app_installation_id,
            new_installation.id,
            "TrackedRepository should be migrated to new installation",
        )

    def test_reinstall_deactivates_old_installation(self):
        """Test that old installation is deactivated (if not already)."""
        from apps.integrations.models import GitHubAppInstallation
        from apps.integrations.webhooks.github_app import handle_installation_event

        # Make old installation active (simulating race where webhook arrives before deletion)
        self.old_installation.is_active = True
        self.old_installation.save()

        payload = {
            "action": "created",
            "installation": {
                "id": 22222222,
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,
                },
                "permissions": {},
                "events": [],
                "repository_selection": "all",
            },
        }

        handle_installation_event(payload)

        # Verify old installation was deactivated
        self.old_installation.refresh_from_db()
        self.assertFalse(
            self.old_installation.is_active,
            "Old installation should be deactivated when new one is created",
        )

        # Verify new installation is active
        new_installation = GitHubAppInstallation.objects.get(installation_id=22222222)
        self.assertTrue(new_installation.is_active)

    def test_reinstall_inherits_team_from_old_installation(self):
        """Test that new installation inherits team from old installation."""
        from apps.integrations.models import GitHubAppInstallation
        from apps.integrations.webhooks.github_app import handle_installation_event

        payload = {
            "action": "created",
            "installation": {
                "id": 22222222,
                "account": {
                    "type": "Organization",
                    "login": "acme-corp",
                    "id": 87654321,
                },
                "permissions": {},
                "events": [],
                "repository_selection": "all",
            },
        }

        handle_installation_event(payload)

        # Verify new installation inherited team from old installation
        new_installation = GitHubAppInstallation.objects.get(installation_id=22222222)
        self.assertEqual(
            new_installation.team_id,
            self.team.id,
            "New installation should inherit team from old installation with same account_id",
        )

    def test_fresh_install_has_no_team(self):
        """Test that fresh installations (no previous) have team=None."""
        from apps.integrations.models import GitHubAppInstallation
        from apps.integrations.webhooks.github_app import handle_installation_event

        # New account that never had an installation
        payload = {
            "action": "created",
            "installation": {
                "id": 33333333,
                "account": {
                    "type": "Organization",
                    "login": "brand-new-org",
                    "id": 99999999,  # Different account ID
                },
                "permissions": {},
                "events": [],
                "repository_selection": "all",
            },
        }

        handle_installation_event(payload)

        # Verify new installation has no team (fresh install)
        new_installation = GitHubAppInstallation.objects.get(installation_id=33333333)
        self.assertIsNone(
            new_installation.team,
            "Fresh installation should have team=None",
        )
