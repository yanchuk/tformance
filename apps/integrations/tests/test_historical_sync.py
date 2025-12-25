"""Tests for historical sync utilities and services."""

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.integrations.models import TrackedRepository
from apps.metrics.factories import PullRequestFactory, TeamFactory


class TestCalculateSyncDateRange(TestCase):
    """Tests for calculate_sync_date_range function."""

    def test_returns_tuple_of_dates(self):
        """Test that function returns a tuple of two dates."""
        from apps.integrations.services.historical_sync import calculate_sync_date_range

        result = calculate_sync_date_range()

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], date)
        self.assertIsInstance(result[1], date)

    def test_end_date_is_today(self):
        """Test that end date is today."""
        from apps.integrations.services.historical_sync import calculate_sync_date_range

        _, end_date = calculate_sync_date_range()

        self.assertEqual(end_date, date.today())

    def test_default_12_months_back(self):
        """Test that default is 12 months of history."""
        from apps.integrations.services.historical_sync import calculate_sync_date_range

        start_date, end_date = calculate_sync_date_range()

        # Should be at least 12 months of data
        days_diff = (end_date - start_date).days
        self.assertGreaterEqual(days_diff, 365)

    def test_start_date_is_first_of_month(self):
        """Test that start date is extended to beginning of month."""
        from apps.integrations.services.historical_sync import calculate_sync_date_range

        start_date, _ = calculate_sync_date_range()

        # Start date should always be day 1
        self.assertEqual(start_date.day, 1)

    @patch("apps.integrations.services.historical_sync.date")
    def test_mid_month_extends_to_start_of_month(self, mock_date):
        """Test that date range extends to start of earliest month.

        Example: Dec 25, 2025 - 12 months = Dec 25, 2024 → Dec 1, 2024
        """
        from apps.integrations.services.historical_sync import calculate_sync_date_range

        # Mock today as Dec 25, 2025
        mock_date.today.return_value = date(2025, 12, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        start_date, end_date = calculate_sync_date_range(months=12)

        # End date should be Dec 25, 2025
        self.assertEqual(end_date, date(2025, 12, 25))
        # Start should be Dec 1, 2024 (12 months back, then to start of month)
        self.assertEqual(start_date, date(2024, 12, 1))

    def test_custom_months_parameter(self):
        """Test that months parameter changes date range."""
        from apps.integrations.services.historical_sync import calculate_sync_date_range

        start_6, _ = calculate_sync_date_range(months=6)
        start_24, _ = calculate_sync_date_range(months=24)

        # 24 months should go further back than 6 months
        self.assertLess(start_24, start_6)

    @patch("apps.integrations.services.historical_sync.date")
    def test_first_of_month_stays_same(self, mock_date):
        """Test that if 12 months back lands on day 1, it stays."""
        from apps.integrations.services.historical_sync import calculate_sync_date_range

        # Mock today as Jan 1, 2025
        mock_date.today.return_value = date(2025, 1, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        start_date, end_date = calculate_sync_date_range(months=12)

        # 12 months back from Jan 1, 2025 = Jan 1, 2024
        self.assertEqual(start_date, date(2024, 1, 1))


class TestPrioritizeRepositories(TestCase):
    """Tests for prioritize_repositories function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)

    def test_returns_list(self):
        """Test that function returns a list."""
        from apps.integrations.services.historical_sync import prioritize_repositories

        repos = TrackedRepository.objects.filter(team=self.team)

        result = prioritize_repositories(repos)

        self.assertIsInstance(result, list)

    def test_orders_by_recent_pr_count_descending(self):
        """Test that repos are ordered by PR count in last 6 months (descending)."""
        from apps.integrations.services.historical_sync import prioritize_repositories

        # Create 3 repos with different PR counts
        repo_low = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/low-activity",
        )
        repo_high = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/high-activity",
        )
        repo_medium = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/medium-activity",
        )

        # Create PRs in last 6 months
        recent_date = timezone.now() - timedelta(days=30)

        # High activity: 10 PRs
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                github_repo=repo_high.full_name,
                pr_created_at=recent_date,
            )

        # Medium activity: 5 PRs
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                github_repo=repo_medium.full_name,
                pr_created_at=recent_date,
            )

        # Low activity: 1 PR
        PullRequestFactory(
            team=self.team,
            github_repo=repo_low.full_name,
            pr_created_at=recent_date,
        )

        repos = TrackedRepository.objects.filter(team=self.team)
        result = prioritize_repositories(repos)

        # Should be ordered: high (10), medium (5), low (1)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].id, repo_high.id)
        self.assertEqual(result[1].id, repo_medium.id)
        self.assertEqual(result[2].id, repo_low.id)

    def test_ignores_old_prs(self):
        """Test that PRs older than 6 months don't affect priority."""
        from apps.integrations.services.historical_sync import prioritize_repositories

        repo_old_activity = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/old-activity",
        )
        repo_new_activity = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/new-activity",
        )

        # Old PRs (8 months ago) - should not count
        old_date = timezone.now() - timedelta(days=240)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                github_repo=repo_old_activity.full_name,
                pr_created_at=old_date,
            )

        # New PRs (1 month ago) - should count
        recent_date = timezone.now() - timedelta(days=30)
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                github_repo=repo_new_activity.full_name,
                pr_created_at=recent_date,
            )

        repos = TrackedRepository.objects.filter(team=self.team)
        result = prioritize_repositories(repos)

        # New activity should be first (3 recent PRs > 0 recent PRs)
        self.assertEqual(result[0].id, repo_new_activity.id)
        self.assertEqual(result[1].id, repo_old_activity.id)

    def test_repos_with_zero_prs(self):
        """Test handling of repos with no PRs."""
        from apps.integrations.services.historical_sync import prioritize_repositories

        repo_empty = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/empty-repo",
        )
        repo_with_prs = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/active-repo",
        )

        recent_date = timezone.now() - timedelta(days=30)
        PullRequestFactory(
            team=self.team,
            github_repo=repo_with_prs.full_name,
            pr_created_at=recent_date,
        )

        repos = TrackedRepository.objects.filter(team=self.team)
        result = prioritize_repositories(repos)

        # Active repo should be first
        self.assertEqual(result[0].id, repo_with_prs.id)
        self.assertEqual(result[1].id, repo_empty.id)

    def test_single_repo(self):
        """Test handling of single repo."""
        from apps.integrations.services.historical_sync import prioritize_repositories

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/only-repo",
        )

        repos = TrackedRepository.objects.filter(team=self.team)
        result = prioritize_repositories(repos)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, repo.id)

    def test_empty_queryset(self):
        """Test handling of empty queryset."""
        from apps.integrations.services.historical_sync import prioritize_repositories

        repos = TrackedRepository.objects.filter(team=self.team)  # Empty
        result = prioritize_repositories(repos)

        self.assertEqual(result, [])


