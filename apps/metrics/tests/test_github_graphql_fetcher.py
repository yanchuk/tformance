"""
Tests for GitHubGraphQLFetcher optimizations.

Tests verify the following optimizations:
1. _get_cached_repo() - Caches repo objects to avoid repeated API calls
2. _fetch_check_runs_for_commit() - Uses commit SHA directly (1 API call)
3. _add_check_runs_to_prs() - Parallel fetching using commit SHA from PR
4. _map_pr() - Maps GraphQL PR nodes to FetchedPRFull with Phase 2 fields

These tests verify the CURRENT behavior of the implementation.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.metrics.seeding.github_authenticated_fetcher import FetchedCheckRun, FetchedCommit, FetchedPRFull
from apps.metrics.seeding.github_graphql_fetcher import GitHubGraphQLFetcher


class TestGitHubGraphQLFetcherRepoCaching(TestCase):
    """Tests for _get_cached_repo() optimization."""

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_first_repo_access_fetches_from_api(self, mock_client_class, mock_github_class):
        """Test that first access to a repo fetches it from API and increments counter."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        initial_api_calls = fetcher.api_calls_made

        # Act
        result = fetcher._get_cached_repo("owner/repo")

        # Assert
        self.assertEqual(result, mock_repo)
        mock_github.get_repo.assert_called_once_with("owner/repo")
        self.assertEqual(fetcher.api_calls_made, initial_api_calls + 1, "Should increment api_calls_made by 1")

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_second_repo_access_uses_cache_without_api_call(self, mock_client_class, mock_github_class):
        """Test that second access to same repo returns cached object WITHOUT incrementing counter."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # First call - should fetch
        fetcher._get_cached_repo("owner/repo")
        api_calls_after_first = fetcher.api_calls_made

        # Act - Second call to same repo
        result = fetcher._get_cached_repo("owner/repo")

        # Assert
        self.assertEqual(result, mock_repo, "Should return same cached repo object")
        self.assertEqual(mock_github.get_repo.call_count, 1, "Should NOT call get_repo again for cached repo")
        self.assertEqual(
            fetcher.api_calls_made,
            api_calls_after_first,
            "Should NOT increment api_calls_made when using cache",
        )

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_different_repos_are_cached_separately(self, mock_client_class, mock_github_class):
        """Test that different repos are cached separately."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo1 = Mock(name="repo1")
        mock_repo2 = Mock(name="repo2")
        mock_github.get_repo.side_effect = [mock_repo1, mock_repo2]

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        result1 = fetcher._get_cached_repo("owner/repo1")
        result2 = fetcher._get_cached_repo("owner/repo2")
        result1_again = fetcher._get_cached_repo("owner/repo1")

        # Assert
        self.assertEqual(result1, mock_repo1)
        self.assertEqual(result2, mock_repo2)
        self.assertEqual(result1_again, mock_repo1)
        self.assertEqual(mock_github.get_repo.call_count, 2, "Should fetch each unique repo once")


