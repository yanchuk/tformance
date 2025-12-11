"""Tests for GitHub sync service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    GitHubOAuthError,
    get_pull_request_reviews,
    get_repository_pull_requests,
)


class TestGetRepositoryPullRequests(TestCase):
    """Tests for fetching pull requests from GitHub repository."""

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_repository_pull_requests_returns_prs(self, mock_get):
        """Test that get_repository_pull_requests returns list of PRs from GitHub API."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}  # No pagination - single page
        mock_response.json.return_value = [
            {
                "id": 1,
                "number": 101,
                "title": "Add new feature",
                "state": "open",
                "user": {"login": "developer1", "id": 1001},
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-02T15:30:00Z",
                "merged_at": None,
                "draft": False,
            },
            {
                "id": 2,
                "number": 102,
                "title": "Fix bug in login",
                "state": "closed",
                "user": {"login": "developer2", "id": 1002},
                "created_at": "2025-01-03T09:00:00Z",
                "updated_at": "2025-01-04T11:15:00Z",
                "merged_at": "2025-01-04T11:15:00Z",
                "draft": False,
            },
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"

        result = get_repository_pull_requests(access_token, repo_full_name)

        # Verify result contains PRs
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["number"], 101)
        self.assertEqual(result[0]["title"], "Add new feature")
        self.assertEqual(result[1]["number"], 102)
        self.assertEqual(result[1]["title"], "Fix bug in login")

        # Verify the request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(
            call_args[0][0], "https://api.github.com/repos/acme-corp/backend-api/pulls?state=all&per_page=100"
        )

        # Verify headers
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["Authorization"], "token gho_test_token")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_repository_pull_requests_handles_pagination(self, mock_get):
        """Test that get_repository_pull_requests fetches all pages when Link header has next relation."""
        # Mock first page response with Link header pointing to page 2
        mock_response_page1 = MagicMock()
        mock_response_page1.status_code = 200
        mock_response_page1.headers = {
            "Link": (
                '<https://api.github.com/repos/acme-corp/backend-api/pulls?page=2>; rel="next", '
                '<https://api.github.com/repos/acme-corp/backend-api/pulls?page=2>; rel="last"'
            )
        }
        mock_response_page1.json.return_value = [
            {
                "id": 1,
                "number": 101,
                "title": "PR from page 1",
                "state": "open",
                "user": {"login": "user1", "id": 1001},
            },
        ]

        # Mock second page response with no next link (last page)
        mock_response_page2 = MagicMock()
        mock_response_page2.status_code = 200
        mock_response_page2.headers = {
            "Link": (
                '<https://api.github.com/repos/acme-corp/backend-api/pulls?page=1>; rel="first", '
                '<https://api.github.com/repos/acme-corp/backend-api/pulls?page=1>; rel="prev"'
            )
        }
        mock_response_page2.json.return_value = [
            {
                "id": 2,
                "number": 102,
                "title": "PR from page 2",
                "state": "closed",
                "user": {"login": "user2", "id": 1002},
            },
        ]

        # Set up mock to return different responses for each call
        mock_get.side_effect = [mock_response_page1, mock_response_page2]

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"

        result = get_repository_pull_requests(access_token, repo_full_name)

        # Verify all pages were fetched and combined
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2, "Should return all PRs from all pages combined")
        self.assertEqual(result[0]["number"], 101)
        self.assertEqual(result[1]["number"], 102)

        # Verify requests.get was called 2 times (for 2 pages)
        self.assertEqual(mock_get.call_count, 2, "Should make 2 API requests for 2 pages")

        # Verify first call was to the base endpoint
        first_call_args = mock_get.call_args_list[0]
        self.assertEqual(
            first_call_args[0][0],
            "https://api.github.com/repos/acme-corp/backend-api/pulls?state=all&per_page=100",
        )

        # Verify second call used the URL from Link header
        second_call_args = mock_get.call_args_list[1]
        self.assertEqual(
            second_call_args[0][0],
            "https://api.github.com/repos/acme-corp/backend-api/pulls?page=2",
        )

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_repository_pull_requests_filters_by_state(self, mock_get):
        """Test that get_repository_pull_requests passes state parameter to API correctly."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = [
            {
                "id": 1,
                "number": 101,
                "title": "Open PR",
                "state": "open",
            },
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "test-org/test-repo"

        # Test with state="open"
        get_repository_pull_requests(access_token, repo_full_name, state="open")
        call_args = mock_get.call_args
        self.assertIn("state=open", call_args[0][0])

        # Reset mock
        mock_get.reset_mock()
        mock_get.return_value = mock_response

        # Test with state="closed"
        get_repository_pull_requests(access_token, repo_full_name, state="closed")
        call_args = mock_get.call_args
        self.assertIn("state=closed", call_args[0][0])

        # Reset mock
        mock_get.reset_mock()
        mock_get.return_value = mock_response

        # Test with state="all" (default)
        get_repository_pull_requests(access_token, repo_full_name, state="all")
        call_args = mock_get.call_args
        self.assertIn("state=all", call_args[0][0])

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_repository_pull_requests_uses_custom_per_page(self, mock_get):
        """Test that get_repository_pull_requests respects custom per_page parameter."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "test-org/test-repo"

        # Test with custom per_page value
        get_repository_pull_requests(access_token, repo_full_name, per_page=50)
        call_args = mock_get.call_args
        self.assertIn("per_page=50", call_args[0][0])

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_repository_pull_requests_raises_on_403_forbidden(self, mock_get):
        """Test that get_repository_pull_requests raises GitHubOAuthError on 403 (no permission)."""
        # Mock 403 response (insufficient permissions)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "You must have read access to this repository.",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "private-org/secret-repo"

        with self.assertRaises(GitHubOAuthError) as context:
            get_repository_pull_requests(access_token, repo_full_name)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_repository_pull_requests_raises_on_404_not_found(self, mock_get):
        """Test that get_repository_pull_requests raises GitHubOAuthError on 404 (repo not found)."""
        # Mock 404 response (repository not found)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "org/nonexistent-repo"

        with self.assertRaises(GitHubOAuthError) as context:
            get_repository_pull_requests(access_token, repo_full_name)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_repository_pull_requests_raises_on_other_error_codes(self, mock_get):
        """Test that get_repository_pull_requests raises GitHubOAuthError on other HTTP errors."""
        # Mock 500 response (server error)
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "message": "Internal Server Error",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "org/repo"

        with self.assertRaises(GitHubOAuthError) as context:
            get_repository_pull_requests(access_token, repo_full_name)

        self.assertIn("500", str(context.exception))