class TestSyncHistoricalDataTask(TestCase):
    """Tests for sync_historical_data_task Celery task."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)

    def test_task_exists(self):
        """Test that the task is registered."""
        from apps.integrations.tasks import sync_historical_data_task

        self.assertTrue(callable(sync_historical_data_task))

    def test_task_updates_repo_sync_status(self):
        """Test that task updates TrackedRepository sync_status."""
        from apps.integrations.tasks import sync_historical_data_task

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            sync_status="pending",
        )

        # Run task synchronously
        with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.return_value = {"prs_synced": 10}

            sync_historical_data_task(
                team_id=self.team.id,
                repo_ids=[repo.id],
            )

        repo.refresh_from_db()
        self.assertEqual(repo.sync_status, "completed")

    def test_task_returns_result(self):
        """Test that task returns expected result structure."""
        from apps.integrations.tasks import sync_historical_data_task

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
        )

        with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.return_value = {"prs_synced": 10}

            result = sync_historical_data_task(
                team_id=self.team.id,
                repo_ids=[repo.id],
            )

        self.assertIn("status", result)
        self.assertEqual(result["status"], "complete")
        self.assertIn("repos_synced", result)

    def test_task_handles_failed_repo(self):
        """Test that task continues on repo failure and marks as failed."""
        from apps.integrations.tasks import sync_historical_data_task

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            sync_status="pending",
        )

        with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.side_effect = Exception("GitHub API error")

            # Should not raise
            sync_historical_data_task(
                team_id=self.team.id,
                repo_ids=[repo.id],
            )

        repo.refresh_from_db()
        self.assertEqual(repo.sync_status, "failed")
        self.assertIn("GitHub API error", repo.last_sync_error or "")


class TestOnboardingSyncService(TestCase):
    """Tests for OnboardingSyncService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.github_token = "fake_token_12345"

    def test_service_initialization(self):
        """Test that service initializes with team and token."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        self.assertEqual(service.team, self.team)
        self.assertEqual(service.github_token, self.github_token)

    def test_sync_repository_returns_dict(self):
        """Test that sync_repository returns a dict with expected keys."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_graphql") as mock_sync:
            mock_sync.return_value = {"prs_synced": 5}

            result = service.sync_repository(repo)

        self.assertIsInstance(result, dict)
        self.assertIn("prs_synced", result)

    def test_sync_repository_calls_graphql_sync(self):
        """Test that sync_repository uses GraphQL sync function."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_graphql") as mock_sync:
            mock_sync.return_value = {"prs_synced": 10}

            service.sync_repository(repo)

            mock_sync.assert_called_once()

    def test_sync_repository_uses_configured_history_months(self):
        """Test that sync uses HISTORY_MONTHS config for days_back."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_graphql") as mock_sync:
            mock_sync.return_value = {"prs_synced": 0}

            service.sync_repository(repo)

            # Check that days_back was passed (12 months = ~365 days)
            call_kwargs = mock_sync.call_args[1]
            self.assertIn("days_back", call_kwargs)
            self.assertGreaterEqual(call_kwargs["days_back"], 365)

    def test_sync_repository_progress_callback(self):
        """Test that progress callback is invoked during sync."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        progress_calls = []

        def track_progress(prs_completed, prs_total, message):
            progress_calls.append((prs_completed, prs_total, message))

        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_graphql") as mock_sync:
            mock_sync.return_value = {"prs_synced": 5}

            service.sync_repository(repo, progress_callback=track_progress)

        # At minimum, should report completion
        self.assertGreaterEqual(len(progress_calls), 1)

    def test_sync_all_repositories_returns_aggregate_results(self):
        """Test that sync_all_repositories aggregates results from all repos."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        repo1 = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        repo2 = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_graphql") as mock_sync:
            mock_sync.return_value = {"prs_synced": 10}

            result = service.sync_all_repositories([repo1, repo2])

        self.assertIn("repos_synced", result)
        self.assertEqual(result["repos_synced"], 2)
        self.assertIn("total_prs", result)
        self.assertEqual(result["total_prs"], 20)


