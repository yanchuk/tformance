"""
Tests for real project seeding functionality.

Follows TDD approach - tests written before bug fixes.
"""

from datetime import UTC, datetime
from unittest.mock import patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import PRCheckRun, PRFile
from apps.metrics.seeding.github_authenticated_fetcher import (
    FetchedCheckRun,
    FetchedFile,
    FetchedPRFull,
)
from apps.metrics.seeding.real_project_seeder import RealProjectSeeder
from apps.metrics.seeding.real_projects import RealProjectConfig


class TestFetchedFileMapping(TestCase):
    """Tests for mapping FetchedFile to PRFile model."""

    def test_fetched_file_has_correct_fields(self):
        """FetchedFile should have filename, status, additions, deletions, patch."""
        file = FetchedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ -1,5 +1,10 @@",
        )

        self.assertEqual(file.filename, "src/main.py")
        self.assertEqual(file.status, "modified")
        self.assertEqual(file.additions, 10)
        self.assertEqual(file.deletions, 5)
        self.assertEqual(file.patch, "@@ -1,5 +1,10 @@")

    def test_fetched_file_changes_computed_from_additions_deletions(self):
        """Changes should be computed as additions + deletions when creating PRFile."""
        file = FetchedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
        )

        # Changes should be computed, not stored on FetchedFile
        expected_changes = file.additions + file.deletions
        self.assertEqual(expected_changes, 15)


class TestFetchedCheckRunMapping(TestCase):
    """Tests for mapping FetchedCheckRun to PRCheckRun model."""

    def test_fetched_check_run_has_correct_fields(self):
        """FetchedCheckRun should have github_id, name, status, conclusion, started_at, completed_at."""
        check = FetchedCheckRun(
            github_id=123456,
            name="pytest",
            status="completed",
            conclusion="success",
            started_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
            completed_at=datetime(2025, 1, 1, 10, 5, 0, tzinfo=UTC),
        )

        self.assertEqual(check.github_id, 123456)
        self.assertEqual(check.name, "pytest")
        self.assertEqual(check.status, "completed")
        self.assertEqual(check.conclusion, "success")
        self.assertIsNotNone(check.started_at)
        self.assertIsNotNone(check.completed_at)

    def test_fetched_check_run_duration_computed(self):
        """Duration should be computed from started_at and completed_at."""
        check = FetchedCheckRun(
            github_id=123456,
            name="pytest",
            status="completed",
            conclusion="success",
            started_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
            completed_at=datetime(2025, 1, 1, 10, 5, 0, tzinfo=UTC),
        )

        # Duration should be computed, not stored on FetchedCheckRun
        duration = None
        if check.started_at and check.completed_at:
            duration = int((check.completed_at - check.started_at).total_seconds())

        self.assertEqual(duration, 300)  # 5 minutes in seconds


class TestRealProjectSeederPRFileCreation(TestCase):
    """Tests for RealProjectSeeder._create_pr_files method."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.config = RealProjectConfig(
            repos=("test/repo",),
            team_name="Test Team",
            team_slug="test-team",
            max_prs=5,
            max_members=2,
            days_back=14,
            jira_project_key="TEST",
            ai_base_adoption_rate=0.3,
        )

    @patch("apps.metrics.seeding.real_project_seeder.GitHubAuthenticatedFetcher")
    def test_create_pr_files_uses_computed_changes(self, mock_fetcher_class):
        """_create_pr_files should compute changes from additions + deletions."""
        from apps.metrics.factories import PullRequestFactory

        # Create a PR
        pr = PullRequestFactory(team=self.team)

        # Create FetchedFile without changes field
        file_data = FetchedFile(
            filename="src/main.py",
            status="modified",
            additions=25,
            deletions=10,
        )

        # Create FetchedPRFull with the file
        now = datetime.now(UTC)
        pr_data = FetchedPRFull(
            github_pr_id=123,
            number=1,
            github_repo="test/repo",
            title="Test PR",
            body="Test body",
            state="merged",
            is_merged=True,
            is_draft=False,
            created_at=now,
            updated_at=now,
            merged_at=now,
            closed_at=now,
            additions=25,
            deletions=10,
            changed_files=1,
            commits_count=1,
            author_login="testuser",
            author_id=123,
            author_name="Test User",
            author_avatar_url=None,
            head_ref="feature",
            base_ref="main",
            files=[file_data],
        )

        # Create seeder and call _create_pr_files
        seeder = RealProjectSeeder(
            config=self.config,
            random_seed=42,
            github_token="fake-token",
        )

        # This should NOT raise AttributeError
        seeder._create_pr_files(self.team, pr, pr_data)

        # Verify the file was created with computed changes
        pr_file = PRFile.objects.get(pull_request=pr)
        self.assertEqual(pr_file.filename, "src/main.py")
        self.assertEqual(pr_file.additions, 25)
        self.assertEqual(pr_file.deletions, 10)
        self.assertEqual(pr_file.changes, 35)  # 25 + 10


class TestRealProjectSeederCheckRunCreation(TestCase):
    """Tests for RealProjectSeeder._create_pr_check_runs method."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.config = RealProjectConfig(
            repos=("test/repo",),
            team_name="Test Team",
            team_slug="test-team",
            max_prs=5,
            max_members=2,
            days_back=14,
            jira_project_key="TEST",
            ai_base_adoption_rate=0.3,
        )

    @patch("apps.metrics.seeding.real_project_seeder.GitHubAuthenticatedFetcher")
    def test_create_pr_check_runs_uses_computed_duration(self, mock_fetcher_class):
        """_create_pr_check_runs should compute duration from timestamps."""
        from apps.metrics.factories import PullRequestFactory

        # Create a PR
        pr = PullRequestFactory(team=self.team)

        # Create FetchedCheckRun without github_id or duration_seconds
        started = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2025, 1, 1, 10, 5, 0, tzinfo=UTC)

        check_data = FetchedCheckRun(
            github_id=999888,
            name="pytest",
            status="completed",
            conclusion="success",
            started_at=started,
            completed_at=completed,
        )

        # Create FetchedPRFull with the check run
        now = datetime.now(UTC)
        pr_data = FetchedPRFull(
            github_pr_id=123,
            number=1,
            github_repo="test/repo",
            title="Test PR",
            body="Test body",
            state="merged",
            is_merged=True,
            is_draft=False,
            created_at=now,
            updated_at=now,
            merged_at=now,
            closed_at=now,
            additions=10,
            deletions=5,
            changed_files=1,
            commits_count=1,
            author_login="testuser",
            author_id=123,
            author_name="Test User",
            author_avatar_url=None,
            head_ref="feature",
            base_ref="main",
            check_runs=[check_data],
        )

        # Create seeder and call _create_pr_check_runs
        seeder = RealProjectSeeder(
            config=self.config,
            random_seed=42,
            github_token="fake-token",
        )

        # This should NOT raise AttributeError
        seeder._create_pr_check_runs(self.team, pr, pr_data)

        # Verify the check run was created with computed duration
        check_run = PRCheckRun.objects.get(pull_request=pr)
        self.assertEqual(check_run.name, "pytest")
        self.assertEqual(check_run.status, "completed")
        self.assertEqual(check_run.conclusion, "success")
        self.assertEqual(check_run.duration_seconds, 300)  # 5 minutes
