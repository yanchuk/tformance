"""Tests for async webhook creation in github_repo_toggle view.

Phase 4.2: Webhook creation should be queued as a Celery task instead of
blocking the view response. The view should return immediately without
waiting for webhook creation.

Current behavior (blocking):
    _create_repository_webhook() is called synchronously in the view.

Desired behavior:
    1. View queues create_repository_webhook_task.delay(tracked_repo.id, webhook_url)
    2. View returns immediately (no webhook_id yet)
    3. Task creates webhook and updates TrackedRepository.webhook_id
"""

import time
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    TrackedRepositoryFactory,
    UserFactory,
)
from apps.integrations.models import TrackedRepository
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN


class TestAsyncWebhookCreationView(TestCase):
    """Tests for async webhook creation in github_repo_toggle view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})

        # Create GitHub integration
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="fake_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="acme-corp",
        )

        self.client = Client()
        self.client.force_login(self.admin)

    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_queues_webhook_task_instead_of_sync_call(self, mock_initial_task):
        """Test that toggle view queues webhook creation task instead of calling sync helper."""
        # Mock the delay method
        mock_initial_task.delay = MagicMock()

        # POST to toggle view to track a new repo
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 111111111})
        response = self.client.post(
            url,
            data={"full_name": "acme-corp/async-webhook-repo"},
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=111111111)
        self.assertIsNotNone(tracked_repo)

        # KEY ASSERTION: Verify that the TrackedRepository was created WITHOUT webhook_id
        # because webhook creation should be async (not blocking the view)
        self.assertIsNone(
            tracked_repo.webhook_id,
            "TrackedRepository should be created WITHOUT webhook_id initially (webhook creation should be async)",
        )

    @patch("apps.integrations.tasks.sync_repository_initial_task")
    @patch("apps.integrations.tasks.create_repository_webhook_task")
    def test_toggle_calls_webhook_task_delay(self, mock_webhook_task, mock_initial_task):
        """Test that toggle view calls create_repository_webhook_task.delay()."""
        # Mock the delay methods
        mock_initial_task.delay = MagicMock()
        mock_webhook_task.delay = MagicMock()

        # POST to toggle view to track a new repo
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 222222222})
        response = self.client.post(
            url,
            data={"full_name": "acme-corp/webhook-task-repo"},
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=222222222)

        # KEY ASSERTION: Verify create_repository_webhook_task.delay was called
        mock_webhook_task.delay.assert_called_once()

        # Verify the task was called with tracked_repo.id
        call_args = mock_webhook_task.delay.call_args
        self.assertEqual(call_args[0][0], tracked_repo.id)

    @patch("apps.integrations.tasks.sync_repository_initial_task")
    @patch("apps.integrations.views.helpers._create_repository_webhook")
    def test_toggle_does_not_call_sync_webhook_helper(self, mock_sync_webhook, mock_initial_task):
        """Test that toggle view does NOT call _create_repository_webhook synchronously."""
        # Mock the delay method
        mock_initial_task.delay = MagicMock()

        # Mock webhook helper (should NOT be called in async implementation)
        mock_sync_webhook.return_value = 123456

        # POST to toggle view to track a new repo
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 333333333})
        response = self.client.post(
            url,
            data={"full_name": "acme-corp/no-sync-webhook-repo"},
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful
        self.assertEqual(response.status_code, 200)

        # KEY ASSERTION: Verify _create_repository_webhook was NOT called
        # (it should be called from the task, not from the view)
        mock_sync_webhook.assert_not_called()

    @patch("apps.integrations.tasks.sync_repository_initial_task")
    @patch("apps.integrations.views.helpers._create_repository_webhook")
    def test_toggle_returns_immediately_without_blocking(self, mock_sync_webhook, mock_initial_task):
        """Test that view returns quickly without blocking on webhook creation."""
        # Mock the delay method
        mock_initial_task.delay = MagicMock()

        # Mock webhook creation with artificial delay (should NOT block if async)
        def slow_webhook_creation(*args, **kwargs):
            time.sleep(3)  # 3 second delay
            return 123456

        mock_sync_webhook.side_effect = slow_webhook_creation

        # Measure response time
        start_time = time.time()

        # POST to toggle view to track a new repo
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 444444444})
        response = self.client.post(
            url,
            data={"full_name": "acme-corp/fast-response-repo"},
            HTTP_HX_REQUEST="true",
        )

        elapsed_time = time.time() - start_time

        # Verify response is successful
        self.assertEqual(response.status_code, 200)

        # KEY ASSERTION: View should return quickly (< 1 second) if async
        # If webhook creation is sync, this would take 3+ seconds
        self.assertLess(
            elapsed_time,
            1.0,
            f"View took {elapsed_time:.2f}s but should return immediately (<1s) when webhook creation is async",
        )


class TestWebhookCreationTask(TestCase):
    """Tests for the create_repository_webhook_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})

        # Create GitHub integration
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="fake_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="acme-corp",
            webhook_secret="test_webhook_secret_123",
        )

        # Create a tracked repository without webhook_id
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=555555555,
            full_name="acme-corp/task-test-repo",
            webhook_id=None,  # No webhook yet
        )

    def test_task_exists(self):
        """Test that create_repository_webhook_task is defined."""
        from apps.integrations import tasks

        # KEY ASSERTION: The task should exist
        self.assertTrue(
            hasattr(tasks, "create_repository_webhook_task"),
            "create_repository_webhook_task should be defined in apps.integrations.tasks",
        )

    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_task_creates_webhook_and_updates_repo(self, mock_create_webhook):
        """Test that task calls webhook service and updates TrackedRepository."""
        from apps.integrations.tasks import create_repository_webhook_task

        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 999888777

        # Build the webhook URL (matching what view would pass)
        webhook_url = "https://app.example.com/webhooks/github/"

        # Run the task
        result = create_repository_webhook_task(self.tracked_repo.id, webhook_url)

        # Verify webhook service was called
        mock_create_webhook.assert_called_once_with(
            access_token=self.credential.access_token,
            repo_full_name=self.tracked_repo.full_name,
            webhook_url=webhook_url,
            secret=self.integration.webhook_secret,
        )

        # KEY ASSERTION: Verify TrackedRepository.webhook_id was updated
        self.tracked_repo.refresh_from_db()
        self.assertEqual(
            self.tracked_repo.webhook_id,
            999888777,
            "TrackedRepository.webhook_id should be updated after task completes",
        )

        # Verify result contains the webhook_id
        self.assertEqual(result.get("webhook_id"), 999888777)

    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_task_handles_webhook_creation_failure_gracefully(self, mock_create_webhook):
        """Test that task handles failures without crashing."""
        from apps.integrations.services.github_oauth import GitHubOAuthError
        from apps.integrations.tasks import create_repository_webhook_task

        # Mock webhook creation to raise an error
        mock_create_webhook.side_effect = GitHubOAuthError("Insufficient permissions")

        # Build the webhook URL
        webhook_url = "https://app.example.com/webhooks/github/"

        # Run the task - should not raise exception
        result = create_repository_webhook_task(self.tracked_repo.id, webhook_url)

        # KEY ASSERTION: Task should return error status, not crash
        self.assertIn("error", result)
        self.assertIn("permissions", result["error"].lower())

        # Verify webhook_id remains None
        self.tracked_repo.refresh_from_db()
        self.assertIsNone(
            self.tracked_repo.webhook_id,
            "webhook_id should remain None when webhook creation fails",
        )

    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_task_handles_missing_tracked_repo(self, mock_create_webhook):
        """Test that task handles non-existent TrackedRepository gracefully."""
        from apps.integrations.tasks import create_repository_webhook_task

        # Use a non-existent repo ID
        non_existent_id = 99999999

        # Run the task - should not raise exception
        result = create_repository_webhook_task(non_existent_id, "https://example.com/webhooks/")

        # KEY ASSERTION: Task should return error status
        self.assertIn("error", result)

        # Verify webhook service was NOT called
        mock_create_webhook.assert_not_called()

    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_task_logs_error_on_failure(self, mock_create_webhook):
        """Test that task logs error when webhook creation fails."""
        from apps.integrations.services.github_oauth import GitHubOAuthError
        from apps.integrations.tasks import create_repository_webhook_task

        # Mock webhook creation to raise an error
        mock_create_webhook.side_effect = GitHubOAuthError("API rate limit exceeded")

        webhook_url = "https://app.example.com/webhooks/github/"

        # Run the task with logging captured
        # Logs go to the actual task module location
        with self.assertLogs("apps.integrations._task_modules.github_sync", level="ERROR") as log_context:
            create_repository_webhook_task(self.tracked_repo.id, webhook_url)

        # KEY ASSERTION: Error should be logged
        self.assertTrue(
            any("rate limit" in log.lower() or "webhook" in log.lower() for log in log_context.output),
            "Error should be logged when webhook creation fails",
        )
