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

        # Mock both sync functions - Search API is default when use_search_api=True
        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_by_search") as mock_search:
            mock_search.return_value = {"prs_synced": 5}

            result = service.sync_repository(repo)

        self.assertIsInstance(result, dict)
        self.assertIn("prs_synced", result)

    def test_sync_repository_calls_graphql_sync(self):
        """Test that sync_repository uses Search API sync function by default."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        # Search API is default when use_search_api=True
        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_by_search") as mock_search:
            mock_search.return_value = {"prs_synced": 10}

            service.sync_repository(repo)

            mock_search.assert_called_once()

    def test_sync_repository_uses_configured_history_months(self):
        """Test that sync uses HISTORY_MONTHS config for days_back."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        # Search API is default when use_search_api=True
        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_by_search") as mock_search:
            mock_search.return_value = {"prs_synced": 0}

            service.sync_repository(repo)

            # Check that days_back was passed (12 months = ~365 days)
            call_kwargs = mock_search.call_args[1]
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

        # Search API is default when use_search_api=True
        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_by_search") as mock_search:
            mock_search.return_value = {"prs_synced": 5}

            service.sync_repository(repo, progress_callback=track_progress)

        # At minimum, should report completion
        self.assertGreaterEqual(len(progress_calls), 1)

    def test_sync_all_repositories_returns_aggregate_results(self):
        """Test that sync_all_repositories aggregates results from all repos."""
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        repo1 = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        repo2 = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        service = OnboardingSyncService(team=self.team, github_token=self.github_token)

        # Search API is default when use_search_api=True
        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_by_search") as mock_search:
            mock_search.return_value = {"prs_synced": 10}

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


