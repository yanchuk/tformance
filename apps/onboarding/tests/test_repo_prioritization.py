"""Tests for repository prioritization in onboarding.

Phase 4.1: Repository Prioritization
- Sort repositories by updated_at descending (most recent first)
- Most active repos appear at top of selection list

NOTE: Repo sorting now happens in the fetch_repos HTMX endpoint,
not in the initial select_repos page load.
"""

from datetime import UTC, datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory
from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class TestRepositoryPrioritization(TestCase):
    """Tests for repository sorting by updated_at in fetch_repos view."""

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

            response = self.client.get(reverse("onboarding:fetch_repos"))

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

            response = self.client.get(reverse("onboarding:fetch_repos"))

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

            response = self.client.get(reverse("onboarding:fetch_repos"))

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

            response = self.client.get(reverse("onboarding:fetch_repos"))

        repos = response.context["repos"]

        # Verify exact order: repo-a (Dec), repo-b (Aug), repo-c (Mar)
        expected_order = ["repo-a", "repo-b", "repo-c"]
        actual_order = [repo["name"] for repo in repos]
        self.assertEqual(actual_order, expected_order)

    def test_empty_repos_list_handled_gracefully(self):
        """Test that empty repository list is handled without errors."""
        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = []

            response = self.client.get(reverse("onboarding:fetch_repos"))

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

            response = self.client.get(reverse("onboarding:fetch_repos"))

        repos = response.context["repos"]
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["name"], "only-repo")


class TestSelectReposPageLoading(TestCase):
    """Tests for select_repos page with HTMX loading pattern."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(
            username="repo_loading_test@example.com",
            email="repo_loading_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.client.login(username="repo_loading_test@example.com", password="testpassword123")

    def test_select_repos_page_does_not_fetch_repos_on_initial_load(self):
        """Test that initial page load does not call GitHub API."""
        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            response = self.client.get(reverse("onboarding:select_repos"))

        self.assertEqual(response.status_code, 200)
        # API should NOT be called on initial page load (HTMX will call fetch_repos)
        mock_get_repos.assert_not_called()

    def test_select_repos_page_has_htmx_trigger(self):
        """Test that the page has HTMX trigger to fetch repos."""
        response = self.client.get(reverse("onboarding:select_repos"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Check for HTMX attributes
        self.assertIn("hx-get", content)
        self.assertIn('hx-trigger="load"', content)
        # The URL should include the fetch path
        self.assertIn("/onboarding/repos/fetch/", content)

    def test_select_repos_page_has_loading_indicator(self):
        """Test that the page has a loading indicator."""
        response = self.client.get(reverse("onboarding:select_repos"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Check for loading indicator
        self.assertIn("htmx-indicator", content)
        self.assertIn("fa-spinner", content)


class TestTrackedReposAtTop(TestCase):
    """Tests for A-008: Tracked repos should appear at top of list."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(
            username="tracked_repos_test@example.com",
            email="tracked_repos_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.client.login(username="tracked_repos_test@example.com", password="testpassword123")

    def test_tracked_repos_appear_first_in_list(self):
        """Test that repos already being tracked appear before untracked repos.

        A-008: When user views repo list during onboarding, repos they already
        track should appear at the top of the list (before sorting by updated_at).
        """
        from apps.integrations.factories import TrackedRepositoryFactory

        # Create a tracked repository (repo id 2)
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=2,
            full_name="org/tracked-repo",
        )

        # Mock repos from GitHub API - note the tracked one has older updated_at
        mock_repos = [
            {
                "id": 1,
                "full_name": "org/untracked-recent",
                "name": "untracked-recent",
                "description": "Untracked but most recently updated",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 12, 25, 12, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 2,
                "full_name": "org/tracked-repo",
                "name": "tracked-repo",
                "description": "Already being tracked but older",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 6, 1, 10, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 3,
                "full_name": "org/another-untracked",
                "name": "another-untracked",
                "description": "Another untracked repo",
                "language": "JavaScript",
                "private": True,
                "updated_at": datetime(2024, 9, 15, 8, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
        ]

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = mock_repos

            response = self.client.get(reverse("onboarding:fetch_repos"))

        self.assertEqual(response.status_code, 200)
        repos = response.context["repos"]

        # Tracked repo should be first, even though it has older updated_at
        self.assertEqual(repos[0]["name"], "tracked-repo")
        # Then untracked repos sorted by updated_at
        self.assertEqual(repos[1]["name"], "untracked-recent")  # Dec 25
        self.assertEqual(repos[2]["name"], "another-untracked")  # Sep 15

    def test_multiple_tracked_repos_sorted_by_updated_at(self):
        """Test that multiple tracked repos are sorted by updated_at among themselves."""
        from apps.integrations.factories import TrackedRepositoryFactory

        # Create two tracked repositories
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=1,
            full_name="org/tracked-old",
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=2,
            full_name="org/tracked-recent",
        )

        mock_repos = [
            {
                "id": 1,
                "full_name": "org/tracked-old",
                "name": "tracked-old",
                "description": "Tracked but older",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 3, 1, 0, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 2,
                "full_name": "org/tracked-recent",
                "name": "tracked-recent",
                "description": "Tracked and recent",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 12, 1, 0, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
            {
                "id": 3,
                "full_name": "org/untracked",
                "name": "untracked",
                "description": "Not tracked",
                "language": "Python",
                "private": False,
                "updated_at": datetime(2024, 12, 20, 0, 0, 0, tzinfo=UTC),
                "archived": False,
                "default_branch": "main",
            },
        ]

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            mock_get_repos.return_value = mock_repos

            response = self.client.get(reverse("onboarding:fetch_repos"))

        repos = response.context["repos"]

        # Both tracked repos should come first, sorted by updated_at
        self.assertEqual(repos[0]["name"], "tracked-recent")  # Tracked, Dec 1
        self.assertEqual(repos[1]["name"], "tracked-old")  # Tracked, Mar 1
        # Then untracked repo
        self.assertEqual(repos[2]["name"], "untracked")  # Not tracked, Dec 20