class TestGitHubGraphQLFetcherCheckRunsForCommit(TestCase):
    """Tests for _fetch_check_runs_for_commit() optimization."""

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_fetches_check_runs_using_commit_sha_directly(self, mock_client_class, mock_github_class):
        """Test that check runs are fetched using repo.get_commit(sha) directly."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_commit = Mock()
        mock_check_run = Mock()
        mock_check_run.id = 123456
        mock_check_run.name = "CI Build"
        mock_check_run.status = "completed"
        mock_check_run.conclusion = "success"
        mock_check_run.started_at = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        mock_check_run.completed_at = datetime(2025, 1, 1, 10, 5, 0, tzinfo=UTC)

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.return_value = mock_commit
        mock_commit.get_check_runs.return_value = [mock_check_run]

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        result = fetcher._fetch_check_runs_for_commit("owner/repo", "abc123def456")

        # Assert
        mock_repo.get_commit.assert_called_once_with("abc123def456")
        mock_commit.get_check_runs.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], FetchedCheckRun)
        self.assertEqual(result[0].github_id, 123456)
        self.assertEqual(result[0].name, "CI Build")
        self.assertEqual(result[0].status, "completed")
        self.assertEqual(result[0].conclusion, "success")

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_increments_api_calls_by_one(self, mock_client_class, mock_github_class):
        """Test that fetching check runs increments api_calls_made by 1 (not 3)."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.get_check_runs.return_value = []

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.return_value = mock_commit

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        # Prime the cache to isolate the test
        fetcher._get_cached_repo("owner/repo")
        api_calls_before = fetcher.api_calls_made

        # Act
        fetcher._fetch_check_runs_for_commit("owner/repo", "abc123")

        # Assert
        self.assertEqual(
            fetcher.api_calls_made,
            api_calls_before + 1,
            "Should increment api_calls_made by exactly 1 (get_commit call)",
        )

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_returns_empty_list_on_error(self, mock_client_class, mock_github_class):
        """Test that errors are handled gracefully by returning empty list."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.side_effect = Exception("API error")

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        result = fetcher._fetch_check_runs_for_commit("owner/repo", "invalid_sha")

        # Assert
        self.assertEqual(result, [])

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_handles_check_runs_without_timestamps(self, mock_client_class, mock_github_class):
        """Test that check runs without started_at/completed_at are handled correctly."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_commit = Mock()
        mock_check_run = Mock()
        mock_check_run.id = 789
        mock_check_run.name = "Pending Check"
        mock_check_run.status = "queued"
        mock_check_run.conclusion = None
        mock_check_run.started_at = None
        mock_check_run.completed_at = None

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.return_value = mock_commit
        mock_commit.get_check_runs.return_value = [mock_check_run]

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        result = fetcher._fetch_check_runs_for_commit("owner/repo", "abc123")

        # Assert
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].started_at)
        self.assertIsNone(result[0].completed_at)
        self.assertIsNone(result[0].conclusion)

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_uses_cached_repo_for_multiple_commits(self, mock_client_class, mock_github_class):
        """Test that repo cache is used when fetching check runs for multiple commits."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.get_check_runs.return_value = []

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.return_value = mock_commit

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act - Fetch check runs for 3 different commits in same repo
        fetcher._fetch_check_runs_for_commit("owner/repo", "commit1")
        fetcher._fetch_check_runs_for_commit("owner/repo", "commit2")
        fetcher._fetch_check_runs_for_commit("owner/repo", "commit3")

        # Assert
        # Should only call get_repo once (cached), but get_commit 3 times
        self.assertEqual(mock_github.get_repo.call_count, 1, "Should use cached repo")
        self.assertEqual(mock_repo.get_commit.call_count, 3, "Should fetch each commit")


class TestGitHubGraphQLFetcherAddCheckRunsToPRs(TestCase):
    """Tests for _add_check_runs_to_prs() optimization."""

    def _mock_rate_limit(self, mock_github, remaining=5000):
        """Helper to set up rate limit mock."""
        mock_rate_limit = Mock()
        mock_rate_limit.rate.remaining = remaining
        mock_rate_limit.rate.reset.timestamp.return_value = 1704110400
        mock_github.get_rate_limit.return_value = mock_rate_limit

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_uses_commit_sha_from_pr_object(self, mock_client_class, mock_github_class):
        """Test that check runs are fetched using commit SHA from PR.commits[-1].sha."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        self._mock_rate_limit(mock_github)
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.get_check_runs.return_value = []

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.return_value = mock_commit

        # Create PR with commits
        pr = FetchedPRFull(
            github_pr_id=1,
            number=1,
            github_repo="owner/repo",
            title="Test PR",
            body=None,
            state="open",
            is_merged=False,
            is_draft=False,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            merged_at=None,
            closed_at=None,
            additions=10,
            deletions=5,
            changed_files=1,
            commits_count=2,
            author_login="testuser",
            author_id=0,
            author_name=None,
            author_avatar_url=None,
            head_ref="feature",
            base_ref="main",
            labels=[],
            jira_key_from_title=None,
            jira_key_from_branch=None,
            reviews=[],
            commits=[
                FetchedCommit(
                    sha="commit1_sha",
                    message="First commit",
                    author_login="testuser",
                    author_name="Test User",
                    committed_at=datetime(2025, 1, 1, tzinfo=UTC),
                    additions=5,
                    deletions=2,
                ),
                FetchedCommit(
                    sha="head_commit_sha",  # This should be used
                    message="Latest commit",
                    author_login="testuser",
                    author_name="Test User",
                    committed_at=datetime(2025, 1, 2, tzinfo=UTC),
                    additions=5,
                    deletions=3,
                ),
            ],
            files=[],
            check_runs=[],
        )

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        fetcher._add_check_runs_to_prs([pr], "owner/repo")

        # Assert
        # Should use the last commit SHA directly
        mock_repo.get_commit.assert_called_with("head_commit_sha")

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_skips_prs_without_commits(self, mock_client_class, mock_github_class):
        """Test that PRs without commits are skipped."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        # Create PR without commits
        pr_no_commits = FetchedPRFull(
            github_pr_id=1,
            number=1,
            github_repo="owner/repo",
            title="Test PR",
            body=None,
            state="open",
            is_merged=False,
            is_draft=False,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            merged_at=None,
            closed_at=None,
            additions=0,
            deletions=0,
            changed_files=0,
            commits_count=0,
            author_login="testuser",
            author_id=0,
            author_name=None,
            author_avatar_url=None,
            head_ref="feature",
            base_ref="main",
            labels=[],
            jira_key_from_title=None,
            jira_key_from_branch=None,
            reviews=[],
            commits=[],  # No commits
            files=[],
            check_runs=[],
        )

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        fetcher._add_check_runs_to_prs([pr_no_commits], "owner/repo")

        # Assert
        # Should not call get_commit at all
        mock_repo.get_commit.assert_not_called()
        self.assertEqual(len(pr_no_commits.check_runs), 0)

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_adds_check_runs_to_pr_in_place(self, mock_client_class, mock_github_class):
        """Test that check runs are added to PR.check_runs list in place."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        self._mock_rate_limit(mock_github)
        mock_repo = Mock()
        mock_commit = Mock()
        mock_check_run = Mock()
        mock_check_run.id = 123
        mock_check_run.name = "Test Check"
        mock_check_run.status = "completed"
        mock_check_run.conclusion = "success"
        mock_check_run.started_at = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        mock_check_run.completed_at = datetime(2025, 1, 1, 10, 5, 0, tzinfo=UTC)

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.return_value = mock_commit
        mock_commit.get_check_runs.return_value = [mock_check_run]

        pr = FetchedPRFull(
            github_pr_id=1,
            number=1,
            github_repo="owner/repo",
            title="Test PR",
            body=None,
            state="open",
            is_merged=False,
            is_draft=False,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            merged_at=None,
            closed_at=None,
            additions=10,
            deletions=5,
            changed_files=1,
            commits_count=1,
            author_login="testuser",
            author_id=0,
            author_name=None,
            author_avatar_url=None,
            head_ref="feature",
            base_ref="main",
            labels=[],
            jira_key_from_title=None,
            jira_key_from_branch=None,
            reviews=[],
            commits=[
                FetchedCommit(
                    sha="commit_sha",
                    message="Commit",
                    author_login="testuser",
                    author_name="Test User",
                    committed_at=datetime(2025, 1, 1, tzinfo=UTC),
                    additions=10,
                    deletions=5,
                )
            ],
            files=[],
            check_runs=[],
        )

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        fetcher._add_check_runs_to_prs([pr], "owner/repo")

        # Assert
        self.assertEqual(len(pr.check_runs), 1)
        self.assertEqual(pr.check_runs[0].github_id, 123)
        self.assertEqual(pr.check_runs[0].name, "Test Check")

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_fetches_check_runs_for_multiple_prs_sequentially(self, mock_client_class, mock_github_class):
        """Test that check runs for multiple PRs are fetched sequentially per GitHub best practices."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        self._mock_rate_limit(mock_github)
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.get_check_runs.return_value = []

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.return_value = mock_commit

        # Create 3 PRs with different commits
        prs = [
            FetchedPRFull(
                github_pr_id=i,
                number=i,
                github_repo="owner/repo",
                title=f"PR #{i}",
                body=None,
                state="open",
                is_merged=False,
                is_draft=False,
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, tzinfo=UTC),
                merged_at=None,
                closed_at=None,
                additions=10,
                deletions=5,
                changed_files=1,
                commits_count=1,
                author_login="testuser",
                author_id=0,
                author_name=None,
                author_avatar_url=None,
                head_ref="feature",
                base_ref="main",
                labels=[],
                jira_key_from_title=None,
                jira_key_from_branch=None,
                reviews=[],
                commits=[
                    FetchedCommit(
                        sha=f"commit_{i}_sha",
                        message=f"Commit {i}",
                        author_login="testuser",
                        author_name="Test User",
                        committed_at=datetime(2025, 1, 1, tzinfo=UTC),
                        additions=10,
                        deletions=5,
                    )
                ],
                files=[],
                check_runs=[],
            )
            for i in range(1, 4)
        ]

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        fetcher._add_check_runs_to_prs(prs, "owner/repo")

        # Assert
        # Should fetch commit for each PR
        self.assertEqual(mock_repo.get_commit.call_count, 3)
        # Verify each commit SHA was requested
        called_shas = [call[0][0] for call in mock_repo.get_commit.call_args_list]
        self.assertIn("commit_1_sha", called_shas)
        self.assertIn("commit_2_sha", called_shas)
        self.assertIn("commit_3_sha", called_shas)

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_pre_caches_repo_before_sequential_execution(self, mock_client_class, mock_github_class):
        """Test that repo is pre-cached before fetching check runs."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        self._mock_rate_limit(mock_github)
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.get_check_runs.return_value = []

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.return_value = mock_commit

        pr = FetchedPRFull(
            github_pr_id=1,
            number=1,
            github_repo="owner/repo",
            title="Test PR",
            body=None,
            state="open",
            is_merged=False,
            is_draft=False,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            merged_at=None,
            closed_at=None,
            additions=10,
            deletions=5,
            changed_files=1,
            commits_count=1,
            author_login="testuser",
            author_id=0,
            author_name=None,
            author_avatar_url=None,
            head_ref="feature",
            base_ref="main",
            labels=[],
            jira_key_from_title=None,
            jira_key_from_branch=None,
            reviews=[],
            commits=[
                FetchedCommit(
                    sha="commit_sha",
                    message="Commit",
                    author_login="testuser",
                    author_name="Test User",
                    committed_at=datetime(2025, 1, 1, tzinfo=UTC),
                    additions=10,
                    deletions=5,
                )
            ],
            files=[],
            check_runs=[],
        )

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        fetcher._add_check_runs_to_prs([pr], "owner/repo")

        # Assert
        # Should call get_repo exactly once (pre-cached)
        self.assertEqual(mock_github.get_repo.call_count, 1)
        mock_github.get_repo.assert_called_with("owner/repo")

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_handles_errors_gracefully_for_individual_prs(self, mock_client_class, mock_github_class):
        """Test that errors fetching check runs for one PR don't affect others."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        self._mock_rate_limit(mock_github)
        mock_repo = Mock()

        # First commit succeeds, second fails, third succeeds
        mock_commit_success = Mock()
        mock_commit_success.get_check_runs.return_value = []

        def get_commit_side_effect(sha):
            if sha == "commit_2_sha":
                raise Exception("API error")
            return mock_commit_success

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.side_effect = get_commit_side_effect

        prs = [
            FetchedPRFull(
                github_pr_id=i,
                number=i,
                github_repo="owner/repo",
                title=f"PR #{i}",
                body=None,
                state="open",
                is_merged=False,
                is_draft=False,
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, tzinfo=UTC),
                merged_at=None,
                closed_at=None,
                additions=10,
                deletions=5,
                changed_files=1,
                commits_count=1,
                author_login="testuser",
                author_id=0,
                author_name=None,
                author_avatar_url=None,
                head_ref="feature",
                base_ref="main",
                labels=[],
                jira_key_from_title=None,
                jira_key_from_branch=None,
                reviews=[],
                commits=[
                    FetchedCommit(
                        sha=f"commit_{i}_sha",
                        message=f"Commit {i}",
                        author_login="testuser",
                        author_name="Test User",
                        committed_at=datetime(2025, 1, 1, tzinfo=UTC),
                        additions=10,
                        deletions=5,
                    )
                ],
                files=[],
                check_runs=[],
            )
            for i in range(1, 4)
        ]

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        fetcher._add_check_runs_to_prs(prs, "owner/repo")

        # Assert
        # All PRs should have been processed (error doesn't stop others)
        self.assertEqual(mock_repo.get_commit.call_count, 3)
        # PR 2 should have empty check_runs due to error
        self.assertEqual(len(prs[1].check_runs), 0)

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_executes_requests_in_order_per_github_best_practices(self, mock_client_class, mock_github_class):
        """Test that check run requests are made sequentially in order (not parallel).

        GitHub API best practices state: "Make requests serially instead of concurrently"
        to avoid secondary rate limits.
        See: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
        """
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        self._mock_rate_limit(mock_github)
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.get_check_runs.return_value = []

        # Track order of get_commit calls
        call_order = []

        def track_commit_order(sha):
            call_order.append(sha)
            return mock_commit

        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_commit.side_effect = track_commit_order

        prs = [
            FetchedPRFull(
                github_pr_id=i,
                number=i,
                github_repo="owner/repo",
                title=f"PR #{i}",
                body=None,
                state="open",
                is_merged=False,
                is_draft=False,
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, tzinfo=UTC),
                merged_at=None,
                closed_at=None,
                additions=10,
                deletions=5,
                changed_files=1,
                commits_count=1,
                author_login="testuser",
                author_id=0,
                author_name=None,
                author_avatar_url=None,
                head_ref="feature",
                base_ref="main",
                labels=[],
                jira_key_from_title=None,
                jira_key_from_branch=None,
                reviews=[],
                commits=[
                    FetchedCommit(
                        sha=f"commit_{i}_sha",
                        message=f"Commit {i}",
                        author_login="testuser",
                        author_name="Test User",
                        committed_at=datetime(2025, 1, 1, tzinfo=UTC),
                        additions=10,
                        deletions=5,
                    )
                ],
                files=[],
                check_runs=[],
            )
            for i in range(1, 6)  # 5 PRs
        ]

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act
        fetcher._add_check_runs_to_prs(prs, "owner/repo")

        # Assert - calls should be in sequential order (PR 1, 2, 3, 4, 5)
        expected_order = ["commit_1_sha", "commit_2_sha", "commit_3_sha", "commit_4_sha", "commit_5_sha"]
        self.assertEqual(call_order, expected_order, "Requests should be made sequentially in order")


class TestGitHubGraphQLFetcherMapPR(TestCase):
    """Tests for _map_pr() Phase 2 fields (labels, milestone, assignees, linked_issues)."""

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_maps_labels_from_graphql_nodes(self, mock_client_class, mock_github_class):
        """Test that labels are extracted from GraphQL labels.nodes."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "MERGED",
            "createdAt": "2025-01-01T10:00:00Z",
            "labels": {
                "nodes": [
                    {"name": "bug", "color": "d73a4a"},
                    {"name": "priority:high", "color": "ff0000"},
                    {"name": "area:backend", "color": "0e8a16"},
                ]
            },
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertEqual(result.labels, ["bug", "priority:high", "area:backend"])

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_handles_empty_labels(self, mock_client_class, mock_github_class):
        """Test that empty labels list is returned when no labels."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "OPEN",
            "createdAt": "2025-01-01T10:00:00Z",
            "labels": {"nodes": []},
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertEqual(result.labels, [])

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_handles_null_labels(self, mock_client_class, mock_github_class):
        """Test that empty labels list is returned when labels is null."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "OPEN",
            "createdAt": "2025-01-01T10:00:00Z",
            "labels": None,
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertEqual(result.labels, [])

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_maps_milestone_title(self, mock_client_class, mock_github_class):
        """Test that milestone title is extracted from GraphQL milestone."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "MERGED",
            "createdAt": "2025-01-01T10:00:00Z",
            "milestone": {
                "title": "v2.0 Release",
                "number": 5,
                "dueOn": "2025-03-01T00:00:00Z",
            },
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertEqual(result.milestone_title, "v2.0 Release")

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_handles_null_milestone(self, mock_client_class, mock_github_class):
        """Test that milestone_title is None when no milestone assigned."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "OPEN",
            "createdAt": "2025-01-01T10:00:00Z",
            "milestone": None,
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertIsNone(result.milestone_title)

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_maps_assignees_from_graphql_nodes(self, mock_client_class, mock_github_class):
        """Test that assignees are extracted from GraphQL assignees.nodes."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "OPEN",
            "createdAt": "2025-01-01T10:00:00Z",
            "assignees": {
                "nodes": [
                    {"login": "developer1"},
                    {"login": "developer2"},
                ]
            },
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertEqual(result.assignees, ["developer1", "developer2"])

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_handles_empty_assignees(self, mock_client_class, mock_github_class):
        """Test that empty assignees list is returned when no assignees."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "OPEN",
            "createdAt": "2025-01-01T10:00:00Z",
            "assignees": {"nodes": []},
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertEqual(result.assignees, [])

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_maps_linked_issues_from_closing_references(self, mock_client_class, mock_github_class):
        """Test that linked issues are extracted from closingIssuesReferences."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "MERGED",
            "createdAt": "2025-01-01T10:00:00Z",
            "closingIssuesReferences": {
                "nodes": [
                    {"number": 42, "title": "Bug in login"},
                    {"number": 123, "title": "Feature request"},
                ]
            },
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertEqual(result.linked_issues, [42, 123])

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_handles_empty_linked_issues(self, mock_client_class, mock_github_class):
        """Test that empty linked_issues list is returned when none linked."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 1,
            "title": "Test PR",
            "state": "OPEN",
            "createdAt": "2025-01-01T10:00:00Z",
            "closingIssuesReferences": {"nodes": []},
            "author": {"login": "testuser"},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertEqual(result.linked_issues, [])

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_maps_is_draft_field(self, mock_client_class, mock_github_class):
        """Test that isDraft is mapped to is_draft."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node_draft = {
            "number": 1,
            "title": "WIP: Feature",
            "state": "OPEN",
            "createdAt": "2025-01-01T10:00:00Z",
            "isDraft": True,
            "author": {"login": "testuser"},
        }
        node_ready = {
            "number": 2,
            "title": "Ready Feature",
            "state": "OPEN",
            "createdAt": "2025-01-01T10:00:00Z",
            "isDraft": False,
            "author": {"login": "testuser"},
        }

        # Act
        result_draft = fetcher._map_pr(node_draft, "owner/repo")
        result_ready = fetcher._map_pr(node_ready, "owner/repo")

        # Assert
        self.assertTrue(result_draft.is_draft)
        self.assertFalse(result_ready.is_draft)

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_all_phase2_fields_in_complete_pr(self, mock_client_class, mock_github_class):
        """Test that all Phase 2 fields are correctly mapped in a complete PR."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        node = {
            "number": 100,
            "title": "Fix critical bug",
            "body": "Fixes #42",
            "state": "MERGED",
            "createdAt": "2025-01-01T10:00:00Z",
            "updatedAt": "2025-01-02T15:00:00Z",
            "mergedAt": "2025-01-02T14:00:00Z",
            "additions": 50,
            "deletions": 20,
            "isDraft": False,
            "author": {"login": "developer"},
            "labels": {
                "nodes": [
                    {"name": "bug", "color": "d73a4a"},
                    {"name": "urgent", "color": "ff0000"},
                ]
            },
            "milestone": {
                "title": "Sprint 5",
                "number": 5,
                "dueOn": None,
            },
            "assignees": {
                "nodes": [
                    {"login": "developer"},
                    {"login": "reviewer"},
                ]
            },
            "closingIssuesReferences": {
                "nodes": [
                    {"number": 42, "title": "Critical bug"},
                ]
            },
            "reviews": {"nodes": []},
            "commits": {"nodes": []},
            "files": {"nodes": []},
        }

        # Act
        result = fetcher._map_pr(node, "owner/repo")

        # Assert
        self.assertFalse(result.is_draft)
        self.assertEqual(result.labels, ["bug", "urgent"])
        self.assertEqual(result.milestone_title, "Sprint 5")
        self.assertEqual(result.assignees, ["developer", "reviewer"])
        self.assertEqual(result.linked_issues, [42])