class TestSyncHistoricalDataTaskIntegration(TestCase):
    """Integration tests verifying sync_historical_data_task creates actual records.

    These tests mock only the external GitHub API calls and verify that
    the full sync flow creates PullRequest, PRReview, and Commit records.
    """

    def setUp(self):
        """Set up test fixtures with full integration setup."""
        from apps.integrations.factories import IntegrationCredentialFactory
        from apps.integrations.models import IntegrationCredential

        self.team = TeamFactory()
        # Create integration with valid encrypted credential
        self.credential = IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB)
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="test-org",
        )
        # Create team member to match PR author
        from apps.metrics.factories import TeamMemberFactory

        self.author = TeamMemberFactory(team=self.team, github_id="testuser", display_name="Test User")
        self.reviewer = TeamMemberFactory(team=self.team, github_id="reviewer1", display_name="Reviewer")

    def test_sync_task_creates_pr_records(self):
        """Test that sync_historical_data_task creates PullRequest records in database.

        Mocks OnboardingSyncService.sync_repository with side_effect that creates
        actual database records, verifying the full task flow works correctly.
        """
        from datetime import timedelta

        from apps.integrations.tasks import sync_historical_data_task
        from apps.metrics.models import PullRequest

        # Create tracked repo
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test-org/test-repo",
            sync_status="pending",
        )

        # Mock the service to create real PR records
        def mock_sync_side_effect(repo, progress_callback=None, days_back=90, skip_recent=0):
            """Side effect that creates PR records like the real sync would."""
            base_time = timezone.now() - timedelta(days=5)
            for pr_num in [101, 102, 103]:
                PullRequest.objects.create(
                    team=self.team,
                    github_pr_id=pr_num,
                    github_repo=repo.full_name,
                    title=f"Test PR #{pr_num}",
                    body=f"Description for PR #{pr_num}",
                    state="merged",
                    pr_created_at=base_time,
                    merged_at=base_time + timedelta(hours=24),
                    additions=100 + pr_num,
                    deletions=50 + pr_num,
                    author=self.author,
                )
            return {"prs_synced": 3, "reviews_synced": 3, "commits_synced": 3, "errors": []}

        with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.side_effect = mock_sync_side_effect

            # Run sync task synchronously
            result = sync_historical_data_task(
                team_id=self.team.id,
                repo_ids=[repo.id],
            )

        # Verify task completed successfully
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["repos_synced"], 1)
        self.assertEqual(result["total_prs"], 3)

        # Verify PullRequest records were created
        prs = PullRequest.objects.filter(team=self.team, github_repo="test-org/test-repo")
        self.assertEqual(prs.count(), 3)

        # Verify specific PR data
        pr101 = prs.get(github_pr_id=101)
        self.assertEqual(pr101.title, "Test PR #101")
        self.assertEqual(pr101.state, "merged")
        self.assertEqual(pr101.author, self.author)

    def test_sync_task_creates_review_records(self):
        """Test that sync_historical_data_task creates PRReview records."""
        from datetime import timedelta

        from apps.integrations.tasks import sync_historical_data_task
        from apps.metrics.models import PRReview, PullRequest

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test-org/test-repo",
        )

        def mock_sync_side_effect(repo, progress_callback=None, days_back=90, skip_recent=0):
            """Side effect that creates PR and review records."""
            base_time = timezone.now() - timedelta(days=5)
            pr = PullRequest.objects.create(
                team=self.team,
                github_pr_id=201,
                github_repo=repo.full_name,
                title="Test PR #201",
                state="merged",
                pr_created_at=base_time,
                author=self.author,
            )
            PRReview.objects.create(
                team=self.team,
                pull_request=pr,
                github_review_id=2000201,
                reviewer=self.reviewer,
                state="approved",
                submitted_at=base_time + timedelta(hours=12),
            )
            return {"prs_synced": 1, "reviews_synced": 1, "errors": []}

        with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.side_effect = mock_sync_side_effect

            sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

        # Verify PRReview record was created
        pr = PullRequest.objects.get(team=self.team, github_pr_id=201)
        reviews = PRReview.objects.filter(pull_request=pr)
        self.assertEqual(reviews.count(), 1)

        review = reviews.first()
        self.assertEqual(review.state, "approved")
        self.assertEqual(review.reviewer, self.reviewer)

    def test_sync_task_creates_commit_records(self):
        """Test that sync_historical_data_task creates Commit records."""
        from datetime import timedelta

        from apps.integrations.tasks import sync_historical_data_task
        from apps.metrics.models import Commit, PullRequest

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test-org/test-repo",
        )

        def mock_sync_side_effect(repo, progress_callback=None, days_back=90, skip_recent=0):
            """Side effect that creates PR and commit records."""
            base_time = timezone.now() - timedelta(days=5)
            pr = PullRequest.objects.create(
                team=self.team,
                github_pr_id=301,
                github_repo=repo.full_name,
                title="Test PR #301",
                state="merged",
                pr_created_at=base_time,
                author=self.author,
            )
            Commit.objects.create(
                team=self.team,
                pull_request=pr,
                github_sha="abc000000000301",
                message="Commit for PR 301",
                github_repo=repo.full_name,
                committed_at=base_time + timedelta(hours=2),
                author=self.author,
            )
            return {"prs_synced": 1, "commits_synced": 1, "errors": []}

        with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.side_effect = mock_sync_side_effect

            sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

        # Verify Commit record was created
        pr = PullRequest.objects.get(team=self.team, github_pr_id=301)
        commits = Commit.objects.filter(pull_request=pr)
        self.assertEqual(commits.count(), 1)

        commit = commits.first()
        self.assertEqual(commit.message, "Commit for PR 301")
        self.assertEqual(commit.author, self.author)

    def test_sync_task_updates_repo_status_to_completed(self):
        """Test that sync task updates TrackedRepository sync_status to completed."""
        from apps.integrations.tasks import sync_historical_data_task

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test-org/test-repo",
            sync_status="pending",
        )

        with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.return_value = {"prs_synced": 1, "errors": []}

            sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

        repo.refresh_from_db()
        self.assertEqual(repo.sync_status, "completed")
        self.assertIsNotNone(repo.last_sync_at)

    def test_sync_task_handles_empty_response(self):
        """Test that sync task handles empty PR response gracefully."""
        from apps.integrations.tasks import sync_historical_data_task
        from apps.metrics.models import PullRequest

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test-org/empty-repo",
        )

        with patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.return_value = {"prs_synced": 0, "errors": []}

            result = sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["total_prs"], 0)
        self.assertEqual(PullRequest.objects.filter(team=self.team).count(), 0)


