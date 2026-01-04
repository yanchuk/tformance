"""Tests for onboarding views."""

from django.test import TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag
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

    def test_returns_pipeline_status(self):
        """Test that API returns pipeline status info (signal-based pipeline)."""
        from unittest.mock import patch

        self.client.login(username="api_test@example.com", password="testpassword123")

        with patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline:
            # Signal-based pipeline returns dict, not AsyncResult
            mock_pipeline.return_value = {"status": "started", "team_id": self.team.id}

            response = self.client.post(reverse("onboarding:start_sync"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # New response format uses pipeline_status and status, not task_id
        self.assertIn("status", data)
        self.assertIn("pipeline_status", data)


@override_flag("integration_jira_enabled", active=True)
@override_flag("integration_slack_enabled", active=True)
class ConnectJiraViewTests(TestCase):
    """Tests for connect_jira view."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure flags exist for override_flag to work
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

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


@override_flag("integration_jira_enabled", active=True)
@override_flag("integration_slack_enabled", active=True)
class SelectJiraProjectsViewTests(TestCase):
    """Tests for select_jira_projects view."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import JiraIntegrationFactory

        # Ensure flags exist for override_flag to work
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

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


@override_flag("integration_slack_enabled", active=True)
class SlackConnectViewTests(TestCase):
    """Tests for connect_slack onboarding view."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.teams.roles import ROLE_ADMIN

        # Ensure flags exist for override_flag to work
        Flag.objects.get_or_create(name="integration_slack_enabled")

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


class SyncStatusViewTests(TestCase):
    """Tests for sync_status API endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import GitHubIntegrationFactory, IntegrationCredentialFactory
        from apps.integrations.models import TrackedRepository

        self.user = CustomUser.objects.create_user(
            username="syncstatus@example.com",
            email="syncstatus@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)

        # Create GitHub integration
        credential = IntegrationCredentialFactory(team=self.team, provider="github")
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=credential,
            organization_slug="test-org",
        )

        # Create some tracked repos
        self.repo1 = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            github_repo_id=12345,
            full_name="test-org/repo1",
            sync_status="completed",
        )
        self.repo2 = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            github_repo_id=12346,
            full_name="test-org/repo2",
            sync_status="pending",
        )

    def test_requires_authentication(self):
        """Test that unauthenticated requests are rejected."""
        response = self.client.get(reverse("onboarding:sync_status"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_returns_json_with_repos(self):
        """Test that authenticated requests get JSON with repo statuses."""
        self.client.login(username="syncstatus@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_status"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertIn("repos", data)
        self.assertIn("overall_status", data)
        self.assertIn("prs_synced", data)
        self.assertEqual(len(data["repos"]), 2)

    def test_returns_correct_repo_statuses(self):
        """Test that repo statuses are correctly returned."""
        self.client.login(username="syncstatus@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        repo_by_id = {r["id"]: r for r in data["repos"]}
        self.assertEqual(repo_by_id[self.repo1.id]["sync_status"], "completed")
        self.assertEqual(repo_by_id[self.repo2.id]["sync_status"], "pending")

    def test_overall_status_partial_when_mixed(self):
        """Test overall status is partial when repos have mixed statuses."""
        self.client.login(username="syncstatus@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        # One completed, one pending = partial
        self.assertEqual(data["overall_status"], "partial")

    def test_overall_status_completed_when_all_done(self):
        """Test overall status is completed when all repos are completed."""
        self.repo2.sync_status = "completed"
        self.repo2.save()

        self.client.login(username="syncstatus@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(data["overall_status"], "completed")

    def test_returns_prs_synced_count(self):
        """Test that prs_synced count is returned."""
        from apps.metrics.factories import PullRequestFactory, TeamMemberFactory

        author = TeamMemberFactory(team=self.team)
        PullRequestFactory(team=self.team, author=author)
        PullRequestFactory(team=self.team, author=author)

        self.client.login(username="syncstatus@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(data["prs_synced"], 2)

    def test_error_when_no_team(self):
        """Test error response when user has no team."""
        # Create user without team
        CustomUser.objects.create_user(
            username="noteam@example.com",
            email="noteam@example.com",
            password="testpassword123",
        )
        self.client.login(username="noteam@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:sync_status"))

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)


class SyncStatusPipelineFieldsTests(TestCase):
    """Tests for sync_status API endpoint pipeline progress fields.

    These tests verify that the sync_status endpoint returns pipeline
    progress information for tracking the onboarding data pipeline.
    """

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import GitHubIntegrationFactory, IntegrationCredentialFactory
        from apps.integrations.models import TrackedRepository

        self.user = CustomUser.objects.create_user(
            username="pipeline_test@example.com",
            email="pipeline_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)

        # Create GitHub integration
        credential = IntegrationCredentialFactory(team=self.team, provider="github")
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=credential,
            organization_slug="test-org",
        )

        # Create tracked repo
        self.repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            github_repo_id=99999,
            full_name="test-org/pipeline-repo",
            sync_status="completed",
        )

        self.client.login(username="pipeline_test@example.com", password="testpassword123")

    def test_returns_pipeline_status_field(self):
        """Test that sync_status returns pipeline_status from team model."""

        # Set a specific pipeline status
        self.team.onboarding_pipeline_status = "llm_processing"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("pipeline_status", data)
        self.assertEqual(data["pipeline_status"], "llm_processing")

    def test_returns_pipeline_stage_display_for_not_started(self):
        """Test that pipeline_stage returns human-readable display for not_started."""
        self.team.onboarding_pipeline_status = "not_started"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("pipeline_stage", data)
        self.assertEqual(data["pipeline_stage"], "Not Started")

    def test_returns_pipeline_stage_display_for_syncing(self):
        """Test that pipeline_stage returns human-readable display for syncing."""
        self.team.onboarding_pipeline_status = "syncing"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("pipeline_stage", data)
        self.assertEqual(data["pipeline_stage"], "Syncing PRs")

    def test_returns_pipeline_stage_display_for_llm_processing(self):
        """Test that pipeline_stage returns human-readable display for llm_processing."""
        self.team.onboarding_pipeline_status = "llm_processing"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("pipeline_stage", data)
        self.assertEqual(data["pipeline_stage"], "Analyzing with AI")

    def test_returns_pipeline_stage_display_for_computing_metrics(self):
        """Test that pipeline_stage returns human-readable display for computing_metrics."""
        self.team.onboarding_pipeline_status = "computing_metrics"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("pipeline_stage", data)
        self.assertEqual(data["pipeline_stage"], "Computing Metrics")

    def test_returns_pipeline_stage_display_for_complete(self):
        """Test that pipeline_stage returns human-readable display for complete."""
        self.team.onboarding_pipeline_status = "complete"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("pipeline_stage", data)
        self.assertEqual(data["pipeline_stage"], "Complete")

    def test_returns_llm_progress_with_zero_when_no_prs(self):
        """Test that llm_progress returns zeros when no PRs exist."""
        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("llm_progress", data)
        self.assertIsInstance(data["llm_progress"], dict)
        self.assertEqual(data["llm_progress"]["processed"], 0)
        self.assertEqual(data["llm_progress"]["total"], 0)

    def test_returns_llm_progress_with_counts(self):
        """Test that llm_progress returns correct processed/total counts."""
        from apps.metrics.factories import PullRequestFactory, TeamMemberFactory

        author = TeamMemberFactory(team=self.team)

        # Create 3 PRs, 2 with llm_summary (processed), 1 without
        PullRequestFactory(
            team=self.team,
            author=author,
            llm_summary={"ai": {"is_assisted": True}},
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            llm_summary={"ai": {"is_assisted": False}},
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            llm_summary=None,
        )

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("llm_progress", data)
        self.assertEqual(data["llm_progress"]["total"], 3)
        self.assertEqual(data["llm_progress"]["processed"], 2)

    def test_returns_metrics_ready_false_when_no_weekly_metrics(self):
        """Test that metrics_ready is False when no WeeklyMetrics exist."""
        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("metrics_ready", data)
        self.assertFalse(data["metrics_ready"])

    def test_returns_metrics_ready_true_when_weekly_metrics_exist(self):
        """Test that metrics_ready is True when WeeklyMetrics exist for team."""
        from apps.metrics.factories import TeamMemberFactory, WeeklyMetricsFactory

        member = TeamMemberFactory(team=self.team)
        WeeklyMetricsFactory(team=self.team, member=member)

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("metrics_ready", data)
        self.assertTrue(data["metrics_ready"])

    def test_returns_insights_ready_false_when_no_daily_insights(self):
        """Test that insights_ready is False when no DailyInsight exist."""
        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("insights_ready", data)
        self.assertFalse(data["insights_ready"])

    def test_returns_insights_ready_true_when_daily_insights_exist(self):
        """Test that insights_ready is True when DailyInsight exist for team."""
        from apps.metrics.factories import DailyInsightFactory

        DailyInsightFactory(team=self.team)

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIn("insights_ready", data)
        self.assertTrue(data["insights_ready"])

    def test_all_pipeline_fields_returned_together(self):
        """Test that all new pipeline fields are returned in a single response."""
        from apps.metrics.factories import (
            DailyInsightFactory,
            PullRequestFactory,
            TeamMemberFactory,
            WeeklyMetricsFactory,
        )

        # Set up complete scenario
        self.team.onboarding_pipeline_status = "complete"
        self.team.save()

        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(team=self.team, author=member, llm_summary={"ai": {"is_assisted": True}})
        WeeklyMetricsFactory(team=self.team, member=member)
        DailyInsightFactory(team=self.team)

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        # Verify all new fields are present
        self.assertIn("pipeline_status", data)
        self.assertIn("pipeline_stage", data)
        self.assertIn("llm_progress", data)
        self.assertIn("metrics_ready", data)
        self.assertIn("insights_ready", data)

        # Verify correct values
        self.assertEqual(data["pipeline_status"], "complete")
        self.assertEqual(data["pipeline_stage"], "Complete")
        self.assertEqual(data["llm_progress"]["processed"], 1)
        self.assertEqual(data["llm_progress"]["total"], 1)
        self.assertTrue(data["metrics_ready"])
        self.assertTrue(data["insights_ready"])


class SyncStatusPhaseFieldsTests(TestCase):
    """Tests for sync_status API endpoint sync_phase and sync_phase_label fields.

    These tests verify that the sync_status endpoint returns phase-specific
    messaging for the onboarding progress UI.
    """

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import GitHubIntegrationFactory, IntegrationCredentialFactory
        from apps.integrations.models import TrackedRepository

        self.user = CustomUser.objects.create_user(
            username="phase_test@example.com",
            email="phase_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)

        credential = IntegrationCredentialFactory(team=self.team, provider="github")
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=credential,
            organization_slug="test-org",
        )

        TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            github_repo_id=88888,
            full_name="test-org/phase-repo",
            sync_status="syncing",
        )

        self.client.login(username="phase_test@example.com", password="testpassword123")

    def test_returns_sync_phase_fields(self):
        """Test that sync_status returns sync_phase and sync_phase_label."""
        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("sync_phase", data)
        self.assertIn("sync_phase_label", data)

    def test_phase1_syncing_status(self):
        """Test sync_phase for Phase 1 (syncing recent 30 days)."""
        self.team.onboarding_pipeline_status = "syncing"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(data["sync_phase"], "sync")
        self.assertEqual(data["sync_phase_label"], "Importing PRs from last 30 days")

    def test_phase2_background_syncing_status(self):
        """Test sync_phase for Phase 2 (background sync 31-90 days)."""
        self.team.onboarding_pipeline_status = "background_syncing"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(data["sync_phase"], "phase2")
        self.assertEqual(data["sync_phase_label"], "Syncing older PRs (31-90 days)")

    def test_llm_processing_status(self):
        """Test sync_phase for LLM processing phase."""
        self.team.onboarding_pipeline_status = "llm_processing"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(data["sync_phase"], "llm")
        self.assertEqual(data["sync_phase_label"], "Analyzing PRs with AI")

    def test_done_phase_for_complete_status(self):
        """Test sync_phase is 'done' when pipeline is complete."""
        self.team.onboarding_pipeline_status = "complete"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(data["sync_phase"], "done")
        self.assertEqual(data["sync_phase_label"], "All done!")

    def test_null_phase_for_not_started_status(self):
        """Test sync_phase is null when pipeline not started."""
        self.team.onboarding_pipeline_status = "not_started"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertIsNone(data["sync_phase"])
        self.assertIsNone(data["sync_phase_label"])

    def test_metrics_phase_for_computing_metrics_status(self):
        """Test sync_phase is 'metrics' when computing metrics."""
        self.team.onboarding_pipeline_status = "computing_metrics"
        self.team.save()

        response = self.client.get(reverse("onboarding:sync_status"))
        data = response.json()

        self.assertEqual(data["sync_phase"], "metrics")
        self.assertEqual(data["sync_phase_label"], "Computing team metrics")


class PipelineIntegrationTests(TestCase):
    """Tests for onboarding views integration with the onboarding pipeline.

    These tests verify that the onboarding views use start_onboarding_pipeline()
    instead of sync_historical_data_task.delay() directly.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.factories import (
            GitHubIntegrationFactory,
            IntegrationCredentialFactory,
            TrackedRepositoryFactory,
        )

        self.user = CustomUser.objects.create_user(
            username="pipeline_views@example.com",
            email="pipeline_views@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)

        # Create GitHub integration
        self.credential = IntegrationCredentialFactory(team=self.team, provider="github")
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="test-org",
        )

        # Create tracked repositories
        self.repo1 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test-org/repo-1",
        )
        self.repo2 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="test-org/repo-2",
        )

        self.client.login(username="pipeline_views@example.com", password="testpassword123")

    def test_select_repos_post_calls_start_onboarding_pipeline(self):
        """Test that select_repos POST calls start_onboarding_pipeline instead of sync_historical_data_task.

        This test verifies that when a user submits repository selection,
        the view triggers the full onboarding pipeline, not just the sync task.
        """
        from unittest.mock import patch

        # Mock both the GitHub API call and the pipeline function
        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_repos:
            mock_repos.return_value = [
                {"id": self.repo1.github_repo_id, "full_name": "test-org/repo-1"},
                {"id": self.repo2.github_repo_id, "full_name": "test-org/repo-2"},
            ]

            with patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline:
                mock_pipeline.return_value.id = "pipeline-task-id-123"

                response = self.client.post(
                    reverse("onboarding:select_repos"),
                    {"repos": [str(self.repo1.github_repo_id)]},
                )

                # Verify the pipeline was called
                mock_pipeline.assert_called_once()
                call_args = mock_pipeline.call_args
                self.assertEqual(call_args[0][0], self.team.id)  # First arg is team_id
                self.assertIsInstance(call_args[0][1], list)  # Second arg is repo_ids list

        # Should redirect to sync_progress
        self.assertRedirects(response, reverse("onboarding:sync_progress"))

    def test_select_repos_post_clears_old_task_id_from_session(self):
        """Test that select_repos clears old task_id from session.

        Signal-based pipeline uses status field for tracking, not task_id.
        Any old task_id should be cleared from session.
        """
        from unittest.mock import patch

        # First, set an old task_id in session
        session = self.client.session
        session["sync_task_id"] = "old-task-id"
        session.save()

        with patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_repos:
            mock_repos.return_value = [
                {"id": self.repo1.github_repo_id, "full_name": "test-org/repo-1"},
            ]

            with patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline:
                # Signal-based pipeline returns dict, not AsyncResult
                mock_pipeline.return_value = {"status": "started", "team_id": self.team.id}

                self.client.post(
                    reverse("onboarding:select_repos"),
                    {"repos": [str(self.repo1.github_repo_id)]},
                )

                # Verify old task_id was cleared (signal-based pipeline doesn't need it)
                session = self.client.session
                self.assertIsNone(session.get("sync_task_id"))

    def test_start_sync_post_calls_start_onboarding_pipeline(self):
        """Test that start_sync POST calls start_onboarding_pipeline instead of sync_historical_data_task.

        The start_sync API endpoint should trigger the full onboarding pipeline
        for processing historical data.
        """
        from unittest.mock import patch

        with patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline:
            # Signal-based pipeline returns dict, not AsyncResult
            mock_pipeline.return_value = {"status": "started", "team_id": self.team.id}

            response = self.client.post(reverse("onboarding:start_sync"))

            # Verify the pipeline was called with correct arguments
            mock_pipeline.assert_called_once()
            call_args = mock_pipeline.call_args
            self.assertEqual(call_args[0][0], self.team.id)  # team_id

            # Verify repo_ids include both repos
            repo_ids = call_args[0][1]
            self.assertIn(self.repo1.id, repo_ids)
            self.assertIn(self.repo2.id, repo_ids)

        # Should return JSON with status info (signal-based pipeline)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "started")

    def test_start_sync_returns_pipeline_status_in_response(self):
        """Test that start_sync returns pipeline status info (signal-based pipeline).

        The JSON response contains status info for the signal-based pipeline,
        which uses the team's pipeline_status field for tracking progress.
        """
        from unittest.mock import patch

        with patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline:
            # Signal-based pipeline returns dict with status info
            mock_pipeline.return_value = {
                "status": "started",
                "team_id": self.team.id,
                "execution_mode": "signal_based",
            }

            response = self.client.post(reverse("onboarding:start_sync"))

            data = response.json()
            # Should have status and message for frontend to switch to DB polling
            self.assertIn("status", data)
            self.assertIn("pipeline_status", data)
            self.assertIn("message", data)

    def test_select_repos_does_not_call_sync_historical_data_task_directly(self):
        """Test that select_repos does NOT call sync_historical_data_task.delay() directly.

        This is a negative test to ensure we migrated away from the old pattern.
        The sync_historical_data_task should not even be imported in the views module.
        """
        from apps.onboarding import views

        # The old task should not be imported in views at all
        self.assertFalse(
            hasattr(views, "sync_historical_data_task"),
            "sync_historical_data_task should not be imported in onboarding views",
        )

    def test_start_sync_does_not_call_sync_historical_data_task_directly(self):
        """Test that start_sync does NOT call sync_historical_data_task.delay() directly.

        This is a negative test to ensure we migrated away from the old pattern.
        The sync_historical_data_task should not even be imported in the views module.
        """
        from apps.onboarding import views

        # The old task should not be imported in views at all
        self.assertFalse(
            hasattr(views, "sync_historical_data_task"),
            "sync_historical_data_task should not be imported in onboarding views",
        )
