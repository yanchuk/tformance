"""Tests for GitHub GraphQL repository history sync functionality."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TransactionTestCase
from django.utils import timezone

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.integrations.services.github_graphql import GitHubGraphQLError, GitHubGraphQLRateLimitError
from apps.integrations.services.github_graphql_sync import sync_repository_history_graphql
from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.metrics.models import Commit, PRFile, PRReview, PullRequest, TeamMember


def create_mock_graphql_client():
    """Create a mock GitHubGraphQLClient with all async methods properly mocked.

    Returns a MagicMock with all async methods set up as AsyncMock to prevent
    'can't be used in await expression' errors.
    """
    mock_client = MagicMock()
    # The get_pr_count_in_date_range method is called before fetch_prs_bulk
    # Return 0 to trigger fallback to totalCount from fetch_prs_bulk response
    mock_client.get_pr_count_in_date_range = AsyncMock(return_value=0)
    return mock_client


def create_graphql_pr_response(pr_number=123, state="MERGED", has_reviews=True, has_commits=True, has_files=True):
    """Helper to create realistic GraphQL PR response data."""
    base_time = timezone.now() - timedelta(days=5)
    pr_data = {
        "number": pr_number,
        "databaseId": 1000000 + pr_number,
        "title": f"Test PR #{pr_number}",
        "body": "PR description here",
        "state": state,
        "createdAt": base_time.isoformat(),
        "mergedAt": (base_time + timedelta(hours=24)).isoformat() if state == "MERGED" else None,
        "additions": 150,
        "deletions": 50,
        "author": {"login": "testuser"},
        "reviews": {"nodes": []},
        "commits": {"nodes": []},
        "files": {"nodes": []},
    }

    if has_reviews:
        pr_data["reviews"]["nodes"] = [
            {
                "databaseId": 2000000 + pr_number,
                "author": {"login": "reviewer1"},
                "state": "APPROVED",
                "submittedAt": (base_time + timedelta(hours=12)).isoformat(),
                "body": "LGTM",
            }
        ]

    if has_commits:
        pr_data["commits"]["nodes"] = [
            {
                "commit": {
                    "oid": f"abc123def456{pr_number:08d}",
                    "message": f"Commit message for PR {pr_number}",
                    "author": {
                        "user": {"login": "testuser"},
                        "date": (base_time + timedelta(hours=2)).isoformat(),
                    },
                    "additions": 100,
                    "deletions": 30,
                }
            }
        ]

    if has_files:
        pr_data["files"]["nodes"] = [
            {"path": "src/app.py", "additions": 80, "deletions": 20, "status": "modified"},
            {"path": "tests/test_app.py", "additions": 70, "deletions": 30, "status": "added"},
        ]

    return pr_data


class TestSyncRepositoryHistoryGraphQLBasicFunctionality(TransactionTestCase):
    """Tests for basic sync_repository_history_graphql functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_creates_pull_request_from_graphql_data(self, mock_client_class):
        """Test that sync creates PullRequest records from GraphQL response."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=123, state="MERGED")
        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertEqual(result["prs_synced"], 1)
        pr = PullRequest.objects.filter(team=self.team, github_pr_id=123).first()
        self.assertIsNotNone(pr)
        self.assertEqual(pr.title, "Test PR #123")
        self.assertEqual(pr.state, "merged")  # MERGED -> merged (lowercase)
        self.assertEqual(pr.author, self.author)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_maps_graphql_fields_to_model_fields(self, mock_client_class):
        """Test that sync correctly maps GraphQL camelCase fields to snake_case model fields."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        base_time = timezone.now() - timedelta(days=5)
        pr_data = {
            "number": 456,
            "databaseId": 1000456,
            "title": "Feature PR",
            "body": "PR body text",
            "state": "MERGED",
            "createdAt": base_time.isoformat(),
            "mergedAt": (base_time + timedelta(hours=48)).isoformat(),
            "additions": 200,
            "deletions": 100,
            "author": {"login": "testuser"},
            "reviews": {"nodes": []},
            "commits": {"nodes": []},
            "files": {"nodes": []},
        }

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=456)
        self.assertEqual(pr.title, "Feature PR")
        self.assertEqual(pr.body, "PR body text")
        self.assertEqual(pr.additions, 200)
        self.assertEqual(pr.deletions, 100)
        self.assertIsNotNone(pr.pr_created_at)
        self.assertIsNotNone(pr.merged_at)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_uses_graphql_client_fetch_prs_bulk(self, mock_client_class):
        """Test that sync uses GitHubGraphQLClient.fetch_prs_bulk to fetch PRs."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        mock_client.fetch_prs_bulk.assert_called()
        call_args = mock_client.fetch_prs_bulk.call_args
        self.assertEqual(call_args[1]["owner"], "owner")
        self.assertEqual(call_args[1]["repo"], "repo")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_returns_result_dict_with_counts(self, mock_client_class):
        """Test that sync returns dict with prs_synced, reviews_synced, etc."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertIn("prs_synced", result)
        self.assertIn("reviews_synced", result)
        self.assertIn("commits_synced", result)
        self.assertIn("files_synced", result)
        self.assertIn("comments_synced", result)
        self.assertIn("errors", result)
        self.assertEqual(result["prs_synced"], 0)
        self.assertEqual(result["errors"], [])


