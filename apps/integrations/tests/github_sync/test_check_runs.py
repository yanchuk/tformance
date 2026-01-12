"""Tests for GitHub sync service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    sync_pr_check_runs,
)


class TestSyncPRCheckRuns(TestCase):
    """Tests for syncing check runs from a GitHub pull request."""

    def _create_mock_check_run(
        self,
        check_run_id: int,
        name: str,
        status: str,
        conclusion: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> MagicMock:
        """Create a mock PyGithub CheckRun object with all required attributes."""
        mock_check_run = MagicMock()
        mock_check_run.id = check_run_id
        mock_check_run.name = name
        mock_check_run.status = status
        mock_check_run.conclusion = conclusion
        mock_check_run.started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00")) if started_at else None
        mock_check_run.completed_at = (
            datetime.fromisoformat(completed_at.replace("Z", "+00:00")) if completed_at else None
        )
        return mock_check_run

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_check_runs_creates_records(self, mock_github_class):
        """Test that sync_pr_check_runs creates PRCheckRun records from GitHub check runs."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRCheckRun

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345", display_name="John Dev")
        pr = PullRequestFactory(
            team=team,
            github_pr_id=101,
            github_repo="acme/repo",
            author=member,
        )

        # Mock check runs
        mock_check_run1 = self._create_mock_check_run(
            check_run_id=11111,
            name="pytest",
            status="completed",
            conclusion="success",
            started_at="2025-01-01T10:00:00Z",
            completed_at="2025-01-01T10:05:00Z",
        )
        mock_check_run2 = self._create_mock_check_run(
            check_run_id=22222,
            name="eslint",
            status="completed",
            conclusion="failure",
            started_at="2025-01-01T10:00:00Z",
            completed_at="2025-01-01T10:02:00Z",
        )

        # Mock check runs response
        mock_check_runs = MagicMock()
        mock_check_runs.__iter__ = MagicMock(return_value=iter([mock_check_run1, mock_check_run2]))

        # Mock commit object
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = mock_check_runs

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_commit.return_value = mock_commit
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Mock the PR to return head SHA
        mock_pr = MagicMock()
        mock_pr.head.sha = "abc123def456"
        mock_repo.get_pull.return_value = mock_pr

        # Call sync function
        access_token = "gho_test_token"
        errors = []
        sync_pr_check_runs(
            pr=pr,
            pr_number=101,
            access_token=access_token,
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify check runs were created
        check_runs = PRCheckRun.objects.filter(team=team, pull_request=pr).order_by("github_check_run_id")
        self.assertEqual(check_runs.count(), 2)

        # Check first check run
        check_run1 = check_runs[0]
        self.assertEqual(check_run1.github_check_run_id, 11111)
        self.assertEqual(check_run1.name, "pytest")
        self.assertEqual(check_run1.status, "completed")
        self.assertEqual(check_run1.conclusion, "success")
        self.assertEqual(check_run1.pull_request, pr)
        self.assertIsNotNone(check_run1.started_at)
        self.assertIsNotNone(check_run1.completed_at)

        # Check second check run
        check_run2 = check_runs[1]
        self.assertEqual(check_run2.github_check_run_id, 22222)
        self.assertEqual(check_run2.name, "eslint")
        self.assertEqual(check_run2.conclusion, "failure")

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_check_runs_calculates_duration(self, mock_github_class):
        """Test that sync_pr_check_runs calculates duration_seconds from started_at and completed_at."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRCheckRun

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=102, github_repo="acme/repo", author=member)

        # Mock check run with 5 minute duration (300 seconds)
        mock_check_run = self._create_mock_check_run(
            check_run_id=33333,
            name="build",
            status="completed",
            conclusion="success",
            started_at="2025-01-01T10:00:00Z",
            completed_at="2025-01-01T10:05:00Z",  # 5 minutes later
        )

        # Mock check runs response
        mock_check_runs = MagicMock()
        mock_check_runs.__iter__ = MagicMock(return_value=iter([mock_check_run]))

        # Mock commit object
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = mock_check_runs

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_commit.return_value = mock_commit
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Mock the PR to return head SHA
        mock_pr = MagicMock()
        mock_pr.head.sha = "abc123def456"
        mock_repo.get_pull.return_value = mock_pr

        # Call sync function
        errors = []
        sync_pr_check_runs(
            pr=pr,
            pr_number=102,
            access_token="gho_test_token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify duration was calculated correctly
        check_run = PRCheckRun.objects.get(team=team, github_check_run_id=33333)
        self.assertEqual(check_run.duration_seconds, 300)  # 5 minutes = 300 seconds

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_check_runs_handles_pending_check(self, mock_github_class):
        """Test that sync_pr_check_runs handles in_progress check runs with no conclusion."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRCheckRun

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=103, github_repo="acme/repo", author=member)

        # Mock check run that's still in progress
        mock_check_run = self._create_mock_check_run(
            check_run_id=44444,
            name="deploy",
            status="in_progress",
            conclusion=None,  # No conclusion yet
            started_at="2025-01-01T10:00:00Z",
            completed_at=None,  # Not completed yet
        )

        # Mock check runs response
        mock_check_runs = MagicMock()
        mock_check_runs.__iter__ = MagicMock(return_value=iter([mock_check_run]))

        # Mock commit object
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = mock_check_runs

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_commit.return_value = mock_commit
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Mock the PR to return head SHA
        mock_pr = MagicMock()
        mock_pr.head.sha = "abc123def456"
        mock_repo.get_pull.return_value = mock_pr

        # Call sync function
        errors = []
        sync_pr_check_runs(
            pr=pr,
            pr_number=103,
            access_token="gho_test_token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify check run was created with correct state
        check_run = PRCheckRun.objects.get(team=team, github_check_run_id=44444)
        self.assertEqual(check_run.status, "in_progress")
        self.assertIsNone(check_run.conclusion)
        self.assertIsNone(check_run.completed_at)
        self.assertIsNone(check_run.duration_seconds)  # No duration if not completed

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_check_runs_updates_existing(self, mock_github_class):
        """Test that sync_pr_check_runs updates existing check runs (idempotent)."""
        from apps.metrics.factories import PRCheckRunFactory, PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRCheckRun

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=104, github_repo="acme/repo", author=member)

        # Create existing check run that's in progress
        PRCheckRunFactory(
            team=team,
            pull_request=pr,
            github_check_run_id=55555,
            name="integration-tests",
            status="in_progress",
            conclusion=None,
            started_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
            completed_at=None,
            duration_seconds=None,
        )

        # Mock updated check run (now completed)
        mock_check_run = self._create_mock_check_run(
            check_run_id=55555,  # Same ID
            name="integration-tests",
            status="completed",  # Updated status
            conclusion="success",  # Now has conclusion
            started_at="2025-01-01T10:00:00Z",
            completed_at="2025-01-01T10:10:00Z",  # Now completed
        )

        # Mock check runs response
        mock_check_runs = MagicMock()
        mock_check_runs.__iter__ = MagicMock(return_value=iter([mock_check_run]))

        # Mock commit object
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = mock_check_runs

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_commit.return_value = mock_commit
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Mock the PR to return head SHA
        mock_pr = MagicMock()
        mock_pr.head.sha = "abc123def456"
        mock_repo.get_pull.return_value = mock_pr

        # Call sync function
        errors = []
        sync_pr_check_runs(
            pr=pr,
            pr_number=104,
            access_token="gho_test_token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify only one check run exists (not duplicated)
        self.assertEqual(PRCheckRun.objects.filter(team=team, github_check_run_id=55555).count(), 1)

        # Verify check run was updated
        check_run = PRCheckRun.objects.get(team=team, github_check_run_id=55555)
        self.assertEqual(check_run.status, "completed")
        self.assertEqual(check_run.conclusion, "success")
        self.assertIsNotNone(check_run.completed_at)
        self.assertEqual(check_run.duration_seconds, 600)  # 10 minutes = 600 seconds
