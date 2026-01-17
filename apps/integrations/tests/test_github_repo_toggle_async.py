"""Tests for async background sync in github_repo_toggle view."""

from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.constants import SYNC_STATUS_PENDING
from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    UserFactory,
)
from apps.integrations.models import TrackedRepository
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN


class TestGitHubRepoToggleAsync(TestCase):
    """Tests for async background sync in github_repo_toggle view."""

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

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_toggle_queues_background_sync_task(self, mock_sync_history, mock_initial_task, mock_create_webhook):
        """Test that toggling a repo queues sync_repository_initial_task.delay."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method to track calls
        mock_initial_task.delay = MagicMock()

        # POST to toggle view to track a new repo (with HTMX headers to get 200 response)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 987654321})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/test-repo",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=987654321)
        self.assertIsNotNone(tracked_repo)

        # Verify sync_repository_initial_task.delay was called with repo.id and days_back
        mock_initial_task.delay.assert_called_once_with(tracked_repo.id, days_back=30)

        # Verify sync_repository_history was NOT called synchronously
        mock_sync_history.assert_not_called()

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_toggle_does_not_call_sync_synchronously(self, mock_sync_history, mock_initial_task, mock_create_webhook):
        """Test that github_repo_toggle does NOT call sync_repository_history synchronously."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method
        mock_initial_task.delay = MagicMock()

        # POST to toggle view to track a new repo (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 888888888})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/another-repo",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify sync_repository_history was NOT called
        mock_sync_history.assert_not_called()

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_sets_pending_status(self, mock_initial_task, mock_create_webhook):
        """Test that TrackedRepository is created with sync_status=PENDING."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method
        mock_initial_task.delay = MagicMock()

        # POST to toggle view to track a new repo (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 777777777})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/status-test-repo",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created with sync_status=PENDING
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=777777777)
        self.assertEqual(tracked_repo.sync_status, SYNC_STATUS_PENDING)

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_toggle_returns_immediately(self, mock_sync_history, mock_initial_task, mock_create_webhook):
        """Test that view returns quickly without blocking on sync."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method
        mock_initial_task.delay = MagicMock()

        # Mock sync_repository_history to simulate slow sync (should never be called)
        import time

        def slow_sync(*args, **kwargs):
            time.sleep(5)  # This should never run
            return {"prs_synced": 10}

        mock_sync_history.side_effect = slow_sync

        # Measure response time

        start_time = time.time()

        # POST to toggle view to track a new repo (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 666666666})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/fast-repo",
            },
            HTTP_HX_REQUEST="true",
        )

        elapsed_time = time.time() - start_time

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify view returned quickly (less than 2 seconds)
        # If sync was called synchronously, this would take 5+ seconds
        self.assertLess(elapsed_time, 2.0, "View should return immediately without blocking on sync")

        # Verify sync_repository_history was NOT called (so the slow_sync never ran)
        mock_sync_history.assert_not_called()


class TestGitHubRepoTogglePipelineTrigger(TestCase):
    """Tests for onboarding pipeline triggering in github_repo_toggle view.

    These tests verify that when a repo is toggled ON and the team's
    pipeline status is 'not_started', the onboarding pipeline is triggered
    automatically. This enables LLM analysis, metrics aggregation, and
    insights computation to run after the initial sync.
    """

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

    @patch("apps.integrations.onboarding_pipeline.start_onboarding_pipeline")
    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_triggers_pipeline_when_not_started(
        self, mock_initial_task, mock_create_webhook, mock_start_pipeline
    ):
        """Test that enabling a repo triggers pipeline when status is 'not_started'."""
        # Ensure team pipeline status is 'not_started'
        self.team.onboarding_pipeline_status = "not_started"
        self.team.save()

        # Mock the delay method
        mock_initial_task.delay = MagicMock()
        mock_create_webhook.return_value = 123456

        # POST to toggle view to track a new repo
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 111111111})
        response = self.client.post(
            url,
            data={"full_name": "acme-corp/pipeline-test-repo"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=111111111)

        # Verify start_onboarding_pipeline was called with team_id and repo_id
        mock_start_pipeline.assert_called_once_with(self.team.id, [tracked_repo.id])

    @patch("apps.integrations.onboarding_pipeline.start_onboarding_pipeline")
    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_does_not_trigger_pipeline_when_already_running(
        self, mock_initial_task, mock_create_webhook, mock_start_pipeline
    ):
        """Test that enabling a repo does NOT trigger pipeline when already syncing."""
        # Set team pipeline status to 'syncing' (already running)
        self.team.onboarding_pipeline_status = "syncing"
        self.team.save()

        # Mock the delay method
        mock_initial_task.delay = MagicMock()
        mock_create_webhook.return_value = 123456

        # POST to toggle view to track a new repo
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 222222222})
        response = self.client.post(
            url,
            data={"full_name": "acme-corp/running-pipeline-repo"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)

        # Verify start_onboarding_pipeline was NOT called (pipeline already running)
        mock_start_pipeline.assert_not_called()

    @patch("apps.integrations.onboarding_pipeline.start_onboarding_pipeline")
    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_does_not_trigger_pipeline_when_complete(
        self, mock_initial_task, mock_create_webhook, mock_start_pipeline
    ):
        """Test that enabling a repo does NOT trigger pipeline when already complete."""
        # Set team pipeline status to 'complete'
        self.team.onboarding_pipeline_status = "complete"
        self.team.save()

        # Mock the delay method
        mock_initial_task.delay = MagicMock()
        mock_create_webhook.return_value = 123456

        # POST to toggle view to track a new repo
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 333333333})
        response = self.client.post(
            url,
            data={"full_name": "acme-corp/complete-pipeline-repo"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)

        # Verify start_onboarding_pipeline was NOT called (pipeline already complete)
        mock_start_pipeline.assert_not_called()

    @patch("apps.integrations.onboarding_pipeline.start_onboarding_pipeline")
    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_still_queues_initial_sync_task(self, mock_initial_task, mock_create_webhook, mock_start_pipeline):
        """Test that initial sync task is queued even when pipeline is triggered."""
        # Ensure team pipeline status is 'not_started'
        self.team.onboarding_pipeline_status = "not_started"
        self.team.save()

        # Mock the delay method
        mock_initial_task.delay = MagicMock()
        mock_create_webhook.return_value = 123456

        # POST to toggle view to track a new repo
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 444444444})
        response = self.client.post(
            url,
            data={"full_name": "acme-corp/both-tasks-repo"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=444444444)

        # Verify sync_repository_initial_task.delay was called
        mock_initial_task.delay.assert_called_once_with(tracked_repo.id, days_back=30)

        # Verify start_onboarding_pipeline was also called
        mock_start_pipeline.assert_called_once()
