"""Tests for repository prioritization in onboarding.

Phase 4.1: Repository Prioritization
- Sort repositories by updated_at descending (most recent first)
- Most active repos appear at top of selection list
"""

from datetime import UTC, datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory
from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class TestRepositoryPrioritization(TestCase):
    """Tests for repository sorting by updated_at in select_repositories view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(
            username="repo_test@example.com",
            email="repo_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.client.login(username="repo_test@example.com", password="testpassword123")

    def test_repos_are_sorted_by_updated_at_descending(self):
        """Test that repositories are sorted by updated_at descending (most recent first)."""
        mock_repos = [
            {
                "id": 1,
                "full_name": "org/old-repo",
                "name": "old-repo",
                "description": "Updated a year ago",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2023, 1, 15, 10, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 2,
                "full_name": "org/recent-repo",
                "name": "recent-repo",
                "description": "Updated recently",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 12, 20, 15, 30, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 3,
                "full_name": "org/medium-repo",
                "name": "medium-repo",
                "description": "Updated a few months ago",
                "language": "JavaScript",
                "private": True,
                "updated_at": datetime(2024, 6, 10, 8, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
        ]

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = mock_repos

            response = self.client.get(reverse("onboarding:select_repos"))

        self.assertEqual(response.status_code, 200)

        # Get repos from context
        repos = response.context["repos"]

        # Verify repos are sorted by updated_at descending
        # Most recent (2024-12-20) should be first, oldest (2023-01-15) should be last
        self.assertEqual(len(repos), 3)
        self.assertEqual(repos[0]["name"], "recent-repo")  # 2024-12-20
        self.assertEqual(repos[1]["name"], "medium-repo")  # 2024-06-10
        self.assertEqual(repos[2]["name"], "old-repo")  # 2023-01-15

    def test_most_recently_updated_repo_appears_first(self):
        """Test that the most recently updated repository appears at the top."""
        mock_repos = [
            {
                "id": 1,
                "full_name": "org/alpha-repo",
                "name": "alpha-repo",
                "description": "Alphabetically first but not most recent",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 2,
                "full_name": "org/zebra-repo",
                "name": "zebra-repo",
                "description": "Alphabetically last but most recent",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 12, 28, 12, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
        ]

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = mock_repos

            response = self.client.get(reverse("onboarding:select_repos"))

        repos = response.context["repos"]

        # zebra-repo should be first because it has the most recent updated_at
        self.assertEqual(repos[0]["name"], "zebra-repo")
        self.assertEqual(repos[1]["name"], "alpha-repo")

    def test_sorting_handles_none_updated_at_values(self):
        """Test that repos with None updated_at are placed at the end."""
        mock_repos = [
            {
                "id": 1,
                "full_name": "org/no-date-repo",
                "name": "no-date-repo",
                "description": "Repository with no updated_at",
                "language": "Python",
                "private": False,
                "updated_at": None,
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 2,
                "full_name": "org/dated-repo",
                "name": "dated-repo",
                "description": "Repository with valid updated_at",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 3,
                "full_name": "org/another-no-date",
                "name": "another-no-date",
                "description": "Another repo without updated_at",
                "language": "JavaScript",
                "private": True,
                "updated_at": None,
                "archived": False,
                "default_branch": "main",
            },
        ]

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = mock_repos

            response = self.client.get(reverse("onboarding:select_repos"))

        repos = response.context["repos"]

        # Repo with valid updated_at should be first
        self.assertEqual(repos[0]["name"], "dated-repo")
        # Repos with None updated_at should be at the end
        self.assertIn(repos[1]["name"], ["no-date-repo", "another-no-date"])
        self.assertIn(repos[2]["name"], ["no-date-repo", "another-no-date"])

    def test_repos_list_is_properly_ordered_in_template_context(self):
        """Test that the repos passed to template context maintain proper order."""
        mock_repos = [
            {
                "id": 1,
                "full_name": "org/repo-c",
                "name": "repo-c",
                "description": "Third by update date",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 3, 1, 0, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 2,
                "full_name": "org/repo-a",
                "name": "repo-a",
                "description": "First by update date",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 12, 1, 0, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 3,
                "full_name": "org/repo-b",
                "name": "repo-b",
                "description": "Second by update date",
                "language": "JavaScript",
                "private": True,
                "updated_at": datetime(2024, 8, 1, 0, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
        ]

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = mock_repos

            response = self.client.get(reverse("onboarding:select_repos"))

        repos = response.context["repos"]

        # Verify exact order: repo-a (Dec), repo-b (Aug), repo-c (Mar)
        expected_order = ["repo-a", "repo-b", "repo-c"]
        actual_order = [repo["name"] for repo in repos]
        self.assertEqual(actual_order, expected_order)

    def test_empty_repos_list_handled_gracefully(self):
        """Test that empty repository list is handled without errors."""
        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = []

            response = self.client.get(reverse("onboarding:select_repos"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["repos"], [])

    def test_single_repo_returns_correctly(self):
        """Test that a single repository is returned correctly."""
        mock_repos = [
            {
                "id": 1,
                "full_name": "org/only-repo",
                "name": "only-repo",
                "description": "The only repository",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 12, 1, 0, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
        ]

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = mock_repos

            response = self.client.get(reverse("onboarding:select_repos"))

        repos = response.context["repos"]
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["name"], "only-repo")
