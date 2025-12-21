"""Tests for GitHub sync service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    GitHubOAuthError,
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
