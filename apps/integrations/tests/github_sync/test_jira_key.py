"""Tests for GitHub sync service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    sync_repository_history,
    sync_repository_incremental,
)


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
        # EncryptedTextField auto-decrypts access_token
        with patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests") as mock_get_prs:
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
        # EncryptedTextField auto-decrypts access_token
        with patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests") as mock_get_prs:
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
        # EncryptedTextField auto-decrypts access_token
        with patch("apps.integrations.services.github_sync.sync.get_updated_pull_requests") as mock_get_updated_prs:
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
