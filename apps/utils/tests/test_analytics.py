"""Tests for PostHog analytics wrapper functions.

These tests verify the analytics module provides a safe wrapper around PostHog SDK
that handles errors gracefully and provides consistent behavior when PostHog is
unavailable or unconfigured.
"""

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory

from ..analytics import group_identify, identify_user, is_feature_enabled, track_event


class TestTrackEvent(TestCase):
    """Tests for track_event function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = UserFactory()
        self.team = TeamFactory()

    @patch("apps.utils.analytics.posthog")
    def test_track_event_calls_posthog_capture(self, mock_posthog):
        """Test that track_event calls posthog.capture with correct arguments."""
        track_event(self.user, "button_clicked", {"button_name": "submit"})

        mock_posthog.capture.assert_called_once()
        call_args = mock_posthog.capture.call_args
        self.assertEqual(call_args[1]["distinct_id"], str(self.user.id))
        self.assertEqual(call_args[1]["event"], "button_clicked")
        self.assertIn("button_name", call_args[1]["properties"])

    @patch("apps.utils.analytics.posthog")
    def test_track_event_without_properties(self, mock_posthog):
        """Test that track_event works without additional properties."""
        track_event(self.user, "page_viewed")

        mock_posthog.capture.assert_called_once()
        call_args = mock_posthog.capture.call_args
        self.assertEqual(call_args[1]["event"], "page_viewed")

    @patch("apps.utils.analytics.posthog")
    def test_track_event_adds_team_context(self, mock_posthog):
        """Test that track_event auto-adds team context if user has a team."""
        # Associate user with team via membership
        from apps.teams.models import Membership

        Membership.objects.create(team=self.team, user=self.user, role="member")

        track_event(self.user, "feature_used")

        mock_posthog.capture.assert_called_once()
        call_args = mock_posthog.capture.call_args
        properties = call_args[1]["properties"]
        self.assertIn("team_id", properties)
        self.assertEqual(properties["team_id"], str(self.team.id))

    @patch("apps.utils.analytics.posthog")
    def test_track_event_handles_posthog_exception(self, mock_posthog):
        """Test that track_event does not crash if PostHog raises an exception."""
        mock_posthog.capture.side_effect = Exception("PostHog unavailable")

        # Should not raise an exception
        track_event(self.user, "test_event")

    def test_track_event_handles_none_user(self):
        """Test that track_event handles None user gracefully."""
        # Should not raise an exception
        track_event(None, "anonymous_event")

    @override_settings(POSTHOG_API_KEY=None)
    def test_track_event_handles_unconfigured_posthog(self):
        """Test that track_event works when PostHog is not configured."""
        # Should not raise an exception
        track_event(self.user, "test_event")


class TestIdentifyUser(TestCase):
    """Tests for identify_user function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = UserFactory(email="test@example.com", first_name="Test", last_name="User")

    @patch("apps.utils.analytics.posthog")
    def test_identify_user_calls_posthog_identify(self, mock_posthog):
        """Test that identify_user calls posthog.identify with correct arguments."""
        identify_user(self.user, {"plan": "enterprise"})

        mock_posthog.identify.assert_called_once()
        call_args = mock_posthog.identify.call_args
        self.assertEqual(call_args[1]["distinct_id"], str(self.user.id))
        self.assertIn("plan", call_args[1]["properties"])

    @patch("apps.utils.analytics.posthog")
    def test_identify_user_includes_default_properties(self, mock_posthog):
        """Test that identify_user includes default user properties."""
        identify_user(self.user)

        mock_posthog.identify.assert_called_once()
        call_args = mock_posthog.identify.call_args
        properties = call_args[1]["properties"]
        self.assertIn("email", properties)
        self.assertEqual(properties["email"], "test@example.com")

    @patch("apps.utils.analytics.posthog")
    def test_identify_user_handles_exception(self, mock_posthog):
        """Test that identify_user does not crash if PostHog raises an exception."""
        mock_posthog.identify.side_effect = Exception("PostHog unavailable")

        # Should not raise an exception
        identify_user(self.user)

    def test_identify_user_handles_none_user(self):
        """Test that identify_user handles None user gracefully."""
        # Should not raise an exception
        identify_user(None)


