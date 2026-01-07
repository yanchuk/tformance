"""Tests for TeamMember Copilot fields.

These fields track per-user Copilot activity synced from the GitHub Copilot Seats API.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import TeamFactory, TeamMemberFactory


class TestTeamMemberCopilotFields(TestCase):
    """Tests for Copilot-related fields on the TeamMember model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test fixtures using factories."""
        cls.team = TeamFactory()

    def test_team_member_has_copilot_last_activity_at_field(self):
        """Test that TeamMember has copilot_last_activity_at DateTimeField."""
        activity_time = timezone.now() - timedelta(days=1)
        member = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=activity_time,
        )

        member.refresh_from_db()
        self.assertEqual(member.copilot_last_activity_at, activity_time)

    def test_team_member_has_copilot_last_editor_field(self):
        """Test that TeamMember has copilot_last_editor CharField."""
        member = TeamMemberFactory(
            team=self.team,
            copilot_last_editor="vscode/1.85.1",
        )

        member.refresh_from_db()
        self.assertEqual(member.copilot_last_editor, "vscode/1.85.1")

    def test_copilot_fields_are_nullable(self):
        """Test that Copilot fields can be null (no data synced yet)."""
        member = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
            copilot_last_editor=None,
        )

        member.refresh_from_db()
        self.assertIsNone(member.copilot_last_activity_at)
        self.assertIsNone(member.copilot_last_editor)

    def test_copilot_fields_can_be_updated(self):
        """Test that Copilot fields can be updated with new values."""
        initial_activity = timezone.now() - timedelta(days=5)
        member = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=initial_activity,
            copilot_last_editor="vscode/1.84.0",
        )

        # Update with new values
        new_activity_time = timezone.now()
        member.copilot_last_activity_at = new_activity_time
        member.copilot_last_editor = "jetbrains-rider/2024.1"
        member.save()

        member.refresh_from_db()
        self.assertEqual(member.copilot_last_activity_at, new_activity_time)
        self.assertEqual(member.copilot_last_editor, "jetbrains-rider/2024.1")


class TestTeamMemberCopilotActivityProperty(TestCase):
    """Tests for the has_recent_copilot_activity property."""

    @classmethod
    def setUpTestData(cls):
        """Set up test fixtures using factories."""
        cls.team = TeamFactory()

    def test_has_recent_copilot_activity_property(self):
        """Test that has_recent_copilot_activity returns True if activity within 30 days."""
        recent_activity = timezone.now() - timedelta(days=15)
        member = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=recent_activity,
        )

        self.assertTrue(member.has_recent_copilot_activity)

    def test_has_recent_copilot_activity_false_when_no_activity(self):
        """Test that has_recent_copilot_activity returns False when last_activity_at is None."""
        member = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        self.assertFalse(member.has_recent_copilot_activity)

    def test_has_recent_copilot_activity_false_when_old(self):
        """Test that has_recent_copilot_activity returns False when activity > 30 days ago."""
        old_activity = timezone.now() - timedelta(days=45)
        member = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=old_activity,
        )

        self.assertFalse(member.has_recent_copilot_activity)
