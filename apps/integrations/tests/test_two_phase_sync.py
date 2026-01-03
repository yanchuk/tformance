"""Tests for Two-Phase Onboarding sync tasks.

TDD GREEN Phase: These tests verify the days_back and skip_recent parameters
work correctly for Phase 1 (30 days) and Phase 2 (31-90 days) sync.

Two-Phase Onboarding:
- Phase 1: sync_historical_data_task(team_id, repo_ids, days_back=30)
- Phase 2: sync_historical_data_task(team_id, repo_ids, days_back=90, skip_recent=30)
"""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory


class TestSyncHistoricalDataTaskDaysBack(TestCase):
    """Tests for days_back parameter in sync_historical_data_task."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(
            integration=self.integration,
            team=self.team,
            full_name="test-org/test-repo",
        )

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService.sync_repository")
    def test_task_accepts_days_back_parameter(self, mock_sync_repo):
        """Test that sync_historical_data_task accepts days_back parameter."""
        from apps.integrations.tasks import sync_historical_data_task

        mock_sync_repo.return_value = {"prs_synced": 10}

        # Call with days_back=30 for Phase 1
        result = sync_historical_data_task(
            self.team.id,
            [self.repo.id],
            days_back=30,
        )

        self.assertEqual(result["status"], "complete")

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService.sync_repository")
    def test_task_passes_days_back_to_service(self, mock_sync_repo):
        """Test that days_back is passed to OnboardingSyncService.sync_repository."""
        from apps.integrations.tasks import sync_historical_data_task

        mock_sync_repo.return_value = {"prs_synced": 10}

        sync_historical_data_task(
            self.team.id,
            [self.repo.id],
            days_back=30,
        )

        # Verify sync_repository was called with days_back
        mock_sync_repo.assert_called_once()
        call_kwargs = mock_sync_repo.call_args.kwargs
        self.assertIn("days_back", call_kwargs)
        self.assertEqual(call_kwargs["days_back"], 30)

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService.sync_repository")
    def test_task_default_days_back_is_90(self, mock_sync_repo):
        """Test that default days_back is 90 (full sync)."""
        from apps.integrations.tasks import sync_historical_data_task

        mock_sync_repo.return_value = {"prs_synced": 10}

        # Call without days_back (should default to 90)
        sync_historical_data_task(
            self.team.id,
            [self.repo.id],
        )

        call_kwargs = mock_sync_repo.call_args.kwargs
        self.assertEqual(call_kwargs.get("days_back", 90), 90)


class TestSyncHistoricalDataTaskSkipRecent(TestCase):
    """Tests for skip_recent parameter in sync_historical_data_task."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(
            integration=self.integration,
            team=self.team,
            full_name="test-org/test-repo",
        )

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService.sync_repository")
    def test_task_accepts_skip_recent_parameter(self, mock_sync_repo):
        """Test that sync_historical_data_task accepts skip_recent parameter."""
        from apps.integrations.tasks import sync_historical_data_task

        mock_sync_repo.return_value = {"prs_synced": 10}

        # Call with skip_recent=30 for Phase 2
        result = sync_historical_data_task(
            self.team.id,
            [self.repo.id],
            days_back=90,
            skip_recent=30,
        )

        self.assertEqual(result["status"], "complete")

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService.sync_repository")
    def test_task_passes_skip_recent_to_service(self, mock_sync_repo):
        """Test that skip_recent is passed to OnboardingSyncService.sync_repository."""
        from apps.integrations.tasks import sync_historical_data_task

        mock_sync_repo.return_value = {"prs_synced": 10}

        sync_historical_data_task(
            self.team.id,
            [self.repo.id],
            days_back=90,
            skip_recent=30,
        )

        call_kwargs = mock_sync_repo.call_args.kwargs
        self.assertIn("skip_recent", call_kwargs)
        self.assertEqual(call_kwargs["skip_recent"], 30)

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService.sync_repository")
    def test_task_default_skip_recent_is_zero(self, mock_sync_repo):
        """Test that default skip_recent is 0 (skip nothing)."""
        from apps.integrations.tasks import sync_historical_data_task

        mock_sync_repo.return_value = {"prs_synced": 10}

        sync_historical_data_task(
            self.team.id,
            [self.repo.id],
            days_back=90,
        )

        call_kwargs = mock_sync_repo.call_args.kwargs
        self.assertEqual(call_kwargs.get("skip_recent", 0), 0)


class TestOnboardingSyncServiceDaysBack(TestCase):
    """Tests for days_back parameter in OnboardingSyncService."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(
            integration=self.integration,
            team=self.team,
            full_name="test-org/test-repo",
        )

    @patch("apps.integrations.services.onboarding_sync.sync_repository_history_graphql")
    def test_sync_repository_accepts_days_back(self, mock_sync_graphql):
        """Test that sync_repository accepts days_back parameter."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        # Mock the async function - async_to_sync will handle wrapping
        mock_sync_graphql.return_value = {"prs_synced": 10}

        service = OnboardingSyncService(team=self.team, github_token="test-token")
        service.sync_repository(repo=self.repo, days_back=30)

        # Verify the GraphQL sync was invoked with days_back parameter
        mock_sync_graphql.assert_called_once()
        call_kwargs = mock_sync_graphql.call_args.kwargs
        self.assertEqual(call_kwargs["days_back"], 30)

    @patch("apps.integrations.services.onboarding_sync.sync_repository_history_graphql")
    def test_sync_repository_accepts_skip_recent(self, mock_sync_graphql):
        """Test that sync_repository accepts skip_recent parameter."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        mock_sync_graphql.return_value = {"prs_synced": 10}

        service = OnboardingSyncService(team=self.team, github_token="test-token")
        # This should not raise an error
        service.sync_repository(repo=self.repo, days_back=90, skip_recent=30)

        mock_sync_graphql.assert_called_once()
        call_kwargs = mock_sync_graphql.call_args.kwargs
        self.assertEqual(call_kwargs["days_back"], 90)
        self.assertEqual(call_kwargs["skip_recent"], 30)