class TestSyncRepositoryHistoryGraphQLPagination(TransactionTestCase):
    """Tests for pagination handling in sync_repository_history_graphql."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_handles_multiple_pages_of_prs(self, mock_client_class):
        """Test that sync fetches all pages of PRs using pagination cursors."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # Page 1 response
        page1_data = {
            "repository": {
                "pullRequests": {
                    "nodes": [create_graphql_pr_response(pr_number=1), create_graphql_pr_response(pr_number=2)],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor_page2"},
                }
            },
            "rateLimit": {"remaining": 5000},
        }

        # Page 2 response
        page2_data = {
            "repository": {
                "pullRequests": {
                    "nodes": [create_graphql_pr_response(pr_number=3)],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 4995},
        }

        # Mock returns different responses based on cursor
        async def fetch_prs_side_effect(owner, repo, cursor=None):
            if cursor is None:
                return page1_data
            elif cursor == "cursor_page2":
                return page2_data

        mock_client.fetch_prs_bulk = AsyncMock(side_effect=fetch_prs_side_effect)

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertEqual(mock_client.fetch_prs_bulk.call_count, 2)
        self.assertEqual(result["prs_synced"], 3)
        self.assertEqual(PullRequest.objects.filter(team=self.team).count(), 3)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_passes_pagination_cursor_correctly(self, mock_client_class):
        """Test that sync passes pagination cursor to subsequent fetch_prs_bulk calls."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        page1_data = {
            "repository": {
                "pullRequests": {
                    "nodes": [create_graphql_pr_response(pr_number=1)],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor_xyz"},
                }
            },
            "rateLimit": {"remaining": 5000},
        }

        page2_data = {
            "repository": {
                "pullRequests": {
                    "nodes": [create_graphql_pr_response(pr_number=2)],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 4995},
        }

        mock_client.fetch_prs_bulk = AsyncMock(side_effect=[page1_data, page2_data])

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        calls = mock_client.fetch_prs_bulk.call_args_list
        self.assertEqual(len(calls), 2)
        # First call should have no cursor
        self.assertIsNone(calls[0][1].get("cursor"))
        # Second call should have cursor from page1
        self.assertEqual(calls[1][1]["cursor"], "cursor_xyz")


class TestSyncRepositoryHistoryGraphQLDaysBackFilter(TransactionTestCase):
    """Tests for days_back filtering in sync_repository_history_graphql."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_filters_prs_older_than_days_back(self, mock_client_class):
        """Test that sync filters out PRs created before days_back threshold."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # PR created 100 days ago (should be filtered out with days_back=90)
        old_pr = create_graphql_pr_response(pr_number=1)
        old_pr["createdAt"] = (timezone.now() - timedelta(days=100)).isoformat()

        # PR created 30 days ago (should be synced)
        recent_pr = create_graphql_pr_response(pr_number=2)
        recent_pr["createdAt"] = (timezone.now() - timedelta(days=30)).isoformat()

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {
                        "nodes": [old_pr, recent_pr],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertEqual(result["prs_synced"], 1)  # Only recent PR synced
        self.assertFalse(PullRequest.objects.filter(team=self.team, github_pr_id=1).exists())
        self.assertTrue(PullRequest.objects.filter(team=self.team, github_pr_id=2).exists())

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_respects_custom_days_back_parameter(self, mock_client_class):
        """Test that sync respects custom days_back parameter."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # PR created 20 days ago (should be filtered out with days_back=10)
        pr_data = create_graphql_pr_response(pr_number=1)
        pr_data["createdAt"] = (timezone.now() - timedelta(days=20)).isoformat()

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=10))

        # Assert
        self.assertEqual(result["prs_synced"], 0)
        self.assertFalse(PullRequest.objects.filter(team=self.team).exists())


class TestSyncRepositoryHistoryGraphQLNestedData(TransactionTestCase):
    """Tests for syncing nested data (reviews, commits, files, comments)."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")
        self.reviewer = TeamMemberFactory(team=self.team, github_id="reviewer1")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_creates_pr_reviews_from_nested_data(self, mock_client_class):
        """Test that sync creates PRReview records from nested reviews data."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=123, has_reviews=True)
        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertEqual(result["reviews_synced"], 1)
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123)
        review = PRReview.objects.filter(team=self.team, pull_request=pr).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.reviewer, self.reviewer)
        self.assertEqual(review.state, "approved")  # APPROVED -> approved

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_creates_commits_from_nested_data(self, mock_client_class):
        """Test that sync creates Commit records from nested commits data."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=123, has_commits=True)
        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertEqual(result["commits_synced"], 1)
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123)
        commit = Commit.objects.filter(team=self.team, pull_request=pr).first()
        self.assertIsNotNone(commit)
        self.assertIn("abc123def456", commit.github_sha)
        self.assertEqual(commit.author, self.author)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_creates_pr_files_from_nested_data(self, mock_client_class):
        """Test that sync creates PRFile records from nested files data."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=123, has_files=True)
        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertEqual(result["files_synced"], 2)
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123)
        files = PRFile.objects.filter(team=self.team, pull_request=pr)
        self.assertEqual(files.count(), 2)
        filenames = [f.filename for f in files]
        self.assertIn("src/app.py", filenames)
        self.assertIn("tests/test_app.py", filenames)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_handles_pr_without_nested_data(self, mock_client_class):
        """Test that sync handles PRs with no reviews, commits, or files gracefully."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=123, has_reviews=False, has_commits=False, has_files=False)
        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertEqual(result["prs_synced"], 1)
        self.assertEqual(result["reviews_synced"], 0)
        self.assertEqual(result["commits_synced"], 0)
        self.assertEqual(result["files_synced"], 0)


class TestSyncRepositoryHistoryGraphQLErrorHandling(TransactionTestCase):
    """Tests for error handling in sync_repository_history_graphql."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_logs_errors_but_continues_processing_other_prs(self, mock_client_class):
        """Test that sync logs errors for individual PRs but continues processing others."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # PR with invalid data that will cause processing error
        bad_pr = create_graphql_pr_response(pr_number=1)
        bad_pr["author"] = None  # Missing author should cause error

        # Valid PR
        good_pr = create_graphql_pr_response(pr_number=2)

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {
                        "nodes": [bad_pr, good_pr],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Create author for good PR
        TeamMemberFactory(team=self.team, github_id="testuser")

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertGreater(len(result["errors"]), 0)  # Should have error for bad PR
        self.assertEqual(result["prs_synced"], 1)  # Should still sync good PR

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_returns_errors_list_in_result(self, mock_client_class):
        """Test that sync returns list of errors in result dict."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(side_effect=GitHubGraphQLError("API error"))

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertIn("errors", result)
        self.assertIsInstance(result["errors"], list)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_handles_graphql_rate_limit_error(self, mock_client_class):
        """Test that sync handles GitHubGraphQLRateLimitError appropriately."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(side_effect=GitHubGraphQLRateLimitError("Rate limit exceeded"))

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertGreater(len(result["errors"]), 0)
        self.assertIn("rate limit", result["errors"][0].lower())

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_handles_graphql_error(self, mock_client_class):
        """Test that sync handles GitHubGraphQLError appropriately."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(side_effect=GitHubGraphQLError("GraphQL query failed"))

        # Act
        result = asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertGreater(len(result["errors"]), 0)
        self.assertIn("graphql", result["errors"][0].lower())


