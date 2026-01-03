"""Tests for Slack configuration form during onboarding."""

from django.test import TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from apps.integrations.factories import SlackIntegrationFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag
from apps.users.models import CustomUser


@override_flag("integration_slack_enabled", active=True)
class SlackConfigurationFormTests(TestCase):
    """Tests for Slack configuration form in onboarding."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure flags exist for override_flag to work
        Flag.objects.get_or_create(name="integration_slack_enabled")

        self.user = CustomUser.objects.create_user(
            username="slack_config@example.com",
            email="slack_config@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.client.login(username="slack_config@example.com", password="testpassword123")

    def test_config_form_shown_when_slack_connected(self):
        """Test that configuration form is shown when Slack is connected."""
        SlackIntegrationFactory(team=self.team)

        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should show configuration options
        self.assertIn("leaderboard", content.lower())

    def test_config_form_has_channel_field(self):
        """Test that config form has a channel selection field."""
        SlackIntegrationFactory(team=self.team)

        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have channel input or select
        self.assertIn("channel", content.lower())

    def test_config_form_has_schedule_fields(self):
        """Test that config form has day and time selection fields."""
        SlackIntegrationFactory(team=self.team)

        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have day and time fields
        self.assertIn("leaderboard_day", content)
        self.assertIn("leaderboard_time", content)

    def test_config_form_has_feature_toggles(self):
        """Test that config form has feature toggle checkboxes."""
        SlackIntegrationFactory(team=self.team)

        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have toggle fields for surveys, leaderboard, reveals
        self.assertIn("surveys_enabled", content)
        self.assertIn("leaderboard_enabled", content)
        self.assertIn("reveals_enabled", content)

    def test_config_form_submit_updates_integration(self):
        """Test that submitting config form updates the Slack integration."""
        slack_integration = SlackIntegrationFactory(
            team=self.team,
            surveys_enabled=True,
            leaderboard_enabled=True,
            reveals_enabled=True,
            leaderboard_day=0,  # Monday
        )

        response = self.client.post(
            reverse("onboarding:connect_slack"),
            {
                "surveys_enabled": "on",
                "leaderboard_enabled": "",  # Unchecked
                "reveals_enabled": "on",
                "leaderboard_day": "4",  # Friday
                "leaderboard_time": "14:00",
            },
        )

        # Should redirect to complete page
        self.assertEqual(response.status_code, 302)

        # Reload and check values
        slack_integration.refresh_from_db()
        self.assertTrue(slack_integration.surveys_enabled)
        self.assertFalse(slack_integration.leaderboard_enabled)
        self.assertTrue(slack_integration.reveals_enabled)
        self.assertEqual(slack_integration.leaderboard_day, 4)

    def test_config_not_shown_when_slack_not_connected(self):
        """Test that config form is not shown when Slack is not connected."""
        # No Slack integration created

        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should show connect button, not config form
        self.assertIn("Add to Slack", content)
        # Should NOT show the config form fields
        self.assertNotIn("leaderboard_day", content)
