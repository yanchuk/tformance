"""Tests for onboarding skip logic when integration flags are off.

TDD Phase: These tests are written FIRST before implementation.
Uses waffle's override_flag for thread-safe flag testing in parallel execution.
"""

from django.test import Client, TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag, Membership
from apps.teams.roles import ROLE_ADMIN


class TestJiraStepSkip(TestCase):
    """Tests for skipping Jira step when flag is off."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(onboarding_complete=False)
        self.user = UserFactory()
        Membership.objects.create(team=self.team, user=self.user, role=ROLE_ADMIN)
        self.client = Client()
        self.client.force_login(self.user)

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

    def test_connect_jira_redirects_to_slack_when_jira_disabled_slack_enabled(self):
        """Test that connect_jira redirects to connect_slack when jira flag is off but slack is on."""
        with (
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=True),
        ):
            response = self.client.get(reverse("onboarding:connect_jira"))

            # Should redirect to slack step
            self.assertRedirects(
                response,
                reverse("onboarding:connect_slack"),
                fetch_redirect_response=False,
            )

    def test_connect_jira_redirects_to_complete_when_both_disabled(self):
        """Test that connect_jira redirects to complete when both flags are off."""
        with (
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
        ):
            response = self.client.get(reverse("onboarding:connect_jira"))

            # Should redirect to complete step
            self.assertRedirects(
                response,
                reverse("onboarding:complete"),
                fetch_redirect_response=False,
            )

    def test_connect_jira_shows_page_when_flag_enabled(self):
        """Test that connect_jira shows the page normally when flag is on."""
        with (
            override_flag("integration_jira_enabled", active=True),
            override_flag("integration_slack_enabled", active=False),
        ):
            response = self.client.get(reverse("onboarding:connect_jira"))

            # Should show the page, not redirect
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "onboarding/connect_jira.html")


class TestSlackStepSkip(TestCase):
    """Tests for skipping Slack step when flag is off."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(onboarding_complete=False)
        self.user = UserFactory()
        Membership.objects.create(team=self.team, user=self.user, role=ROLE_ADMIN)
        self.client = Client()
        self.client.force_login(self.user)

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

    def test_connect_slack_redirects_to_complete_when_disabled(self):
        """Test that connect_slack redirects to complete when flag is off."""
        with override_flag("integration_slack_enabled", active=False):
            response = self.client.get(reverse("onboarding:connect_slack"))

            # Should redirect to complete step
            self.assertRedirects(
                response,
                reverse("onboarding:complete"),
                fetch_redirect_response=False,
            )

    def test_connect_slack_shows_page_when_flag_enabled(self):
        """Test that connect_slack shows the page normally when flag is on."""
        with override_flag("integration_slack_enabled", active=True):
            response = self.client.get(reverse("onboarding:connect_slack"))

            # Should show the page, not redirect
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "onboarding/connect_slack.html")


class TestSyncProgressNavigation(TestCase):
    """Tests for sync_progress 'Continue' button destination."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(onboarding_complete=False)
        self.user = UserFactory()
        Membership.objects.create(team=self.team, user=self.user, role=ROLE_ADMIN)
        self.client = Client()
        self.client.force_login(self.user)

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

    def test_sync_progress_continue_links_to_jira_when_enabled(self):
        """Test that sync_progress Continue button links to Jira when flag is on."""
        with (
            override_flag("integration_jira_enabled", active=True),
            override_flag("integration_slack_enabled", active=False),
        ):
            response = self.client.get(reverse("onboarding:sync_progress"))

            self.assertEqual(response.status_code, 200)
            # Check that the next_step context variable is set correctly (slug)
            self.assertEqual(response.context.get("next_step"), "jira")

    def test_sync_progress_continue_links_to_slack_when_jira_disabled(self):
        """Test that sync_progress Continue button links to Slack when Jira off but Slack on."""
        with (
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=True),
        ):
            response = self.client.get(reverse("onboarding:sync_progress"))

            self.assertEqual(response.status_code, 200)
            # Slug, not URL name
            self.assertEqual(response.context.get("next_step"), "slack")

    def test_sync_progress_continue_links_to_complete_when_both_disabled(self):
        """Test that sync_progress Continue button links to complete when both flags off."""
        with (
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
        ):
            response = self.client.get(reverse("onboarding:sync_progress"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context.get("next_step"), "complete")