class TestSyncRepositoryHistoryGraphQLProgressTracking(TransactionTestCase):
    """Tests for progress tracking in sync_repository_history_graphql."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo", sync_status="pending")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_updates_tracked_repository_sync_status(self, mock_client_class):
        """Test that sync updates TrackedRepository.sync_status during sync."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_status, "complete")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_updates_tracked_repository_last_sync_at(self, mock_client_class):
        """Test that sync updates TrackedRepository.last_sync_at timestamp."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        before_sync = timezone.now()
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))
        after_sync = timezone.now()

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertIsNotNone(self.tracked_repo.last_sync_at)
        self.assertGreaterEqual(self.tracked_repo.last_sync_at, before_sync)
        self.assertLessEqual(self.tracked_repo.last_sync_at, after_sync)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_sets_sync_status_to_error_on_failure(self, mock_client_class):
        """Test that sync sets TrackedRepository.sync_status to 'error' on failure."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(side_effect=Exception("Unexpected error"))

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_status, "error")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_updates_progress_fields_during_sync(self, mock_client_class):
        """Test that sync updates sync_progress, sync_prs_completed, sync_prs_total."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=1)
        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {
                        "nodes": [pr_data],
                        "totalCount": 50,  # Total PRs in repo
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_prs_total, 50)
        self.assertEqual(self.tracked_repo.sync_prs_completed, 50)  # Should be total at end
        self.assertEqual(self.tracked_repo.sync_progress, 100)  # Should be 100% at end

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_initializes_progress_from_totalcount(self, mock_client_class):
        """Test that sync gets totalCount from first GraphQL response."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # First page with hasNextPage=True to simulate pagination
        first_page_prs = [create_graphql_pr_response(pr_number=i) for i in range(1, 11)]
        second_page_prs = [create_graphql_pr_response(pr_number=i) for i in range(11, 16)]

        mock_client.fetch_prs_bulk = AsyncMock(
            side_effect=[
                {
                    "repository": {
                        "pullRequests": {
                            "nodes": first_page_prs,
                            "totalCount": 100,
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor1"},
                        }
                    },
                    "rateLimit": {"remaining": 5000},
                },
                {
                    "repository": {
                        "pullRequests": {
                            "nodes": second_page_prs,
                            "totalCount": 100,
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    },
                    "rateLimit": {"remaining": 5000},
                },
            ]
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_prs_total, 100)
        # Progress should be 100% at end (completed/total capped)
        self.assertEqual(self.tracked_repo.sync_progress, 100)


class TestSyncRepositoryHistoryGraphQLDataUpdateBehavior(TransactionTestCase):
    """Tests for update/create behavior in sync_repository_history_graphql."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_updates_existing_pull_request(self, mock_client_class):
        """Test that sync updates existing PullRequest if already synced."""
        # Arrange
        from apps.metrics.factories import PullRequestFactory

        existing_pr = PullRequestFactory(
            team=self.team,
            github_pr_id=123,
            github_repo="owner/repo",  # Match tracked_repo.full_name
            title="Old Title",
            state="open",
        )

        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=123, state="MERGED")
        pr_data["title"] = "Updated Title"

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        existing_pr.refresh_from_db()
        self.assertEqual(existing_pr.title, "Updated Title")
        self.assertEqual(existing_pr.state, "merged")
        self.assertEqual(PullRequest.objects.filter(team=self.team, github_pr_id=123).count(), 1)  # No duplicate

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_creates_new_pull_request_if_not_exists(self, mock_client_class):
        """Test that sync creates new PullRequest if doesn't exist."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=999)
        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.assertTrue(PullRequest.objects.filter(team=self.team, github_pr_id=999).exists())


# ============================================================================
# Incremental Sync Tests
# ============================================================================


def create_incremental_pr_response(pr_number=123, state="MERGED", updated_at=None):
    """Helper to create GraphQL PR response with updatedAt field for incremental sync."""
    base_time = timezone.now() - timedelta(days=5)
    updated_time = updated_at or timezone.now() - timedelta(hours=1)

    return {
        "number": pr_number,
        "title": f"Updated PR #{pr_number}",
        "body": "Updated description",
        "state": state,
        "createdAt": base_time.isoformat(),
        "updatedAt": updated_time.isoformat(),
        "mergedAt": (base_time + timedelta(hours=24)).isoformat() if state == "MERGED" else None,
        "additions": 100,
        "deletions": 50,
        "author": {"login": "testuser"},
        "reviews": {"nodes": []},
        "commits": {"nodes": []},
        "files": {"nodes": []},
    }


class TestSyncRepositoryIncrementalGraphQLBasicFunctionality(TransactionTestCase):
    """Tests for basic sync_repository_incremental_graphql functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            full_name="owner/repo",
            last_sync_at=timezone.now() - timedelta(hours=24),
        )
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")

    def test_sync_incremental_function_exists(self):
        """Test that sync_repository_incremental_graphql function exists and is importable."""
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        self.assertTrue(callable(sync_repository_incremental_graphql))

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_returns_result_dict_with_counts(self, mock_client_class):
        """Test that sync_repository_incremental_graphql returns dict with sync counts."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        result = asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.assertIn("prs_synced", result)
        self.assertIn("reviews_synced", result)
        self.assertIn("commits_synced", result)
        self.assertIn("files_synced", result)
        self.assertIn("errors", result)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_uses_fetch_prs_updated_since(self, mock_client_class):
        """Test that incremental sync uses fetch_prs_updated_since method."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        mock_client.fetch_prs_updated_since.assert_called()

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_passes_since_parameter(self, mock_client_class):
        """Test that incremental sync passes the last_sync_at as since parameter."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        call_kwargs = mock_client.fetch_prs_updated_since.call_args[1]
        self.assertEqual(call_kwargs["owner"], "owner")
        self.assertEqual(call_kwargs["repo"], "repo")
        self.assertIsNotNone(call_kwargs.get("since"))


class TestSyncRepositoryIncrementalGraphQLPRProcessing(TransactionTestCase):
    """Tests for PR processing in incremental sync."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            full_name="owner/repo",
            last_sync_at=timezone.now() - timedelta(hours=24),
        )
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_creates_pr_from_response(self, mock_client_class):
        """Test that incremental sync creates PullRequest from GraphQL response."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_incremental_pr_response(pr_number=456)
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        result = asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.assertEqual(result["prs_synced"], 1)
        self.assertTrue(PullRequest.objects.filter(team=self.team, github_pr_id=456).exists())

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_updates_existing_pr(self, mock_client_class):
        """Test that incremental sync updates existing PullRequest."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # Create existing PR
        existing_pr = PullRequest.objects.create(
            team=self.team,
            github_pr_id=123,
            github_repo="owner/repo",
            title="Original Title",
            state="open",
            author=self.author,
        )

        # GraphQL response with updated data
        pr_data = create_incremental_pr_response(pr_number=123, state="MERGED")
        pr_data["title"] = "Updated Title"
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        existing_pr.refresh_from_db()
        self.assertEqual(existing_pr.title, "Updated Title")
        self.assertEqual(existing_pr.state, "merged")


class TestSyncRepositoryIncrementalGraphQLErrorHandling(TransactionTestCase):
    """Tests for error handling in incremental sync."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            full_name="owner/repo",
            last_sync_at=timezone.now() - timedelta(hours=24),
        )

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_handles_graphql_error(self, mock_client_class):
        """Test that incremental sync handles GraphQL errors gracefully."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(side_effect=GitHubGraphQLError("Query failed"))

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        result = asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.assertIn("errors", result)
        self.assertTrue(len(result["errors"]) > 0)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_handles_rate_limit_error(self, mock_client_class):
        """Test that incremental sync handles rate limit errors."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(side_effect=GitHubGraphQLRateLimitError("Rate limit"))

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        result = asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.assertIn("errors", result)
        self.assertTrue(any("rate limit" in e.lower() for e in result["errors"]))


