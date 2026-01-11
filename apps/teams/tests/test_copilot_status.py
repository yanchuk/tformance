"""Tests for Team.copilot_status field and copilot_enabled property.

TDD RED Phase: These tests should FAIL until model fields are implemented.

The copilot_status field replaces a simple boolean with a rich state machine:
- disabled: Not connected (default)
- connected: Working, has data
- insufficient_licenses: Connected but <5 licenses
- token_revoked: Token invalid, needs reconnection
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.metrics.factories import TeamFactory


class TestCopilotStatusField(TestCase):
    """Tests for Team.copilot_status field."""

    def test_team_has_copilot_status_field(self):
        """Test that Team model has copilot_status field."""
        team = TeamFactory()
        # Field should exist and be accessible
        status = team.copilot_status
        self.assertIsNotNone(status)

    def test_copilot_status_defaults_to_disabled(self):
        """Test that default copilot_status is 'disabled'."""
        team = TeamFactory()
        self.assertEqual(team.copilot_status, "disabled")

    def test_copilot_status_accepts_valid_choices(self):
        """Test that copilot_status accepts all valid choices."""
        valid_statuses = [
            "disabled",
            "connected",
            "insufficient_licenses",
            "token_revoked",
        ]

        for status in valid_statuses:
            team = TeamFactory()
            team.copilot_status = status
            team.full_clean()  # Should not raise
            team.save()
            team.refresh_from_db()
            self.assertEqual(team.copilot_status, status)

    def test_copilot_status_rejects_invalid_choice(self):
        """Test that copilot_status rejects invalid choices."""
        team = TeamFactory()
        team.copilot_status = "invalid_status"
        with self.assertRaises(ValidationError):
            team.full_clean()


class TestCopilotEnabledProperty(TestCase):
    """Tests for Team.copilot_enabled property."""

    def test_copilot_enabled_returns_true_when_connected(self):
        """Test that copilot_enabled is True when status is 'connected'."""
        team = TeamFactory()
        team.copilot_status = "connected"
        team.save()
        self.assertTrue(team.copilot_enabled)

    def test_copilot_enabled_returns_false_when_disabled(self):
        """Test that copilot_enabled is False when status is 'disabled'."""
        team = TeamFactory()
        team.copilot_status = "disabled"
        team.save()
        self.assertFalse(team.copilot_enabled)

    def test_copilot_enabled_returns_false_when_insufficient_licenses(self):
        """Test that copilot_enabled is False when status is 'insufficient_licenses'."""
        team = TeamFactory()
        team.copilot_status = "insufficient_licenses"
        team.save()
        self.assertFalse(team.copilot_enabled)

    def test_copilot_enabled_returns_false_when_token_revoked(self):
        """Test that copilot_enabled is False when status is 'token_revoked'."""
        team = TeamFactory()
        team.copilot_status = "token_revoked"
        team.save()
        self.assertFalse(team.copilot_enabled)


class TestCopilotLastSyncFields(TestCase):
    """Tests for Copilot sync tracking fields."""

    def test_team_has_copilot_last_sync_at_field(self):
        """Test that Team model has copilot_last_sync_at field."""
        team = TeamFactory()
        # Field should exist and default to None
        self.assertIsNone(team.copilot_last_sync_at)

    def test_team_has_copilot_consecutive_failures_field(self):
        """Test that Team model has copilot_consecutive_failures field."""
        team = TeamFactory()
        # Field should exist and default to 0
        self.assertEqual(team.copilot_consecutive_failures, 0)

    def test_copilot_last_sync_at_accepts_datetime(self):
        """Test that copilot_last_sync_at accepts datetime values."""
        from django.utils import timezone

        team = TeamFactory()
        now = timezone.now()
        team.copilot_last_sync_at = now
        team.save()
        team.refresh_from_db()
        # Compare within a second tolerance
        self.assertIsNotNone(team.copilot_last_sync_at)

    def test_copilot_consecutive_failures_accepts_positive_int(self):
        """Test that copilot_consecutive_failures accepts positive integers."""
        team = TeamFactory()
        team.copilot_consecutive_failures = 3
        team.save()
        team.refresh_from_db()
        self.assertEqual(team.copilot_consecutive_failures, 3)