class TestGitHubGraphQLFetcherRateLimitMonitoring(TestCase):
    """Tests for rate limit monitoring (Phase 3.2).

    Verifies that the fetcher tracks and logs rate limit status.
    """

    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_fetcher_initializes_with_graphql_client(self, mock_client_class):
        """Test that fetcher initializes with a GraphQL client for rate limit tracking."""
        # Arrange
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Assert GraphQL client is initialized (which handles rate limit checking)
        self.assertIsNotNone(fetcher._client)
        mock_client_class.assert_called_once_with("ghp_test_token")

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_logs_rest_api_rate_limit_warning_when_low(self, mock_client_class, mock_github_class):
        """Test that fetcher logs warning when REST API rate limit is low."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github

        # Mock rate limit response
        mock_rate_limit = Mock()
        mock_rate_limit.rate.remaining = 50  # Low remaining
        mock_rate_limit.rate.reset.timestamp.return_value = 1704110400
        mock_github.get_rate_limit.return_value = mock_rate_limit

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Act - access REST client which should check rate limit
        with patch("apps.metrics.seeding.github_graphql_fetcher.logger") as mock_logger:
            # Force REST client initialization
            fetcher._get_rest_client()
            fetcher._check_rest_rate_limit()

            # Assert warning was logged
            mock_logger.warning.assert_called()

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_check_rest_rate_limit_returns_remaining_points(self, mock_client_class, mock_github_class):
        """Test that _check_rest_rate_limit returns the remaining points."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github

        mock_rate_limit = Mock()
        mock_rate_limit.rate.remaining = 4500
        mock_rate_limit.rate.reset.timestamp.return_value = 1704110400
        mock_github.get_rate_limit.return_value = mock_rate_limit

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        fetcher._get_rest_client()

        # Act
        remaining = fetcher._check_rest_rate_limit()

        # Assert
        self.assertEqual(remaining, 4500)

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_check_rest_rate_limit_increments_api_counter(self, mock_client_class, mock_github_class):
        """Test that _check_rest_rate_limit increments the API call counter."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github

        mock_rate_limit = Mock()
        mock_rate_limit.rate.remaining = 4500
        mock_rate_limit.rate.reset.timestamp.return_value = 1704110400
        mock_github.get_rate_limit.return_value = mock_rate_limit

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        fetcher._get_rest_client()
        initial_calls = fetcher.api_calls_made

        # Act
        fetcher._check_rest_rate_limit()

        # Assert
        self.assertEqual(fetcher.api_calls_made, initial_calls + 1)

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_add_check_runs_skips_when_rate_limit_too_low(self, mock_client_class, mock_github_class):
        """Test that _add_check_runs_to_prs skips when rate limit is too low."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github

        # Mock low rate limit (fewer points than PRs)
        mock_rate_limit = Mock()
        mock_rate_limit.rate.remaining = 2  # Only 2 remaining, but we need 3 (2 PRs + 1 repo cache)
        mock_rate_limit.rate.reset.timestamp.return_value = 1704110400
        mock_github.get_rate_limit.return_value = mock_rate_limit

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        # Create mock PRs with commits
        pr1 = Mock(spec=FetchedPRFull)
        pr1.number = 1
        pr1.commits = [
            FetchedCommit(
                sha="abc123",
                message="test",
                author_login="user",
                author_name=None,
                committed_at=datetime.now(UTC),
                additions=0,
                deletions=0,
            )
        ]
        pr1.check_runs = []

        pr2 = Mock(spec=FetchedPRFull)
        pr2.number = 2
        pr2.commits = [
            FetchedCommit(
                sha="def456",
                message="test",
                author_login="user",
                author_name=None,
                committed_at=datetime.now(UTC),
                additions=0,
                deletions=0,
            )
        ]
        pr2.check_runs = []

        # Act
        fetcher._add_check_runs_to_prs([pr1, pr2], "owner/repo")

        # Assert - check runs should NOT be fetched (skipped due to low rate limit)
        mock_github.get_repo.assert_not_called()  # Repo cache not accessed
        self.assertEqual(len(pr1.check_runs), 0)
        self.assertEqual(len(pr2.check_runs), 0)