class TestSyncRepositoryIncrementalGraphQLStatusTracking(TransactionTestCase):
    """Tests for sync status tracking in incremental sync."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            full_name="owner/repo",
            last_sync_at=timezone.now() - timedelta(hours=24),
        )

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_updates_last_sync_at(self, mock_client_class):
        """Test that incremental sync updates last_sync_at on completion."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        old_sync_at = self.tracked_repo.last_sync_at

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertIsNotNone(self.tracked_repo.last_sync_at)
        self.assertGreater(self.tracked_repo.last_sync_at, old_sync_at)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_sets_sync_status_complete(self, mock_client_class):
        """Test that incremental sync sets sync_status to complete on success."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}},
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_status, "complete")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_sets_sync_status_error_on_failure(self, mock_client_class):
        """Test that incremental sync sets sync_status to error on failure."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(side_effect=GitHubGraphQLError("Query failed"))

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_status, "error")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_incremental_updates_progress_fields(self, mock_client_class):
        """Test that incremental sync updates progress fields."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=1)
        pr_data["updatedAt"] = timezone.now().isoformat()  # Recent update

        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {
                        "nodes": [pr_data],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.tracked_repo.refresh_from_db()
        # Progress should be 100% at completion
        self.assertEqual(self.tracked_repo.sync_progress, 100)
        # For incremental, prs_completed = prs_total at end
        self.assertEqual(self.tracked_repo.sync_prs_completed, self.tracked_repo.sync_prs_total)


# =============================================================================
# Phase 4: fetch_pr_complete_data_graphql Tests
# =============================================================================


class TestFetchPRCompleteDataGraphQLBasic(TransactionTestCase):
    """Tests for fetch_pr_complete_data_graphql basic functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, github_username="testuser")
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            full_name="test-org/test-repo",
            is_active=True,
        )

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_fetch_pr_complete_data_calls_fetch_single_pr(self, mock_client_class):
        """Test that function calls fetch_single_pr with correct params."""
        from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql
        from apps.metrics.factories import PullRequestFactory

        # Arrange
        pr = PullRequestFactory(
            team=self.team,
            github_repo="test-org/test-repo",
            github_pr_id=42,
        )

        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_single_pr = AsyncMock(
            return_value={
                "repository": {
                    "pullRequest": create_graphql_pr_response(pr_number=42),
                },
                "rateLimit": {"remaining": 4900},
            }
        )

        # Act
        asyncio.run(fetch_pr_complete_data_graphql(pr, self.tracked_repo))

        # Assert
        mock_client.fetch_single_pr.assert_called_once_with("test-org", "test-repo", 42)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_fetch_pr_complete_data_returns_sync_counts(self, mock_client_class):
        """Test that function returns dict with sync counts."""
        from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql
        from apps.metrics.factories import PullRequestFactory

        # Arrange
        pr = PullRequestFactory(
            team=self.team,
            github_repo="test-org/test-repo",
            github_pr_id=42,
        )

        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_single_pr = AsyncMock(
            return_value={
                "repository": {
                    "pullRequest": create_graphql_pr_response(pr_number=42),
                },
                "rateLimit": {"remaining": 4900},
            }
        )

        # Act
        result = asyncio.run(fetch_pr_complete_data_graphql(pr, self.tracked_repo))

        # Assert
        self.assertIsInstance(result, dict)
        self.assertIn("commits_synced", result)
        self.assertIn("files_synced", result)
        self.assertIn("reviews_synced", result)
        self.assertIn("errors", result)


class TestFetchPRCompleteDataGraphQLDataProcessing(TransactionTestCase):
    """Tests for fetch_pr_complete_data_graphql data processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, github_username="testuser")
        self.reviewer = TeamMemberFactory(team=self.team, github_username="reviewer1")
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            full_name="test-org/test-repo",
            is_active=True,
        )

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_creates_commits_from_graphql_response(self, mock_client_class):
        """Test that commits are created from GraphQL response."""
        from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql
        from apps.metrics.factories import PullRequestFactory

        # Arrange
        pr = PullRequestFactory(
            team=self.team,
            github_repo="test-org/test-repo",
            github_pr_id=42,
        )

        pr_response = create_graphql_pr_response(pr_number=42, has_commits=True)
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_single_pr = AsyncMock(
            return_value={
                "repository": {"pullRequest": pr_response},
                "rateLimit": {"remaining": 4900},
            }
        )

        # Act
        result = asyncio.run(fetch_pr_complete_data_graphql(pr, self.tracked_repo))

        # Assert
        self.assertEqual(result["commits_synced"], 1)
        self.assertEqual(Commit.objects.filter(team=self.team, pull_request=pr).count(), 1)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_creates_files_from_graphql_response(self, mock_client_class):
        """Test that files are created from GraphQL response."""
        from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql
        from apps.metrics.factories import PullRequestFactory

        # Arrange
        pr = PullRequestFactory(
            team=self.team,
            github_repo="test-org/test-repo",
            github_pr_id=42,
        )

        pr_response = create_graphql_pr_response(pr_number=42, has_files=True)
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_single_pr = AsyncMock(
            return_value={
                "repository": {"pullRequest": pr_response},
                "rateLimit": {"remaining": 4900},
            }
        )

        # Act
        result = asyncio.run(fetch_pr_complete_data_graphql(pr, self.tracked_repo))

        # Assert - helper creates 2 files when has_files=True
        self.assertEqual(result["files_synced"], 2)
        self.assertEqual(PRFile.objects.filter(team=self.team, pull_request=pr).count(), 2)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_creates_reviews_from_graphql_response(self, mock_client_class):
        """Test that reviews are created from GraphQL response."""
        from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql
        from apps.metrics.factories import PullRequestFactory

        # Arrange
        pr = PullRequestFactory(
            team=self.team,
            github_repo="test-org/test-repo",
            github_pr_id=42,
        )

        pr_response = create_graphql_pr_response(pr_number=42, has_reviews=True)
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_single_pr = AsyncMock(
            return_value={
                "repository": {"pullRequest": pr_response},
                "rateLimit": {"remaining": 4900},
            }
        )

        # Act
        result = asyncio.run(fetch_pr_complete_data_graphql(pr, self.tracked_repo))

        # Assert
        self.assertEqual(result["reviews_synced"], 1)
        self.assertEqual(PRReview.objects.filter(team=self.team, pull_request=pr).count(), 1)


class TestFetchPRCompleteDataGraphQLErrorHandling(TransactionTestCase):
    """Tests for fetch_pr_complete_data_graphql error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            full_name="test-org/test-repo",
            is_active=True,
        )

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_handles_graphql_error(self, mock_client_class):
        """Test that GraphQL errors are caught and returned in errors list."""
        from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql
        from apps.metrics.factories import PullRequestFactory

        # Arrange
        pr = PullRequestFactory(
            team=self.team,
            github_repo="test-org/test-repo",
            github_pr_id=42,
        )

        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_single_pr = AsyncMock(side_effect=GitHubGraphQLError("Query failed"))

        # Act
        result = asyncio.run(fetch_pr_complete_data_graphql(pr, self.tracked_repo))

        # Assert
        self.assertIn("errors", result)
        self.assertTrue(len(result["errors"]) > 0)
        self.assertIn("Query failed", result["errors"][0])

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_handles_rate_limit_error(self, mock_client_class):
        """Test that rate limit errors are caught and returned."""
        from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql
        from apps.metrics.factories import PullRequestFactory

        # Arrange
        pr = PullRequestFactory(
            team=self.team,
            github_repo="test-org/test-repo",
            github_pr_id=42,
        )

        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_single_pr = AsyncMock(side_effect=GitHubGraphQLRateLimitError("Rate limit exceeded"))

        # Act
        result = asyncio.run(fetch_pr_complete_data_graphql(pr, self.tracked_repo))

        # Assert
        self.assertIn("errors", result)
        self.assertTrue(len(result["errors"]) > 0)
        self.assertIn("Rate limit", result["errors"][0])

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_handles_null_pr_response(self, mock_client_class):
        """Test that null PR response is handled gracefully."""
        from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql
        from apps.metrics.factories import PullRequestFactory

        # Arrange
        pr = PullRequestFactory(
            team=self.team,
            github_repo="test-org/test-repo",
            github_pr_id=42,
        )

        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_single_pr = AsyncMock(
            return_value={
                "repository": {"pullRequest": None},
                "rateLimit": {"remaining": 4900},
            }
        )

        # Act
        result = asyncio.run(fetch_pr_complete_data_graphql(pr, self.tracked_repo))

        # Assert
        self.assertIn("errors", result)
        self.assertTrue(len(result["errors"]) > 0)


