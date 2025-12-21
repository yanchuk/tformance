"""Tests for configurable sync depth in github_repo_toggle view."""

from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    UserFactory,
)
from apps.integrations.models import TrackedRepository
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN


class TestGitHubRepoToggleSyncDepth(TestCase):
    """Tests for configurable sync depth in github_repo_toggle view."""

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
    def test_toggle_uses_default_30_days_when_no_days_back(self, mock_initial_task, mock_create_webhook):
        """Test that toggling a repo without days_back parameter uses default 30 days."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method to track calls
        mock_initial_task.delay = MagicMock()

        # POST to toggle view WITHOUT days_back parameter (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 111111111})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/default-repo",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=111111111)
        self.assertIsNotNone(tracked_repo)

        # Verify sync_repository_initial_task.delay was called with default days_back=30
        mock_initial_task.delay.assert_called_once_with(tracked_repo.id, days_back=30)

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_passes_custom_days_back_to_task(self, mock_initial_task, mock_create_webhook):
        """Test that days_back=60 is passed correctly to the sync task."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method to track calls
        mock_initial_task.delay = MagicMock()

        # POST to toggle view with days_back=60 (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 222222222})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/custom-60-repo",
                "days_back": "60",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=222222222)
        self.assertIsNotNone(tracked_repo)

        # Verify sync_repository_initial_task.delay was called with days_back=60
        mock_initial_task.delay.assert_called_once_with(tracked_repo.id, days_back=60)

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_handles_all_history_option(self, mock_initial_task, mock_create_webhook):
        """Test that days_back=0 means sync all history (pass 0 to task)."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method to track calls
        mock_initial_task.delay = MagicMock()

        # POST to toggle view with days_back=0 (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 333333333})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/all-history-repo",
                "days_back": "0",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=333333333)
        self.assertIsNotNone(tracked_repo)

        # Verify sync_repository_initial_task.delay was called with days_back=0 (all history)
        mock_initial_task.delay.assert_called_once_with(tracked_repo.id, days_back=0)

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_ignores_invalid_days_back(self, mock_initial_task, mock_create_webhook):
        """Test that invalid days_back values use default 30."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method to track calls
        mock_initial_task.delay = MagicMock()

        # POST to toggle view with invalid days_back (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 444444444})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/invalid-repo",
                "days_back": "invalid_value",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=444444444)
        self.assertIsNotNone(tracked_repo)

        # Verify sync_repository_initial_task.delay was called with default days_back=30
        mock_initial_task.delay.assert_called_once_with(tracked_repo.id, days_back=30)

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_handles_empty_days_back(self, mock_initial_task, mock_create_webhook):
        """Test that empty days_back string uses default 30."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method to track calls
        mock_initial_task.delay = MagicMock()

        # POST to toggle view with empty days_back (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 555555555})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/empty-repo",
                "days_back": "",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=555555555)
        self.assertIsNotNone(tracked_repo)

        # Verify sync_repository_initial_task.delay was called with default days_back=30
        mock_initial_task.delay.assert_called_once_with(tracked_repo.id, days_back=30)

    @patch("apps.integrations.views.helpers._create_repository_webhook")
    @patch("apps.integrations.tasks.sync_repository_initial_task")
    def test_toggle_handles_negative_days_back(self, mock_initial_task, mock_create_webhook):
        """Test that negative days_back values use default 30."""
        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 123456

        # Mock the delay method to track calls
        mock_initial_task.delay = MagicMock()

        # POST to toggle view with negative days_back (with HTMX headers)
        url = reverse("integrations:github_repo_toggle", kwargs={"repo_id": 666666666})
        response = self.client.post(
            url,
            data={
                "full_name": "acme-corp/negative-repo",
                "days_back": "-10",
            },
            HTTP_HX_REQUEST="true",
        )

        # Verify response is successful (200 for HTMX)
        self.assertEqual(response.status_code, 200)

        # Verify TrackedRepository was created
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=666666666)
        self.assertIsNotNone(tracked_repo)

        # Verify sync_repository_initial_task.delay was called with default days_back=30
        mock_initial_task.delay.assert_called_once_with(tracked_repo.id, days_back=30)
