"""Tests for signal receivers in integrations app.

TDD RED Phase: Tests for signal receivers that handle onboarding events.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations.factories import TrackedRepositoryFactory
from apps.integrations.signals import (
    onboarding_sync_completed,
    onboarding_sync_started,
    repository_sync_completed,
)
from apps.metrics.factories import TeamFactory


class TestOnboardingSyncStartedReceiver(TestCase):
    """Tests for the onboarding_sync_started signal receiver."""

    def setUp(self):
        self.team = TeamFactory()

    def test_receiver_is_connected(self):
        """Test that a receiver is connected to onboarding_sync_started signal."""
        from apps.integrations import receivers  # noqa: F401

        # Signal should have at least one receiver
        self.assertTrue(len(onboarding_sync_started.receivers) > 0)

    def test_receiver_logs_sync_start(self):
        """Test that receiver logs when sync starts."""
        from apps.integrations import receivers  # noqa: F401

        with self.assertLogs("apps.integrations.receivers", level="INFO") as log:
            onboarding_sync_started.send(
                sender=self.__class__,
                team_id=self.team.id,
                repo_ids=[1, 2, 3],
            )

        # Check that log message was created
        self.assertTrue(
            any("sync started" in msg.lower() for msg in log.output),
            f"Expected 'sync started' in logs, got: {log.output}",
        )


class TestOnboardingSyncCompletedReceiver(TestCase):
    """Tests for the onboarding_sync_completed signal receiver."""

    def setUp(self):
        self.team = TeamFactory()

    def test_receiver_is_connected(self):
        """Test that a receiver is connected to onboarding_sync_completed signal."""
        from apps.integrations import receivers  # noqa: F401

        # Signal should have at least one receiver
        self.assertTrue(len(onboarding_sync_completed.receivers) > 0)

    def test_receiver_logs_sync_completion(self):
        """Test that receiver logs when sync completes."""
        from apps.integrations import receivers  # noqa: F401

        with self.assertLogs("apps.integrations.receivers", level="INFO") as log:
            onboarding_sync_completed.send(
                sender=self.__class__,
                team_id=self.team.id,
                repos_synced=3,
                failed_repos=0,
                total_prs=150,
            )

        # Check that log message contains relevant info
        log_output = " ".join(log.output)
        self.assertIn(str(self.team.id), log_output)

    def test_receiver_tracks_analytics_event(self):
        """Test that receiver sends analytics event on sync completion."""
        from apps.integrations import receivers  # noqa: F401

        with patch("apps.integrations.receivers.track_event") as mock_track:
            onboarding_sync_completed.send(
                sender=self.__class__,
                team_id=self.team.id,
                repos_synced=3,
                failed_repos=0,
                total_prs=150,
            )

            # Verify track_event was called
            mock_track.assert_called_once()
            call_kwargs = mock_track.call_args[1]
            self.assertEqual(call_kwargs.get("event_name"), "onboarding_sync_completed")


class TestRepositorySyncCompletedReceiver(TestCase):
    """Tests for the repository_sync_completed signal receiver."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    def test_receiver_is_connected(self):
        """Test that a receiver is connected to repository_sync_completed signal."""
        from apps.integrations import receivers  # noqa: F401

        # Signal should have at least one receiver
        self.assertTrue(len(repository_sync_completed.receivers) > 0)

    def test_receiver_logs_repo_sync_completion(self):
        """Test that receiver logs when individual repo sync completes."""
        from apps.integrations import receivers  # noqa: F401

        with self.assertLogs("apps.integrations.receivers", level="INFO") as log:
            repository_sync_completed.send(
                sender=self.__class__,
                team_id=self.team.id,
                repo_id=self.repo.id,
                prs_synced=50,
            )

        # Check that log contains repo info
        log_output = " ".join(log.output)
        self.assertIn(str(self.repo.id), log_output)


class TestAppConfigReady(TestCase):
    """Tests for IntegrationsConfig.ready() method."""

    def test_receivers_registered_on_app_ready(self):
        """Test that receivers are registered when app is ready."""
        from django.apps import apps

        # Ensure the integrations app config is loaded
        apps.get_app_config("integrations")

        # Verify ready() was called and receivers are registered
        # After ready(), signals should have receivers
        self.assertTrue(len(onboarding_sync_completed.receivers) > 0)
        self.assertTrue(len(onboarding_sync_started.receivers) > 0)
        self.assertTrue(len(repository_sync_completed.receivers) > 0)


class TestReceiverErrorHandling(TestCase):
    """Tests for error handling in signal receivers."""

    def setUp(self):
        self.team = TeamFactory()

    def test_receiver_handles_invalid_team_id_gracefully(self):
        """Test that receiver doesn't crash with invalid team_id."""
        from apps.integrations import receivers  # noqa: F401

        # Should not raise exception
        try:
            onboarding_sync_completed.send(
                sender=self.__class__,
                team_id=99999,  # Non-existent team
                repos_synced=0,
                failed_repos=0,
                total_prs=0,
            )
        except Exception as e:
            self.fail(f"Receiver raised exception: {e}")

    def test_receiver_handles_missing_kwargs_gracefully(self):
        """Test that receiver handles missing kwargs without crashing."""
        from apps.integrations import receivers  # noqa: F401

        # Should not raise exception (though it may log a warning)
        try:
            onboarding_sync_completed.send(
                sender=self.__class__,
                team_id=self.team.id,
                # Missing: repos_synced, failed_repos, total_prs
            )
        except Exception as e:
            self.fail(f"Receiver raised exception: {e}")
