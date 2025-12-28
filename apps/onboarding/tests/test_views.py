"""Tests for onboarding views."""

from django.test import TestCase
from django.urls import reverse

from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class OnboardingStartViewTests(TestCase):
    """Tests for onboarding_start view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="testpassword123",
        )

    def test_redirect_to_login_when_not_authenticated(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("onboarding:start"))
        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={reverse('onboarding:start')}",
        )

    def test_redirect_to_app_when_user_has_team(self):
        """Test that users with teams are redirected to /app/ (web:home).

        Regression test: Previously this used web_team:home with team_slug
        which caused NoReverseMatch error.
        """
        self.client.login(username="test@example.com", password="testpassword123")

        # Create a team and add user as member
        team = TeamFactory()
        team.members.add(self.user)

        response = self.client.get(reverse("onboarding:start"))

        # Should redirect to web:home (which is /)
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)

    def test_shows_start_page_when_user_has_no_team(self):
        """Test that users without teams see the onboarding start page."""
        self.client.login(username="test@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "onboarding/start.html")


class GithubConnectViewTests(TestCase):
    """Tests for github_connect view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="test2@example.com",
            email="test2@example.com",
            password="testpassword123",
        )

    def test_redirect_to_app_when_user_has_team(self):
        """Test that users with teams are redirected to /app/ (web:home).

        Regression test: Previously this used web_team:home with team_slug
        which caused NoReverseMatch error.
        """
        self.client.login(username="test2@example.com", password="testpassword123")

        # Create a team and add user as member
        team = TeamFactory()
        team.members.add(self.user)

        response = self.client.get(reverse("onboarding:github_connect"))

        # Should redirect to web:home (which is /)
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)


class SelectOrganizationViewTests(TestCase):
    """Tests for select_organization view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="test3@example.com",
            email="test3@example.com",
            password="testpassword123",
        )

    def test_redirect_to_app_when_user_has_team(self):
        """Test that users with teams are redirected to /app/ (web:home).

        Regression test: Previously this used web_team:home with team_slug
        which caused NoReverseMatch error.
        """
        self.client.login(username="test3@example.com", password="testpassword123")

        # Create a team and add user as member
        team = TeamFactory()
        team.members.add(self.user)

        response = self.client.get(reverse("onboarding:select_org"))

        # Should redirect to web:home (which is /)
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)


class SkipOnboardingViewTests(TestCase):
    """Tests for skip_onboarding view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="skip_test@example.com",
            email="skip_test@example.com",
            password="testpassword123",
        )

    def test_redirect_to_login_when_not_authenticated(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("onboarding:skip"))
        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={reverse('onboarding:skip')}",
        )

    def test_redirect_to_app_when_user_already_has_team(self):
        """Test that users with teams are redirected to app without creating new team."""
        self.client.login(username="skip_test@example.com", password="testpassword123")

        # Create a team and add user as member
        team = TeamFactory()
        team.members.add(self.user)

        initial_team_count = self.user.teams.count()

        response = self.client.get(reverse("onboarding:skip"))

        # Should redirect to web:home
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)
        # Should not create a new team
        self.assertEqual(self.user.teams.count(), initial_team_count)

    def test_creates_team_and_redirects_for_user_without_team(self):
        """Test that skip creates a team for users without one."""
        self.client.login(username="skip_test@example.com", password="testpassword123")

        # Verify user has no teams
        self.assertEqual(self.user.teams.count(), 0)

        response = self.client.get(reverse("onboarding:skip"))

        # Should redirect to web:home
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)

        # Should have created a team
        self.assertEqual(self.user.teams.count(), 1)

        # Team name should be based on email prefix
        team = self.user.teams.first()
        self.assertEqual(team.name, "skip_test's Team")

    def test_user_is_team_admin_after_skip(self):
        """Test that user becomes admin of the created team."""
        from apps.teams.models import Membership
        from apps.teams.roles import ROLE_ADMIN

        self.client.login(username="skip_test@example.com", password="testpassword123")

        self.client.get(reverse("onboarding:skip"))

        team = self.user.teams.first()
        membership = Membership.objects.get(team=team, user=self.user)
        self.assertEqual(membership.role, ROLE_ADMIN)


