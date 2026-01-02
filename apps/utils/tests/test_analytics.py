"""Tests for PostHog analytics wrapper functions.

These tests verify the analytics module provides a safe wrapper around PostHog SDK
that handles errors gracefully and provides consistent behavior when PostHog is
unavailable or unconfigured.
"""

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory

from ..analytics import (
    group_identify,
    identify_user,
    is_feature_enabled,
    track_event,
    update_team_properties,
    update_user_properties,
)


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


class TestUpdateUserProperties(TestCase):
    """Tests for update_user_properties helper function.

    update_user_properties is a lightweight alternative to identify_user that
    only updates specific properties without re-sending the full user profile.
    """

    def setUp(self):
        self.user = UserFactory()

    @patch("apps.utils.analytics.posthog")
    def test_update_user_properties_calls_identify(self, mock_posthog):
        """update_user_properties should call posthog.identify with only the given properties."""
        update_user_properties(
            self.user,
            {"role": "admin", "teams_count": 3},
        )

        mock_posthog.identify.assert_called_once()
        call_args = mock_posthog.identify.call_args
        self.assertEqual(call_args[1]["distinct_id"], str(self.user.id))
        self.assertEqual(call_args[1]["properties"]["role"], "admin")
        self.assertEqual(call_args[1]["properties"]["teams_count"], 3)

    @patch("apps.utils.analytics.posthog")
    def test_update_user_properties_with_integration_flags(self, mock_posthog):
        """update_user_properties should handle has_connected_* flags."""
        update_user_properties(
            self.user,
            {
                "has_connected_github": True,
                "has_connected_jira": False,
                "has_connected_slack": True,
            },
        )

        mock_posthog.identify.assert_called_once()
        props = mock_posthog.identify.call_args[1]["properties"]
        self.assertTrue(props["has_connected_github"])
        self.assertFalse(props["has_connected_jira"])
        self.assertTrue(props["has_connected_slack"])

    @patch("apps.utils.analytics.posthog")
    def test_update_user_properties_does_not_auto_add_defaults(self, mock_posthog):
        """update_user_properties should NOT auto-add email/name like identify_user does."""
        update_user_properties(self.user, {"custom_prop": "value"})

        props = mock_posthog.identify.call_args[1]["properties"]
        # Should only have the custom prop, not auto-added email
        self.assertEqual(props, {"custom_prop": "value"})
        self.assertNotIn("email", props)

    @override_settings(POSTHOG_API_KEY=None)
    @patch("apps.utils.analytics.posthog")
    def test_update_user_properties_noop_when_not_configured(self, mock_posthog):
        """update_user_properties should not call PostHog when not configured."""
        update_user_properties(self.user, {"prop": "value"})

        mock_posthog.identify.assert_not_called()

    @patch("apps.utils.analytics.posthog")
    def test_update_user_properties_handles_none_user(self, mock_posthog):
        """update_user_properties should handle None user gracefully."""
        update_user_properties(None, {"prop": "value"})

        mock_posthog.identify.assert_not_called()

    @patch("apps.utils.analytics.posthog")
    def test_update_user_properties_handles_exception(self, mock_posthog):
        """update_user_properties should handle PostHog exceptions gracefully."""
        mock_posthog.identify.side_effect = Exception("PostHog error")

        # Should not raise
        update_user_properties(self.user, {"prop": "value"})


class TestUpdateTeamProperties(TestCase):
    """Tests for update_team_properties helper function.

    update_team_properties is a lightweight alternative to group_identify that
    only updates specific properties without re-sending the full team profile.
    """

    def setUp(self):
        self.team = TeamFactory()

    @patch("apps.utils.analytics.posthog")
    def test_update_team_properties_calls_group_identify(self, mock_posthog):
        """update_team_properties should call posthog.group_identify."""
        update_team_properties(
            self.team,
            {"plan": "pro", "repos_tracked": 5},
        )

        mock_posthog.group_identify.assert_called_once()
        call_args = mock_posthog.group_identify.call_args
        self.assertEqual(call_args[1]["group_type"], "team")
        self.assertEqual(call_args[1]["group_key"], str(self.team.id))
        self.assertEqual(call_args[1]["properties"]["plan"], "pro")
        self.assertEqual(call_args[1]["properties"]["repos_tracked"], 5)

    @patch("apps.utils.analytics.posthog")
    def test_update_team_properties_with_metrics(self, mock_posthog):
        """update_team_properties should handle metric properties."""
        update_team_properties(
            self.team,
            {
                "total_prs": 150,
                "ai_adoption_rate": 0.42,
                "member_count": 8,
            },
        )

        mock_posthog.group_identify.assert_called_once()
        props = mock_posthog.group_identify.call_args[1]["properties"]
        self.assertEqual(props["total_prs"], 150)
        self.assertEqual(props["ai_adoption_rate"], 0.42)
        self.assertEqual(props["member_count"], 8)

    @patch("apps.utils.analytics.posthog")
    def test_update_team_properties_does_not_auto_add_defaults(self, mock_posthog):
        """update_team_properties should NOT auto-add name/slug like group_identify does."""
        update_team_properties(self.team, {"custom_prop": "value"})

        props = mock_posthog.group_identify.call_args[1]["properties"]
        # Should only have the custom prop, not auto-added name/slug
        self.assertEqual(props, {"custom_prop": "value"})
        self.assertNotIn("name", props)
        self.assertNotIn("slug", props)

    @override_settings(POSTHOG_API_KEY=None)
    @patch("apps.utils.analytics.posthog")
    def test_update_team_properties_noop_when_not_configured(self, mock_posthog):
        """update_team_properties should not call PostHog when not configured."""
        update_team_properties(self.team, {"prop": "value"})

        mock_posthog.group_identify.assert_not_called()

    @patch("apps.utils.analytics.posthog")
    def test_update_team_properties_handles_none_team(self, mock_posthog):
        """update_team_properties should handle None team gracefully."""
        update_team_properties(None, {"prop": "value"})

        mock_posthog.group_identify.assert_not_called()

    @patch("apps.utils.analytics.posthog")
    def test_update_team_properties_handles_exception(self, mock_posthog):
        """update_team_properties should handle PostHog exceptions gracefully."""
        mock_posthog.group_identify.side_effect = Exception("PostHog error")

        # Should not raise
        update_team_properties(self.team, {"prop": "value"})
