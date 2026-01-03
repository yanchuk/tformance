"""Tests for integration feature flags.

TDD Phase: These tests are written FIRST before implementation.
Uses waffle's override_flag for thread-safe flag testing in parallel execution.
"""

from django.test import RequestFactory, TestCase
from waffle.testutils import override_flag

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag


class TestIntegrationFlagHelpers(TestCase):
    """Tests for integration flag helper functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.team = TeamFactory()

        # Ensure flags exist (required for override_flag to work)
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_copilot_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")
        Flag.objects.get_or_create(name="integration_google_workspace_enabled")

    def test_is_integration_enabled_returns_false_by_default(self):
        """Test that integrations are disabled by default (no flag active)."""
        from apps.integrations.services.integration_flags import is_integration_enabled

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        # Use override_flag with active=False to ensure flags are off
        with (
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_copilot_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
            override_flag("integration_google_workspace_enabled", active=False),
        ):
            self.assertFalse(is_integration_enabled(request, "jira"))
            self.assertFalse(is_integration_enabled(request, "copilot"))
            self.assertFalse(is_integration_enabled(request, "slack"))
            self.assertFalse(is_integration_enabled(request, "google_workspace"))

    def test_is_integration_enabled_returns_true_when_flag_active(self):
        """Test that integration is enabled when flag is active for everyone."""
        from apps.integrations.services.integration_flags import is_integration_enabled

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        with (
            override_flag("integration_jira_enabled", active=True),
            override_flag("integration_copilot_enabled", active=False),
        ):
            self.assertTrue(is_integration_enabled(request, "jira"))
            self.assertFalse(is_integration_enabled(request, "copilot"))

    def test_google_workspace_always_coming_soon(self):
        """Test that Google Workspace always shows as coming soon."""
        from apps.integrations.services.integration_flags import get_integration_status

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        status = get_integration_status(request, "google_workspace")

        self.assertTrue(status.coming_soon)
        self.assertFalse(status.enabled)


class TestIntegrationStatus(TestCase):
    """Tests for IntegrationStatus dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.team = TeamFactory()

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_copilot_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")
        Flag.objects.get_or_create(name="integration_google_workspace_enabled")

    def test_get_all_integration_statuses_returns_all_integrations(self):
        """Test that get_all_integration_statuses returns all 4 integrations."""
        from apps.integrations.services.integration_flags import get_all_integration_statuses

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        statuses = get_all_integration_statuses(request)

        # Should have 4 integrations: jira, copilot, slack, google_workspace
        self.assertEqual(len(statuses), 4)

        slugs = [s.slug for s in statuses]
        self.assertIn("jira", slugs)
        self.assertIn("copilot", slugs)
        self.assertIn("slack", slugs)
        self.assertIn("google_workspace", slugs)

    def test_integration_status_has_required_fields(self):
        """Test that IntegrationStatus has all required fields."""
        from apps.integrations.services.integration_flags import get_integration_status

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        status = get_integration_status(request, "jira")

        # Check all required fields exist
        self.assertEqual(status.name, "Jira")
        self.assertEqual(status.slug, "jira")
        self.assertIsInstance(status.enabled, bool)
        self.assertIsInstance(status.coming_soon, bool)
        self.assertIsNotNone(status.icon_color)
        self.assertIsNotNone(status.description)
        self.assertIsInstance(status.benefits, list)
        self.assertGreater(len(status.benefits), 0)

    def test_integration_status_benefits_have_title_and_description(self):
        """Test that each benefit has title and description."""
        from apps.integrations.services.integration_flags import get_integration_status

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        status = get_integration_status(request, "jira")

        for benefit in status.benefits:
            self.assertIn("title", benefit)
            self.assertIn("description", benefit)
            self.assertIsInstance(benefit["title"], str)
            self.assertIsInstance(benefit["description"], str)


class TestOnboardingStepLogic(TestCase):
    """Tests for onboarding step skip logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.team = TeamFactory()

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

    def test_get_enabled_onboarding_steps_returns_empty_when_no_flags(self):
        """Test that no optional steps are returned when all flags are off."""
        from apps.integrations.services.integration_flags import get_enabled_onboarding_steps

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        with (
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
        ):
            steps = get_enabled_onboarding_steps(request)

            # Only jira and slack can be skipped, not github/repos
            # With no flags active, both should be skipped
            self.assertNotIn("jira", steps)
            self.assertNotIn("slack", steps)

    def test_get_enabled_onboarding_steps_includes_jira_when_enabled(self):
        """Test that jira step is included when flag is active."""
        from apps.integrations.services.integration_flags import get_enabled_onboarding_steps

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        with (
            override_flag("integration_jira_enabled", active=True),
            override_flag("integration_slack_enabled", active=False),
        ):
            steps = get_enabled_onboarding_steps(request)

            self.assertIn("jira", steps)
            self.assertNotIn("slack", steps)

    def test_get_enabled_onboarding_steps_includes_both_when_enabled(self):
        """Test that both steps are included when both flags are active."""
        from apps.integrations.services.integration_flags import get_enabled_onboarding_steps

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        with (
            override_flag("integration_jira_enabled", active=True),
            override_flag("integration_slack_enabled", active=True),
        ):
            steps = get_enabled_onboarding_steps(request)

            self.assertIn("jira", steps)
            self.assertIn("slack", steps)

    def test_get_next_onboarding_step_from_sync_progress(self):
        """Test next step calculation from sync_progress."""
        from apps.integrations.services.integration_flags import get_next_onboarding_step

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        # No flags active - should go to complete
        with (
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
        ):
            next_step = get_next_onboarding_step(request, "sync_progress")
            self.assertEqual(next_step, "complete")

        # Jira enabled - should go to jira
        with (
            override_flag("integration_jira_enabled", active=True),
            override_flag("integration_slack_enabled", active=False),
        ):
            next_step = get_next_onboarding_step(request, "sync_progress")
            self.assertEqual(next_step, "jira")

    def test_get_next_onboarding_step_from_jira(self):
        """Test next step calculation from jira step."""
        from apps.integrations.services.integration_flags import get_next_onboarding_step

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        # No slack flag - should go to complete
        with override_flag("integration_slack_enabled", active=False):
            next_step = get_next_onboarding_step(request, "jira")
            self.assertEqual(next_step, "complete")

        # Slack enabled - should go to slack
        with override_flag("integration_slack_enabled", active=True):
            next_step = get_next_onboarding_step(request, "jira")
            self.assertEqual(next_step, "slack")

    def test_get_next_onboarding_step_from_slack(self):
        """Test next step from slack always goes to complete."""
        from apps.integrations.services.integration_flags import get_next_onboarding_step

        request = self.factory.get("/")
        request.user = self.user
        request.team = self.team

        next_step = get_next_onboarding_step(request, "slack")
        self.assertEqual(next_step, "complete")
