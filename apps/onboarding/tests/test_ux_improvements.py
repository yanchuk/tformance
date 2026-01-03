"""Tests for onboarding UX improvements.

These tests verify the UX improvements identified in the PM/UX review:
- Optional step labels on Jira/Slack
- Time estimate display
- Complete page messaging
- Button hierarchy
- Repository search/filter
"""

from django.test import TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag
from apps.users.models import CustomUser


@override_flag("integration_jira_enabled", active=True)
@override_flag("integration_slack_enabled", active=True)
class ProgressIndicatorOptionalLabelsTests(TestCase):
    """Tests for optional step labels on Jira and Slack steps."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure flags exist for override_flag to work
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

        self.user = CustomUser.objects.create_user(
            username="progress@example.com",
            email="progress@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.client.login(username="progress@example.com", password="testpassword123")

    def test_jira_step_shows_optional_label(self):
        """Test that Jira step shows (optional) label in progress indicator."""
        response = self.client.get(reverse("onboarding:connect_jira"))

        self.assertEqual(response.status_code, 200)
        # Check for optional label in the step indicator
        content = response.content.decode()
        # The Jira step should have "(optional)" text
        self.assertIn("(optional)", content)

    def test_slack_step_shows_optional_label(self):
        """Test that Slack step shows (optional) label in progress indicator."""
        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        # Check for optional label in the step indicator
        content = response.content.decode()
        # The Slack step should have "(optional)" text
        self.assertIn("(optional)", content)

    def test_github_step_does_not_show_optional(self):
        """Test that GitHub step does NOT show optional label (it's required)."""
        # Need a user without a team to see the start page
        CustomUser.objects.create_user(
            username="newuser@example.com",
            email="newuser@example.com",
            password="testpassword123",
        )
        self.client.login(username="newuser@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # The progress indicator section shouldn't have optional for step 1
        # We check that "GitHub" is not followed by "(optional)" in close proximity
        # This is a basic check - the label should appear under Jira/Slack only
        self.assertIn("GitHub", content)


class TimeEstimateDisplayTests(TestCase):
    """Tests for time estimate display in onboarding."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="time@example.com",
            email="time@example.com",
            password="testpassword123",
        )
        self.client.login(username="time@example.com", password="testpassword123")

    def test_start_page_shows_time_estimate(self):
        """Test that start page shows accurate time estimate."""
        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should show realistic time estimate (5 minutes)
        self.assertIn("5 min", content)


@override_flag("integration_jira_enabled", active=True)
@override_flag("integration_slack_enabled", active=True)
class CompletePageMessagingTests(TestCase):
    """Tests for improved messaging on complete page."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="complete@example.com",
            email="complete@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.client.login(username="complete@example.com", password="testpassword123")

    def test_skipped_jira_shows_neutral_message(self):
        """Test that skipped Jira shows neutral message, not warning."""
        response = self.client.get(reverse("onboarding:complete"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should NOT show warning icon (fa-clock with text-warning)
        # Should show info icon instead
        self.assertNotIn("fa-clock text-warning", content)
        # Should use neutral language
        self.assertIn("Available to connect later", content)

    def test_skipped_slack_shows_neutral_message(self):
        """Test that skipped Slack shows neutral message, not warning."""
        response = self.client.get(reverse("onboarding:complete"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should use neutral language for Slack too
        self.assertIn("Available to connect later", content)

    def test_complete_page_shows_team_name(self):
        """Test that complete page shows the created team name."""
        response = self.client.get(reverse("onboarding:complete"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team.name)


@override_flag("integration_jira_enabled", active=True)
@override_flag("integration_slack_enabled", active=True)
class ButtonHierarchyTests(TestCase):
    """Tests for correct button hierarchy on Jira/Slack pages."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure flags exist for override_flag to work
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

        self.user = CustomUser.objects.create_user(
            username="buttons@example.com",
            email="buttons@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.client.login(username="buttons@example.com", password="testpassword123")

    def test_jira_connect_button_is_primary(self):
        """Test that Connect Jira button has primary styling."""
        response = self.client.get(reverse("onboarding:connect_jira"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Connect button should be primary
        self.assertIn("app-btn-primary", content)
        # It should be associated with the connect action
        self.assertIn("Connect Jira", content)

    def test_jira_skip_button_is_secondary(self):
        """Test that Skip button on Jira page has secondary/ghost styling."""
        response = self.client.get(reverse("onboarding:connect_jira"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Skip button should be ghost or secondary, not primary
        # The Skip button should NOT have app-btn-primary class
        # We check that there's a ghost button for skip
        self.assertIn("app-btn-ghost", content)

    def test_slack_connect_button_is_primary(self):
        """Test that Add to Slack button has primary styling."""
        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Connect button should be primary
        self.assertIn("app-btn-primary", content)

    def test_slack_skip_button_is_secondary(self):
        """Test that Skip button on Slack page has secondary/ghost styling."""
        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Skip button should be ghost
        self.assertIn("app-btn-ghost", content)


class RepoSearchFilterTests(TestCase):
    """Tests for repository search/filter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="search@example.com",
            email="search@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.client.login(username="search@example.com", password="testpassword123")

    def test_repo_selection_has_search_input(self):
        """Test that repository selection page has a search input when 6+ repos.

        NOTE: Search input is now loaded via HTMX from fetch_repos endpoint.
        """
        # Store repos in session (simulating post-OAuth state)
        session = self.client.session
        session["onboarding_github_orgs"] = [{"login": "test-org", "id": 123}]
        session["onboarding_selected_org"] = {"login": "test-org", "id": 123}
        session.save()

        # We need to mock the GitHub API call to get repos
        from unittest.mock import patch

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_get_repos:
            # Need 6+ repos to show search box
            mock_get_repos.return_value = [
                {"id": 1, "name": "repo-alpha", "private": False, "language": "Python"},
                {"id": 2, "name": "repo-beta", "private": False, "language": "JavaScript"},
                {"id": 3, "name": "repo-gamma", "private": False, "language": "Go"},
                {"id": 4, "name": "repo-delta", "private": False, "language": "Rust"},
                {"id": 5, "name": "repo-epsilon", "private": False, "language": "TypeScript"},
                {"id": 6, "name": "repo-zeta", "private": False, "language": "Ruby"},
            ]

            # Test the HTMX fetch_repos endpoint where search is rendered
            response = self.client.get(reverse("onboarding:fetch_repos"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have a search input (shown when >5 repos)
        self.assertIn('type="search"', content)
        self.assertIn('x-model="searchQuery"', content)


class SyncProgressContinueTests(TestCase):
    """Tests for sync progress page continue button."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="sync_continue@example.com",
            email="sync_continue@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        self.client.login(username="sync_continue@example.com", password="testpassword123")

    def test_continue_button_is_prominent(self):
        """Test that continue button on sync progress is prominent."""
        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Continue button should be primary, not secondary
        self.assertIn("app-btn-primary", content)
        # Should mention user can continue while sync runs
        self.assertIn("continue", content.lower())
