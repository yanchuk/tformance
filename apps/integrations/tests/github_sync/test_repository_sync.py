"""Tests for GitHub sync service."""

from datetime import UTC, datetime
from unittest.mock import patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    sync_repository_history,
    sync_repository_incremental,
)


class TestSyncRepositoryHistory(TestCase):
    """Tests for syncing historical PR data from a tracked repository."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.factories import (
            GitHubIntegrationFactory,
            IntegrationCredentialFactory,
            TrackedRepositoryFactory,
        )
        from apps.metrics.factories import TeamFactory, TeamMemberFactory

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="encrypted_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
        )
        # Create team member to match author
        self.member = TeamMemberFactory(
            team=self.team,
            github_id="12345",
            display_name="John Dev",
        )

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_creates_pull_requests(
        self,
        mock_get_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history creates PullRequest records from API data."""
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-02T15:00:00Z",
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]

        # Sync the repository
        result = sync_repository_history(self.tracked_repo)

        # Verify PR was created
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123456789)
        self.assertEqual(pr.title, "Add feature")
        self.assertEqual(pr.state, "merged")
        self.assertEqual(pr.github_repo, "acme-corp/api-server")
        self.assertEqual(pr.author, self.member)
        self.assertEqual(pr.additions, 100)
        self.assertEqual(pr.deletions, 50)

        # Verify result summary
        self.assertEqual(result["prs_synced"], 1)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_updates_existing_prs(
        self,
        mock_get_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history updates existing PRs (idempotent)."""
        from apps.metrics.factories import PullRequestFactory
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # Create existing PR with old data
        existing_pr = PullRequestFactory(
            team=self.team,
            github_pr_id=123456789,
            github_repo="acme-corp/api-server",
            title="Old Title",
            state="open",
        )

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Updated Title",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-02T15:00:00Z",
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]

        # Sync the repository
        result = sync_repository_history(self.tracked_repo)

        # Verify PR was updated, not duplicated
        self.assertEqual(PullRequest.objects.filter(github_pr_id=123456789).count(), 1)
        pr = PullRequest.objects.get(github_pr_id=123456789)
        self.assertEqual(pr.title, "Updated Title")
        self.assertEqual(pr.state, "merged")
        self.assertEqual(pr.id, existing_pr.id)  # Same record

        # Verify result summary
        self.assertEqual(result["prs_synced"], 1)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_maps_author_to_team_member(
        self,
        mock_get_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history links author FK correctly."""
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]

        # Sync the repository
        sync_repository_history(self.tracked_repo)

        # Verify author was linked correctly
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123456789)
        self.assertEqual(pr.author, self.member)
        self.assertEqual(pr.author.github_id, "12345")

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_handles_unknown_author(
        self,
        mock_get_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history sets author=None if not found."""
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 99999, "login": "unknown_dev"},  # Not in team
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]

        # Sync the repository
        sync_repository_history(self.tracked_repo)

        # Verify author is None for unknown user
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123456789)
        self.assertIsNone(pr.author)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_calculates_cycle_time(
        self,
        mock_get_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history calculates cycle_time_hours for merged PRs."""
        from decimal import Decimal

        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-02T15:00:00Z",  # 29 hours after creation
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]

        # Sync the repository
        sync_repository_history(self.tracked_repo)

        # Verify cycle_time_hours was calculated correctly
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123456789)
        self.assertIsNotNone(pr.cycle_time_hours)
        # 29 hours between 2025-01-01T10:00:00Z and 2025-01-02T15:00:00Z
        self.assertEqual(pr.cycle_time_hours, Decimal("29.00"))

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_updates_last_sync_at(
        self,
        mock_get_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history updates TrackedRepository.last_sync_at."""
        from django.utils import timezone

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0
        mock_get_prs.return_value = []

        # Verify last_sync_at is None initially
        self.assertIsNone(self.tracked_repo.last_sync_at)

        # Sync the repository
        before_sync = timezone.now()
        sync_repository_history(self.tracked_repo)
        after_sync = timezone.now()

        # Verify last_sync_at was updated
        self.tracked_repo.refresh_from_db()
        self.assertIsNotNone(self.tracked_repo.last_sync_at)
        self.assertGreaterEqual(self.tracked_repo.last_sync_at, before_sync)
        self.assertLessEqual(self.tracked_repo.last_sync_at, after_sync)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_returns_summary(
        self,
        mock_get_prs,
        mock_sync_reviews,
        mock_sync_commits,
        mock_sync_check_runs,
        mock_sync_files,
        mock_sync_issue_comments,
        mock_sync_review_comments,
        mock_sync_deployments,
    ):
        """Test that sync_repository_history returns dict with prs_synced count."""
        # Mock all sync functions to return 0
        mock_sync_reviews.return_value = 0
        mock_sync_commits.return_value = 0
        mock_sync_check_runs.return_value = 0
        mock_sync_files.return_value = 0
        mock_sync_issue_comments.return_value = 0
        mock_sync_review_comments.return_value = 0
        mock_sync_deployments.return_value = 0

        mock_get_prs.return_value = [
            {
                "id": 1,
                "number": 1,
                "title": "PR 1",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 10,
                "deletions": 5,
            },
            {
                "id": 2,
                "number": 2,
                "title": "PR 2",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-02T15:00:00Z",
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T11:00:00Z",
                "additions": 20,
                "deletions": 10,
            },
        ]

        # Sync the repository
        result = sync_repository_history(self.tracked_repo)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("prs_synced", result)
        self.assertEqual(result["prs_synced"], 2)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.processors.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_fetches_reviews_for_each_pr(
        self,
        mock_get_prs,
        mock_get_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history calls get_pull_request_reviews for each PR."""
        # Mock all sync functions to return 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            },
            {
                "id": 987654321,
                "number": 43,
                "title": "Fix bug",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-02T15:00:00Z",
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T11:00:00Z",
                "additions": 20,
                "deletions": 10,
            },
        ]
        mock_get_reviews.return_value = []

        # Sync the repository
        sync_repository_history(self.tracked_repo)

        # Verify get_pull_request_reviews was called for each PR with correct arguments
        self.assertEqual(mock_get_reviews.call_count, 2)
        # First PR (number 42)
        first_call = mock_get_reviews.call_args_list[0]
        self.assertEqual(first_call[0][0], "encrypted_token_12345")  # access_token
        self.assertEqual(first_call[0][1], "acme-corp/api-server")  # repo_full_name
        self.assertEqual(first_call[0][2], 42)  # pr_number
        # Second PR (number 43)
        second_call = mock_get_reviews.call_args_list[1]
        self.assertEqual(second_call[0][0], "encrypted_token_12345")
        self.assertEqual(second_call[0][1], "acme-corp/api-server")
        self.assertEqual(second_call[0][2], 43)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.processors.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_creates_review_records(
        self,
        mock_get_prs,
        mock_get_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history creates PRReview records from API data."""
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PRReview

        # Mock all sync functions to return 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # Create reviewer team member
        reviewer = TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]
        mock_get_reviews.return_value = [
            {
                "id": 456789,
                "user": {"id": 54321, "login": "reviewer"},
                "state": "APPROVED",
                "submitted_at": "2025-01-01T12:00:00Z",
            },
            {
                "id": 456790,
                "user": {"id": 54321, "login": "reviewer"},
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2025-01-01T14:00:00Z",
            },
        ]

        # Sync the repository
        sync_repository_history(self.tracked_repo)

        # Verify reviews were created
        reviews = PRReview.objects.filter(team=self.team).order_by("github_review_id")
        self.assertEqual(reviews.count(), 2)

        # Check first review
        review1 = reviews[0]
        self.assertEqual(review1.github_review_id, 456789)
        self.assertEqual(review1.reviewer, reviewer)
        self.assertEqual(review1.state, "approved")
        self.assertIsNotNone(review1.submitted_at)

        # Check second review
        review2 = reviews[1]
        self.assertEqual(review2.github_review_id, 456790)
        self.assertEqual(review2.reviewer, reviewer)
        self.assertEqual(review2.state, "changes_requested")

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.processors.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_maps_reviewer_to_team_member(
        self,
        mock_get_prs,
        mock_get_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history links reviewer FK correctly."""
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PRReview

        # Mock all sync functions to return 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # Create reviewer team member
        reviewer = TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]
        mock_get_reviews.return_value = [
            {
                "id": 456789,
                "user": {"id": 54321, "login": "reviewer"},
                "state": "APPROVED",
                "submitted_at": "2025-01-01T12:00:00Z",
            }
        ]

        # Sync the repository
        sync_repository_history(self.tracked_repo)

        # Verify reviewer was linked correctly
        review = PRReview.objects.get(team=self.team, github_review_id=456789)
        self.assertEqual(review.reviewer, reviewer)
        self.assertEqual(review.reviewer.github_id, "54321")

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.processors.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_sets_first_review_at(
        self,
        mock_get_prs,
        mock_get_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history updates PR's first_review_at with earliest review."""
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # Create reviewer team member
        TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]
        # Multiple reviews - should take earliest
        mock_get_reviews.return_value = [
            {
                "id": 456789,
                "user": {"id": 54321, "login": "reviewer"},
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2025-01-01T14:00:00Z",  # Later review
            },
            {
                "id": 456788,
                "user": {"id": 54321, "login": "reviewer"},
                "state": "COMMENTED",
                "submitted_at": "2025-01-01T12:00:00Z",  # Earlier review
            },
        ]

        # Sync the repository
        sync_repository_history(self.tracked_repo)

        # Verify first_review_at was set to earliest review time
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123456789)
        self.assertIsNotNone(pr.first_review_at)
        # Should be 2025-01-01T12:00:00Z (the earlier review)
        expected_time = pr.first_review_at.isoformat().replace("+00:00", "Z")
        self.assertEqual(expected_time, "2025-01-01T12:00:00Z")

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.processors.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_calculates_review_time(
        self,
        mock_get_prs,
        mock_get_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history calculates review_time_hours correctly."""
        from decimal import Decimal

        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # Create reviewer team member
        TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",  # PR created
                "additions": 100,
                "deletions": 50,
            }
        ]
        mock_get_reviews.return_value = [
            {
                "id": 456789,
                "user": {"id": 54321, "login": "reviewer"},
                "state": "APPROVED",
                "submitted_at": "2025-01-01T12:00:00Z",  # 2 hours after PR creation
            }
        ]

        # Sync the repository
        sync_repository_history(self.tracked_repo)

        # Verify review_time_hours was calculated correctly
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123456789)
        self.assertIsNotNone(pr.review_time_hours)
        # 2 hours between 10:00 and 12:00
        self.assertEqual(pr.review_time_hours, Decimal("2.00"))

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.processors.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")
    def test_sync_repository_history_returns_reviews_synced_count(
        self,
        mock_get_prs,
        mock_get_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_history returns reviews_synced in summary."""
        from apps.metrics.factories import TeamMemberFactory

        # Mock all sync functions to return 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # Create reviewer team member
        TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_get_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "additions": 100,
                "deletions": 50,
            },
            {
                "id": 987654321,
                "number": 43,
                "title": "Fix bug",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-02T15:00:00Z",
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T11:00:00Z",
                "additions": 20,
                "deletions": 10,
            },
        ]

        # First PR has 2 reviews, second has 1 review
        def side_effect(token, repo, pr_number):
            if pr_number == 42:
                return [
                    {
                        "id": 456789,
                        "user": {"id": 54321, "login": "reviewer"},
                        "state": "APPROVED",
                        "submitted_at": "2025-01-01T12:00:00Z",
                    },
                    {
                        "id": 456790,
                        "user": {"id": 54321, "login": "reviewer"},
                        "state": "COMMENTED",
                        "submitted_at": "2025-01-01T13:00:00Z",
                    },
                ]
            else:  # pr_number == 43
                return [
                    {
                        "id": 456791,
                        "user": {"id": 54321, "login": "reviewer"},
                        "state": "APPROVED",
                        "submitted_at": "2025-01-02T14:00:00Z",
                    }
                ]

        mock_get_reviews.side_effect = side_effect

        # Sync the repository
        result = sync_repository_history(self.tracked_repo)

        # Verify result includes reviews_synced count
        self.assertIn("reviews_synced", result)
        self.assertEqual(result["reviews_synced"], 3)  # Total: 2 + 1 = 3 reviews


