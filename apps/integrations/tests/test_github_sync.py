"""Tests for GitHub sync service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    GitHubOAuthError,
    get_pull_request_reviews,
    get_repository_pull_requests,
    get_updated_pull_requests,
)


class TestGetRepositoryPullRequests(TestCase):
    """Tests for fetching pull requests from GitHub repository."""

    def _create_mock_pr(
        self,
        pr_id: int,
        number: int,
        title: str,
        state: str,
        user_id: int,
        user_login: str,
        merged: bool = False,
        merged_at: str | None = None,
        created_at: str = "2025-01-01T10:00:00Z",
        updated_at: str = "2025-01-01T10:00:00Z",
        additions: int = 10,
        deletions: int = 5,
        commits: int = 1,
        changed_files: int = 1,
        base_ref: str = "main",
        head_ref: str = "feature-branch",
        head_sha: str = "abc123",
        html_url: str = "https://github.com/org/repo/pull/1",
    ) -> MagicMock:
        """Create a mock PyGithub PullRequest object with all required attributes."""
        mock_pr = MagicMock()
        mock_pr.id = pr_id
        mock_pr.number = number
        mock_pr.title = title
        mock_pr.state = state
        mock_pr.merged = merged
        mock_pr.merged_at = datetime.fromisoformat(merged_at.replace("Z", "+00:00")) if merged_at else None
        mock_pr.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        mock_pr.updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        mock_pr.additions = additions
        mock_pr.deletions = deletions
        mock_pr.commits = commits
        mock_pr.changed_files = changed_files
        mock_pr.html_url = html_url

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.login = user_login
        mock_pr.user = mock_user

        # Mock base ref
        mock_base = MagicMock()
        mock_base.ref = base_ref
        mock_pr.base = mock_base

        # Mock head ref
        mock_head = MagicMock()
        mock_head.ref = head_ref
        mock_head.sha = head_sha
        mock_pr.head = mock_head

        return mock_pr

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_repository_pull_requests_returns_prs(self, mock_github_class):
        """Test that get_repository_pull_requests returns list of PRs from GitHub API."""
        # Create mock PRs
        mock_pr1 = self._create_mock_pr(
            pr_id=1,
            number=101,
            title="Add new feature",
            state="open",
            user_id=1001,
            user_login="developer1",
            created_at="2025-01-01T10:00:00Z",
            updated_at="2025-01-02T15:30:00Z",
        )
        mock_pr2 = self._create_mock_pr(
            pr_id=2,
            number=102,
            title="Fix bug in login",
            state="closed",
            user_id=1002,
            user_login="developer2",
            merged=True,
            merged_at="2025-01-04T11:15:00Z",
            created_at="2025-01-03T09:00:00Z",
            updated_at="2025-01-04T11:15:00Z",
        )

        # Mock PyGithub chain: Github().get_repo().get_pulls()
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr1, mock_pr2]
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"

        result = get_repository_pull_requests(access_token, repo_full_name)

        # Verify result contains PRs
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["number"], 101)
        self.assertEqual(result[0]["title"], "Add new feature")
        self.assertEqual(result[0]["state"], "open")
        self.assertEqual(result[0]["merged"], False)
        self.assertEqual(result[1]["number"], 102)
        self.assertEqual(result[1]["title"], "Fix bug in login")
        self.assertEqual(result[1]["state"], "closed")
        self.assertEqual(result[1]["merged"], True)

        # Verify PyGithub was called correctly
        mock_github_class.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with(repo_full_name)
        mock_repo.get_pulls.assert_called_once_with(state="all")

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_repository_pull_requests_handles_empty_list(self, mock_github_class):
        """Test that get_repository_pull_requests returns empty list when no PRs exist."""
        # Mock PyGithub to return empty list
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = []
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"

        result = get_repository_pull_requests(access_token, repo_full_name)

        # Verify result is an empty list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

        # Verify PyGithub was called correctly
        mock_github_class.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with(repo_full_name)
        mock_repo.get_pulls.assert_called_once()

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_repository_pull_requests_handles_pagination(self, mock_github_class):
        """Test that PyGithub handles pagination automatically (no manual pagination needed)."""
        # Create multiple mock PRs (PyGithub handles pagination internally)
        mock_prs = [
            self._create_mock_pr(
                pr_id=i,
                number=100 + i,
                title=f"PR {i}",
                state="open",
                user_id=1000 + i,
                user_login=f"user{i}",
            )
            for i in range(1, 151)  # 150 PRs - would span multiple pages
        ]

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = mock_prs  # PyGithub returns all PRs automatically
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"

        result = get_repository_pull_requests(access_token, repo_full_name)

        # Verify all PRs were returned (PyGithub handled pagination internally)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 150, "Should return all PRs - PyGithub handles pagination")
        self.assertEqual(result[0]["number"], 101)
        self.assertEqual(result[-1]["number"], 250)

        # Verify only one call was made to get_pulls (PyGithub handles pagination internally)
        mock_repo.get_pulls.assert_called_once()

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_repository_pull_requests_filters_by_state(self, mock_github_class):
        """Test that get_repository_pull_requests passes state parameter to PyGithub correctly."""
        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = []
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "test-org/test-repo"

        # Test with state="open"
        get_repository_pull_requests(access_token, repo_full_name, state="open")
        mock_repo.get_pulls.assert_called_with(state="open")

        # Reset mock
        mock_repo.get_pulls.reset_mock()

        # Test with state="closed"
        get_repository_pull_requests(access_token, repo_full_name, state="closed")
        mock_repo.get_pulls.assert_called_with(state="closed")

        # Reset mock
        mock_repo.get_pulls.reset_mock()

        # Test with state="all" (default)
        get_repository_pull_requests(access_token, repo_full_name, state="all")
        mock_repo.get_pulls.assert_called_with(state="all")

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_repository_pull_requests_raises_on_api_error(self, mock_github_class):
        """Test that get_repository_pull_requests raises GitHubOAuthError on API errors."""
        from github import GithubException

        # Mock PyGithub to raise exception (404, 403, etc)
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pulls.side_effect = GithubException(404, {"message": "Not Found"})
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "org/nonexistent-repo"

        with self.assertRaises(GitHubOAuthError) as context:
            get_repository_pull_requests(access_token, repo_full_name)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_repository_pull_requests_returns_all_pr_attributes(self, mock_github_class):
        """Test that get_repository_pull_requests returns all required PR attributes."""
        # Create mock PR with all attributes
        mock_pr = self._create_mock_pr(
            pr_id=123456789,
            number=42,
            title="Complete PR with all attributes",
            state="closed",
            user_id=12345,
            user_login="developer",
            merged=True,
            merged_at="2025-01-05T16:00:00Z",
            created_at="2025-01-01T10:00:00Z",
            updated_at="2025-01-05T16:00:00Z",
            additions=250,
            deletions=100,
            commits=5,
            changed_files=8,
            base_ref="main",
            head_ref="feature/new-feature",
            head_sha="abc123def456",
            html_url="https://github.com/org/repo/pull/42",
        )

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr]
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "org/repo"

        result = get_repository_pull_requests(access_token, repo_full_name)

        # Verify all attributes are present in result
        self.assertEqual(len(result), 1)
        pr_dict = result[0]

        self.assertEqual(pr_dict["id"], 123456789)
        self.assertEqual(pr_dict["number"], 42)
        self.assertEqual(pr_dict["title"], "Complete PR with all attributes")
        self.assertEqual(pr_dict["state"], "closed")
        self.assertEqual(pr_dict["merged"], True)
        self.assertIsNotNone(pr_dict["merged_at"])
        self.assertIsNotNone(pr_dict["created_at"])
        self.assertIsNotNone(pr_dict["updated_at"])
        self.assertEqual(pr_dict["additions"], 250)
        self.assertEqual(pr_dict["deletions"], 100)
        self.assertEqual(pr_dict["commits"], 5)
        self.assertEqual(pr_dict["changed_files"], 8)
        self.assertEqual(pr_dict["user"]["id"], 12345)
        self.assertEqual(pr_dict["user"]["login"], "developer")
        self.assertEqual(pr_dict["base"]["ref"], "main")
        self.assertEqual(pr_dict["head"]["ref"], "feature/new-feature")
        self.assertEqual(pr_dict["head"]["sha"], "abc123def456")
        self.assertEqual(pr_dict["html_url"], "https://github.com/org/repo/pull/42")


class TestGetPullRequestReviews(TestCase):
    """Tests for fetching reviews for a specific pull request."""

    def _create_mock_review(
        self,
        review_id: int,
        user_id: int,
        user_login: str,
        state: str,
        body: str,
        submitted_at: str,
    ) -> MagicMock:
        """Create a mock PyGithub Review object with all required attributes."""
        mock_review = MagicMock()
        mock_review.id = review_id
        mock_review.state = state
        mock_review.body = body
        mock_review.submitted_at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.login = user_login
        mock_review.user = mock_user

        return mock_review

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_pull_request_reviews_returns_reviews(self, mock_github_class):
        """Test that get_pull_request_reviews returns list of reviews from GitHub API."""
        # Create mock reviews
        mock_review1 = self._create_mock_review(
            review_id=12345,
            user_id=2001,
            user_login="reviewer1",
            state="APPROVED",
            body="Looks good to me!",
            submitted_at="2025-01-05T14:30:00Z",
        )
        mock_review2 = self._create_mock_review(
            review_id=12346,
            user_id=2002,
            user_login="reviewer2",
            state="CHANGES_REQUESTED",
            body="Please fix the typo in line 45",
            submitted_at="2025-01-05T15:00:00Z",
        )

        # Mock PyGithub chain: Github().get_repo().get_pull().get_reviews()
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_reviews.return_value = [mock_review1, mock_review2]
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 101

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify result contains reviews
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 12345)
        self.assertEqual(result[0]["state"], "APPROVED")
        self.assertEqual(result[0]["body"], "Looks good to me!")
        self.assertEqual(result[1]["id"], 12346)
        self.assertEqual(result[1]["state"], "CHANGES_REQUESTED")

        # Verify PyGithub was called correctly
        mock_github_class.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with(repo_full_name)
        mock_repo.get_pull.assert_called_once_with(pr_number)
        mock_pr.get_reviews.assert_called_once()

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_pull_request_reviews_handles_empty_reviews(self, mock_github_class):
        """Test that get_pull_request_reviews returns empty list when no reviews exist."""
        # Mock PyGithub chain to return empty list
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_reviews.return_value = []
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 999

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify result is an empty list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

        # Verify PyGithub was called correctly
        mock_github_class.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with(repo_full_name)
        mock_repo.get_pull.assert_called_once_with(pr_number)

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_pull_request_reviews_handles_pagination(self, mock_github_class):
        """Test that PyGithub handles pagination automatically (no manual pagination needed)."""
        # Create multiple mock reviews (PyGithub handles pagination internally)
        mock_reviews = [
            self._create_mock_review(
                review_id=i,
                user_id=2000 + i,
                user_login=f"reviewer{i}",
                state="APPROVED",
                body=f"Review {i}",
                submitted_at=f"2025-01-{1 + (i // 24):02d}T{i % 24:02d}:00:00Z",
            )
            for i in range(1, 151)  # 150 reviews - would span multiple pages
        ]

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_reviews.return_value = mock_reviews  # PyGithub returns all reviews automatically
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 101

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify all reviews were returned (PyGithub handled pagination internally)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 150, "Should return all reviews - PyGithub handles pagination")
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[-1]["id"], 150)

        # Verify only one call was made to get_reviews (PyGithub handles pagination internally)
        mock_pr.get_reviews.assert_called_once()

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_pull_request_reviews_raises_on_api_error(self, mock_github_class):
        """Test that get_pull_request_reviews raises GitHubOAuthError on API errors."""
        from github import GithubException

        # Mock PyGithub to raise exception (404, 403, etc)
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_reviews.side_effect = GithubException(404, {"message": "Not Found"})
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 99999

        with self.assertRaises(GitHubOAuthError) as context:
            get_pull_request_reviews(access_token, repo_full_name, pr_number)

        self.assertIn("404", str(context.exception))


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

    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_creates_pull_requests(self, mock_decrypt, mock_get_prs):
        """Test that sync_repository_history creates PullRequest records from API data."""
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.models import PullRequest

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_updates_existing_prs(self, mock_decrypt, mock_get_prs):
        """Test that sync_repository_history updates existing PRs (idempotent)."""
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.factories import PullRequestFactory
        from apps.metrics.models import PullRequest

        # Create existing PR with old data
        existing_pr = PullRequestFactory(
            team=self.team,
            github_pr_id=123456789,
            github_repo="acme-corp/api-server",
            title="Old Title",
            state="open",
        )

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_maps_author_to_team_member(self, mock_decrypt, mock_get_prs):
        """Test that sync_repository_history links author FK correctly."""
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.models import PullRequest

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_handles_unknown_author(self, mock_decrypt, mock_get_prs):
        """Test that sync_repository_history sets author=None if not found."""
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.models import PullRequest

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_calculates_cycle_time(self, mock_decrypt, mock_get_prs):
        """Test that sync_repository_history calculates cycle_time_hours for merged PRs."""
        from decimal import Decimal

        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.models import PullRequest

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_updates_last_sync_at(self, mock_decrypt, mock_get_prs):
        """Test that sync_repository_history updates TrackedRepository.last_sync_at."""
        from django.utils import timezone

        from apps.integrations.services.github_sync import sync_repository_history

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_returns_summary(self, mock_decrypt, mock_get_prs):
        """Test that sync_repository_history returns dict with prs_synced count."""
        from apps.integrations.services.github_sync import sync_repository_history

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_fetches_reviews_for_each_pr(self, mock_decrypt, mock_get_prs, mock_get_reviews):
        """Test that sync_repository_history calls get_pull_request_reviews for each PR."""
        from apps.integrations.services.github_sync import sync_repository_history

        mock_decrypt.return_value = "decrypted_token"
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
        self.assertEqual(first_call[0][0], "decrypted_token")  # access_token
        self.assertEqual(first_call[0][1], "acme-corp/api-server")  # repo_full_name
        self.assertEqual(first_call[0][2], 42)  # pr_number
        # Second PR (number 43)
        second_call = mock_get_reviews.call_args_list[1]
        self.assertEqual(second_call[0][0], "decrypted_token")
        self.assertEqual(second_call[0][1], "acme-corp/api-server")
        self.assertEqual(second_call[0][2], 43)

    @patch("apps.integrations.services.github_sync.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_creates_review_records(self, mock_decrypt, mock_get_prs, mock_get_reviews):
        """Test that sync_repository_history creates PRReview records from API data."""
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PRReview

        # Create reviewer team member
        reviewer = TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_maps_reviewer_to_team_member(self, mock_decrypt, mock_get_prs, mock_get_reviews):
        """Test that sync_repository_history links reviewer FK correctly."""
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PRReview

        # Create reviewer team member
        reviewer = TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_sets_first_review_at(self, mock_decrypt, mock_get_prs, mock_get_reviews):
        """Test that sync_repository_history updates PR's first_review_at with earliest review."""
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PullRequest

        # Create reviewer team member
        TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_calculates_review_time(self, mock_decrypt, mock_get_prs, mock_get_reviews):
        """Test that sync_repository_history calculates review_time_hours correctly."""
        from decimal import Decimal

        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PullRequest

        # Create reviewer team member
        TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_history_returns_reviews_synced_count(self, mock_decrypt, mock_get_prs, mock_get_reviews):
        """Test that sync_repository_history returns reviews_synced in summary."""
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.factories import TeamMemberFactory

        # Create reviewer team member
        TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_decrypt.return_value = "decrypted_token"
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


