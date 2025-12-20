"""Tests for the GitHub PR fetcher."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.seeding.github_fetcher import FetchedPR, GitHubPublicFetcher


class TestFetchedPR(TestCase):
    """Tests for the FetchedPR dataclass."""

    def test_fetched_pr_creation(self):
        """FetchedPR should store all PR metadata."""
        pr = FetchedPR(
            title="Add new feature",
            additions=100,
            deletions=20,
            files_changed=5,
            commits_count=3,
            labels=["enhancement", "needs-review"],
            is_draft=False,
            review_comments_count=2,
        )

        self.assertEqual(pr.title, "Add new feature")
        self.assertEqual(pr.additions, 100)
        self.assertEqual(pr.deletions, 20)
        self.assertEqual(pr.files_changed, 5)
        self.assertEqual(pr.commits_count, 3)
        self.assertEqual(pr.labels, ["enhancement", "needs-review"])
        self.assertFalse(pr.is_draft)
        self.assertEqual(pr.review_comments_count, 2)


class TestGitHubPublicFetcher(TestCase):
    """Tests for the GitHubPublicFetcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = GitHubPublicFetcher()

    def _create_mock_pr(
        self,
        title="Test PR",
        additions=50,
        deletions=10,
        changed_files=3,
        commits=2,
        labels=None,
        draft=False,
        review_comments=1,
    ):
        """Create a mock PR object."""
        mock_pr = MagicMock()
        mock_pr.title = title
        mock_pr.additions = additions
        mock_pr.deletions = deletions
        mock_pr.changed_files = changed_files
        mock_pr.commits = commits
        mock_pr.draft = draft
        mock_pr.review_comments = review_comments

        # Mock labels
        if labels is None:
            labels = []
        mock_labels = []
        for label_name in labels:
            mock_label = MagicMock()
            mock_label.name = label_name
            mock_labels.append(mock_label)
        mock_pr.labels = mock_labels

        return mock_pr

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_fetch_prs_success(self, mock_github_class):
        """fetch_prs should return list of FetchedPR objects."""
        # Set up mocks
        mock_pr1 = self._create_mock_pr(title="PR 1", additions=100, labels=["bug"])
        mock_pr2 = self._create_mock_pr(title="PR 2", additions=50, labels=["feature"])

        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr1, mock_pr2]

        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_client

        # Create fresh fetcher with mocked client
        fetcher = GitHubPublicFetcher()

        # Execute
        result = fetcher.fetch_prs("test/repo", limit=10)

        # Verify
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, "PR 1")
        self.assertEqual(result[0].additions, 100)
        self.assertEqual(result[0].labels, ["bug"])
        self.assertEqual(result[1].title, "PR 2")

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_fetch_prs_caches_results(self, mock_github_class):
        """fetch_prs should cache results and not call API twice."""
        mock_pr = self._create_mock_pr(title="Cached PR")

        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr]

        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()

        # First call
        result1 = fetcher.fetch_prs("test/repo")
        # Second call (should use cache)
        result2 = fetcher.fetch_prs("test/repo")

        # Verify API was only called once
        self.assertEqual(mock_client.get_repo.call_count, 1)
        self.assertEqual(result1, result2)

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_fetch_prs_different_states_not_cached_together(self, mock_github_class):
        """fetch_prs with different states should have separate cache entries."""
        mock_pr_closed = self._create_mock_pr(title="Closed PR")
        mock_pr_open = self._create_mock_pr(title="Open PR")

        mock_repo = MagicMock()
        mock_repo.get_pulls.side_effect = [
            [mock_pr_closed],
            [mock_pr_open],
        ]

        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()

        # Fetch with different states
        closed = fetcher.fetch_prs("test/repo", state="closed")
        opened = fetcher.fetch_prs("test/repo", state="open")

        # Verify different results
        self.assertEqual(closed[0].title, "Closed PR")
        self.assertEqual(opened[0].title, "Open PR")
        self.assertEqual(mock_repo.get_pulls.call_count, 2)

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_fetch_prs_rate_limit_returns_empty(self, mock_github_class):
        """fetch_prs should return empty list when rate limited."""
        from github import RateLimitExceededException

        mock_client = MagicMock()
        mock_client.get_repo.side_effect = RateLimitExceededException(403, {"message": "Rate limit exceeded"}, {})
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()
        result = fetcher.fetch_prs("test/repo")

        self.assertEqual(result, [])

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_fetch_prs_repo_not_found_returns_empty(self, mock_github_class):
        """fetch_prs should return empty list when repo not found."""
        from github import GithubException

        mock_client = MagicMock()
        mock_client.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, {})
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()
        result = fetcher.fetch_prs("nonexistent/repo")

        self.assertEqual(result, [])

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_fetch_prs_respects_limit(self, mock_github_class):
        """fetch_prs should respect the limit parameter."""
        mock_prs = [self._create_mock_pr(title=f"PR {i}") for i in range(10)]

        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = mock_prs

        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()
        result = fetcher.fetch_prs("test/repo", limit=5)

        self.assertEqual(len(result), 5)

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_fetch_from_defaults(self, mock_github_class):
        """fetch_from_defaults should fetch from all default repos."""
        mock_pr = self._create_mock_pr(title="Default PR")

        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr]

        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()
        result = fetcher.fetch_from_defaults(per_repo_limit=5)

        # Should have fetched from 3 default repos
        self.assertEqual(mock_client.get_repo.call_count, 3)
        self.assertEqual(len(result), 3)  # 1 PR from each repo

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_clear_cache(self, mock_github_class):
        """clear_cache should empty the cache."""
        mock_pr = self._create_mock_pr()

        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr]

        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()

        # Populate cache
        fetcher.fetch_prs("test/repo")
        self.assertEqual(mock_client.get_repo.call_count, 1)

        # Clear and fetch again
        fetcher.clear_cache()
        fetcher.fetch_prs("test/repo")
        self.assertEqual(mock_client.get_repo.call_count, 2)

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_get_rate_limit_remaining(self, mock_github_class):
        """get_rate_limit_remaining should return remaining requests."""
        mock_rate_limit = MagicMock()
        mock_rate_limit.core.remaining = 45

        mock_client = MagicMock()
        mock_client.get_rate_limit.return_value = mock_rate_limit
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()
        remaining = fetcher.get_rate_limit_remaining()

        self.assertEqual(remaining, 45)

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_get_rate_limit_returns_zero_on_error(self, mock_github_class):
        """get_rate_limit_remaining should return 0 on API error."""
        from github import GithubException

        mock_client = MagicMock()
        mock_client.get_rate_limit.side_effect = GithubException(500, {"message": "Server Error"}, {})
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()
        remaining = fetcher.get_rate_limit_remaining()

        self.assertEqual(remaining, 0)

    def test_default_repos_defined(self):
        """DEFAULT_REPOS should be a non-empty list."""
        self.assertIsInstance(GitHubPublicFetcher.DEFAULT_REPOS, list)
        self.assertGreater(len(GitHubPublicFetcher.DEFAULT_REPOS), 0)

    @patch("apps.metrics.seeding.github_fetcher.Github")
    def test_handles_individual_pr_fetch_error(self, mock_github_class):
        """Should skip PRs that fail to fetch and continue with others."""
        from github import GithubException

        mock_pr1 = self._create_mock_pr(title="Good PR")
        mock_pr2 = MagicMock()
        # Accessing any attribute raises an error
        type(mock_pr2).title = property(lambda self: (_ for _ in ()).throw(GithubException(500, {}, {})))
        mock_pr3 = self._create_mock_pr(title="Another Good PR")

        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr1, mock_pr2, mock_pr3]

        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_client

        fetcher = GitHubPublicFetcher()
        result = fetcher.fetch_prs("test/repo")

        # Should have 2 PRs (skipped the error one)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, "Good PR")
        self.assertEqual(result[1].title, "Another Good PR")
