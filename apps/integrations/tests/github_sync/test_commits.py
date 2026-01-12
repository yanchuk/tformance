"""Tests for GitHub sync service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    sync_pr_commits,
)


class TestSyncPRCommits(TestCase):
    """Tests for syncing commits from a GitHub pull request."""

    def _create_mock_commit(
        self,
        sha: str,
        message: str,
        author_id: int,
        author_login: str,
        committed_at: str = "2025-01-01T10:00:00Z",
        additions: int = 10,
        deletions: int = 5,
    ) -> MagicMock:
        """Create a mock PyGithub Commit object with all required attributes."""
        mock_commit = MagicMock()
        mock_commit.sha = sha

        # Mock commit details
        mock_commit.commit.message = message
        mock_commit.commit.author.date = datetime.fromisoformat(committed_at.replace("Z", "+00:00"))

        # Mock author (can be None for commits by non-GitHub users)
        if author_id:
            mock_author = MagicMock()
            mock_author.id = author_id
            mock_author.login = author_login
            mock_commit.author = mock_author
        else:
            mock_commit.author = None

        # Mock stats
        mock_stats = MagicMock()
        mock_stats.additions = additions
        mock_stats.deletions = deletions
        mock_commit.stats = mock_stats

        return mock_commit

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_commits_creates_commit_records(self, mock_github_class):
        """Test that sync_pr_commits creates Commit records from GitHub PR commits."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import Commit

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345", display_name="John Dev")
        pr = PullRequestFactory(team=team, github_pr_id=101, github_repo="acme/repo", author=member)

        # Mock commits
        mock_commit1 = self._create_mock_commit(
            sha="abc123def456789012345678901234567890abcd",
            message="Add feature X",
            author_id=12345,
            author_login="john",
            committed_at="2025-01-01T10:00:00Z",
            additions=50,
            deletions=10,
        )
        mock_commit2 = self._create_mock_commit(
            sha="def456abc123789012345678901234567890abcd",
            message="Fix typo",
            author_id=12345,
            author_login="john",
            committed_at="2025-01-01T11:00:00Z",
            additions=5,
            deletions=2,
        )

        # Mock PyGithub PR object
        mock_pr = MagicMock()
        mock_pr.get_commits.return_value = [mock_commit1, mock_commit2]

        # Mock GitHub client chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Call sync function
        access_token = "gho_test_token"
        errors = []
        sync_pr_commits(
            pr=pr,
            pr_number=101,
            access_token=access_token,
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify commits were created
        commits = Commit.objects.filter(team=team, pull_request=pr).order_by("committed_at")
        self.assertEqual(commits.count(), 2)

        # Check first commit
        commit1 = commits[0]
        self.assertEqual(commit1.github_sha, "abc123def456789012345678901234567890abcd")
        self.assertEqual(commit1.github_repo, "acme/repo")
        self.assertEqual(commit1.message, "Add feature X")
        self.assertEqual(commit1.author, member)
        self.assertEqual(commit1.additions, 50)
        self.assertEqual(commit1.deletions, 10)
        self.assertEqual(commit1.pull_request, pr)

        # Check second commit
        commit2 = commits[1]
        self.assertEqual(commit2.github_sha, "def456abc123789012345678901234567890abcd")
        self.assertEqual(commit2.message, "Fix typo")

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_commits_links_to_pull_request(self, mock_github_class):
        """Test that sync_pr_commits correctly links commits to the pull request."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import Commit

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=102, github_repo="acme/repo", author=member)

        # Mock commit
        mock_commit = self._create_mock_commit(
            sha="abc123def456789012345678901234567890abcd",
            message="Update README",
            author_id=12345,
            author_login="dev",
            committed_at="2025-01-01T10:00:00Z",
            additions=20,
            deletions=5,
        )

        # Mock PyGithub PR object
        mock_pr = MagicMock()
        mock_pr.get_commits.return_value = [mock_commit]

        # Mock GitHub client chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Call sync function
        errors = []
        sync_pr_commits(
            pr=pr,
            pr_number=102,
            access_token="gho_test_token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify commit is linked to PR
        commit = Commit.objects.get(team=team, github_sha="abc123def456789012345678901234567890abcd")
        self.assertEqual(commit.pull_request, pr)
        self.assertEqual(commit.pull_request.github_pr_id, 102)

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_commits_maps_author_by_github_id(self, mock_github_class):
        """Test that sync_pr_commits maps commit author to TeamMember via github_id."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import Commit

        # Set up test data with specific github_id
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="99999", display_name="Jane Developer")
        pr = PullRequestFactory(team=team, github_pr_id=103, github_repo="acme/repo", author=member)

        # Mock commit with matching github_id
        mock_commit = self._create_mock_commit(
            sha="abc123def456789012345678901234567890abcd",
            message="Implement feature Y",
            author_id=99999,  # Matches member.github_id
            author_login="jane",
            committed_at="2025-01-01T10:00:00Z",
            additions=100,
            deletions=20,
        )

        # Mock PyGithub PR object
        mock_pr = MagicMock()
        mock_pr.get_commits.return_value = [mock_commit]

        # Mock GitHub client chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Call sync function
        errors = []
        sync_pr_commits(
            pr=pr,
            pr_number=103,
            access_token="gho_test_token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify commit author was mapped via github_id
        commit = Commit.objects.get(team=team, github_sha="abc123def456789012345678901234567890abcd")
        self.assertEqual(commit.author, member)
        self.assertEqual(commit.author.github_id, "99999")
        self.assertEqual(commit.author.display_name, "Jane Developer")

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_commits_handles_unknown_author(self, mock_github_class):
        """Test that sync_pr_commits sets author=None if GitHub user not found in team."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import Commit

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=104, github_repo="acme/repo", author=member)

        # Mock commit with unknown author (github_id not in team)
        mock_commit = self._create_mock_commit(
            sha="abc123def456789012345678901234567890abcd",
            message="External contribution",
            author_id=88888,  # Does NOT match any team member
            author_login="external-contributor",
            committed_at="2025-01-01T10:00:00Z",
            additions=15,
            deletions=3,
        )

        # Mock PyGithub PR object
        mock_pr = MagicMock()
        mock_pr.get_commits.return_value = [mock_commit]

        # Mock GitHub client chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Call sync function
        errors = []
        sync_pr_commits(
            pr=pr,
            pr_number=104,
            access_token="gho_test_token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify commit was created with author=None
        commit = Commit.objects.get(team=team, github_sha="abc123def456789012345678901234567890abcd")
        self.assertIsNone(commit.author)
        self.assertEqual(commit.message, "External contribution")

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_commits_handles_null_author(self, mock_github_class):
        """Test that sync_pr_commits handles commits with no author (e.g., deleted accounts)."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import Commit

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=105, github_repo="acme/repo", author=member)

        # Mock commit with no author (author field is None)
        mock_commit = self._create_mock_commit(
            sha="abc123def456789012345678901234567890abcd",
            message="Commit from deleted account",
            author_id=None,  # No GitHub user
            author_login=None,
            committed_at="2025-01-01T10:00:00Z",
            additions=5,
            deletions=1,
        )

        # Mock PyGithub PR object
        mock_pr = MagicMock()
        mock_pr.get_commits.return_value = [mock_commit]

        # Mock GitHub client chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Call sync function
        errors = []
        sync_pr_commits(
            pr=pr,
            pr_number=105,
            access_token="gho_test_token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify commit was created with author=None
        commit = Commit.objects.get(team=team, github_sha="abc123def456789012345678901234567890abcd")
        self.assertIsNone(commit.author)

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_commits_updates_existing_commits(self, mock_github_class):
        """Test that sync_pr_commits is idempotent - updates existing commits."""
        from apps.metrics.factories import CommitFactory, PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import Commit

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=106, github_repo="acme/repo", author=member)

        # Create existing commit with same SHA
        CommitFactory(
            team=team,
            github_sha="abc123def456789012345678901234567890abcd",
            github_repo="acme/repo",
            message="Old message",
            author=member,
            additions=10,
            deletions=5,
            pull_request=pr,
        )

        # Mock commit with updated data
        mock_commit = self._create_mock_commit(
            sha="abc123def456789012345678901234567890abcd",  # Same SHA
            message="Updated message",  # Different message
            author_id=12345,
            author_login="dev",
            committed_at="2025-01-01T10:00:00Z",
            additions=25,  # Different stats
            deletions=8,
        )

        # Mock PyGithub PR object
        mock_pr = MagicMock()
        mock_pr.get_commits.return_value = [mock_commit]

        # Mock GitHub client chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        # Call sync function
        errors = []
        sync_pr_commits(
            pr=pr,
            pr_number=106,
            access_token="gho_test_token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify only one commit exists (updated, not duplicated)
        self.assertEqual(
            Commit.objects.filter(team=team, github_sha="abc123def456789012345678901234567890abcd").count(), 1
        )

        # Verify commit was updated
        commit = Commit.objects.get(team=team, github_sha="abc123def456789012345678901234567890abcd")
        self.assertEqual(commit.message, "Updated message")
        self.assertEqual(commit.additions, 25)
        self.assertEqual(commit.deletions, 8)
