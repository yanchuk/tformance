"""Tests for Copilot activation service.

TDD RED Phase: These tests define the expected behavior of the
activate_copilot_for_team service function.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory


class TestActivateCopilotForTeam(TestCase):
    """Test activate_copilot_for_team service function."""

    def setUp(self):
        self.team = TeamFactory(copilot_status="disabled")

    def test_activate_sets_copilot_status_to_connected(self):
        """Activating Copilot should set team.copilot_status to 'connected'."""
        from apps.integrations.services.copilot_activation import activate_copilot_for_team

        result = activate_copilot_for_team(self.team)

        self.team.refresh_from_db()
        self.assertEqual(self.team.copilot_status, "connected")
        self.assertEqual(result["status"], "activated")

    def test_activate_dispatches_sync_task(self):
        """Activating Copilot should dispatch the sync_copilot_metrics_task."""
        from apps.integrations.services.copilot_activation import activate_copilot_for_team

        with patch("apps.integrations.services.copilot_activation.sync_copilot_metrics_task") as mock_task:
            mock_task.delay.return_value = None

            activate_copilot_for_team(self.team)

            mock_task.delay.assert_called_once_with(self.team.id)

    def test_activate_returns_already_connected_if_already_connected(self):
        """If team already has copilot_status='connected', return early."""
        from apps.integrations.services.copilot_activation import activate_copilot_for_team

        self.team.copilot_status = "connected"
        self.team.save()

        with patch("apps.integrations.services.copilot_activation.sync_copilot_metrics_task") as mock_task:
            result = activate_copilot_for_team(self.team)

            # Should not dispatch sync task again
            mock_task.delay.assert_not_called()
            self.assertEqual(result["status"], "already_connected")

    def test_activate_returns_team_id_in_result(self):
        """Result should include team_id for tracking."""
        from apps.integrations.services.copilot_activation import activate_copilot_for_team

        result = activate_copilot_for_team(self.team)

        self.assertEqual(result["team_id"], self.team.id)

    def test_activate_handles_insufficient_licenses_status(self):
        """If team has insufficient_licenses, still activate and try sync."""
        from apps.integrations.services.copilot_activation import activate_copilot_for_team

        self.team.copilot_status = "insufficient_licenses"
        self.team.save()

        with patch("apps.integrations.services.copilot_activation.sync_copilot_metrics_task") as mock_task:
            mock_task.delay.return_value = None

            result = activate_copilot_for_team(self.team)

            self.team.refresh_from_db()
            self.assertEqual(self.team.copilot_status, "connected")
            mock_task.delay.assert_called_once()
            self.assertEqual(result["status"], "activated")

    def test_activate_handles_token_revoked_status(self):
        """If team has token_revoked, still activate (user re-authorized)."""
        from apps.integrations.services.copilot_activation import activate_copilot_for_team

        self.team.copilot_status = "token_revoked"
        self.team.save()

        with patch("apps.integrations.services.copilot_activation.sync_copilot_metrics_task") as mock_task:
            mock_task.delay.return_value = None

            result = activate_copilot_for_team(self.team)

            self.team.refresh_from_db()
            self.assertEqual(self.team.copilot_status, "connected")
            mock_task.delay.assert_called_once()
            self.assertEqual(result["status"], "activated")


class TestDeactivateCopilotForTeam(TestCase):
    """Test deactivate_copilot_for_team service function."""

    def setUp(self):
        self.team = TeamFactory(copilot_status="connected")

    def test_deactivate_sets_copilot_status_to_disabled(self):
        """Deactivating Copilot should set team.copilot_status to 'disabled'."""
        from apps.integrations.services.copilot_activation import deactivate_copilot_for_team

        result = deactivate_copilot_for_team(self.team)

        self.team.refresh_from_db()
        self.assertEqual(self.team.copilot_status, "disabled")
        self.assertEqual(result["status"], "deactivated")

    def test_deactivate_returns_already_disabled_if_disabled(self):
        """If team already has copilot_status='disabled', return early."""
        from apps.integrations.services.copilot_activation import deactivate_copilot_for_team

        self.team.copilot_status = "disabled"
        self.team.save()

        result = deactivate_copilot_for_team(self.team)

        self.assertEqual(result["status"], "already_disabled")