class TestGitHubGraphQLFetcherIncrementalSync(TestCase):
    """Tests for incremental PR sync (Phase 3.3).

    When cache exists but repo has changed, fetch only updated PRs
    and merge with cached PRs instead of re-fetching everything.
    """

    def _create_pr(self, number: int, updated_at: datetime) -> FetchedPRFull:
        """Helper to create a PR for testing."""
        return FetchedPRFull(
            github_pr_id=number,
            number=number,
            github_repo="owner/repo",
            title=f"PR #{number}",
            body=None,
            state="merged",
            is_merged=True,
            is_draft=False,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=updated_at,
            merged_at=datetime(2025, 1, 2, tzinfo=UTC),
            closed_at=None,
            additions=10,
            deletions=5,
            changed_files=1,
            commits_count=1,
            author_login="testuser",
            author_id=0,
            author_name=None,
            author_avatar_url=None,
            head_ref="feature",
            base_ref="main",
            labels=[],
            jira_key_from_title=None,
            jira_key_from_branch=None,
            reviews=[],
            commits=[],
            files=[],
            check_runs=[],
        )

    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_merge_prs_replaces_updated_prs(self, mock_client_class):
        """Test that _merge_prs replaces PRs with same number from updates."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        old_pr1 = self._create_pr(1, datetime(2025, 1, 1, tzinfo=UTC))
        old_pr1.title = "Old PR #1"
        old_pr2 = self._create_pr(2, datetime(2025, 1, 1, tzinfo=UTC))
        old_pr2.title = "Old PR #2"
        cached_prs = [old_pr1, old_pr2]

        updated_pr1 = self._create_pr(1, datetime(2025, 1, 10, tzinfo=UTC))
        updated_pr1.title = "Updated PR #1"
        updated_prs = [updated_pr1]

        # Act
        merged = fetcher._merge_prs(cached_prs, updated_prs)

        # Assert
        self.assertEqual(len(merged), 2)
        # PR #1 should be updated
        pr1 = next(pr for pr in merged if pr.number == 1)
        self.assertEqual(pr1.title, "Updated PR #1")
        # PR #2 should be unchanged
        pr2 = next(pr for pr in merged if pr.number == 2)
        self.assertEqual(pr2.title, "Old PR #2")

    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_merge_prs_adds_new_prs(self, mock_client_class):
        """Test that _merge_prs adds new PRs that weren't in cache."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        old_pr1 = self._create_pr(1, datetime(2025, 1, 1, tzinfo=UTC))
        cached_prs = [old_pr1]

        new_pr2 = self._create_pr(2, datetime(2025, 1, 10, tzinfo=UTC))
        new_pr2.title = "New PR #2"
        updated_prs = [new_pr2]

        # Act
        merged = fetcher._merge_prs(cached_prs, updated_prs)

        # Assert
        self.assertEqual(len(merged), 2)
        self.assertTrue(any(pr.number == 1 for pr in merged))
        self.assertTrue(any(pr.number == 2 for pr in merged))

    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_merge_prs_sorts_by_updated_at_desc(self, mock_client_class):
        """Test that merged PRs are sorted by updated_at descending."""
        # Arrange
        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")

        pr1 = self._create_pr(1, datetime(2025, 1, 5, tzinfo=UTC))
        pr2 = self._create_pr(2, datetime(2025, 1, 10, tzinfo=UTC))
        pr3 = self._create_pr(3, datetime(2025, 1, 1, tzinfo=UTC))
        cached_prs = [pr1, pr2, pr3]

        # Act
        merged = fetcher._merge_prs(cached_prs, [])

        # Assert - should be sorted by updated_at DESC
        self.assertEqual(merged[0].number, 2)  # Jan 10
        self.assertEqual(merged[1].number, 1)  # Jan 5
        self.assertEqual(merged[2].number, 3)  # Jan 1

    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_fetch_updated_prs_async_uses_client_method(self, mock_client_class):
        """Test that _fetch_updated_prs_async uses fetch_prs_updated_since."""
        import asyncio
        from unittest.mock import AsyncMock

        # Arrange
        mock_client = mock_client_class.return_value
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {
                        "nodes": [
                            {
                                "number": 1,
                                "title": "Updated PR",
                                "body": None,
                                "state": "MERGED",
                                "createdAt": "2025-01-01T00:00:00Z",
                                "updatedAt": "2025-01-10T00:00:00Z",
                                "mergedAt": "2025-01-02T00:00:00Z",
                                "additions": 10,
                                "deletions": 5,
                                "isDraft": False,
                                "author": {"login": "testuser"},
                                "headRefName": "feature",
                                "baseRefName": "main",
                                "labels": {"nodes": []},
                                "milestone": None,
                                "assignees": {"nodes": []},
                                "closingIssuesReferences": {"nodes": []},
                                "reviews": {"nodes": []},
                                "commits": {"nodes": []},
                                "files": {"nodes": []},
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 4500},
            }
        )

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        since = datetime(2025, 1, 5, tzinfo=UTC)

        # Act
        prs = asyncio.run(fetcher._fetch_updated_prs_async("owner/repo", since))

        # Assert
        mock_client.fetch_prs_updated_since.assert_called_once_with("owner", "repo", since, None)
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0].number, 1)
        self.assertEqual(prs[0].title, "Updated PR")

    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_fetch_updated_prs_async_stops_at_old_prs(self, mock_client_class):
        """Test that _fetch_updated_prs_async stops when PRs are older than since."""
        import asyncio
        from unittest.mock import AsyncMock

        # Arrange
        mock_client = mock_client_class.return_value

        # Return PRs where second one is older than `since`
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {
                        "nodes": [
                            {
                                "number": 1,
                                "title": "New PR",
                                "body": None,
                                "state": "OPEN",
                                "createdAt": "2025-01-01T00:00:00Z",
                                "updatedAt": "2025-01-10T00:00:00Z",  # After since
                                "mergedAt": None,
                                "additions": 10,
                                "deletions": 5,
                                "isDraft": False,
                                "author": {"login": "testuser"},
                                "headRefName": "feature",
                                "baseRefName": "main",
                                "labels": {"nodes": []},
                                "milestone": None,
                                "assignees": {"nodes": []},
                                "closingIssuesReferences": {"nodes": []},
                                "reviews": {"nodes": []},
                                "commits": {"nodes": []},
                                "files": {"nodes": []},
                            },
                            {
                                "number": 2,
                                "title": "Old PR",
                                "body": None,
                                "state": "MERGED",
                                "createdAt": "2024-12-01T00:00:00Z",
                                "updatedAt": "2025-01-01T00:00:00Z",  # Before since (Jan 5)
                                "mergedAt": "2024-12-15T00:00:00Z",
                                "additions": 5,
                                "deletions": 2,
                                "isDraft": False,
                                "author": {"login": "testuser"},
                                "headRefName": "old-feature",
                                "baseRefName": "main",
                                "labels": {"nodes": []},
                                "milestone": None,
                                "assignees": {"nodes": []},
                                "closingIssuesReferences": {"nodes": []},
                                "reviews": {"nodes": []},
                                "commits": {"nodes": []},
                                "files": {"nodes": []},
                            },
                        ],
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor123"},
                    }
                },
                "rateLimit": {"remaining": 4500},
            }
        )

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token")
        since = datetime(2025, 1, 5, tzinfo=UTC)

        # Act
        prs = asyncio.run(fetcher._fetch_updated_prs_async("owner/repo", since))

        # Assert - should only return PRs updated after `since`
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0].number, 1)
        # Should not call for next page since we found an old PR
        self.assertEqual(mock_client.fetch_prs_updated_since.call_count, 1)

    @patch("apps.metrics.seeding.github_graphql_fetcher.PRCache")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_fetch_prs_with_details_uses_incremental_sync_when_cache_stale(self, mock_client_class, mock_cache_class):
        """Test that fetch_prs_with_details uses incremental sync when cache is stale."""
        from unittest.mock import AsyncMock

        # Arrange
        mock_client = mock_client_class.return_value

        # Setup stale cache (exists but repo has changed)
        cache_fetched_at = datetime(2025, 1, 5, 12, 0, 0, tzinfo=UTC)

        # Create a proper serialized cached PR
        cached_pr_serialized = {
            "github_pr_id": 1,
            "number": 1,
            "github_repo": "owner/repo",
            "title": "Cached PR #1",
            "body": None,
            "state": "merged",
            "is_merged": True,
            "is_draft": False,
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-03T00:00:00+00:00",
            "merged_at": "2025-01-02T00:00:00+00:00",
            "closed_at": None,
            "additions": 10,
            "deletions": 5,
            "changed_files": 1,
            "commits_count": 1,
            "author_login": "testuser",
            "author_id": 0,
            "author_name": None,
            "author_avatar_url": None,
            "head_ref": "feature",
            "base_ref": "main",
            "labels": [],
            "jira_key_from_title": None,
            "jira_key_from_branch": None,
            "reviews": [],
            "commits": [],
            "files": [],
            "check_runs": [],
            "milestone_title": None,
            "assignees": [],
            "linked_issues": [],
        }

        mock_cache = Mock()
        mock_cache.fetched_at = cache_fetched_at
        mock_cache.prs = [cached_pr_serialized]
        mock_cache.is_valid.return_value = False  # Cache is stale
        mock_cache_class.load.return_value = mock_cache

        # Mock repo metadata (repo was pushed to after cache was created)
        mock_client.fetch_repo_metadata = AsyncMock(return_value={"repository": {"pushedAt": "2025-01-10T00:00:00Z"}})

        # Mock incremental fetch - returns one updated PR
        updated_pr_node = {
            "number": 1,
            "title": "Updated PR #1",
            "body": None,
            "state": "MERGED",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-08T00:00:00Z",  # After cache.fetched_at
            "mergedAt": "2025-01-07T00:00:00Z",
            "additions": 15,
            "deletions": 8,
            "isDraft": False,
            "author": {"login": "testuser"},
            "headRefName": "feature",
            "baseRefName": "main",
            "labels": {"nodes": []},
            "milestone": None,
            "assignees": {"nodes": []},
            "closingIssuesReferences": {"nodes": []},
            "reviews": {"nodes": []},
            "commits": {"nodes": []},
            "files": {"nodes": []},
        }
        mock_client.fetch_prs_updated_since = AsyncMock(
            return_value={
                "repository": {
                    "pullRequests": {
                        "nodes": [updated_pr_node],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {"remaining": 4500},
            }
        )

        fetcher = GitHubGraphQLFetcher(token="ghp_test_token", use_cache=True)

        # Act
        since = datetime(2025, 1, 1, tzinfo=UTC)
        prs = fetcher.fetch_prs_with_details("owner/repo", since, max_prs=100)

        # Assert - should use incremental sync
        mock_client.fetch_prs_updated_since.assert_called_once()
        # Should save merged result to cache
        mock_cache_class.assert_called()  # New cache created
        # Result should have the updated PR
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0].title, "Updated PR #1")
