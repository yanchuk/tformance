"""
Tests for GitHubGraphQLFetcher optimizations.

Tests verify the following optimizations:
1. _get_cached_repo() - Caches repo objects to avoid repeated API calls
2. _fetch_check_runs_for_commit() - Uses commit SHA directly (1 API call)
3. _add_check_runs_to_prs() - Parallel fetching using commit SHA from PR

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

    @patch("github.Github")
    @patch("apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLClient")
    def test_uses_commit_sha_from_pr_object(self, mock_client_class, mock_github_class):
        """Test that check runs are fetched using commit SHA from PR.commits[-1].sha."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
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
    def test_handles_multiple_prs_in_parallel(self, mock_client_class, mock_github_class):
        """Test that check runs for multiple PRs are fetched (uses parallel execution)."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
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
    def test_pre_caches_repo_before_parallel_execution(self, mock_client_class, mock_github_class):
        """Test that repo is pre-cached before parallel fetching."""
        # Arrange
        mock_github = Mock()
        mock_github_class.return_value = mock_github
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