class SyncProgressViewTests(TestCase):
    """Tests for sync_progress view."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.user = CustomUser.objects.create_user(
            username="sync_test@example.com",
            email="sync_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    def test_redirect_to_login_when_not_authenticated(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("onboarding:sync_progress"))
        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={reverse('onboarding:sync_progress')}",
        )

    def test_redirect_to_start_when_no_team(self):
        """Test that users without teams are redirected to start."""
        CustomUser.objects.create_user(
            username="noteam@example.com",
            email="noteam@example.com",
            password="testpassword123",
        )
        self.client.login(username="noteam@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertRedirects(response, reverse("onboarding:start"))

    def test_shows_sync_progress_page(self):
        """Test that sync progress page loads correctly."""
        self.client.login(username="sync_test@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "onboarding/sync_progress.html")

    def test_context_contains_team_and_repos(self):
        """Test that context contains team and repository info."""
        self.client.login(username="sync_test@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.context["team"], self.team)
        self.assertIn("repos", response.context)


class StartSyncApiViewTests(TestCase):
    """Tests for start_sync API view."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.user = CustomUser.objects.create_user(
            username="api_test@example.com",
            email="api_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    def test_requires_authentication(self):
        """Test that API requires authentication."""
        response = self.client.post(reverse("onboarding:start_sync"))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_requires_post_method(self):
        """Test that API only accepts POST."""
        self.client.login(username="api_test@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start_sync"))

        self.assertEqual(response.status_code, 405)  # Method not allowed

    def test_returns_task_id(self):
        """Test that API returns a task ID."""
        from unittest.mock import patch

        self.client.login(username="api_test@example.com", password="testpassword123")

        with patch("apps.onboarding.views.sync_historical_data_task") as mock_task:
            mock_task.delay.return_value.id = "test-task-id-123"

            response = self.client.post(reverse("onboarding:start_sync"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("task_id", response.json())
        self.assertEqual(response.json()["task_id"], "test-task-id-123")


class ConnectJiraViewTests(TestCase):
    """Tests for connect_jira view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="jira_test@example.com",
            email="jira_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)

    def test_redirect_to_login_when_not_authenticated(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("onboarding:connect_jira"))
        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={reverse('onboarding:connect_jira')}",
        )

    def test_redirect_to_start_when_no_team(self):
        """Test that users without teams are redirected to start."""
        CustomUser.objects.create_user(
            username="noteam_jira@example.com",
            email="noteam_jira@example.com",
            password="testpassword123",
        )
        self.client.login(username="noteam_jira@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:connect_jira"))

        self.assertRedirects(response, reverse("onboarding:start"))

    def test_shows_jira_connect_page(self):
        """Test that Jira connect page loads correctly."""
        self.client.login(username="jira_test@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:connect_jira"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "onboarding/connect_jira.html")

    def test_post_skips_to_slack(self):
        """Test that POST skips Jira and continues to Slack."""
        self.client.login(username="jira_test@example.com", password="testpassword123")

        response = self.client.post(reverse("onboarding:connect_jira"))

        self.assertRedirects(response, reverse("onboarding:connect_slack"))

    def test_action_connect_redirects_to_jira_oauth(self):
        """Test that action=connect initiates Jira OAuth flow."""
        self.client.login(username="jira_test@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:connect_jira"), {"action": "connect"})

        # Should redirect to Jira OAuth URL
        self.assertEqual(response.status_code, 302)
        self.assertIn("atlassian.com", response.url)

    def test_redirect_to_projects_when_already_connected(self):
        """Test that users with Jira connected are redirected to project selection."""
        from apps.integrations.factories import JiraIntegrationFactory

        self.client.login(username="jira_test@example.com", password="testpassword123")

        # Create Jira integration for team
        JiraIntegrationFactory(team=self.team)

        response = self.client.get(reverse("onboarding:connect_jira"))

        self.assertRedirects(response, reverse("onboarding:select_jira_projects"))


class SelectJiraProjectsViewTests(TestCase):
    """Tests for select_jira_projects view."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import JiraIntegrationFactory

        self.user = CustomUser.objects.create_user(
            username="jira_projects@example.com",
            email="jira_projects@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.jira_integration = JiraIntegrationFactory(team=self.team)

    def test_redirect_to_login_when_not_authenticated(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("onboarding:select_jira_projects"))
        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={reverse('onboarding:select_jira_projects')}",
        )

    def test_redirect_to_start_when_no_team(self):
        """Test that users without teams are redirected to start."""
        CustomUser.objects.create_user(
            username="noteam_projects@example.com",
            email="noteam_projects@example.com",
            password="testpassword123",
        )
        self.client.login(username="noteam_projects@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:select_jira_projects"))

        self.assertRedirects(response, reverse("onboarding:start"))

    def test_redirect_to_connect_jira_when_not_connected(self):
        """Test that users without Jira are redirected to connect."""
        # Create user with team but no Jira integration
        user2 = CustomUser.objects.create_user(
            username="no_jira@example.com",
            email="no_jira@example.com",
            password="testpassword123",
        )
        team2 = TeamFactory()
        team2.members.add(user2)

        self.client.login(username="no_jira@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:select_jira_projects"))

        self.assertRedirects(response, reverse("onboarding:connect_jira"))

    def test_shows_project_selection_page(self):
        """Test that project selection page loads correctly."""
        from unittest.mock import patch

        self.client.login(username="jira_projects@example.com", password="testpassword123")

        with patch("apps.integrations.services.jira_client.get_accessible_projects") as mock_get_projects:
            mock_get_projects.return_value = [
                {"id": "10001", "key": "PROJ", "name": "My Project", "projectTypeKey": "software"}
            ]

            response = self.client.get(reverse("onboarding:select_jira_projects"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "onboarding/select_jira_projects.html")

    def test_context_contains_projects(self):
        """Test that context contains projects list."""
        from unittest.mock import patch

        self.client.login(username="jira_projects@example.com", password="testpassword123")

        with patch("apps.integrations.services.jira_client.get_accessible_projects") as mock_get_projects:
            mock_get_projects.return_value = [
                {"id": "10001", "key": "PROJ1", "name": "Project 1"},
                {"id": "10002", "key": "PROJ2", "name": "Project 2"},
            ]

            response = self.client.get(reverse("onboarding:select_jira_projects"))

        self.assertIn("projects", response.context)
        self.assertEqual(len(response.context["projects"]), 2)

    def test_post_creates_tracked_projects(self):
        """Test that POST creates TrackedJiraProject records."""
        from unittest.mock import patch

        from apps.integrations.models import TrackedJiraProject

        self.client.login(username="jira_projects@example.com", password="testpassword123")

        with patch("apps.integrations.services.jira_client.get_accessible_projects") as mock_get_projects:
            mock_get_projects.return_value = [
                {"id": "10001", "key": "PROJ1", "name": "Project 1", "projectTypeKey": "software"},
                {"id": "10002", "key": "PROJ2", "name": "Project 2", "projectTypeKey": "business"},
            ]

            response = self.client.post(
                reverse("onboarding:select_jira_projects"),
                {"projects": ["10001", "10002"]},
            )

        # Should redirect to Slack
        self.assertRedirects(response, reverse("onboarding:connect_slack"))

        # Should have created tracked projects
        self.assertEqual(TrackedJiraProject.objects.filter(team=self.team).count(), 2)

    def test_post_with_no_selection_redirects_to_slack(self):
        """Test that POST with no selection continues to Slack."""
        from unittest.mock import patch

        self.client.login(username="jira_projects@example.com", password="testpassword123")

        with patch("apps.integrations.services.jira_client.get_accessible_projects") as mock_get_projects:
            mock_get_projects.return_value = []

            response = self.client.post(reverse("onboarding:select_jira_projects"))

        # Should redirect to Slack
        self.assertRedirects(response, reverse("onboarding:connect_slack"))


class SlackConnectViewTests(TestCase):
    """Tests for connect_slack onboarding view."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.teams.roles import ROLE_ADMIN

        self.user = CustomUser.objects.create_user(
            username="slack_test@example.com",
            email="slack_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.login(username="slack_test@example.com", password="testpassword123")

    def test_redirect_to_start_when_user_has_no_team(self):
        """Test that users without teams are redirected to onboarding start."""
        # Create new user without team
        CustomUser.objects.create_user(
            username="no_team@example.com",
            email="no_team@example.com",
            password="testpassword123",
        )
        self.client.login(username="no_team@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertRedirects(response, reverse("onboarding:start"))

    def test_shows_connect_slack_page(self):
        """Test that users with teams see the connect slack page."""
        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "onboarding/connect_slack.html")

    def test_action_connect_redirects_to_slack_oauth(self):
        """Test that ?action=connect initiates Slack OAuth flow."""
        response = self.client.get(
            reverse("onboarding:connect_slack"),
            {"action": "connect"},
        )

        # Should redirect to Slack OAuth
        self.assertEqual(response.status_code, 302)
        self.assertIn("slack.com/oauth", response.url)
        self.assertIn("state=", response.url)
        # Verify scope is included
        self.assertIn("scope=", response.url)

    def test_skip_redirects_to_complete(self):
        """Test that POST (skip) redirects to complete."""
        response = self.client.post(reverse("onboarding:connect_slack"))

        self.assertRedirects(response, reverse("onboarding:complete"))

    def test_shows_connected_workspace_when_slack_connected(self):
        """Test that connected workspace name is shown when Slack is already connected."""
        from apps.integrations.factories import IntegrationCredentialFactory, SlackIntegrationFactory

        # Create Slack integration for the team
        credential = IntegrationCredentialFactory(team=self.team, provider="slack")
        SlackIntegrationFactory(
            team=self.team,
            credential=credential,
            workspace_name="Test Workspace",
        )

        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Workspace")
        self.assertContains(response, "Connected to")