class TestGetUpdatedPullRequests(TestCase):
    """Tests for fetching pull requests updated since a given datetime."""

    def _create_mock_pr(
        self,
        pr_id: int,
        number: int,
        title: str,
        state: str,
        user_id: int,
        user_login: str,
        merged: bool = False,
        merged_at: str | None = None,
        created_at: str = "2025-01-01T10:00:00Z",
        updated_at: str = "2025-01-01T10:00:00Z",
        additions: int = 10,
        deletions: int = 5,
        commits: int = 1,
        changed_files: int = 1,
        base_ref: str = "main",
        head_ref: str = "feature-branch",
        head_sha: str = "abc123",
        html_url: str = "https://github.com/org/repo/pull/1",
    ) -> MagicMock:
        """Create a mock PyGithub PullRequest object with all required attributes."""
        mock_pr = MagicMock()
        mock_pr.id = pr_id
        mock_pr.number = number
        mock_pr.title = title
        mock_pr.state = state
        mock_pr.merged = merged
        mock_pr.merged_at = datetime.fromisoformat(merged_at.replace("Z", "+00:00")) if merged_at else None
        mock_pr.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        mock_pr.updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        mock_pr.additions = additions
        mock_pr.deletions = deletions
        mock_pr.commits = commits
        mock_pr.changed_files = changed_files
        mock_pr.html_url = html_url

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.login = user_login
        mock_pr.user = mock_user

        # Mock base ref
        mock_base = MagicMock()
        mock_base.ref = base_ref
        mock_pr.base = mock_base

        # Mock head ref
        mock_head = MagicMock()
        mock_head.ref = head_ref
        mock_head.sha = head_sha
        mock_pr.head = mock_head

        return mock_pr

    def _create_mock_issue(
        self,
        number: int,
        is_pull_request: bool = False,
    ) -> MagicMock:
        """Create a mock PyGithub Issue object.

        Args:
            number: Issue/PR number
            is_pull_request: If True, issue has pull_request attribute (making it a PR)
        """
        mock_issue = MagicMock()
        mock_issue.number = number

        if is_pull_request:
            # Issues that are PRs have a pull_request attribute (dict with url, etc)
            mock_issue.pull_request = {"url": f"https://api.github.com/repos/org/repo/pulls/{number}"}
        else:
            # Regular issues don't have this attribute - set to None
            mock_issue.pull_request = None

        return mock_issue

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_updated_pull_requests_returns_prs_updated_since_datetime(self, mock_github_class):
        """Test that get_updated_pull_requests returns PRs updated since the given datetime."""
        # Create mock issues - mix of PRs and regular issues
        mock_issue_pr1 = self._create_mock_issue(number=101, is_pull_request=True)
        mock_issue_pr2 = self._create_mock_issue(number=102, is_pull_request=True)
        mock_issue_regular = self._create_mock_issue(number=103, is_pull_request=False)

        # Create mock PR details (returned by get_pull)
        mock_pr1 = self._create_mock_pr(
            pr_id=1,
            number=101,
            title="Add new feature",
            state="open",
            user_id=1001,
            user_login="developer1",
            updated_at="2025-01-05T10:00:00Z",
        )
        mock_pr2 = self._create_mock_pr(
            pr_id=2,
            number=102,
            title="Fix bug",
            state="closed",
            user_id=1002,
            user_login="developer2",
            merged=True,
            merged_at="2025-01-06T15:00:00Z",
            updated_at="2025-01-06T15:00:00Z",
        )

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()

        # get_issues returns mix of issues and PRs
        mock_repo.get_issues.return_value = [mock_issue_pr1, mock_issue_regular, mock_issue_pr2]

        # get_pull returns full PR details
        def get_pull_side_effect(number):
            if number == 101:
                return mock_pr1
            elif number == 102:
                return mock_pr2
            raise Exception(f"Unexpected PR number: {number}")

        mock_repo.get_pull.side_effect = get_pull_side_effect
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        since = datetime(2025, 1, 5, 0, 0, 0)

        result = get_updated_pull_requests(access_token, repo_full_name, since)

        # Verify result contains only PRs (issue 103 filtered out)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["number"], 101)
        self.assertEqual(result[0]["title"], "Add new feature")
        self.assertEqual(result[1]["number"], 102)
        self.assertEqual(result[1]["title"], "Fix bug")

        # Verify PyGithub was called correctly
        mock_github_class.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with(repo_full_name)
        mock_repo.get_issues.assert_called_once_with(since=since, state="all")

        # Verify get_pull was called only for PR issues (not regular issue 103)
        self.assertEqual(mock_repo.get_pull.call_count, 2)
        mock_repo.get_pull.assert_any_call(101)
        mock_repo.get_pull.assert_any_call(102)

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_updated_pull_requests_filters_out_regular_issues(self, mock_github_class):
        """Test that get_updated_pull_requests filters out regular issues (only returns PRs)."""
        # Create mock issues - all regular issues, no PRs
        mock_issue1 = self._create_mock_issue(number=201, is_pull_request=False)
        mock_issue2 = self._create_mock_issue(number=202, is_pull_request=False)
        mock_issue3 = self._create_mock_issue(number=203, is_pull_request=False)

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [mock_issue1, mock_issue2, mock_issue3]
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        since = datetime(2025, 1, 1, 0, 0, 0)

        result = get_updated_pull_requests(access_token, repo_full_name, since)

        # Verify result is empty (no PRs, only regular issues)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

        # Verify get_pull was never called (no PR issues found)
        mock_repo.get_pull.assert_not_called()

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_updated_pull_requests_returns_empty_list_when_no_updates(self, mock_github_class):
        """Test that get_updated_pull_requests returns empty list if no PRs updated since datetime."""
        # Mock PyGithub to return empty list
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = []
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        since = datetime(2025, 1, 10, 0, 0, 0)

        result = get_updated_pull_requests(access_token, repo_full_name, since)

        # Verify result is an empty list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

        # Verify PyGithub was called correctly
        mock_github_class.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with(repo_full_name)
        mock_repo.get_issues.assert_called_once()

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_updated_pull_requests_raises_on_api_error(self, mock_github_class):
        """Test that get_updated_pull_requests raises GitHubOAuthError on API errors."""
        from github import GithubException

        # Mock PyGithub to raise exception
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_issues.side_effect = GithubException(404, {"message": "Not Found"})
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "org/nonexistent-repo"
        since = datetime(2025, 1, 1, 0, 0, 0)

        with self.assertRaises(GitHubOAuthError) as context:
            get_updated_pull_requests(access_token, repo_full_name, since)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_updated_pull_requests_passes_since_parameter_correctly(self, mock_github_class):
        """Test that get_updated_pull_requests passes the since parameter to GitHub API correctly."""
        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = []
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "test-org/test-repo"
        since = datetime(2025, 1, 5, 14, 30, 0)

        get_updated_pull_requests(access_token, repo_full_name, since)

        # Verify get_issues was called with correct since parameter
        mock_repo.get_issues.assert_called_once_with(since=since, state="all")

    @patch("apps.integrations.services.github_sync.Github")
    def test_get_updated_pull_requests_returns_same_format_as_get_repository_pull_requests(self, mock_github_class):
        """Test that get_updated_pull_requests returns PRs in same dict format as get_repository_pull_requests."""
        # Create mock issue and PR
        mock_issue_pr = self._create_mock_issue(number=42, is_pull_request=True)
        mock_pr = self._create_mock_pr(
            pr_id=123456789,
            number=42,
            title="Complete PR with all attributes",
            state="closed",
            user_id=12345,
            user_login="developer",
            merged=True,
            merged_at="2025-01-05T16:00:00Z",
            created_at="2025-01-01T10:00:00Z",
            updated_at="2025-01-05T16:00:00Z",
            additions=250,
            deletions=100,
            commits=5,
            changed_files=8,
            base_ref="main",
            head_ref="feature/new-feature",
            head_sha="abc123def456",
            html_url="https://github.com/org/repo/pull/42",
        )

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [mock_issue_pr]
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "org/repo"
        since = datetime(2025, 1, 1, 0, 0, 0)

        result = get_updated_pull_requests(access_token, repo_full_name, since)

        # Verify all attributes are present in result (same format as get_repository_pull_requests)
        self.assertEqual(len(result), 1)
        pr_dict = result[0]

        self.assertEqual(pr_dict["id"], 123456789)
        self.assertEqual(pr_dict["number"], 42)
        self.assertEqual(pr_dict["title"], "Complete PR with all attributes")
        self.assertEqual(pr_dict["state"], "closed")
        self.assertEqual(pr_dict["merged"], True)
        self.assertIsNotNone(pr_dict["merged_at"])
        self.assertIsNotNone(pr_dict["created_at"])
        self.assertIsNotNone(pr_dict["updated_at"])
        self.assertEqual(pr_dict["additions"], 250)
        self.assertEqual(pr_dict["deletions"], 100)
        self.assertEqual(pr_dict["commits"], 5)
        self.assertEqual(pr_dict["changed_files"], 8)
        self.assertEqual(pr_dict["user"]["id"], 12345)
        self.assertEqual(pr_dict["user"]["login"], "developer")
        self.assertEqual(pr_dict["base"]["ref"], "main")
        self.assertEqual(pr_dict["head"]["ref"], "feature/new-feature")
        self.assertEqual(pr_dict["head"]["sha"], "abc123def456")
        self.assertEqual(pr_dict["html_url"], "https://github.com/org/repo/pull/42")


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

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_falls_back_to_full_sync_when_last_sync_at_is_none(
        self, mock_decrypt, mock_sync_history
    ):
        """Test that sync_repository_incremental calls sync_repository_history when last_sync_at is None."""
        from apps.integrations.services.github_sync import sync_repository_incremental

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_updated_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_calls_get_updated_pull_requests_with_since_parameter(
        self, mock_decrypt, mock_get_updated_prs
    ):
        """Test that sync_repository_incremental calls get_updated_pull_requests with correct since parameter."""
        from datetime import datetime

        from apps.integrations.services.github_sync import sync_repository_incremental

        mock_decrypt.return_value = "decrypted_token"
        mock_get_updated_prs.return_value = []

        # Set last_sync_at to a known time
        last_sync_time = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)
        self.tracked_repo.last_sync_at = last_sync_time
        self.tracked_repo.save()

        # Call incremental sync
        sync_repository_incremental(self.tracked_repo)

        # Verify get_updated_pull_requests was called with correct parameters
        mock_get_updated_prs.assert_called_once_with("decrypted_token", "acme-corp/api-server", last_sync_time)

    @patch("apps.integrations.services.github_sync.get_updated_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_creates_new_pull_requests(self, mock_decrypt, mock_get_updated_prs):
        """Test that sync_repository_incremental creates new PullRequest records from updated PRs."""
        from datetime import datetime

        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.models import PullRequest

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_updated_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_updates_existing_pull_requests(self, mock_decrypt, mock_get_updated_prs):
        """Test that sync_repository_incremental updates existing PRs (idempotent)."""
        from datetime import datetime

        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.factories import PullRequestFactory
        from apps.metrics.models import PullRequest

        # Create existing PR with old data
        existing_pr = PullRequestFactory(
            team=self.team,
            github_pr_id=123456789,
            github_repo="acme-corp/api-server",
            title="Old Title",
            state="open",
        )

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.get_updated_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_syncs_reviews_for_each_updated_pr(
        self, mock_decrypt, mock_get_updated_prs, mock_get_reviews
    ):
        """Test that sync_repository_incremental calls get_pull_request_reviews for each updated PR."""
        from datetime import datetime

        from apps.integrations.services.github_sync import sync_repository_incremental

        mock_decrypt.return_value = "decrypted_token"
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
        self.assertEqual(first_call[0][0], "decrypted_token")
        self.assertEqual(first_call[0][1], "acme-corp/api-server")
        self.assertEqual(first_call[0][2], 42)

        second_call = mock_get_reviews.call_args_list[1]
        self.assertEqual(second_call[0][0], "decrypted_token")
        self.assertEqual(second_call[0][1], "acme-corp/api-server")
        self.assertEqual(second_call[0][2], 43)

    @patch("apps.integrations.services.github_sync.get_pull_request_reviews")
    @patch("apps.integrations.services.github_sync.get_updated_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_creates_review_records(
        self, mock_decrypt, mock_get_updated_prs, mock_get_reviews
    ):
        """Test that sync_repository_incremental creates PRReview records from API data."""
        from datetime import datetime

        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PRReview

        # Create reviewer team member
        reviewer = TeamMemberFactory(
            team=self.team,
            github_id="54321",
            display_name="Jane Reviewer",
        )

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_updated_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_updates_last_sync_at(self, mock_decrypt, mock_get_updated_prs):
        """Test that sync_repository_incremental updates TrackedRepository.last_sync_at on completion."""
        from datetime import datetime

        from apps.integrations.services.github_sync import sync_repository_incremental

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_updated_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_returns_correct_summary_dict(self, mock_decrypt, mock_get_updated_prs):
        """Test that sync_repository_incremental returns dict with prs_synced, reviews_synced, errors."""
        from datetime import datetime

        from apps.integrations.services.github_sync import sync_repository_incremental

        mock_decrypt.return_value = "decrypted_token"
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

    @patch("apps.integrations.services.github_sync.get_updated_pull_requests")
    @patch("apps.integrations.services.encryption.decrypt")
    def test_sync_repository_incremental_handles_individual_pr_errors_gracefully(
        self, mock_decrypt, mock_get_updated_prs
    ):
        """Test that sync_repository_incremental continues processing even if one PR fails."""
        from datetime import datetime

        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.models import PullRequest

        mock_decrypt.return_value = "decrypted_token"
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


class TestJiraKeyExtraction(TestCase):
    """Tests for jira_key extraction integration in GitHub PR sync."""

    def _create_mock_pr(
        self,
        pr_id: int,
        number: int,
        title: str,
        head_ref: str,
        state: str = "open",
        user_id: int = 12345,
        user_login: str = "dev",
        merged: bool = False,
        merged_at: str | None = None,
        created_at: str = "2025-01-01T10:00:00Z",
        updated_at: str = "2025-01-01T10:00:00Z",
        additions: int = 10,
        deletions: int = 5,
        commits: int = 1,
        changed_files: int = 1,
        base_ref: str = "main",
        head_sha: str = "abc123",
        html_url: str = "https://github.com/org/repo/pull/1",
    ) -> MagicMock:
        """Create a mock PyGithub PullRequest object with all required attributes."""
        mock_pr = MagicMock()
        mock_pr.id = pr_id
        mock_pr.number = number
        mock_pr.title = title
        mock_pr.state = state
        mock_pr.merged = merged
        mock_pr.merged_at = datetime.fromisoformat(merged_at.replace("Z", "+00:00")) if merged_at else None
        mock_pr.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        mock_pr.updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        mock_pr.additions = additions
        mock_pr.deletions = deletions
        mock_pr.commits = commits
        mock_pr.changed_files = changed_files
        mock_pr.html_url = html_url

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.login = user_login
        mock_pr.user = mock_user

        # Mock base ref
        mock_base = MagicMock()
        mock_base.ref = base_ref
        mock_pr.base = mock_base

        # Mock head ref
        mock_head = MagicMock()
        mock_head.ref = head_ref
        mock_head.sha = head_sha
        mock_pr.head = mock_head

        return mock_pr

    def test_convert_pr_to_dict_extracts_jira_key_from_title(self):
        """Test that _convert_pr_to_dict extracts jira_key from PR title."""
        from apps.integrations.services.github_sync import _convert_pr_to_dict

        # Create mock PR with Jira key in title
        mock_pr = self._create_mock_pr(
            pr_id=123456789,
            number=42,
            title="PROJ-123: Add new feature",
            head_ref="feature/add-new-feature",
        )

        result = _convert_pr_to_dict(mock_pr)

        # Verify jira_key is extracted from title
        self.assertIn("jira_key", result)
        self.assertEqual(result["jira_key"], "PROJ-123")

    def test_convert_pr_to_dict_extracts_jira_key_from_branch_when_not_in_title(self):
        """Test that _convert_pr_to_dict extracts jira_key from branch name when not in title."""
        from apps.integrations.services.github_sync import _convert_pr_to_dict

        # Create mock PR with Jira key in branch but not title
        mock_pr = self._create_mock_pr(
            pr_id=123456789,
            number=42,
            title="Add new feature",  # No Jira key in title
            head_ref="feature/PROJ-456-add-new-feature",  # Jira key in branch
        )

        result = _convert_pr_to_dict(mock_pr)

        # Verify jira_key is extracted from branch name
        self.assertIn("jira_key", result)
        self.assertEqual(result["jira_key"], "PROJ-456")

    def test_convert_pr_to_dict_returns_empty_string_when_no_jira_key_found(self):
        """Test that _convert_pr_to_dict returns empty string when no jira_key found."""
        from apps.integrations.services.github_sync import _convert_pr_to_dict

        # Create mock PR without Jira key in title or branch
        mock_pr = self._create_mock_pr(
            pr_id=123456789,
            number=42,
            title="Add new feature",
            head_ref="feature/add-new-feature",
        )

        result = _convert_pr_to_dict(mock_pr)

        # Verify jira_key is empty string
        self.assertIn("jira_key", result)
        self.assertEqual(result["jira_key"], "")

    def test_convert_pr_to_dict_prefers_title_over_branch(self):
        """Test that _convert_pr_to_dict prefers Jira key from title over branch."""
        from apps.integrations.services.github_sync import _convert_pr_to_dict

        # Create mock PR with different Jira keys in title and branch
        mock_pr = self._create_mock_pr(
            pr_id=123456789,
            number=42,
            title="PROJ-123: Add new feature",  # Jira key in title
            head_ref="feature/PROJ-456-old-ticket",  # Different Jira key in branch
        )

        result = _convert_pr_to_dict(mock_pr)

        # Verify title's jira_key takes precedence
        self.assertIn("jira_key", result)
        self.assertEqual(result["jira_key"], "PROJ-123")

    def test_sync_repository_history_saves_jira_key_from_pr_title(self):
        """Test that sync_repository_history saves jira_key from PR title to PullRequest record."""
        from apps.integrations.factories import (
            GitHubIntegrationFactory,
            IntegrationCredentialFactory,
            TrackedRepositoryFactory,
        )
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.factories import TeamFactory, TeamMemberFactory
        from apps.metrics.models import PullRequest

        # Set up test fixtures
        team = TeamFactory()
        credential = IntegrationCredentialFactory(
            team=team,
            provider="github",
            access_token="encrypted_token_12345",
        )
        integration = GitHubIntegrationFactory(
            team=team,
            credential=credential,
        )
        tracked_repo = TrackedRepositoryFactory(
            team=team,
            integration=integration,
            full_name="acme-corp/api-server",
        )
        TeamMemberFactory(
            team=team,
            github_id="12345",
            display_name="John Dev",
        )

        # Mock the API to return PR with Jira key in title
        with (
            patch("apps.integrations.services.encryption.decrypt") as mock_decrypt,
            patch("apps.integrations.services.github_sync.get_repository_pull_requests") as mock_get_prs,
        ):
            mock_decrypt.return_value = "decrypted_token"
            mock_get_prs.return_value = [
                {
                    "id": 123456789,
                    "number": 42,
                    "title": "PROJ-123: Add new feature",  # Jira key in title
                    "state": "open",
                    "merged": False,
                    "merged_at": None,
                    "user": {"id": 12345, "login": "dev"},
                    "created_at": "2025-01-01T10:00:00Z",
                    "updated_at": "2025-01-01T10:00:00Z",
                    "additions": 100,
                    "deletions": 50,
                    "head": {"ref": "feature/add-new-feature"},  # No Jira key in branch
                }
            ]

            # Sync the repository
            sync_repository_history(tracked_repo)

        # Verify jira_key was saved to PullRequest record
        pr = PullRequest.objects.get(team=team, github_pr_id=123456789)
        self.assertEqual(pr.jira_key, "PROJ-123")

    def test_sync_repository_history_saves_jira_key_from_branch(self):
        """Test that sync_repository_history saves jira_key from branch when not in title."""
        from apps.integrations.factories import (
            GitHubIntegrationFactory,
            IntegrationCredentialFactory,
            TrackedRepositoryFactory,
        )
        from apps.integrations.services.github_sync import sync_repository_history
        from apps.metrics.factories import TeamFactory, TeamMemberFactory
        from apps.metrics.models import PullRequest

        # Set up test fixtures
        team = TeamFactory()
        credential = IntegrationCredentialFactory(
            team=team,
            provider="github",
            access_token="encrypted_token_12345",
        )
        integration = GitHubIntegrationFactory(
            team=team,
            credential=credential,
        )
        tracked_repo = TrackedRepositoryFactory(
            team=team,
            integration=integration,
            full_name="acme-corp/api-server",
        )
        TeamMemberFactory(
            team=team,
            github_id="12345",
            display_name="John Dev",
        )

        # Mock the API to return PR with Jira key in branch
        with (
            patch("apps.integrations.services.encryption.decrypt") as mock_decrypt,
            patch("apps.integrations.services.github_sync.get_repository_pull_requests") as mock_get_prs,
        ):
            mock_decrypt.return_value = "decrypted_token"
            mock_get_prs.return_value = [
                {
                    "id": 123456789,
                    "number": 42,
                    "title": "Add new feature",  # No Jira key in title
                    "state": "open",
                    "merged": False,
                    "merged_at": None,
                    "user": {"id": 12345, "login": "dev"},
                    "created_at": "2025-01-01T10:00:00Z",
                    "updated_at": "2025-01-01T10:00:00Z",
                    "additions": 100,
                    "deletions": 50,
                    "head": {"ref": "feature/PROJ-456-add-new-feature"},  # Jira key in branch
                }
            ]

            # Sync the repository
            sync_repository_history(tracked_repo)

        # Verify jira_key was saved to PullRequest record
        pr = PullRequest.objects.get(team=team, github_pr_id=123456789)
        self.assertEqual(pr.jira_key, "PROJ-456")

    def test_sync_repository_incremental_saves_jira_key_from_pr_title(self):
        """Test that sync_repository_incremental saves jira_key from PR title to PullRequest record."""
        from datetime import datetime

        from apps.integrations.factories import (
            GitHubIntegrationFactory,
            IntegrationCredentialFactory,
            TrackedRepositoryFactory,
        )
        from apps.integrations.services.github_sync import sync_repository_incremental
        from apps.metrics.factories import TeamFactory, TeamMemberFactory
        from apps.metrics.models import PullRequest

        # Set up test fixtures
        team = TeamFactory()
        credential = IntegrationCredentialFactory(
            team=team,
            provider="github",
            access_token="encrypted_token_12345",
        )
        integration = GitHubIntegrationFactory(
            team=team,
            credential=credential,
        )
        tracked_repo = TrackedRepositoryFactory(
            team=team,
            integration=integration,
            full_name="acme-corp/api-server",
            last_sync_at=datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC),  # Set so it doesn't fall back to full sync
        )
        TeamMemberFactory(
            team=team,
            github_id="12345",
            display_name="John Dev",
        )

        # Mock the API to return PR with Jira key in title
        with (
            patch("apps.integrations.services.encryption.decrypt") as mock_decrypt,
            patch("apps.integrations.services.github_sync.get_updated_pull_requests") as mock_get_updated_prs,
        ):
            mock_decrypt.return_value = "decrypted_token"
            mock_get_updated_prs.return_value = [
                {
                    "id": 987654321,
                    "number": 99,
                    "title": "ABC-999: Fix critical bug",  # Jira key in title
                    "state": "open",
                    "merged": False,
                    "merged_at": None,
                    "user": {"id": 12345, "login": "dev"},
                    "created_at": "2025-01-06T10:00:00Z",
                    "updated_at": "2025-01-06T12:00:00Z",
                    "additions": 50,
                    "deletions": 25,
                    "head": {"ref": "hotfix/critical-bug"},  # No Jira key in branch
                }
            ]

            # Sync incrementally
            sync_repository_incremental(tracked_repo)

        # Verify jira_key was saved to PullRequest record
        pr = PullRequest.objects.get(team=team, github_pr_id=987654321)
        self.assertEqual(pr.jira_key, "ABC-999")
