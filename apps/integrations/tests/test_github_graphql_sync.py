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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.fetch_prs_bulk = AsyncMock(side_effect=Exception("Unexpected error"))

        # Act
        asyncio.run(sync_repository_history_graphql(self.tracked_repo, days_back=90))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_status, "error")


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

        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_updated_since = AsyncMock(side_effect=GitHubGraphQLError("Query failed"))

        # Act
        from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

        asyncio.run(sync_repository_incremental_graphql(self.tracked_repo))

        # Assert
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_status, "error")


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

        mock_client = MagicMock()
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

        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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

        mock_client = MagicMock()
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

        mock_client = MagicMock()
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

        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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

        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
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
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_org_members = AsyncMock(side_effect=GitHubGraphQLRateLimitError("Rate limit"))

        # Act
        from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

        result = asyncio.run(sync_github_members_graphql(self.integration, org_name="test-org"))

        # Assert
        self.assertIn("errors", result)
        self.assertTrue(any("rate limit" in e.lower() for e in result["errors"]))