class TestGetPullRequestReviews(TestCase):
    """Tests for fetching reviews for a specific pull request."""

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_pull_request_reviews_returns_reviews(self, mock_get):
        """Test that get_pull_request_reviews returns list of reviews from GitHub API."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}  # No pagination - single page
        mock_response.json.return_value = [
            {
                "id": 12345,
                "user": {"login": "reviewer1", "id": 2001},
                "body": "Looks good to me!",
                "state": "APPROVED",
                "submitted_at": "2025-01-05T14:30:00Z",
            },
            {
                "id": 12346,
                "user": {"login": "reviewer2", "id": 2002},
                "body": "Please fix the typo in line 45",
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2025-01-05T15:00:00Z",
            },
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 101

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify result contains reviews
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 12345)
        self.assertEqual(result[0]["state"], "APPROVED")
        self.assertEqual(result[1]["id"], 12346)
        self.assertEqual(result[1]["state"], "CHANGES_REQUESTED")

        # Verify the request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(
            call_args[0][0], "https://api.github.com/repos/acme-corp/backend-api/pulls/101/reviews?per_page=100"
        )

        # Verify headers
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["Authorization"], "token gho_test_token")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_pull_request_reviews_handles_empty_reviews(self, mock_get):
        """Test that get_pull_request_reviews returns empty list when no reviews exist."""
        # Mock response with empty reviews array
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 999

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify result is an empty list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

        # Verify the request was made
        mock_get.assert_called_once()

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_pull_request_reviews_handles_pagination(self, mock_get):
        """Test that get_pull_request_reviews fetches all pages when Link header has next relation."""
        # Mock first page response with Link header pointing to page 2
        mock_response_page1 = MagicMock()
        mock_response_page1.status_code = 200
        mock_response_page1.headers = {
            "Link": (
                '<https://api.github.com/repos/acme-corp/backend-api/pulls/101/reviews?page=2>; rel="next", '
                '<https://api.github.com/repos/acme-corp/backend-api/pulls/101/reviews?page=2>; rel="last"'
            )
        }
        mock_response_page1.json.return_value = [
            {
                "id": 1,
                "user": {"login": "reviewer1", "id": 2001},
                "state": "APPROVED",
                "submitted_at": "2025-01-01T10:00:00Z",
            },
        ]

        # Mock second page response with no next link (last page)
        mock_response_page2 = MagicMock()
        mock_response_page2.status_code = 200
        mock_response_page2.headers = {
            "Link": (
                '<https://api.github.com/repos/acme-corp/backend-api/pulls/101/reviews?page=1>; rel="first", '
                '<https://api.github.com/repos/acme-corp/backend-api/pulls/101/reviews?page=1>; rel="prev"'
            )
        }
        mock_response_page2.json.return_value = [
            {
                "id": 2,
                "user": {"login": "reviewer2", "id": 2002},
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2025-01-02T11:00:00Z",
            },
        ]

        # Set up mock to return different responses for each call
        mock_get.side_effect = [mock_response_page1, mock_response_page2]

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 101

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify all pages were fetched and combined
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2, "Should return all reviews from all pages combined")
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[1]["id"], 2)

        # Verify requests.get was called 2 times (for 2 pages)
        self.assertEqual(mock_get.call_count, 2, "Should make 2 API requests for 2 pages")

        # Verify first call was to the base endpoint
        first_call_args = mock_get.call_args_list[0]
        self.assertEqual(
            first_call_args[0][0],
            "https://api.github.com/repos/acme-corp/backend-api/pulls/101/reviews?per_page=100",
        )

        # Verify second call used the URL from Link header
        second_call_args = mock_get.call_args_list[1]
        self.assertEqual(
            second_call_args[0][0],
            "https://api.github.com/repos/acme-corp/backend-api/pulls/101/reviews?page=2",
        )

    @patch("apps.integrations.services.github_sync.requests.get")
    def test_get_pull_request_reviews_raises_on_api_error(self, mock_get):
        """Test that get_pull_request_reviews raises GitHubOAuthError on API errors."""
        # Mock 404 response (PR not found)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found",
        }
        mock_get.return_value = mock_response

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
