"""Tests for Two-Phase Onboarding pipeline tracking fields.

TDD RED Phase: These tests should FAIL until model fields are implemented.

Two-Phase Onboarding:
- Phase 1: Quick Start (30 days) → phase1_complete
- Phase 2: Background (31-90 days) → background_syncing → background_llm → complete
"""

from django.test import TestCase

from apps.metrics.factories import TeamFactory


class TestTwoPhaseStatusChoices(TestCase):
    """Tests for new pipeline status choices in two-phase onboarding."""

    def test_phase1_complete_is_valid_status(self):
        """Test that 'phase1_complete' is a valid pipeline status."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "phase1_complete"
        team.full_clean()  # Should not raise
        team.save()
        team.refresh_from_db()
        self.assertEqual(team.onboarding_pipeline_status, "phase1_complete")

    def test_background_syncing_is_valid_status(self):
        """Test that 'background_syncing' is a valid pipeline status."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "background_syncing"
        team.full_clean()  # Should not raise
        team.save()
        team.refresh_from_db()
        self.assertEqual(team.onboarding_pipeline_status, "background_syncing")

    def test_background_llm_is_valid_status(self):
        """Test that 'background_llm' is a valid pipeline status."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "background_llm"
        team.full_clean()  # Should not raise
        team.save()
        team.refresh_from_db()
        self.assertEqual(team.onboarding_pipeline_status, "background_llm")


class TestBackgroundProgressFields(TestCase):
    """Tests for background sync progress tracking fields."""

    def test_team_has_background_sync_progress_field(self):
        """Test that Team model has background_sync_progress field."""
        team = TeamFactory()
        self.assertTrue(hasattr(team, "background_sync_progress"))

    def test_background_sync_progress_default_is_zero(self):
        """Test that default background_sync_progress is 0."""
        team = TeamFactory()
        self.assertEqual(team.background_sync_progress, 0)

    def test_background_sync_progress_can_be_set(self):
        """Test that background_sync_progress can be set to a percentage."""
        team = TeamFactory()
        team.background_sync_progress = 45
        team.save()
        team.refresh_from_db()
        self.assertEqual(team.background_sync_progress, 45)

    def test_team_has_background_llm_progress_field(self):
        """Test that Team model has background_llm_progress field."""
        team = TeamFactory()
        self.assertTrue(hasattr(team, "background_llm_progress"))

    def test_background_llm_progress_default_is_zero(self):
        """Test that default background_llm_progress is 0."""
        team = TeamFactory()
        self.assertEqual(team.background_llm_progress, 0)

    def test_background_llm_progress_can_be_set(self):
        """Test that background_llm_progress can be set to a percentage."""
        team = TeamFactory()
        team.background_llm_progress = 78
        team.save()
        team.refresh_from_db()
        self.assertEqual(team.background_llm_progress, 78)


class TestPipelineInProgressWithTwoPhase(TestCase):
    """Tests for pipeline_in_progress property with two-phase statuses."""

    def test_phase1_complete_is_not_in_progress(self):
        """Test that phase1_complete status means pipeline is not in progress.

        Phase 1 is complete, user can access dashboard. Phase 2 runs in background.
        """
        team = TeamFactory()
        team.onboarding_pipeline_status = "phase1_complete"
        self.assertFalse(team.pipeline_in_progress)

    def test_background_syncing_is_in_progress(self):
        """Test that background_syncing status means pipeline is in progress."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "background_syncing"
        self.assertTrue(team.pipeline_in_progress)

    def test_background_llm_is_in_progress(self):
        """Test that background_llm status means pipeline is in progress."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "background_llm"
        self.assertTrue(team.pipeline_in_progress)


class TestDashboardAccessProperty(TestCase):
    """Tests for dashboard_accessible property based on pipeline status."""

    def test_team_has_dashboard_accessible_property(self):
        """Test that Team model has dashboard_accessible property."""
        team = TeamFactory()
        self.assertTrue(hasattr(team, "dashboard_accessible"))

    def test_dashboard_accessible_when_complete(self):
        """Test that dashboard is accessible when status is 'complete'."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "complete"
        self.assertTrue(team.dashboard_accessible)

    def test_dashboard_accessible_when_phase1_complete(self):
        """Test that dashboard is accessible after Phase 1 completes."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "phase1_complete"
        self.assertTrue(team.dashboard_accessible)

    def test_dashboard_accessible_during_background_syncing(self):
        """Test that dashboard is accessible during background sync."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "background_syncing"
        self.assertTrue(team.dashboard_accessible)

    def test_dashboard_accessible_during_background_llm(self):
        """Test that dashboard is accessible during background LLM."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "background_llm"
        self.assertTrue(team.dashboard_accessible)

    def test_dashboard_not_accessible_when_syncing(self):
        """Test that dashboard is not accessible during Phase 1 sync."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "syncing"
        self.assertFalse(team.dashboard_accessible)

    def test_dashboard_not_accessible_when_llm_processing(self):
        """Test that dashboard is not accessible during Phase 1 LLM."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "llm_processing"
        self.assertFalse(team.dashboard_accessible)

    def test_dashboard_not_accessible_when_not_started(self):
        """Test that dashboard is not accessible when onboarding not started."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "not_started"
        self.assertFalse(team.dashboard_accessible)