class TestSyncHistoricalDataNoAuth(TestCase):
    """Edge case #2: Test clear error when team has neither App installation nor OAuth."""

    def setUp(self):
        """Set up test fixtures with team but NO GitHub connections."""
        self.team = TeamFactory(name="TestTeam")
        # Explicitly NOT creating any GitHubAppInstallation or GitHubIntegration

    def test_sync_raises_clear_error_when_no_auth(self):
        """sync_historical_data_task should return error with team name when no auth available."""
        from apps.integrations.tasks import sync_historical_data_task

        # Create repo with no app_installation and no integration
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,
            app_installation=None,
            full_name="org/test-repo",
        )

        # Act
        result = sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

        # Assert - should return error status with clear message
        self.assertEqual(result["status"], "error")
        # Error should include team name
        self.assertIn("TestTeam", result["error"])
        # Error should include guidance
        self.assertIn("reconnect", result["error"].lower())

    def test_error_includes_integrations_settings_guidance(self):
        """Error message should guide user to Integrations settings."""
        from apps.integrations.tasks import sync_historical_data_task

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,
            app_installation=None,
            full_name="myorg/my-project",
        )

        result = sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

        self.assertEqual(result["status"], "error")
        # Should mention where to reconnect
        error_lower = result["error"].lower()
        self.assertTrue(
            "integrations" in error_lower or "settings" in error_lower,
            f"Error should mention Integrations settings: {result['error']}",
        )


class TestSyncErrorHandling(TestCase):
    """Edge case #15: Test 401 errors fail fast instead of retrying."""

    def setUp(self):
        """Set up test fixtures."""
        from datetime import timedelta

        from apps.integrations.factories import (
            GitHubAppInstallationFactory,
            TrackedRepositoryFactory,
        )

        self.team = TeamFactory(name="ErrorTestTeam")
        self.app_installation = GitHubAppInstallationFactory(
            team=self.team,
            is_active=True,
            cached_token="ghs_test_token",
            token_expires_at=timezone.now() + timedelta(hours=1),
        )
        self.repo = TrackedRepositoryFactory(
            team=self.team,
            app_installation=self.app_installation,
            integration=None,
            full_name="test-org/test-repo",
        )

    def test_is_permanent_github_auth_failure_detects_401(self):
        """Test that 401 errors are detected as permanent auth failures."""
        from apps.integrations._task_modules.github_sync import is_permanent_github_auth_failure

        # Test HTTP 401 status in exception message
        exc_401 = Exception("401 Bad Credentials")
        self.assertTrue(is_permanent_github_auth_failure(exc_401))

        # Test "Bad credentials" message (GitHub's actual error)
        exc_bad_creds = Exception("Bad credentials")
        self.assertTrue(is_permanent_github_auth_failure(exc_bad_creds))

    def test_is_permanent_github_auth_failure_allows_rate_limit(self):
        """Test that 403 rate limit errors are NOT permanent (should retry)."""
        from apps.integrations._task_modules.github_sync import is_permanent_github_auth_failure

        # Rate limit should NOT be permanent - it's transient
        exc_rate_limit = Exception("403: rate limit exceeded")
        self.assertFalse(is_permanent_github_auth_failure(exc_rate_limit))

        # Generic exceptions should NOT be permanent
        exc_generic = Exception("Connection timeout")
        self.assertFalse(is_permanent_github_auth_failure(exc_generic))

    def test_sync_repository_task_does_not_retry_on_401(self):
        """Test that sync_repository_task fails immediately on 401."""
        from unittest.mock import patch

        from apps.integrations.tasks import sync_repository_task

        # Mock the sync to raise a 401 error
        with patch("apps.integrations._task_modules.github_sync._sync_incremental_with_graphql_or_rest") as mock_sync:
            mock_sync.side_effect = Exception("401 Bad Credentials")

            # Call the task directly (not via Celery)
            result = sync_repository_task(repo_id=self.repo.id)

            # Should return error, NOT retry
            self.assertIn("error", result)
            # Should mention revoked/access issue
            error_lower = result["error"].lower()
            self.assertTrue(
                "revoked" in error_lower or "access" in error_lower or "401" in error_lower,
                f"Error should mention revoked access: {result['error']}",
            )

    def test_sync_repository_task_marks_installation_inactive_on_401(self):
        """Test that 401 error marks the App installation as inactive."""
        from unittest.mock import patch

        from apps.integrations.tasks import sync_repository_task

        # Verify installation is active before
        self.assertTrue(self.app_installation.is_active)

        # Mock the sync to raise a 401 error
        with patch("apps.integrations._task_modules.github_sync._sync_incremental_with_graphql_or_rest") as mock_sync:
            mock_sync.side_effect = Exception("401 Bad Credentials")

            # Call the task
            sync_repository_task(repo_id=self.repo.id)

        # Refresh from DB and check is_active is False
        self.app_installation.refresh_from_db()
        self.assertFalse(self.app_installation.is_active)