# =============================================================================
# Phase 5: sync_github_members_graphql Tests
# =============================================================================


class TestSyncGitHubMembersGraphQLBasic(TransactionTestCase):
    """Tests for sync_github_members_graphql basic functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)

    def test_sync_github_members_graphql_function_exists(self):
        """Test that sync_github_members_graphql function exists and is importable."""
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        self.assertTrue(callable(sync_github_members_graphql))

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_github_members_graphql_returns_result_dict(self, mock_client_class):
        """Test that sync_github_members_graphql returns dict with counts."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_org_members = AsyncMock(
            return_value={
                "organization": {
                    "membersWithRole": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        result = asyncio.run(sync_github_members_graphql(self.integration, org_name="test-org"))

        # Assert
        self.assertIsInstance(result, dict)
        self.assertIn("members_synced", result)
        self.assertIn("members_created", result)
        self.assertIn("members_updated", result)
        self.assertIn("errors", result)


class TestSyncGitHubMembersGraphQLDataProcessing(TransactionTestCase):
    """Tests for sync_github_members_graphql data processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_creates_team_member_from_graphql_response(self, mock_client_class):
        """Test that sync creates TeamMember from GraphQL member data."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_org_members = AsyncMock(
            return_value={
                "organization": {
                    "membersWithRole": {
                        "nodes": [
                            {
                                "databaseId": 12345,
                                "login": "newuser",
                                "name": "New User",
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        result = asyncio.run(sync_github_members_graphql(self.integration, org_name="test-org"))

        # Assert
        self.assertEqual(result["members_synced"], 1)
        self.assertEqual(result["members_created"], 1)
        self.assertTrue(TeamMember.objects.filter(team=self.team, github_id="12345").exists())
        member = TeamMember.objects.get(team=self.team, github_id="12345")
        self.assertEqual(member.github_username, "newuser")
        self.assertEqual(member.display_name, "New User")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_updates_existing_team_member(self, mock_client_class):
        """Test that sync updates existing TeamMember with new data."""
        # Arrange - create existing member
        existing_member = TeamMemberFactory(
            team=self.team,
            github_id="12345",
            github_username="oldusername",
            display_name="Old Name",
        )

        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_org_members = AsyncMock(
            return_value={
                "organization": {
                    "membersWithRole": {
                        "nodes": [
                            {
                                "databaseId": 12345,
                                "login": "newusername",
                                "name": "New Name",
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        result = asyncio.run(sync_github_members_graphql(self.integration, org_name="test-org"))

        # Assert
        self.assertEqual(result["members_synced"], 1)
        self.assertEqual(result["members_updated"], 1)
        self.assertEqual(result["members_created"], 0)
        existing_member.refresh_from_db()
        self.assertEqual(existing_member.github_username, "newusername")
        self.assertEqual(existing_member.display_name, "New Name")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_handles_member_without_name(self, mock_client_class):
        """Test that sync handles member with null name field."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_org_members = AsyncMock(
            return_value={
                "organization": {
                    "membersWithRole": {
                        "nodes": [
                            {
                                "databaseId": 99999,
                                "login": "usernoname",
                                "name": None,  # Some users don't set display name
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        result = asyncio.run(sync_github_members_graphql(self.integration, org_name="test-org"))

        # Assert
        self.assertEqual(result["members_created"], 1)
        member = TeamMember.objects.get(team=self.team, github_id="99999")
        self.assertEqual(member.github_username, "usernoname")
        # Should use login as display_name when name is null
        self.assertEqual(member.display_name, "usernoname")


class TestSyncGitHubMembersGraphQLPagination(TransactionTestCase):
    """Tests for sync_github_members_graphql pagination handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_handles_pagination(self, mock_client_class):
        """Test that sync handles paginated responses."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # First page response
        first_page = {
            "organization": {
                "membersWithRole": {
                    "nodes": [{"databaseId": 1, "login": "user1", "name": "User One"}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor1"},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        # Second page response
        second_page = {
            "organization": {
                "membersWithRole": {
                    "nodes": [{"databaseId": 2, "login": "user2", "name": "User Two"}],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 4990},
        }

        mock_client.fetch_org_members = AsyncMock(side_effect=[first_page, second_page])

        # Act
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        result = asyncio.run(sync_github_members_graphql(self.integration, org_name="test-org"))

        # Assert
        self.assertEqual(result["members_synced"], 2)
        self.assertEqual(mock_client.fetch_org_members.call_count, 2)
        self.assertTrue(TeamMember.objects.filter(team=self.team, github_id="1").exists())
        self.assertTrue(TeamMember.objects.filter(team=self.team, github_id="2").exists())


class TestSyncGitHubMembersGraphQLErrorHandling(TransactionTestCase):
    """Tests for sync_github_members_graphql error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_handles_graphql_error(self, mock_client_class):
        """Test that GraphQL errors are caught and returned in errors list."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_org_members = AsyncMock(side_effect=GitHubGraphQLError("Query failed"))

        # Act
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        result = asyncio.run(sync_github_members_graphql(self.integration, org_name="test-org"))

        # Assert
        self.assertIn("errors", result)
        self.assertTrue(len(result["errors"]) > 0)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_handles_rate_limit_error(self, mock_client_class):
        """Test that rate limit errors are caught and returned."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client
        mock_client.fetch_org_members = AsyncMock(side_effect=GitHubGraphQLRateLimitError("Rate limit"))

        # Act
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        result = asyncio.run(sync_github_members_graphql(self.integration, org_name="test-org"))

        # Assert
        self.assertIn("errors", result)
        self.assertTrue(any("rate limit" in e.lower() for e in result["errors"]))


# =============================================================================
# AI Detection in GraphQL Sync Tests
# =============================================================================


class TestGraphQLSyncAIDetectionInitialSync(TransactionTestCase):
    """Tests for AI detection during initial sync (sync_repository_history_graphql)."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.human_author = TeamMemberFactory(team=self.team, github_id="testuser")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_pr_by_bot_author_is_marked_ai_assisted(self, mock_client_class):
        """Test that PR authored by a bot (e.g., Devin) is marked as AI-assisted."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # PR authored by Devin AI bot
        pr_data = create_graphql_pr_response(pr_number=123, state="MERGED")
        pr_data["author"] = {"login": "devin-ai-integration[bot]"}
        pr_data["body"] = "Regular PR description without AI disclosure"

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123)
        self.assertTrue(pr.is_ai_assisted)
        self.assertIn("devin", pr.ai_tools_detected)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_pr_with_ai_disclosure_in_body_is_marked_ai_assisted(self, mock_client_class):
        """Test that PR with AI disclosure in body is marked as AI-assisted."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # PR by human author with AI disclosure in body
        pr_data = create_graphql_pr_response(pr_number=456, state="MERGED")
        pr_data["author"] = {"login": "testuser"}  # Human author
        pr_data["body"] = """## Summary
        Added new feature

        🤖 Generated with [Claude Code](https://claude.com/claude-code)
        """

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=456)
        self.assertTrue(pr.is_ai_assisted)
        self.assertIn("claude_code", pr.ai_tools_detected)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_pr_without_ai_involvement_not_marked_ai_assisted(self, mock_client_class):
        """Test that PR without AI involvement stays is_ai_assisted=False."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # Regular PR by human author
        pr_data = create_graphql_pr_response(pr_number=789, state="MERGED")
        pr_data["author"] = {"login": "testuser"}
        pr_data["body"] = "Fixed a bug in the login flow"

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=789)
        self.assertFalse(pr.is_ai_assisted)
        self.assertEqual(pr.ai_tools_detected, [])

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_pr_by_dependabot_is_marked_ai_assisted(self, mock_client_class):
        """Test that PR by dependabot is marked as AI-assisted."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_graphql_pr_response(pr_number=100, state="MERGED")
        pr_data["author"] = {"login": "dependabot[bot]"}
        pr_data["title"] = "Bump requests from 2.28.0 to 2.31.0"
        pr_data["body"] = "Bumps [requests](https://github.com/psf/requests) from 2.28.0 to 2.31.0."

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=100)
        self.assertTrue(pr.is_ai_assisted)
        self.assertIn("dependabot", pr.ai_tools_detected)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_pr_combines_bot_author_and_text_detection(self, mock_client_class):
        """Test that PR combines bot author and text detection for ai_tools_detected."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # Bot PR with additional AI tool mention in body
        pr_data = create_graphql_pr_response(pr_number=200, state="MERGED")
        pr_data["author"] = {"login": "devin-ai-integration[bot]"}
        pr_data["body"] = "Used GitHub Copilot for some suggestions"

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=200)
        self.assertTrue(pr.is_ai_assisted)
        self.assertIn("devin", pr.ai_tools_detected)
        self.assertIn("copilot", pr.ai_tools_detected)


class TestGraphQLSyncAIDetectionIncrementalSync(TransactionTestCase):
    """Tests for AI detection during incremental sync."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            full_name="owner/repo",
            last_sync_at=timezone.now() - timedelta(hours=24),
        )
        self.human_author = TeamMemberFactory(team=self.team, github_id="testuser")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_incremental_sync_detects_bot_author(self, mock_client_class):
        """Test that incremental sync detects bot authors."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_incremental_pr_response(pr_number=300, state="MERGED")
        pr_data["author"] = {"login": "renovate[bot]"}
        pr_data["body"] = "Dependency update"

        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=300)
        self.assertTrue(pr.is_ai_assisted)
        self.assertIn("renovate", pr.ai_tools_detected)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_incremental_sync_detects_ai_disclosure_in_body(self, mock_client_class):
        """Test that incremental sync detects AI disclosure in PR body."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_data = create_incremental_pr_response(pr_number=400, state="MERGED")
        pr_data["author"] = {"login": "testuser"}
        pr_data["body"] = "AI Disclosure: This PR was created using Cursor AI"

        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=400)
        self.assertTrue(pr.is_ai_assisted)
        self.assertIn("cursor", pr.ai_tools_detected)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_incremental_sync_updates_existing_pr_ai_status(self, mock_client_class):
        """Test that incremental sync can update AI status of existing PR."""
        # Arrange - create existing PR without AI detection
        from apps.metrics.factories import PullRequestFactory

        existing_pr = PullRequestFactory(
            team=self.team,
            github_pr_id=500,
            github_repo="owner/repo",
            is_ai_assisted=False,
            ai_tools_detected=[],
            author=self.human_author,
        )

        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # Update adds AI disclosure
        pr_data = create_incremental_pr_response(pr_number=500, state="MERGED")
        pr_data["author"] = {"login": "testuser"}
        pr_data["body"] = "Updated with Claude Code\n\n🤖 Generated with Claude Code"

        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        existing_pr.refresh_from_db()
        self.assertTrue(existing_pr.is_ai_assisted)
        self.assertIn("claude_code", existing_pr.ai_tools_detected)


# =============================================================================
# Timing Metrics Tests (cycle_time_hours, review_time_hours, first_review_at)
# =============================================================================


class TestGraphQLSyncTimingMetrics(TransactionTestCase):
    """Tests for timing metrics calculation during GraphQL sync."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")
        self.reviewer = TeamMemberFactory(team=self.team, github_id="reviewer1")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_process_pr_calculates_cycle_time_for_merged_pr(self, mock_client_class):
        """Test that _process_pr calculates cycle_time_hours for merged PRs."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # PR created and merged 48 hours later (2 days)
        pr_created = timezone.now() - timedelta(days=3)
        pr_merged = pr_created + timedelta(hours=48)

        pr_data = create_graphql_pr_response(pr_number=123, state="MERGED")
        pr_data["createdAt"] = pr_created.isoformat()
        pr_data["mergedAt"] = pr_merged.isoformat()

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=123)
        self.assertIsNotNone(pr.cycle_time_hours)
        # 48 hours between creation and merge
        self.assertAlmostEqual(float(pr.cycle_time_hours), 48.0, delta=0.1)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_process_pr_does_not_calculate_cycle_time_for_open_pr(self, mock_client_class):
        """Test that _process_pr does not calculate cycle_time_hours for open PRs."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # Open PR (not merged)
        pr_created = timezone.now() - timedelta(days=2)

        pr_data = create_graphql_pr_response(pr_number=456, state="OPEN")
        pr_data["createdAt"] = pr_created.isoformat()
        pr_data["mergedAt"] = None  # Not merged

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=456)
        self.assertIsNone(pr.cycle_time_hours)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_process_reviews_updates_first_review_at(self, mock_client_class):
        """Test that _process_reviews updates PR's first_review_at field."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_created = timezone.now() - timedelta(days=3)
        review_submitted = pr_created + timedelta(hours=6)

        pr_data = create_graphql_pr_response(pr_number=789, state="MERGED", has_reviews=True)
        pr_data["createdAt"] = pr_created.isoformat()
        pr_data["reviews"]["nodes"][0]["submittedAt"] = review_submitted.isoformat()

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=789)
        self.assertIsNotNone(pr.first_review_at)
        # Should match the review submission time
        self.assertEqual(pr.first_review_at.replace(microsecond=0), review_submitted.replace(microsecond=0))

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_process_reviews_calculates_review_time_hours(self, mock_client_class):
        """Test that _process_reviews calculates review_time_hours."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_created = timezone.now() - timedelta(days=3)
        review_submitted = pr_created + timedelta(hours=12)  # 12 hours after PR creation

        pr_data = create_graphql_pr_response(pr_number=101, state="MERGED", has_reviews=True)
        pr_data["createdAt"] = pr_created.isoformat()
        pr_data["reviews"]["nodes"][0]["submittedAt"] = review_submitted.isoformat()

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=101)
        self.assertIsNotNone(pr.review_time_hours)
        # 12 hours between PR creation and first review
        self.assertAlmostEqual(float(pr.review_time_hours), 12.0, delta=0.1)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_process_reviews_uses_earliest_review_timestamp(self, mock_client_class):
        """Test that _process_reviews uses the earliest review when multiple reviews exist."""
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        pr_created = timezone.now() - timedelta(days=3)
        first_review = pr_created + timedelta(hours=4)
        second_review = pr_created + timedelta(hours=10)
        third_review = pr_created + timedelta(hours=15)

        pr_data = create_graphql_pr_response(pr_number=202, state="MERGED")
        pr_data["createdAt"] = pr_created.isoformat()
        pr_data["reviews"] = {
            "nodes": [
                {
                    "databaseId": 2000001,
                    "author": {"login": "reviewer1"},
                    "state": "COMMENTED",
                    "submittedAt": second_review.isoformat(),  # Not the earliest
                    "body": "Looks good",
                },
                {
                    "databaseId": 2000002,
                    "author": {"login": "reviewer2"},
                    "state": "APPROVED",
                    "submittedAt": first_review.isoformat(),  # Earliest
                    "body": "LGTM",
                },
                {
                    "databaseId": 2000003,
                    "author": {"login": "reviewer1"},
                    "state": "APPROVED",
                    "submittedAt": third_review.isoformat(),  # Latest
                    "body": "Approved",
                },
            ]
        }

        # Need reviewer2 for the test
        TeamMemberFactory(team=self.team, github_id="reviewer2")

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {"nodes": [pr_data], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        pr = PullRequest.objects.get(team=self.team, github_pr_id=202)
        self.assertIsNotNone(pr.first_review_at)
        # Should use the earliest review (4 hours after creation)
        self.assertEqual(pr.first_review_at.replace(microsecond=0), first_review.replace(microsecond=0))
        self.assertAlmostEqual(float(pr.review_time_hours), 4.0, delta=0.1)


# =============================================================================
# Sync Progress Tracking Tests (Fix for totalCount bug)
# =============================================================================


class TestSyncProgressTracking(TransactionTestCase):
    """Tests for accurate progress tracking using date-filtered PR count.

    The bug: totalCount from GitHub GraphQL pullRequests connection returns ALL PRs
    in the repository, not just PRs in the sync date range. This causes:
    - Progress showing 2% when sync is actually complete
    - Wrong time estimates during onboarding

    Solution: Use get_pr_count_in_date_range() to get accurate count of PRs
    within the date filter before starting sync.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_progress_uses_date_filtered_count(self, mock_client_class):
        """Test that sync progress uses get_pr_count_in_date_range instead of totalCount.

        This is the core test for the sync progress fix.

        Scenario:
        - Repository has 2410 total PRs (all time)
        - Sync is filtering to last 30 days = 14 PRs
        - totalCount returns 2410 (BUG: wrong for progress)
        - get_pr_count_in_date_range returns 14 (CORRECT for progress)

        Expected: sync_prs_total should be 14, not 2410
        """
        # Arrange
        mock_client = create_mock_graphql_client()
        mock_client_class.return_value = mock_client

        # get_pr_count_in_date_range returns accurate count for date range
        mock_client.get_pr_count_in_date_range = AsyncMock(return_value=14)

        # fetch_prs_bulk returns totalCount of ALL PRs (the bug)
        # But with the fix, we should use get_pr_count_in_date_range instead
        recent_prs = [create_graphql_pr_response(pr_number=i) for i in range(1, 15)]
        for i, pr in enumerate(recent_prs):
            # PRs within last 30 days
            pr["createdAt"] = (timezone.now() - timedelta(days=i + 1)).isoformat()

        mock_client.fetch_prs_bulk = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {
                        "nodes": recent_prs,
                        # BUG: totalCount returns ALL repo PRs, not date-filtered
                        "totalCount": 2410,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 5000},
            }
        )

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=30))

        # Assert
        # Verify get_pr_count_in_date_range was called
        mock_client.get_pr_count_in_date_range.assert_called_once()

        # Verify the call included correct parameters
        call_args = mock_client.get_pr_count_in_date_range.call_args
        self.assertEqual(call_args[1]["owner"], "owner")
        self.assertEqual(call_args[1]["repo"], "repo")
        self.assertIsNotNone(call_args[1].get("since"))  # Should have since date

        # Verify tracked_repo has correct total (date-filtered, not all-time)
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_prs_total, 14)  # NOT 2410

        # Progress should complete successfully
        self.assertEqual(self.tracked_repo.sync_progress, 100)


# ============================================================================
# Search API Sync Tests (sync_repository_history_by_search)
# ============================================================================


def create_search_pr_response(pr_number=123, state="MERGED"):
    """Helper to create PR data as returned by Search API."""
    base_time = timezone.now() - timedelta(days=5)
    return {
        "number": pr_number,
        "title": f"Search PR #{pr_number}",
        "body": "PR description",
        "state": state,
        "createdAt": base_time.isoformat(),
        "mergedAt": (base_time + timedelta(hours=24)).isoformat() if state == "MERGED" else None,
        "additions": 100,
        "deletions": 50,
        "isDraft": False,
        "author": {"login": "testuser"},
        "labels": {"nodes": []},
        "milestone": None,
        "assignees": {"nodes": []},
        "closingIssuesReferences": {"nodes": []},
        "reviews": {"nodes": []},
        "commits": {"nodes": []},
        "files": {"nodes": []},
    }


class TestSyncRepositoryHistoryBySearch(TransactionTestCase):
    """Tests for sync_repository_history_by_search function.

    This function uses the Search API to fetch PRs with date filtering,
    enabling accurate progress tracking and efficient phase 2 syncing.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.tracked_repo = TrackedRepositoryFactory(team=self.team, full_name="owner/repo")
        self.author = TeamMemberFactory(team=self.team, github_id="testuser")

    def test_sync_by_search_function_exists(self):
        """Test that sync_repository_history_by_search function exists and is importable."""
        from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

        self.assertTrue(callable(sync_repository_history_by_search))

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_by_search_sets_prs_total_from_issue_count(self, mock_client_class):
        """Test that sync sets prs_total from Search API issueCount."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Search API returns issueCount which is accurate for date range
        mock_client.search_prs_by_date_range = AsyncMock(
            return_value={
                "issue_count": 15,
                "prs": [],
                "has_next_page": False,
                "end_cursor": None,
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

        asyncio.run(sync_repository_history_by_search(self.tracked_repo, days_back=30))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_prs_total, 15)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_by_search_creates_pull_requests(self, mock_client_class):
        """Test that sync creates PullRequest records from Search API response."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        pr_data = create_search_pr_response(pr_number=123, state="MERGED")
        mock_client.search_prs_by_date_range = AsyncMock(
            return_value={
                "issue_count": 1,
                "prs": [pr_data],
                "has_next_page": False,
                "end_cursor": None,
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

        result = asyncio.run(sync_repository_history_by_search(self.tracked_repo, days_back=30))

        # Assert
        self.assertEqual(result["prs_synced"], 1)
        pr = PullRequest.objects.filter(team=self.team, github_pr_id=123).first()
        self.assertIsNotNone(pr)
        self.assertEqual(pr.title, "Search PR #123")
        self.assertEqual(pr.state, "merged")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_by_search_increments_prs_processed(self, mock_client_class):
        """Test that sync increments prs_processed for each PR."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        prs = [create_search_pr_response(pr_number=i) for i in range(1, 6)]  # 5 PRs
        mock_client.search_prs_by_date_range = AsyncMock(
            return_value={
                "issue_count": 5,
                "prs": prs,
                "has_next_page": False,
                "end_cursor": None,
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

        asyncio.run(sync_repository_history_by_search(self.tracked_repo, days_back=30))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_prs_completed, 5)

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_by_search_phase1_uses_since_only(self, mock_client_class):
        """Test that Phase 1 sync (days_back=30) only uses since date."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.search_prs_by_date_range = AsyncMock(
            return_value={
                "issue_count": 0,
                "prs": [],
                "has_next_page": False,
                "end_cursor": None,
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

        asyncio.run(sync_repository_history_by_search(self.tracked_repo, days_back=30))

        # Assert
        mock_client.search_prs_by_date_range.assert_called_once()
        call_kwargs = mock_client.search_prs_by_date_range.call_args[1]
        self.assertEqual(call_kwargs["owner"], "owner")
        self.assertEqual(call_kwargs["repo"], "repo")
        self.assertIsNotNone(call_kwargs.get("since"))
        self.assertIsNone(call_kwargs.get("until"))  # No until for Phase 1

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_by_search_phase2_uses_date_range(self, mock_client_class):
        """Test that Phase 2 sync (skip_recent=30) uses both since and until dates."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.search_prs_by_date_range = AsyncMock(
            return_value={
                "issue_count": 0,
                "prs": [],
                "has_next_page": False,
                "end_cursor": None,
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

        asyncio.run(sync_repository_history_by_search(self.tracked_repo, days_back=90, skip_recent=30))

        # Assert
        mock_client.search_prs_by_date_range.assert_called_once()
        call_kwargs = mock_client.search_prs_by_date_range.call_args[1]
        self.assertEqual(call_kwargs["owner"], "owner")
        self.assertEqual(call_kwargs["repo"], "repo")
        self.assertIsNotNone(call_kwargs.get("since"))
        self.assertIsNotNone(call_kwargs.get("until"))  # Has until for Phase 2

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_by_search_paginates_through_all_pages(self, mock_client_class):
        """Test that sync paginates through all pages of results."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        page1_prs = [create_search_pr_response(pr_number=i) for i in range(1, 6)]
        page2_prs = [create_search_pr_response(pr_number=i) for i in range(6, 11)]

        mock_client.search_prs_by_date_range = AsyncMock(
            side_effect=[
                {
                    "issue_count": 10,
                    "prs": page1_prs,
                    "has_next_page": True,
                    "end_cursor": "cursor_page2",
                },
                {
                    "issue_count": 10,
                    "prs": page2_prs,
                    "has_next_page": False,
                    "end_cursor": None,
                },
            ]
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

        result = asyncio.run(sync_repository_history_by_search(self.tracked_repo, days_back=30))

        # Assert
        self.assertEqual(mock_client.search_prs_by_date_range.call_count, 2)
        self.assertEqual(result["prs_synced"], 10)

        # Verify cursor was passed for second call
        second_call_kwargs = mock_client.search_prs_by_date_range.call_args_list[1][1]
        self.assertEqual(second_call_kwargs.get("cursor"), "cursor_page2")

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_sync_by_search_returns_result_dict(self, mock_client_class):
        """Test that sync returns dict with all sync counts."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.search_prs_by_date_range = AsyncMock(
            return_value={
                "issue_count": 0,
                "prs": [],
                "has_next_page": False,
                "end_cursor": None,
            }
        )

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

        result = asyncio.run(sync_repository_history_by_search(self.tracked_repo, days_back=30))

        # Assert
        self.assertIn("prs_synced", result)
        self.assertIn("reviews_synced", result)
        self.assertIn("commits_synced", result)
        self.assertIn("files_synced", result)
        self.assertIn("errors", result)
