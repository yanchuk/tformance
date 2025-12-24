"""Tests for GitHub repository languages service."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    TrackedRepositoryFactory,
)
from apps.integrations.services.github_repo_languages import (
    fetch_repo_languages,
    get_top_languages,
    update_repo_languages,
)
from apps.metrics.factories import TeamFactory


class TestFetchRepoLanguages(TestCase):
    """Tests for fetch_repo_languages function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="antiwork/gumroad",
        )

    @patch("apps.integrations.services.github_repo_languages.get_github_client")
    def test_fetches_languages_from_github_api(self, mock_get_client):
        """Test that it fetches languages from GitHub API."""
        mock_gh_repo = MagicMock()
        mock_gh_repo.get_languages.return_value = {
            "Python": 150000,
            "JavaScript": 25000,
            "HTML": 5000,
        }
        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_gh_repo
        mock_get_client.return_value = mock_client

        result = fetch_repo_languages(self.repo)

        mock_get_client.assert_called_once_with("test_token")
        mock_client.get_repo.assert_called_once_with("antiwork/gumroad")
        self.assertEqual(result, {"Python": 150000, "JavaScript": 25000, "HTML": 5000})

    def test_raises_error_without_access_token(self):
        """Test that it raises error when access token is empty."""
        # Create a new team to avoid unique constraint on credential
        team2 = TeamFactory()
        empty_cred = IntegrationCredentialFactory(
            team=team2,
            provider="github",
            access_token="",
        )
        integration_no_token = GitHubIntegrationFactory(
            team=team2,
            credential=empty_cred,
        )
        repo_no_token = TrackedRepositoryFactory(
            team=team2,
            integration=integration_no_token,
            full_name="test/repo",
        )

        with self.assertRaises(ValueError) as ctx:
            fetch_repo_languages(repo_no_token)

        self.assertIn("No GitHub credential", str(ctx.exception))


class TestUpdateRepoLanguages(TestCase):
    """Tests for update_repo_languages function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="antiwork/gumroad",
        )

    @patch("apps.integrations.services.github_repo_languages.fetch_repo_languages")
    def test_stores_languages_and_primary(self, mock_fetch):
        """Test that it stores languages and identifies primary language."""
        mock_fetch.return_value = {
            "Python": 150000,
            "JavaScript": 25000,
            "HTML": 5000,
        }

        result = update_repo_languages(self.repo)

        self.repo.refresh_from_db()
        self.assertEqual(result, {"Python": 150000, "JavaScript": 25000, "HTML": 5000})
        self.assertEqual(self.repo.languages, {"Python": 150000, "JavaScript": 25000, "HTML": 5000})
        self.assertEqual(self.repo.primary_language, "Python")
        self.assertIsNotNone(self.repo.languages_updated_at)

    @patch("apps.integrations.services.github_repo_languages.fetch_repo_languages")
    def test_handles_empty_languages(self, mock_fetch):
        """Test handling of empty languages response."""
        mock_fetch.return_value = {}

        result = update_repo_languages(self.repo)

        self.repo.refresh_from_db()
        self.assertEqual(result, {})
        self.assertEqual(self.repo.languages, {})
        self.assertEqual(self.repo.primary_language, "")

    @patch("apps.integrations.services.github_repo_languages.fetch_repo_languages")
    def test_updates_timestamp(self, mock_fetch):
        """Test that languages_updated_at is set."""
        mock_fetch.return_value = {"Go": 100000}
        before = timezone.now()

        update_repo_languages(self.repo)

        self.repo.refresh_from_db()
        self.assertIsNotNone(self.repo.languages_updated_at)
        self.assertGreaterEqual(self.repo.languages_updated_at, before)


class TestGetTopLanguages(TestCase):
    """Tests for get_top_languages function."""

    def test_returns_top_n_languages(self):
        """Test returning top N languages sorted by bytes."""

        class MockRepo:
            languages = {
                "Python": 150000,
                "JavaScript": 25000,
                "HTML": 5000,
                "CSS": 3000,
                "Shell": 1000,
                "Dockerfile": 500,
            }

        result = get_top_languages(MockRepo(), limit=3)

        self.assertEqual(result, ["Python", "JavaScript", "HTML"])

    def test_returns_all_when_fewer_than_limit(self):
        """Test when fewer languages than limit."""

        class MockRepo:
            languages = {"Python": 150000, "JavaScript": 25000}

        result = get_top_languages(MockRepo(), limit=5)

        self.assertEqual(result, ["Python", "JavaScript"])

    def test_returns_empty_for_no_languages(self):
        """Test empty result for no languages."""

        class MockRepo:
            languages = {}

        result = get_top_languages(MockRepo())

        self.assertEqual(result, [])

    def test_returns_empty_for_none_languages(self):
        """Test empty result when languages is None."""

        class MockRepo:
            languages = None

        result = get_top_languages(MockRepo())

        self.assertEqual(result, [])


class TestRefreshRepoLanguagesTask(TestCase):
    """Tests for refresh_repo_languages_task Celery task."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="antiwork/gumroad",
            is_active=True,
        )

    @patch("apps.integrations.services.github_repo_languages.update_repo_languages")
    def test_refreshes_single_repo(self, mock_update):
        """Test refreshing a single repository."""
        from apps.integrations.tasks import refresh_repo_languages_task

        mock_update.return_value = {"Python": 100000}

        result = refresh_repo_languages_task(self.repo.id)

        mock_update.assert_called_once_with(self.repo)
        self.assertEqual(result["repo"], "antiwork/gumroad")
        self.assertEqual(result["languages_count"], 1)

    def test_skips_inactive_repo(self):
        """Test that inactive repos are skipped."""
        from apps.integrations.tasks import refresh_repo_languages_task

        self.repo.is_active = False
        self.repo.save()

        result = refresh_repo_languages_task(self.repo.id)

        self.assertTrue(result.get("skipped"))
        self.assertEqual(result.get("reason"), "Repository is not active")

    def test_handles_missing_repo(self):
        """Test handling of non-existent repo ID."""
        from apps.integrations.tasks import refresh_repo_languages_task

        result = refresh_repo_languages_task(99999)

        self.assertIn("error", result)
        self.assertIn("not found", result["error"])


