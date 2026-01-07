"""
Tests for Copilot LLM prompt context feature flag gating.

This module tests that Copilot metrics are only included in LLM prompts
when the `copilot_llm_insights` feature flag is enabled.

The implementation should respect the hierarchical flag structure:
1. Master flag `copilot_enabled` must be active
2. Sub-flag `copilot_llm_insights` must be active
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.integrations.services.copilot_metrics_prompt import get_copilot_metrics_for_prompt
from apps.metrics.factories import (
    AIUsageDailyFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.models import CopilotSeatSnapshot


class TestCopilotPromptFlagCheck(TestCase):
    """Tests for Copilot metrics in LLM prompts respecting feature flags."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.request.team = self.team

        self.today = date.today()
        self.start_date = self.today - timedelta(days=7)
        self.end_date = self.today

        # Create Copilot usage data
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
            acceptance_rate=Decimal("40.00"),
        )

        # Create seat snapshot
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

    @patch("apps.integrations.services.copilot_metrics_prompt.is_copilot_feature_active")
    def test_copilot_metrics_excluded_when_flag_disabled(self, mock_flag_check):
        """Test that Copilot metrics are excluded from prompt when flag is disabled.

        When copilot_llm_insights flag is disabled, the function should return
        an empty dict (no Copilot data) even if usage data exists.
        """
        mock_flag_check.return_value = False

        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            request=self.request,
        )

        # Should return empty dict when flag is disabled
        self.assertEqual(result, {})

    @patch("apps.integrations.services.copilot_metrics_prompt.is_copilot_feature_active")
    def test_copilot_metrics_included_when_flag_enabled(self, mock_flag_check):
        """Test that Copilot metrics are included in prompt when flag is enabled.

        When copilot_llm_insights flag is enabled, the function should return
        the full Copilot metrics data.
        """
        mock_flag_check.return_value = True

        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            request=self.request,
        )

        # Should return Copilot metrics when flag is enabled
        self.assertIn("active_users", result)
        self.assertIn("total_suggestions", result)
        self.assertEqual(result["total_suggestions"], 100)
        self.assertIn("seat_data", result)
        self.assertIsNotNone(result["seat_data"])

    @patch("apps.integrations.services.copilot_metrics_prompt.is_copilot_feature_active")
    def test_respects_copilot_llm_insights_flag_specifically(self, mock_flag_check):
        """Test that the function checks the copilot_llm_insights flag specifically.

        The function should call is_copilot_feature_active with 'copilot_llm_insights'
        as the flag name to check.
        """
        mock_flag_check.return_value = True

        get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            request=self.request,
        )

        # Verify the correct flag was checked
        mock_flag_check.assert_called_once()
        call_args = mock_flag_check.call_args
        self.assertEqual(call_args[0][1], "copilot_llm_insights")

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_respects_master_copilot_enabled_flag(self, mock_waffle):
        """Test that master copilot_enabled flag is also checked.

        The hierarchical flag check should ensure both copilot_enabled (master)
        and copilot_llm_insights (sub-flag) are active.
        """

        # Master flag OFF, sub-flag ON
        def flag_check(req, name):
            if name == "copilot_enabled":
                return False
            return name == "copilot_llm_insights"

        mock_waffle.side_effect = flag_check

        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            request=self.request,
        )

        # Should return empty dict because master flag is disabled
        self.assertEqual(result, {})


class TestCopilotPromptFlagCheckWithoutRequest(TestCase):
    """Tests for Copilot metrics in LLM prompts when no request is available.

    In Celery tasks and batch processing, there may not be an HTTP request
    available. The function should handle this gracefully.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

        self.today = date.today()
        self.start_date = self.today - timedelta(days=7)
        self.end_date = self.today

        # Create Copilot usage data
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
            acceptance_rate=Decimal("40.00"),
        )

    def test_returns_empty_when_no_request_and_no_flag_override(self):
        """Test that function returns empty dict when no request and no flag override.

        When called from a context without an HTTP request (e.g., Celery task),
        and no explicit flag override is provided, the function should default
        to excluding Copilot metrics.
        """
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            # No request parameter
        )

        # Should return empty dict by default (conservative approach)
        self.assertEqual(result, {})

    def test_includes_metrics_when_explicit_flag_override_true(self):
        """Test that function includes metrics when flag_override=True.

        When explicitly told to include Copilot metrics (e.g., from a batch
        task that has already verified flags), the function should return data.
        """
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,  # Explicit override
        )

        # Should return Copilot metrics when explicitly enabled
        self.assertIn("active_users", result)
        self.assertIn("total_suggestions", result)

    def test_excludes_metrics_when_explicit_flag_override_false(self):
        """Test that function excludes metrics when flag_override=False.

        When explicitly told to exclude Copilot metrics, the function should
        return an empty dict.
        """
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=False,  # Explicit override
        )

        # Should return empty dict when explicitly disabled
        self.assertEqual(result, {})


class TestCopilotPromptFlagCheckIntegration(TestCase):
    """Integration tests for Copilot prompt flag checking with real flags.

    These tests verify the flag checking works with actual waffle Flag objects
    instead of mocks.
    """

    def setUp(self):
        """Set up test fixtures with real flags."""
        from apps.integrations.factories import UserFactory
        from apps.teams.models import Flag
        from apps.teams.roles import ROLE_ADMIN

        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.request.team = self.team
        self.request.user = self.user  # Add user for waffle flag checking

        self.today = date.today()
        self.start_date = self.today - timedelta(days=7)
        self.end_date = self.today

        # Create Copilot usage data
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
            acceptance_rate=Decimal("40.00"),
        )

        # Create the flags (but don't enable for team yet)
        self.master_flag, _ = Flag.objects.get_or_create(
            name="copilot_enabled",
            defaults={"everyone": False},
        )
        self.llm_flag, _ = Flag.objects.get_or_create(
            name="copilot_llm_insights",
            defaults={"everyone": False},
        )

    def test_excludes_metrics_when_no_flags_enabled(self):
        """Test that metrics are excluded when flags don't exist or aren't enabled."""
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            request=self.request,
        )

        # Should return empty dict when flags are not enabled
        self.assertEqual(result, {})

    def test_includes_metrics_when_both_flags_enabled_for_team(self):
        """Test that metrics are included when both flags are enabled for team."""
        # Enable both flags for the team
        self.master_flag.teams.add(self.team)
        self.llm_flag.teams.add(self.team)

        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            request=self.request,
        )

        # Should return Copilot metrics when both flags enabled
        self.assertIn("active_users", result)
        self.assertIn("total_suggestions", result)

    def test_excludes_metrics_when_only_master_flag_enabled(self):
        """Test that metrics are excluded when only master flag is enabled."""
        # Enable only master flag for the team
        self.master_flag.teams.add(self.team)
        # llm_flag is NOT enabled

        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            request=self.request,
        )

        # Should return empty dict because sub-flag is not enabled
        self.assertEqual(result, {})

    def test_excludes_metrics_when_only_llm_flag_enabled(self):
        """Test that metrics are excluded when only LLM flag is enabled."""
        # Enable only llm flag for the team (master is NOT enabled)
        self.llm_flag.teams.add(self.team)

        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            request=self.request,
        )

        # Should return empty dict because master flag is not enabled
        self.assertEqual(result, {})