class TestOnboardingSyncSignals(TestCase):
    """Tests for onboarding sync Django signals."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.github_token = "fake_token_12345"

    def test_signals_exist(self):
        """Test that sync signals are defined."""
        from django.dispatch import Signal

        from apps.integrations.signals import (
            onboarding_sync_completed,
            onboarding_sync_started,
            repository_sync_completed,
        )

        self.assertIsInstance(onboarding_sync_started, Signal)
        self.assertIsInstance(onboarding_sync_completed, Signal)
        self.assertIsInstance(repository_sync_completed, Signal)

    def test_onboarding_sync_started_signal_sent(self):
        """Test that onboarding_sync_started signal is sent when sync begins."""
        from apps.integrations.signals import onboarding_sync_started

        received_signals = []

        def handler(sender, **kwargs):
            received_signals.append(kwargs)

        onboarding_sync_started.connect(handler)

        try:
            from apps.integrations.tasks import sync_historical_data_task

            repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

            with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.sync_repository.return_value = {"prs_synced": 5}

                sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

            self.assertEqual(len(received_signals), 1)
            self.assertEqual(received_signals[0]["team_id"], self.team.id)
        finally:
            onboarding_sync_started.disconnect(handler)

    def test_onboarding_sync_completed_signal_sent(self):
        """Test that onboarding_sync_completed signal is sent when sync finishes."""
        from apps.integrations.signals import onboarding_sync_completed

        received_signals = []

        def handler(sender, **kwargs):
            received_signals.append(kwargs)

        onboarding_sync_completed.connect(handler)

        try:
            from apps.integrations.tasks import sync_historical_data_task

            repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

            with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.sync_repository.return_value = {"prs_synced": 10}

                sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

            self.assertEqual(len(received_signals), 1)
            self.assertEqual(received_signals[0]["team_id"], self.team.id)
            self.assertEqual(received_signals[0]["repos_synced"], 1)
            self.assertEqual(received_signals[0]["total_prs"], 10)
        finally:
            onboarding_sync_completed.disconnect(handler)

    def test_repository_sync_completed_signal_sent(self):
        """Test that repository_sync_completed signal is sent for each repo."""
        from apps.integrations.signals import repository_sync_completed

        received_signals = []

        def handler(sender, **kwargs):
            received_signals.append(kwargs)

        repository_sync_completed.connect(handler)

        try:
            from apps.integrations.tasks import sync_historical_data_task

            repo1 = TrackedRepositoryFactory(team=self.team, integration=self.integration)
            repo2 = TrackedRepositoryFactory(team=self.team, integration=self.integration)

            with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.sync_repository.return_value = {"prs_synced": 5}

                sync_historical_data_task(team_id=self.team.id, repo_ids=[repo1.id, repo2.id])

            # Should have received 2 signals (one per repo)
            self.assertEqual(len(received_signals), 2)
            repo_ids_signaled = {s["repo_id"] for s in received_signals}
            self.assertEqual(repo_ids_signaled, {repo1.id, repo2.id})
        finally:
            repository_sync_completed.disconnect(handler)