class TestRefreshAllRepoLanguagesTask(TestCase):
    """Tests for refresh_all_repo_languages_task Celery task."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

    @patch("apps.integrations.services.github_repo_languages.update_repo_languages")
    def test_refreshes_repos_needing_update(self, mock_update):
        """Test that repos without recent update are refreshed."""
        from apps.integrations.tasks import refresh_all_repo_languages_task

        # Create repo never updated
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test/repo1",
            is_active=True,
            languages_updated_at=None,
        )
        # Create repo updated 60 days ago
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test/repo2",
            is_active=True,
            languages_updated_at=timezone.now() - timedelta(days=60),
        )
        mock_update.return_value = {"Python": 100000}

        result = refresh_all_repo_languages_task()

        self.assertEqual(mock_update.call_count, 2)
        self.assertEqual(result["repos_updated"], 2)
        self.assertEqual(result["errors_count"], 0)

    @patch("apps.integrations.services.github_repo_languages.update_repo_languages")
    def test_skips_recently_updated_repos(self, mock_update):
        """Test that recently updated repos are skipped."""
        from apps.integrations.tasks import refresh_all_repo_languages_task

        # Create repo updated 5 days ago (within 30 day threshold)
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test/recent",
            is_active=True,
            languages_updated_at=timezone.now() - timedelta(days=5),
        )

        result = refresh_all_repo_languages_task()

        mock_update.assert_not_called()
        self.assertEqual(result["repos_updated"], 0)

    @patch("apps.integrations.services.github_repo_languages.update_repo_languages")
    def test_skips_inactive_repos(self, mock_update):
        """Test that inactive repos are skipped."""
        from apps.integrations.tasks import refresh_all_repo_languages_task

        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test/inactive",
            is_active=False,
            languages_updated_at=None,
        )

        result = refresh_all_repo_languages_task()

        mock_update.assert_not_called()
        self.assertEqual(result["repos_updated"], 0)

    @patch("apps.integrations.services.github_repo_languages.update_repo_languages")
    def test_handles_errors_and_continues(self, mock_update):
        """Test that errors don't stop processing other repos."""
        from apps.integrations.tasks import refresh_all_repo_languages_task

        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test/fail",
            is_active=True,
            languages_updated_at=None,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test/success",
            is_active=True,
            languages_updated_at=None,
        )

        # First call fails, second succeeds
        mock_update.side_effect = [Exception("API error"), {"Python": 100000}]

        result = refresh_all_repo_languages_task()

        self.assertEqual(mock_update.call_count, 2)
        self.assertEqual(result["repos_updated"], 1)
        self.assertEqual(result["errors_count"], 1)