class TestBackgroundInProgressProperty(TestCase):
    """Tests for background_in_progress property."""

    def test_team_has_background_in_progress_property(self):
        """Test that Team model has background_in_progress property."""
        team = TeamFactory()
        self.assertTrue(hasattr(team, "background_in_progress"))

    def test_background_not_in_progress_when_complete(self):
        """Test that background is not in progress when fully complete."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "complete"
        self.assertFalse(team.background_in_progress)

    def test_background_not_in_progress_when_phase1_complete(self):
        """Test that background is not in progress immediately after Phase 1.

        Note: Phase 2 dispatches asynchronously, so there's a brief moment
        where status is phase1_complete before transitioning to background_syncing.
        """
        team = TeamFactory()
        team.onboarding_pipeline_status = "phase1_complete"
        self.assertFalse(team.background_in_progress)

    def test_background_in_progress_during_background_syncing(self):
        """Test that background is in progress during background sync."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "background_syncing"
        self.assertTrue(team.background_in_progress)

    def test_background_in_progress_during_background_llm(self):
        """Test that background is in progress during background LLM."""
        team = TeamFactory()
        team.onboarding_pipeline_status = "background_llm"
        self.assertTrue(team.background_in_progress)


class TestUpdateBackgroundProgress(TestCase):
    """Tests for update_background_progress helper method."""

    def test_update_background_progress_updates_sync_progress(self):
        """Test that update_background_progress updates sync progress."""
        team = TeamFactory()
        team.update_background_progress(sync_progress=50)
        team.refresh_from_db()
        self.assertEqual(team.background_sync_progress, 50)

    def test_update_background_progress_updates_llm_progress(self):
        """Test that update_background_progress updates LLM progress."""
        team = TeamFactory()
        team.update_background_progress(llm_progress=75)
        team.refresh_from_db()
        self.assertEqual(team.background_llm_progress, 75)

    def test_update_background_progress_updates_both(self):
        """Test that update_background_progress can update both at once."""
        team = TeamFactory()
        team.update_background_progress(sync_progress=100, llm_progress=30)
        team.refresh_from_db()
        self.assertEqual(team.background_sync_progress, 100)
        self.assertEqual(team.background_llm_progress, 30)

    def test_update_background_progress_clamps_to_zero(self):
        """Test that negative progress values are clamped to 0."""
        team = TeamFactory()
        team.update_background_progress(sync_progress=-10)
        team.refresh_from_db()
        self.assertEqual(team.background_sync_progress, 0)

    def test_update_background_progress_clamps_to_hundred(self):
        """Test that progress values over 100 are clamped to 100."""
        team = TeamFactory()
        team.update_background_progress(sync_progress=150)
        team.refresh_from_db()
        self.assertEqual(team.background_sync_progress, 100)