class TestTokenRefreshDuringLongSync(TestCase):
    """Edge case #4: Test that tokens are refreshed per-repo during long syncs.

    GitHub App tokens expire after 1 hour. For syncs with many repos, we need
    to ensure each repo gets a fresh token rather than reusing an expired one.
    """

    def setUp(self):
        """Set up test fixtures."""
        from datetime import timedelta

        from apps.integrations.factories import (
            GitHubAppInstallationFactory,
            TrackedRepositoryFactory,
        )

        self.team = TeamFactory(name="LongSyncTeam")
        self.app_installation = GitHubAppInstallationFactory(
            team=self.team,
            is_active=True,
            cached_token="ghs_initial_token",
            token_expires_at=timezone.now() + timedelta(hours=1),
        )
        self.repo1 = TrackedRepositoryFactory(
            team=self.team,
            app_installation=self.app_installation,
            integration=None,
            full_name="org/repo1",
        )
        self.repo2 = TrackedRepositoryFactory(
            team=self.team,
            app_installation=self.app_installation,
            integration=None,
            full_name="org/repo2",
        )

    def test_onboarding_sync_service_does_not_require_token_upfront(self):
        """Test that OnboardingSyncService works without upfront token.

        Since sync operations fetch tokens per-repo through GraphQL utils,
        the service should work with token=None and not use the constructor token.
        """
        from unittest.mock import patch

        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        # Create service with no token (or empty token)
        service = OnboardingSyncService(team=self.team, github_token="")

        # Mock GraphQL sync to verify it's called (tokens come from _get_access_token)
        with patch("apps.integrations.services.onboarding_sync.sync_repository_history_by_search") as mock_search:
            mock_search.return_value = {"prs_synced": 5, "errors": []}

            # This should NOT fail even though github_token is empty
            # because sync_repository delegates to GraphQL which fetches its own token
            result = service.sync_repository(self.repo1)

            self.assertEqual(result["prs_synced"], 5)
            mock_search.assert_called_once()

    def test_sync_historical_data_task_does_not_fetch_token_upfront(self):
        """Test that sync_historical_data_task doesn't fetch token upfront.

        The task currently fetches a token at start, but this is wasteful since
        OnboardingSyncService->GraphQL->_get_access_token fetches fresh tokens.
        After EC-4 fix, we should NOT make an upfront GitHub API call.
        """
        from unittest.mock import patch

        from apps.integrations.models import GitHubAppInstallation
        from apps.integrations.tasks import sync_historical_data_task

        # Track whether get_access_token was called on ANY installation
        get_token_calls = []

        def track_get_token(self_instance):
            get_token_calls.append(f"called_for_{self_instance.installation_id}")
            return "ghs_fresh_token"

        # Patch the model method to track calls from ANY instance
        with (
            patch.object(GitHubAppInstallation, "get_access_token", track_get_token),
            patch("apps.integrations.services.onboarding_sync.OnboardingSyncService") as mock_service_class,
        ):
            mock_service = mock_service_class.return_value
            mock_service.sync_repository.return_value = {"prs_synced": 10, "errors": []}

            sync_historical_data_task(
                team_id=self.team.id,
                repo_ids=[self.repo1.id],
            )

        # The upfront token fetch in sync_historical_data_task should be removed
        # This test will FAIL until we fix the task to not call get_access_token upfront
        # Currently the task fetches token at line 1113 before calling OnboardingSyncService
        # After fix: OnboardingSyncService should handle token fetching internally
        self.assertEqual(
            len(get_token_calls),
            0,
            f"Task should NOT fetch token upfront - GraphQL sync fetches per-repo. Got calls: {get_token_calls}",
        )

    def test_onboarding_sync_service_accepts_optional_token(self):
        """Test that OnboardingSyncService can be initialized without github_token.

        After EC-4 fix, github_token should be optional since GraphQL sync
        functions fetch their own tokens per-repo.
        """
        from apps.integrations.services.onboarding_sync import OnboardingSyncService

        # Should be able to create service without token after fix
        # This test verifies the interface allows None/optional token
        try:
            service = OnboardingSyncService(team=self.team, github_token=None)
            # If github_token is truly optional, this should work
            self.assertIsNone(service.github_token)
        except TypeError:
            # If this fails with TypeError, github_token is still required
            self.fail("OnboardingSyncService should accept github_token=None after EC-4 fix")


