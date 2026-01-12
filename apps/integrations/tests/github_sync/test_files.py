"""Tests for GitHub sync service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    sync_pr_files,
)


class TestSyncPRFiles(TestCase):
    """Tests for syncing files changed in a pull request."""

    def _create_mock_file(
        self,
        filename: str,
        status: str,
        additions: int,
        deletions: int,
        changes: int,
    ) -> MagicMock:
        """Create a mock PyGithub File object with all required attributes."""
        mock_file = MagicMock()
        mock_file.filename = filename
        mock_file.status = status
        mock_file.additions = additions
        mock_file.deletions = deletions
        mock_file.changes = changes
        return mock_file

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_files_creates_records(self, mock_github_class):
        """Test that sync_pr_files creates PRFile records for each file changed in a PR."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRFile

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345", display_name="John Dev")
        pr = PullRequestFactory(
            team=team,
            github_pr_id=101,
            github_repo="acme/repo",
            author=member,
        )

        # Mock files from GitHub API
        mock_file1 = self._create_mock_file(
            filename="src/api/views.py",
            status="modified",
            additions=25,
            deletions=10,
            changes=35,
        )
        mock_file2 = self._create_mock_file(
            filename="tests/test_views.py",
            status="added",
            additions=50,
            deletions=0,
            changes=50,
        )
        mock_file3 = self._create_mock_file(
            filename="README.md",
            status="modified",
            additions=5,
            deletions=2,
            changes=7,
        )

        # Mock PyGithub PR object and API chain
        mock_github_pr = MagicMock()
        mock_github_pr.get_files.return_value = [mock_file1, mock_file2, mock_file3]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_github_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        files_synced = sync_pr_files(
            pr=pr,
            pr_number=101,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify files were created
        files = PRFile.objects.filter(team=team, pull_request=pr).order_by("filename")
        self.assertEqual(files.count(), 3)
        self.assertEqual(files_synced, 3)
        self.assertEqual(errors, [])

        # Check first file (README.md)
        file1 = files[0]
        self.assertEqual(file1.filename, "README.md")
        self.assertEqual(file1.status, "modified")
        self.assertEqual(file1.additions, 5)
        self.assertEqual(file1.deletions, 2)
        self.assertEqual(file1.changes, 7)
        self.assertEqual(file1.pull_request, pr)

        # Check second file (src/api/views.py)
        file2 = files[1]
        self.assertEqual(file2.filename, "src/api/views.py")
        self.assertEqual(file2.status, "modified")
        self.assertEqual(file2.additions, 25)
        self.assertEqual(file2.deletions, 10)

        # Check third file (tests/test_views.py)
        file3 = files[2]
        self.assertEqual(file3.filename, "tests/test_views.py")
        self.assertEqual(file3.status, "added")
        self.assertEqual(file3.additions, 50)
        self.assertEqual(file3.deletions, 0)

        # Verify API calls were made
        mock_github_class.assert_called_once_with("fake-token")
        mock_github_instance.get_repo.assert_called_once_with("acme/repo")
        mock_repo.get_pull.assert_called_once_with(101)
        mock_github_pr.get_files.assert_called_once()

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_files_categorizes_files(self, mock_github_class):
        """Test that sync_pr_files uses categorize_file() to set file_category."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRFile

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=102, github_repo="acme/repo", author=member)

        # Mock files with different categories
        mock_files = [
            self._create_mock_file("src/views.py", "modified", 10, 5, 15),  # backend
            self._create_mock_file("src/components/Header.tsx", "added", 20, 0, 20),  # frontend
            self._create_mock_file("tests/test_api.py", "modified", 15, 3, 18),  # test
            self._create_mock_file("README.md", "modified", 5, 1, 6),  # docs
            self._create_mock_file("config.yaml", "added", 10, 0, 10),  # config
            self._create_mock_file("data.csv", "added", 5, 0, 5),  # other
        ]

        # Mock PyGithub PR object and API chain
        mock_github_pr = MagicMock()
        mock_github_pr.get_files.return_value = mock_files

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_github_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        sync_pr_files(
            pr=pr,
            pr_number=102,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify files were categorized correctly using PRFile.categorize_file()
        files = PRFile.objects.filter(team=team, pull_request=pr)
        self.assertEqual(files.count(), 6)

        # Check categories match what categorize_file() returns
        backend_file = files.get(filename="src/views.py")
        self.assertEqual(backend_file.file_category, "backend")

        frontend_file = files.get(filename="src/components/Header.tsx")
        self.assertEqual(frontend_file.file_category, "frontend")

        test_file = files.get(filename="tests/test_api.py")
        self.assertEqual(test_file.file_category, "test")

        docs_file = files.get(filename="README.md")
        self.assertEqual(docs_file.file_category, "docs")

        config_file = files.get(filename="config.yaml")
        self.assertEqual(config_file.file_category, "config")

        other_file = files.get(filename="data.csv")
        self.assertEqual(other_file.file_category, "other")

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_files_updates_existing(self, mock_github_class):
        """Test that sync_pr_files updates existing PRFile records on re-sync."""
        from apps.integrations.factories import PRFileFactory
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRFile

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=103, github_repo="acme/repo", author=member)

        # Create existing file record (from previous sync)
        PRFileFactory(
            team=team,
            pull_request=pr,
            filename="src/utils.py",
            status="added",
            additions=20,
            deletions=0,
            changes=20,
            file_category="backend",
        )

        # Mock updated file (author added more code)
        mock_file = self._create_mock_file(
            filename="src/utils.py",  # Same filename
            status="modified",  # Status changed from 'added' to 'modified'
            additions=35,  # More additions
            deletions=5,  # Now has deletions
            changes=40,  # More changes
        )

        # Mock PyGithub PR object and API chain
        mock_github_pr = MagicMock()
        mock_github_pr.get_files.return_value = [mock_file]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_github_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        files_synced = sync_pr_files(
            pr=pr,
            pr_number=103,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify only one file exists (not duplicated)
        self.assertEqual(PRFile.objects.filter(team=team, filename="src/utils.py").count(), 1)
        self.assertEqual(files_synced, 1)

        # Verify file was updated
        file = PRFile.objects.get(team=team, filename="src/utils.py")
        self.assertEqual(file.status, "modified")
        self.assertEqual(file.additions, 35)
        self.assertEqual(file.deletions, 5)
        self.assertEqual(file.changes, 40)
        self.assertEqual(file.file_category, "backend")  # Category still correct

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_files_handles_api_error(self, mock_github_class):
        """Test that sync_pr_files accumulates errors on API failure."""
        from github import GithubException

        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRFile

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345")
        pr = PullRequestFactory(team=team, github_pr_id=104, github_repo="acme/repo", author=member)

        # Mock PyGithub to raise exception when getting PR
        mock_repo = MagicMock()
        mock_repo.get_pull.side_effect = GithubException(404, {"message": "Not Found"})

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        files_synced = sync_pr_files(
            pr=pr,
            pr_number=104,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify error was accumulated (not raised)
        self.assertEqual(files_synced, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("104", errors[0])

        # Verify no files were created
        self.assertEqual(PRFile.objects.filter(team=team, pull_request=pr).count(), 0)
