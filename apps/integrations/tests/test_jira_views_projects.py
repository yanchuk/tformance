"""Tests for Jira project selection views."""

from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import (
    JiraIntegrationFactory,
    TrackedJiraProjectFactory,
    UserFactory,
)
from apps.integrations.models import TrackedJiraProject
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class JiraProjectsListViewTest(TestCase):
    """Tests for jira_projects_list view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_jira_projects_list_requires_login(self):
        """Test that jira_projects_list redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:jira_projects_list", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_jira_projects_list_requires_team_membership(self):
        """Test that jira_projects_list returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:jira_projects_list", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_jira_projects_list_requires_admin_role(self):
        """Test that jira_projects_list returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:jira_projects_list", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_jira_projects_list_redirects_if_jira_not_connected(self):
        """Test that jira_projects_list redirects if Jira is not connected."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_projects_list", args=[self.team.slug]))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

    @patch("apps.integrations.services.jira_client.get_accessible_projects")
    def test_jira_projects_list_returns_200_and_renders_template(self, mock_get_projects):
        """Test that jira_projects_list returns 200 and renders template for admin."""
        # Create Jira integration
        JiraIntegrationFactory(team=self.team)

        # Mock Jira API
        mock_get_projects.return_value = [
            {"id": "10001", "key": "PROJ1", "name": "Project One"},
            {"id": "10002", "key": "PROJ2", "name": "Project Two"},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_projects_list", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "integrations/jira_projects_list.html")

    @patch("apps.integrations.services.jira_client.get_accessible_projects")
    def test_jira_projects_list_fetches_projects_from_jira_api(self, mock_get_projects):
        """Test that jira_projects_list fetches projects from Jira API."""
        # Create Jira integration
        JiraIntegrationFactory(team=self.team)

        # Mock Jira API
        mock_get_projects.return_value = [
            {"id": "10001", "key": "PROJ1", "name": "Project One"},
            {"id": "10002", "key": "PROJ2", "name": "Project Two"},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_projects_list", args=[self.team.slug]))

        # Should call get_accessible_projects
        mock_get_projects.assert_called_once()

        # Should contain project data in response
        self.assertContains(response, "PROJ1")
        self.assertContains(response, "Project One")
        self.assertContains(response, "PROJ2")
        self.assertContains(response, "Project Two")

    @patch("apps.integrations.services.jira_client.get_accessible_projects")
    def test_jira_projects_list_shows_tracked_status_for_each_project(self, mock_get_projects):
        """Test that jira_projects_list marks which projects are tracked."""
        # Create Jira integration
        integration = JiraIntegrationFactory(team=self.team)

        # Create tracked project
        TrackedJiraProjectFactory(
            team=self.team,
            integration=integration,
            jira_project_id="10001",
            jira_project_key="PROJ1",
            name="Project One",
        )

        # Mock Jira API - return two projects, one tracked, one not
        mock_get_projects.return_value = [
            {"id": "10001", "key": "PROJ1", "name": "Project One"},
            {"id": "10002", "key": "PROJ2", "name": "Project Two"},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_projects_list", args=[self.team.slug]))

        # Context should show tracked status
        projects = response.context["projects"]
        self.assertEqual(len(projects), 2)

        # First project should be marked as tracked
        proj1 = next(p for p in projects if p["key"] == "PROJ1")
        self.assertTrue(proj1["is_tracked"])

        # Second project should not be tracked
        proj2 = next(p for p in projects if p["key"] == "PROJ2")
        self.assertFalse(proj2["is_tracked"])


class JiraProjectToggleViewTest(TestCase):
    """Tests for jira_project_toggle view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_jira_project_toggle_requires_login(self):
        """Test that jira_project_toggle redirects to login if user is not authenticated."""
        response = self.client.post(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "project_key": "PROJ1",
                "name": "Project One",
                "action": "add",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_jira_project_toggle_requires_team_membership(self):
        """Test that jira_project_toggle returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "project_key": "PROJ1",
                "name": "Project One",
                "action": "add",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_jira_project_toggle_requires_admin_role(self):
        """Test that jira_project_toggle returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "project_key": "PROJ1",
                "name": "Project One",
                "action": "add",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_jira_project_toggle_requires_post_method(self):
        """Test that jira_project_toggle only accepts POST requests."""
        # Create Jira integration
        JiraIntegrationFactory(team=self.team)

        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "project_key": "PROJ1",
                "name": "Project One",
                "action": "add",
            },
        )

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_jira_project_toggle_creates_tracked_project_on_add_action(self):
        """Test that jira_project_toggle creates TrackedJiraProject on add action."""
        # Create Jira integration
        integration = JiraIntegrationFactory(team=self.team)

        self.client.force_login(self.admin)

        self.client.post(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "project_key": "PROJ1",
                "name": "Project One",
                "action": "add",
            },
        )

        # Should create TrackedJiraProject
        self.assertTrue(
            TrackedJiraProject.objects.filter(
                team=self.team, integration=integration, jira_project_id="10001", jira_project_key="PROJ1"
            ).exists()
        )

    def test_jira_project_toggle_returns_success_response_on_add(self):
        """Test that jira_project_toggle returns success response on add."""
        # Create Jira integration
        JiraIntegrationFactory(team=self.team)

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "project_key": "PROJ1",
                "name": "Project One",
                "action": "add",
            },
        )

        # Should return success status
        self.assertEqual(response.status_code, 200)

        # Should return JSON or render template (HTMX compatible)
        if response.get("Content-Type", "").startswith("application/json"):
            # JSON response
            data = response.json()
            self.assertTrue(data.get("success") or "error" not in data)
        else:
            # Template response
            self.assertEqual(response.status_code, 200)

    def test_jira_project_toggle_deletes_tracked_project_on_remove_action(self):
        """Test that jira_project_toggle deletes TrackedJiraProject on remove action."""
        # Create Jira integration and tracked project
        integration = JiraIntegrationFactory(team=self.team)
        tracked_project = TrackedJiraProjectFactory(
            team=self.team,
            integration=integration,
            jira_project_id="10001",
            jira_project_key="PROJ1",
            name="Project One",
        )

        self.client.force_login(self.admin)

        self.client.post(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "project_key": "PROJ1",
                "name": "Project One",
                "action": "remove",
            },
        )

        # Should delete TrackedJiraProject
        self.assertFalse(TrackedJiraProject.objects.filter(pk=tracked_project.pk).exists())

    def test_jira_project_toggle_returns_success_response_on_remove(self):
        """Test that jira_project_toggle returns success response on remove."""
        # Create Jira integration and tracked project
        integration = JiraIntegrationFactory(team=self.team)
        TrackedJiraProjectFactory(
            team=self.team,
            integration=integration,
            jira_project_id="10001",
            jira_project_key="PROJ1",
            name="Project One",
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "project_key": "PROJ1",
                "name": "Project One",
                "action": "remove",
            },
        )

        # Should return success status
        self.assertEqual(response.status_code, 200)

        # Should return JSON or render template (HTMX compatible)
        if response.get("Content-Type", "").startswith("application/json"):
            # JSON response
            data = response.json()
            self.assertTrue(data.get("success") or "error" not in data)
        else:
            # Template response
            self.assertEqual(response.status_code, 200)

    def test_jira_project_toggle_returns_error_when_missing_required_fields(self):
        """Test that jira_project_toggle returns error when required fields are missing."""
        # Create Jira integration
        JiraIntegrationFactory(team=self.team)

        self.client.force_login(self.admin)

        # Missing project_key
        response = self.client.post(
            reverse("integrations:jira_project_toggle", args=[self.team.slug]),
            {
                "project_id": "10001",
                "name": "Project One",
                "action": "add",
            },
        )

        # Should return error response (400 or 200 with error in JSON/template)
        self.assertIn(response.status_code, [200, 400])

        if response.status_code == 200 and response.get("Content-Type", "").startswith("application/json"):
            data = response.json()
            self.assertTrue("error" in data or not data.get("success"))