class TestGroupIdentify(TestCase):
    """Tests for group_identify function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(name="Test Team", slug="test-team")

    @patch("apps.utils.analytics.posthog")
    def test_group_identify_calls_posthog_group_identify(self, mock_posthog):
        """Test that group_identify calls posthog.group_identify with correct arguments."""
        group_identify(self.team, {"plan": "enterprise", "seats": 10})

        mock_posthog.group_identify.assert_called_once()
        call_args = mock_posthog.group_identify.call_args
        self.assertEqual(call_args[1]["group_type"], "team")
        self.assertEqual(call_args[1]["group_key"], str(self.team.id))
        self.assertIn("plan", call_args[1]["properties"])

    @patch("apps.utils.analytics.posthog")
    def test_group_identify_includes_default_properties(self, mock_posthog):
        """Test that group_identify includes default team properties."""
        group_identify(self.team)

        mock_posthog.group_identify.assert_called_once()
        call_args = mock_posthog.group_identify.call_args
        properties = call_args[1]["properties"]
        self.assertIn("name", properties)
        self.assertEqual(properties["name"], "Test Team")
        self.assertIn("slug", properties)
        self.assertEqual(properties["slug"], "test-team")

    @patch("apps.utils.analytics.posthog")
    def test_group_identify_handles_exception(self, mock_posthog):
        """Test that group_identify does not crash if PostHog raises an exception."""
        mock_posthog.group_identify.side_effect = Exception("PostHog unavailable")

        # Should not raise an exception
        group_identify(self.team)

    def test_group_identify_handles_none_team(self):
        """Test that group_identify handles None team gracefully."""
        # Should not raise an exception
        group_identify(None)


class TestIsFeatureEnabled(TestCase):
    """Tests for is_feature_enabled function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = UserFactory()
        self.team = TeamFactory()

    @patch("apps.utils.analytics.posthog")
    def test_is_feature_enabled_calls_posthog(self, mock_posthog):
        """Test that is_feature_enabled calls posthog.feature_enabled."""
        mock_posthog.feature_enabled.return_value = True

        result = is_feature_enabled("new_dashboard", user=self.user)

        self.assertTrue(result)
        mock_posthog.feature_enabled.assert_called_once()

    @patch("apps.utils.analytics.posthog")
    def test_is_feature_enabled_with_team_context(self, mock_posthog):
        """Test that is_feature_enabled includes team in groups."""
        mock_posthog.feature_enabled.return_value = True

        result = is_feature_enabled("team_feature", user=self.user, team=self.team)

        self.assertTrue(result)
        call_args = mock_posthog.feature_enabled.call_args
        self.assertIn("groups", call_args[1])
        self.assertEqual(call_args[1]["groups"]["team"], str(self.team.id))

    @patch("apps.utils.analytics.posthog")
    def test_is_feature_enabled_returns_false_on_exception(self, mock_posthog):
        """Test that is_feature_enabled returns False if PostHog raises an exception."""
        mock_posthog.feature_enabled.side_effect = Exception("PostHog unavailable")

        result = is_feature_enabled("some_feature", user=self.user)

        self.assertFalse(result)

    def test_is_feature_enabled_returns_false_without_user(self):
        """Test that is_feature_enabled returns False without a user."""
        result = is_feature_enabled("some_feature")

        self.assertFalse(result)

    @override_settings(POSTHOG_API_KEY=None)
    def test_is_feature_enabled_returns_false_when_unconfigured(self):
        """Test that is_feature_enabled returns False when PostHog is not configured."""
        result = is_feature_enabled("some_feature", user=self.user)

        self.assertFalse(result)

    @patch("apps.utils.analytics.posthog")
    def test_is_feature_enabled_with_only_team(self, mock_posthog):
        """Test that is_feature_enabled works with only team (no user)."""
        mock_posthog.feature_enabled.return_value = True

        result = is_feature_enabled("team_only_feature", team=self.team)

        # Should work with team-based identification
        self.assertTrue(result)