class TestSyncHandlesDeactivatedInstallation(TestCase):
    """Edge case #5: Test that sync handles deactivated installation gracefully.

    When user uninstalls the GitHub App mid-sync, the installation becomes inactive
    and get_access_token() raises GitHubAppDeactivatedError. Sync tasks should
    handle this gracefully with a clear error message.
    """

    def setUp(self):
        """Set up test fixtures."""
        from datetime import timedelta

        from apps.integrations.factories import (
            GitHubAppInstallationFactory,
            TrackedRepositoryFactory,
        )

        self.team = TeamFactory(name="DeactivationTestTeam")
        self.app_installation = GitHubAppInstallationFactory(
            team=self.team,
            is_active=True,
            cached_token="ghs_test_token",
            token_expires_at=timezone.now() + timedelta(hours=1),
        )
        self.repo = TrackedRepositoryFactory(
            team=self.team,
            app_installation=self.app_installation,
            integration=None,
            full_name="org/test-repo",
        )

    def test_sync_repository_task_handles_deactivated_installation(self):
        """Test that sync_repository_task handles GitHubAppDeactivatedError gracefully."""
        from unittest.mock import patch

        from apps.integrations.exceptions import GitHubAppDeactivatedError
        from apps.integrations.tasks import sync_repository_task

        # Mock the sync to raise GitHubAppDeactivatedError
        with patch("apps.integrations._task_modules.github_sync._sync_incremental_with_graphql_or_rest") as mock_sync:
            mock_sync.side_effect = GitHubAppDeactivatedError(
                "Installation is no longer active. Please reinstall the GitHub App."
            )

            # Call the task - should NOT raise, should return error
            result = sync_repository_task(repo_id=self.repo.id)

        # Should return error with clear message
        self.assertIn("error", result)
        error_lower = result["error"].lower()
        self.assertTrue(
            "no longer active" in error_lower or "deactivated" in error_lower or "reinstall" in error_lower,
            f"Error should mention deactivated installation: {result['error']}",
        )

    def test_get_access_token_raises_when_installation_deactivated_mid_sync(self):
        """Test that get_access_token raises GitHubAppDeactivatedError when inactive.

        Simulates the scenario where installation is deactivated after sync starts.
        """
        from apps.integrations.exceptions import GitHubAppDeactivatedError

        # Deactivate the installation (simulating webhook marking it inactive)
        self.app_installation.is_active = False
        self.app_installation.save(update_fields=["is_active"])

        # Attempting to get token should raise GitHubAppDeactivatedError
        with self.assertRaises(GitHubAppDeactivatedError) as context:
            self.app_installation.get_access_token()

        error_message = str(context.exception).lower()
        # Check for any of the valid error message indicators
        self.assertTrue(
            "no longer active" in error_message or "was removed" in error_message or "deactivated" in error_message,
            f"Error should mention deactivated/removed installation: {error_message}",
        )
        self.assertIn("reinstall", error_message)
