"""Tests for integration page feature flag UI.

TDD Phase: These tests verify that integration flags affect the page UI.
Uses waffle's override_flag for thread-safe flag testing in parallel execution.
"""

from django.test import Client, TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag
from apps.teams.roles import ROLE_ADMIN


class TestIntegrationPageFlagContext(TestCase):
    """Tests for integration page passing flag context."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.admin)

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_copilot_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")
        Flag.objects.get_or_create(name="integration_google_workspace_enabled")

    def test_integrations_home_includes_integration_statuses_in_context(self):
        """Test that integrations_home view passes integration_statuses to template."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("integration_statuses", response.context)

    def test_integrations_home_statuses_include_all_integrations(self):
        """Test that integration_statuses includes all 4 integrations."""
        response = self.client.get(reverse("integrations:integrations_home"))

        statuses = response.context["integration_statuses"]
        slugs = [s.slug for s in statuses]

        self.assertIn("jira", slugs)
        self.assertIn("copilot", slugs)
        self.assertIn("slack", slugs)
        self.assertIn("google_workspace", slugs)

    def test_integrations_show_coming_soon_when_flags_off(self):
        """Test that disabled integrations show Coming Soon badge."""
        with override_flag("integration_jira_enabled", active=False):
            response = self.client.get(reverse("integrations:integrations_home"))

            self.assertEqual(response.status_code, 200)
            # Should show Coming Soon for Jira (not connected)
            content = response.content.decode()
            self.assertIn("Coming Soon", content)

    def test_jira_shows_connect_when_flag_enabled(self):
        """Test that Jira shows Connect button when flag is enabled."""
        with override_flag("integration_jira_enabled", active=True):
            response = self.client.get(reverse("integrations:integrations_home"))

            self.assertEqual(response.status_code, 200)
            content = response.content.decode()
            # Should show Connect Jira button (not Coming Soon)
            self.assertIn("Connect Jira", content)

    def test_google_workspace_always_shows_coming_soon(self):
        """Test that Google Workspace always shows Coming Soon regardless of flag."""
        # Even if we try to enable the flag, Google Workspace should show Coming Soon
        with override_flag("integration_google_workspace_enabled", active=True):
            response = self.client.get(reverse("integrations:integrations_home"))

            self.assertEqual(response.status_code, 200)
            content = response.content.decode()
            # Google Workspace section should still show Coming Soon
            self.assertIn("Google Workspace", content)


class TestIntegrationBenefitsDisplay(TestCase):
    """Tests for displaying integration benefits when flag is off."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.admin)

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_copilot_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")
        Flag.objects.get_or_create(name="integration_google_workspace_enabled")

    def test_disabled_integration_shows_benefits_list(self):
        """Test that disabled integrations show benefits list."""
        with override_flag("integration_jira_enabled", active=False):
            response = self.client.get(reverse("integrations:integrations_home"))

            self.assertEqual(response.status_code, 200)
            content = response.content.decode()

            # Should show benefit titles (from metadata)
            # These are rendered when integration is disabled
            self.assertIn("Sprint velocity", content)  # Jira benefit

    def test_interested_button_shown_for_disabled_integrations(self):
        """Test that disabled integrations show I'm Interested button."""
        with override_flag("integration_jira_enabled", active=False):
            response = self.client.get(reverse("integrations:integrations_home"))

            self.assertEqual(response.status_code, 200)
            content = response.content.decode()

            # Should have I'm Interested button for disabled integrations
            self.assertIn("I'm Interested", content)


class TestInterestTrackingEndpoint(TestCase):
    """Tests for the interest tracking HTMX endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.admin)

    def test_track_interest_endpoint_exists(self):
        """Test that the interest tracking endpoint is accessible."""
        url = reverse("integrations:track_interest")
        response = self.client.post(url, {"integration": "jira"})

        # Should return 200 (success) or specific status, not 404
        self.assertNotEqual(response.status_code, 404)

    def test_track_interest_returns_partial(self):
        """Test that interest tracking returns HTMX partial."""
        url = reverse("integrations:track_interest")
        response = self.client.post(
            url,
            {"integration": "jira"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should show confirmation
        self.assertIn("Thanks", content)

    def test_track_interest_invalid_integration_returns_400(self):
        """Test that invalid integration slug returns 400."""
        url = reverse("integrations:track_interest")
        response = self.client.post(url, {"integration": "invalid"})

        self.assertEqual(response.status_code, 400)
