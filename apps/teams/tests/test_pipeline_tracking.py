"""Tests for Team pipeline tracking fields.

TDD RED Phase: These tests should FAIL until model fields are implemented.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import TeamFactory


class TestTeamPipelineStatusField(TestCase):
    """Tests for Team.onboarding_pipeline_status field."""

    def test_team_has_pipeline_status_field(self):
        """Test that Team model has onboarding_pipeline_status field."""
        team = TeamFactory()
        # Field should exist and be accessible
        status = team.onboarding_pipeline_status
        self.assertIsNotNone(status)

    def test_pipeline_status_default_is_not_started(self):
        """Test that default pipeline status is 'not_started'."""
        team = TeamFactory()
        self.assertEqual(team.onboarding_pipeline_status, "not_started")

    def test_pipeline_status_accepts_valid_choices(self):
        """Test that pipeline status accepts all valid choices."""
        valid_statuses = [
            "not_started",
            "syncing",
            "llm_processing",
            "computing_metrics",
            "computing_insights",
            "complete",
            "failed",
        ]

        for status in valid_statuses:
            team = TeamFactory()
            team.onboarding_pipeline_status = status
            team.full_clean()  # Should not raise
            team.save()
            team.refresh_from_db()
            self.assertEqual(team.onboarding_pipeline_status, status)

    def test_pipeline_status_rejects_invalid_choice(self):
        """Test that pipeline status rejects invalid choices."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "invalid_status"
        with self.assertRaises(ValidationError):
            team.full_clean()


class TestTeamPipelineErrorField(TestCase):
    """Tests for Team.onboarding_pipeline_error field."""

    def test_team_has_pipeline_error_field(self):
        """Test that Team model has onboarding_pipeline_error field."""
        team = TeamFactory()
        # Field should exist and be accessible
        self.assertTrue(hasattr(team, "onboarding_pipeline_error"))

    def test_pipeline_error_default_is_null(self):
        """Test that default pipeline error is None/null."""
        team = TeamFactory()
        self.assertIsNone(team.onboarding_pipeline_error)

    def test_pipeline_error_can_store_error_message(self):
        """Test that pipeline error can store an error message."""
        team = TeamFactory()
        error_message = "Task failed: Connection timeout"
        team.onboarding_pipeline_error = error_message
        team.save()
        team.refresh_from_db()
        self.assertEqual(team.onboarding_pipeline_error, error_message)

    def test_pipeline_error_can_store_long_traceback(self):
        """Test that pipeline error can store a long traceback."""
        team = TeamFactory()
        long_error = "Error:\n" + "x" * 5000  # Long error message
        team.onboarding_pipeline_error = long_error
        team.save()
        team.refresh_from_db()
        self.assertEqual(team.onboarding_pipeline_error, long_error)


class TestTeamPipelineTimestampFields(TestCase):
    """Tests for Team pipeline timestamp fields."""

    def test_team_has_pipeline_started_at_field(self):
        """Test that Team model has onboarding_pipeline_started_at field."""
        team = TeamFactory()
        self.assertTrue(hasattr(team, "onboarding_pipeline_started_at"))

    def test_team_has_pipeline_completed_at_field(self):
        """Test that Team model has onboarding_pipeline_completed_at field."""
        team = TeamFactory()
        self.assertTrue(hasattr(team, "onboarding_pipeline_completed_at"))

    def test_pipeline_started_at_default_is_null(self):
        """Test that default pipeline_started_at is None."""
        team = TeamFactory()
        self.assertIsNone(team.onboarding_pipeline_started_at)

    def test_pipeline_completed_at_default_is_null(self):
        """Test that default pipeline_completed_at is None."""
        team = TeamFactory()
        self.assertIsNone(team.onboarding_pipeline_completed_at)

    def test_pipeline_timestamps_can_be_set(self):
        """Test that pipeline timestamps can be set to datetime values."""
        team = TeamFactory()
        now = timezone.now()

        team.onboarding_pipeline_started_at = now
        team.onboarding_pipeline_completed_at = now
        team.save()
        team.refresh_from_db()

        self.assertEqual(team.onboarding_pipeline_started_at, now)
        self.assertEqual(team.onboarding_pipeline_completed_at, now)


class TestTeamPipelineHelperMethods(TestCase):
    """Tests for Team pipeline helper methods."""

    def test_update_pipeline_status_updates_status(self):
        """Test that update_pipeline_status method updates the status."""
        team = TeamFactory()
        team.update_pipeline_status("syncing")
        team.refresh_from_db()
        self.assertEqual(team.onboarding_pipeline_status, "syncing")

    def test_update_pipeline_status_sets_started_at_on_syncing(self):
        """Test that started_at is set when status changes to syncing."""
        team = TeamFactory()
        team.update_pipeline_status("syncing")
        team.refresh_from_db()
        self.assertIsNotNone(team.onboarding_pipeline_started_at)

    def test_update_pipeline_status_sets_completed_at_on_complete(self):
        """Test that completed_at is set when status changes to complete."""
        team = TeamFactory()
        team.update_pipeline_status("complete")
        team.refresh_from_db()
        self.assertIsNotNone(team.onboarding_pipeline_completed_at)

    def test_update_pipeline_status_sets_completed_at_on_failed(self):
        """Test that completed_at is set when status changes to failed."""
        team = TeamFactory()
        team.update_pipeline_status("failed")
        team.refresh_from_db()
        self.assertIsNotNone(team.onboarding_pipeline_completed_at)

    def test_update_pipeline_status_stores_error(self):
        """Test that update_pipeline_status can store an error message."""
        team = TeamFactory()
        team.update_pipeline_status("failed", error="Connection timeout")
        team.refresh_from_db()
        self.assertEqual(team.onboarding_pipeline_error, "Connection timeout")

    def test_update_pipeline_status_clears_error_on_non_failed_status(self):
        """Test that error is cleared when status is not 'failed'."""
        team = TeamFactory()
        team.onboarding_pipeline_error = "Previous error"
        team.save()

        team.update_pipeline_status("syncing")
        team.refresh_from_db()
        self.assertIsNone(team.onboarding_pipeline_error)

    def test_pipeline_in_progress_property(self):
        """Test that pipeline_in_progress property returns correct value."""
        team = TeamFactory()

        # Not started - not in progress
        team.onboarding_pipeline_status = "not_started"
        self.assertFalse(team.pipeline_in_progress)

        # Syncing - in progress
        team.onboarding_pipeline_status = "syncing"
        self.assertTrue(team.pipeline_in_progress)

        # LLM processing - in progress
        team.onboarding_pipeline_status = "llm_processing"
        self.assertTrue(team.pipeline_in_progress)

        # Complete - not in progress
        team.onboarding_pipeline_status = "complete"
        self.assertFalse(team.pipeline_in_progress)

        # Failed - not in progress
        team.onboarding_pipeline_status = "failed"
        self.assertFalse(team.pipeline_in_progress)
