"""Tests for Copilot feature flags.

These tests verify the feature flag helper functions for controlling
Copilot-specific features like seat utilization, language insights, etc.
"""

from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.integrations.services.integration_flags import (
    COPILOT_FEATURE_FLAGS,
    is_copilot_feature_active,
)


class TestCopilotFeatureFlags(TestCase):
    """Tests for Copilot feature flag helpers."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

    def test_copilot_feature_flags_constant_exists(self):
        """Test that COPILOT_FEATURE_FLAGS constant is defined."""
        self.assertIsInstance(COPILOT_FEATURE_FLAGS, dict)
        self.assertIn("copilot_enabled", COPILOT_FEATURE_FLAGS)
        self.assertIn("copilot_seat_utilization", COPILOT_FEATURE_FLAGS)
        self.assertIn("copilot_language_insights", COPILOT_FEATURE_FLAGS)
        self.assertIn("copilot_delivery_impact", COPILOT_FEATURE_FLAGS)
        self.assertIn("copilot_llm_insights", COPILOT_FEATURE_FLAGS)

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_returns_false_when_master_flag_disabled(self, mock_flag_is_active):
        """Test that sub-flags return False when master flag is disabled."""
        # Master flag off, sub-flag on
        mock_flag_is_active.side_effect = lambda req, name: name == "copilot_seat_utilization"

        result = is_copilot_feature_active(self.request, "copilot_seat_utilization")

        self.assertFalse(result)

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_returns_false_when_sub_flag_disabled(self, mock_flag_is_active):
        """Test that returns False when master is on but sub-flag is off."""
        # Master flag on, sub-flag off
        mock_flag_is_active.side_effect = lambda req, name: name == "copilot_enabled"

        result = is_copilot_feature_active(self.request, "copilot_seat_utilization")

        self.assertFalse(result)

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_returns_true_when_both_flags_enabled(self, mock_flag_is_active):
        """Test that returns True when both master and sub-flag are enabled."""
        # Both flags on
        mock_flag_is_active.return_value = True

        result = is_copilot_feature_active(self.request, "copilot_seat_utilization")

        self.assertTrue(result)

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_master_flag_returns_true_when_enabled(self, mock_flag_is_active):
        """Test that master flag check returns True when enabled."""
        mock_flag_is_active.return_value = True

        result = is_copilot_feature_active(self.request, "copilot_enabled")

        self.assertTrue(result)

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_returns_false_for_unknown_flag(self, mock_flag_is_active):
        """Test that unknown flag names return False."""
        mock_flag_is_active.return_value = True

        result = is_copilot_feature_active(self.request, "copilot_unknown_feature")

        self.assertFalse(result)

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_checks_master_flag_first(self, mock_flag_is_active):
        """Test that master flag is checked before sub-flag."""
        call_order = []

        def track_calls(req, name):
            call_order.append(name)
            return True

        mock_flag_is_active.side_effect = track_calls

        is_copilot_feature_active(self.request, "copilot_seat_utilization")

        # Master flag should be checked first
        self.assertEqual(call_order[0], "copilot_enabled")

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_all_feature_flags_can_be_checked(self, mock_flag_is_active):
        """Test that all defined feature flags can be checked."""
        mock_flag_is_active.return_value = True

        for flag_name in COPILOT_FEATURE_FLAGS:
            result = is_copilot_feature_active(self.request, flag_name)
            self.assertTrue(result, f"Flag {flag_name} should return True when enabled")


class TestCopilotFeatureFlagHierarchy(TestCase):
    """Tests for Copilot feature flag hierarchy behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_disabling_master_disables_all_sub_flags(self, mock_flag_is_active):
        """Test that disabling master flag disables all sub-features."""

        # Master off, all sub-flags on
        def flag_check(req, name):
            return name != "copilot_enabled"

        mock_flag_is_active.side_effect = flag_check

        sub_flags = [
            "copilot_seat_utilization",
            "copilot_language_insights",
            "copilot_delivery_impact",
            "copilot_llm_insights",
        ]

        for flag in sub_flags:
            result = is_copilot_feature_active(self.request, flag)
            self.assertFalse(result, f"Sub-flag {flag} should be disabled when master is off")

    @patch("apps.integrations.services.integration_flags.waffle.flag_is_active")
    def test_sub_flags_independent_of_each_other(self, mock_flag_is_active):
        """Test that sub-flags don't depend on each other."""

        # Master on, only seat_utilization on
        def flag_check(req, name):
            return name in ("copilot_enabled", "copilot_seat_utilization")

        mock_flag_is_active.side_effect = flag_check

        # seat_utilization should be True
        self.assertTrue(is_copilot_feature_active(self.request, "copilot_seat_utilization"))

        # Others should be False
        self.assertFalse(is_copilot_feature_active(self.request, "copilot_language_insights"))
        self.assertFalse(is_copilot_feature_active(self.request, "copilot_delivery_impact"))
        self.assertFalse(is_copilot_feature_active(self.request, "copilot_llm_insights"))