class TestSyncRepositoryIncremental(TestCase):
    """Tests for incremental sync of repository PRs (only updated since last sync)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.factories import (
            GitHubIntegrationFactory,
            IntegrationCredentialFactory,
            TrackedRepositoryFactory,
        )
        from apps.metrics.factories import TeamFactory, TeamMemberFactory

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="encrypted_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
        )
        # Create team member to match author
        self.member = TeamMemberFactory(
            team=self.team,
            github_id="12345",
            display_name="John Dev",
        )

    @patch("apps.integrations.services.github_sync.sync.sync_repository_history")
    # Note: EncryptedTextField handles decryption automatically
    def test_sync_repository_incremental_falls_back_to_full_sync_when_last_sync_at_is_none(self, mock_sync_history):
        """Test that sync_repository_incremental calls sync_repository_history when last_sync_at is None."""

        # EncryptedTextField auto-decrypts access_token
        mock_sync_history.return_value = {
            "prs_synced": 10,
            "reviews_synced": 5,
            "errors": [],
        }

        # Verify last_sync_at is None
        self.assertIsNone(self.tracked_repo.last_sync_at)

        # Call incremental sync
        result = sync_repository_incremental(self.tracked_repo)

        # Verify it called full sync instead
        mock_sync_history.assert_called_once_with(self.tracked_repo)

        # Verify result is passed through from full sync
        self.assertEqual(result["prs_synced"], 10)
        self.assertEqual(result["reviews_synced"], 5)

    @patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests")
    # Note: EncryptedTextField handles decryption automatically
    def test_sync_repository_incremental_calls_get_updated_pull_requests_with_since_parameter(
        self, mock_get_updated_prs
    ):
        """Test that sync_repository_incremental calls get_updated_pull_requests with correct since parameter."""

        from apps.integrations.services.github_sync import sync_repository_incremental

        # EncryptedTextField auto-decrypts access_token
        mock_get_updated_prs.return_value = []

        # Set last_sync_at to a known time
        last_sync_time = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.last_sync_at = last_sync_time
        self.tracked_repo.save()

        # Call incremental sync
        sync_repository_incremental(self.tracked_repo)

        # Verify get_updated_pull_requests was called with correct parameters
        mock_get_updated_prs.assert_called_once_with("encrypted_token_12345", "acme-corp/api-server", last_sync_time)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests")
    def test_sync_repository_incremental_creates_new_pull_requests(
        self,
        mock_get_updated_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_incremental creates new PullRequest records from updated PRs."""
        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        mock_get_updated_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "New feature",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T15:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]

        # Set last_sync_at so it doesn't fall back to full sync
        self.tracked_repo.last_sync_at = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.save()

        # Call incremental sync
        result = sync_repository_incremental(self.tracked_repo)

        # Verify PR was created
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123456789)
        self.assertEqual(pr.title, "New feature")
        self.assertEqual(pr.state, "open")
        self.assertEqual(pr.github_repo, "acme-corp/api-server")
        self.assertEqual(pr.author, self.member)

        # Verify result summary
        self.assertEqual(result["prs_synced"], 1)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests")
    def test_sync_repository_incremental_updates_existing_pull_requests(
        self,
        mock_get_updated_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_incremental updates existing PRs (idempotent)."""
        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.factories import PullRequestFactory
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # Create existing PR with old data
        existing_pr = PullRequestFactory(
            team=self.team,
            github_pr_id=123456789,
            github_repo="acme-corp/api-server",
            title="Old Title",
            state="open",
        )

        # EncryptedTextField auto-decrypts access_token
        mock_get_updated_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Updated Title",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-06T15:00:00Z",
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T15:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]

        # Set last_sync_at so it doesn't fall back to full sync
        self.tracked_repo.last_sync_at = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.save()

        # Call incremental sync
        result = sync_repository_incremental(self.tracked_repo)

        # Verify PR was updated, not duplicated
        self.assertEqual(PullRequest.objects.filter(github_pr_id=123456789).count(), 1)
        pr = PullRequest.objects.get(github_pr_id=123456789)
        self.assertEqual(pr.title, "Updated Title")
        self.assertEqual(pr.state, "merged")
        self.assertEqual(pr.id, existing_pr.id)  # Same record

        # Verify result summary
        self.assertEqual(result["prs_synced"], 1)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.processors.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests")
    def test_sync_repository_incremental_syncs_reviews_for_each_updated_pr(
        self,
        mock_get_updated_prs,
        mock_get_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_incremental calls get_pull_request_reviews for each updated PR."""
        from apps.integrations.services.github_sync import sync_repository_incremental

        # Mock all sync functions to return 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        mock_get_updated_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "PR 1",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T15:00:00Z",
                "additions": 100,
                "deletions": 50,
            },
            {
                "id": 987654321,
                "number": 43,
                "title": "PR 2",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-06T16:00:00Z",
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T11:00:00Z",
                "updated_at": "2025-01-06T16:00:00Z",
                "additions": 50,
                "deletions": 25,
            },
        ]
        mock_get_reviews.return_value = []

        # Set last_sync_at so it doesn't fall back to full sync
        self.tracked_repo.last_sync_at = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.save()

        # Call incremental sync
        sync_repository_incremental(self.tracked_repo)

        # Verify get_pull_request_reviews was called for each PR
        self.assertEqual(mock_get_reviews.call_count, 2)
        first_call = mock_get_reviews.call_args_list[0]
        self.assertEqual(first_call[0][0], "encrypted_token_12345")
        self.assertEqual(first_call[0][1], "acme-corp/api-server")
        self.assertEqual(first_call[0][2], 42)

        second_call = mock_get_reviews.call_args_list[1]
        self.assertEqual(second_call[0][0], "encrypted_token_12345")
        self.assertEqual(second_call[0][1], "acme-corp/api-server")
        self.assertEqual(second_call[0][2], 43)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.processors.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests")
    def test_sync_repository_incremental_creates_review_records(
        self,
        mock_get_updated_prs,
        mock_get_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_incremental creates PRReview records from API data."""
        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PRReview

        # Mock all sync functions to return 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # Create reviewer team member
        reviewer = TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_get_updated_prs.return_value = [
            {
                "id": 123456789,
                "number": 42,
                "title": "Feature PR",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T15:00:00Z",
                "additions": 100,
                "deletions": 50,
            }
        ]
        mock_get_reviews.return_value = [
            {
                "id": 456789,
                "user": {"id": 54321, "login": "reviewer"},
                "state": "APPROVED",
                "submitted_at": "2025-01-02T12:00:00Z",
            }
        ]

        # Set last_sync_at so it doesn't fall back to full sync
        self.tracked_repo.last_sync_at = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.save()

        # Call incremental sync
        result = sync_repository_incremental(self.tracked_repo)

        # Verify review was created
        review = PRReview.objects.get(team=self.team, github_review_id=456789)
        self.assertEqual(review.reviewer, reviewer)
        self.assertEqual(review.state, "approved")

        # Verify result summary
        self.assertEqual(result["reviews_synced"], 1)

    @patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests")
    # Note: EncryptedTextField handles decryption automatically
    def test_sync_repository_incremental_updates_last_sync_at(self, mock_get_updated_prs):
        """Test that sync_repository_incremental updates TrackedRepository.last_sync_at on completion."""

        from apps.integrations.services.github_sync import sync_repository_incremental

        # EncryptedTextField auto-decrypts access_token
        mock_get_updated_prs.return_value = []

        # Set initial last_sync_at
        initial_sync_time = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.last_sync_at = initial_sync_time
        self.tracked_repo.save()

        from django.utils import timezone as django_timezone

        # Call incremental sync
        before_sync = django_timezone.now()
        sync_repository_incremental(self.tracked_repo)
        after_sync = django_timezone.now()

        # Verify last_sync_at was updated to current time
        self.tracked_repo.refresh_from_db()
        self.assertIsNotNone(self.tracked_repo.last_sync_at)
        self.assertGreater(self.tracked_repo.last_sync_at, initial_sync_time)
        self.assertGreaterEqual(self.tracked_repo.last_sync_at, before_sync)
        self.assertLessEqual(self.tracked_repo.last_sync_at, after_sync)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests")
    def test_sync_repository_incremental_returns_correct_summary_dict(
        self,
        mock_get_updated_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_incremental returns dict with prs_synced, reviews_synced, errors."""
        from apps.integrations.services.github_sync import sync_repository_incremental

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        mock_get_updated_prs.return_value = [
            {
                "id": 1,
                "number": 1,
                "title": "PR 1",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T15:00:00Z",
                "additions": 10,
                "deletions": 5,
            },
            {
                "id": 2,
                "number": 2,
                "title": "PR 2",
                "state": "closed",
                "merged": True,
                "merged_at": "2025-01-06T16:00:00Z",
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T11:00:00Z",
                "updated_at": "2025-01-06T16:00:00Z",
                "additions": 20,
                "deletions": 10,
            },
        ]

        # Set last_sync_at so it doesn't fall back to full sync
        self.tracked_repo.last_sync_at = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.save()

        # Call incremental sync
        result = sync_repository_incremental(self.tracked_repo)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("prs_synced", result)
        self.assertIn("reviews_synced", result)
        self.assertIn("errors", result)
        self.assertEqual(result["prs_synced"], 2)
        self.assertIsInstance(result["errors"], list)

    @patch("apps.integrations.services.github_sync.sync.sync_repository_deployments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync.sync.sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests")
    def test_sync_repository_incremental_handles_individual_pr_errors_gracefully(
        self,
        mock_get_updated_prs,
        mock_reviews,
        mock_commits,
        mock_checks,
        mock_files,
        mock_issues,
        mock_review_comments,
        mock_deployments,
    ):
        """Test that sync_repository_incremental continues processing even if one PR fails."""
        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.models import PullRequest

        # Mock all sync functions to return 0
        mock_reviews.return_value = 0
        mock_commits.return_value = 0
        mock_checks.return_value = 0
        mock_files.return_value = 0
        mock_issues.return_value = 0
        mock_review_comments.return_value = 0
        mock_deployments.return_value = 0

        # First PR has invalid data that will cause an error, second PR is valid
        mock_get_updated_prs.return_value = [
            {
                "id": 999,
                "number": 99,
                "title": None,  # This will cause an error
                "state": "invalid_state",
                "merged": "not_a_boolean",  # Invalid type
                "merged_at": "invalid_date",
                "user": None,  # Missing user data
                "created_at": "invalid_date",
                "updated_at": "2025-01-06T15:00:00Z",
                "additions": "not_a_number",
                "deletions": "not_a_number",
            },
            {
                "id": 123456789,
                "number": 42,
                "title": "Valid PR",
                "state": "open",
                "merged": False,
                "merged_at": None,
                "user": {"id": 12345, "login": "dev"},
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-06T15:00:00Z",
                "additions": 100,
                "deletions": 50,
            },
        ]

        # Set last_sync_at so it doesn't fall back to full sync
        self.tracked_repo.last_sync_at = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.save()

        # Call incremental sync
        result = sync_repository_incremental(self.tracked_repo)

        # Verify second PR was still created despite first PR failing
        prs = PullRequest.objects.filter(team=self.team)
        self.assertEqual(prs.count(), 1)
        pr = prs.first()
        self.assertEqual(pr.title, "Valid PR")
        self.assertEqual(pr.github_pr_id, 123456789)

        # Verify error was logged
        self.assertIn("errors", result)
        self.assertIsInstance(result["errors"], list)
        self.assertGreater(len(result["errors"]), 0)
        # At least one PR was synced
        self.assertEqual(result["prs_synced"], 1)
