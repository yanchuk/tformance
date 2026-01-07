"""Tests for cleanup_orphaned_installations management command.

EC-8: Orphaned Installations Without Team
When users abandon the onboarding flow, installations remain in DB with team=None.
This command cleans them up to prevent unique constraint issues on retry.
"""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import GitHubAppInstallationFactory
from apps.integrations.models import GitHubAppInstallation
from apps.metrics.factories import TeamFactory
from apps.teams.context import unset_current_team


class TestCleanupOrphanedInstallationsCommand(TestCase):
    """Tests for the cleanup_orphaned_installations management command."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_cleanup_command_deletes_orphaned_installations(self):
        """Test that orphaned installations older than 24 hours are deleted."""
        # Create an orphaned installation (no team, older than 24 hours)
        old_orphan = GitHubAppInstallationFactory(
            team=None,
            installation_id=11111111,
            account_login="orphaned-org",
        )
        # Manually set created_at to 25 hours ago
        GitHubAppInstallation.objects.filter(pk=old_orphan.pk).update(created_at=timezone.now() - timedelta(hours=25))

        # Create a valid installation with team
        valid_installation = GitHubAppInstallationFactory(
            team=self.team,
            installation_id=22222222,
            account_login="valid-org",
        )

        # Run the command
        out = StringIO()
        call_command("cleanup_orphaned_installations", stdout=out)

        # Verify orphaned installation was deleted
        self.assertFalse(
            GitHubAppInstallation.objects.filter(pk=old_orphan.pk).exists(),
            "Orphaned installation older than 24 hours should be deleted",
        )

        # Verify valid installation was preserved
        self.assertTrue(
            GitHubAppInstallation.objects.filter(pk=valid_installation.pk).exists(),
            "Installation with team should be preserved",
        )

        # Verify output mentions deletion
        output = out.getvalue()
        self.assertIn("1", output)  # Should mention 1 deletion

    def test_cleanup_preserves_recent_installations(self):
        """Test that orphaned installations less than 24 hours old are preserved."""
        # Create a recent orphaned installation (no team, 1 hour ago)
        recent_orphan = GitHubAppInstallationFactory(
            team=None,
            installation_id=33333333,
            account_login="recent-orphan-org",
        )
        # Manually set created_at to 1 hour ago
        GitHubAppInstallation.objects.filter(pk=recent_orphan.pk).update(created_at=timezone.now() - timedelta(hours=1))

        # Run the command
        out = StringIO()
        call_command("cleanup_orphaned_installations", stdout=out)

        # Verify recent orphan was preserved (user might be mid-onboarding)
        self.assertTrue(
            GitHubAppInstallation.objects.filter(pk=recent_orphan.pk).exists(),
            "Recent orphaned installation should be preserved (user might be mid-flow)",
        )

    def test_cleanup_dry_run_shows_without_deleting(self):
        """Test that --dry-run shows what would be deleted without deleting."""
        # Create an orphaned installation (no team, older than 24 hours)
        old_orphan = GitHubAppInstallationFactory(
            team=None,
            installation_id=44444444,
            account_login="dry-run-org",
        )
        GitHubAppInstallation.objects.filter(pk=old_orphan.pk).update(created_at=timezone.now() - timedelta(hours=25))

        # Run the command with --dry-run
        out = StringIO()
        call_command("cleanup_orphaned_installations", "--dry-run", stdout=out)

        # Verify installation was NOT deleted
        self.assertTrue(
            GitHubAppInstallation.objects.filter(pk=old_orphan.pk).exists(),
            "Dry run should not delete installations",
        )

        # Verify output mentions dry run
        output = out.getvalue()
        self.assertIn("dry", output.lower())

    def test_cleanup_handles_no_orphans(self):
        """Test that command handles case when no orphans exist."""
        # Create only a valid installation
        GitHubAppInstallationFactory(
            team=self.team,
            installation_id=55555555,
            account_login="only-valid-org",
        )

        # Run the command
        out = StringIO()
        call_command("cleanup_orphaned_installations", stdout=out)

        # Verify no error and appropriate message
        output = out.getvalue()
        self.assertIn("0", output)  # Should mention 0 deletions

    def test_cleanup_custom_hours_threshold(self):
        """Test that --hours option changes the threshold."""
        # Create an orphaned installation (no team, 12 hours ago)
        medium_orphan = GitHubAppInstallationFactory(
            team=None,
            installation_id=66666666,
            account_login="medium-orphan-org",
        )
        GitHubAppInstallation.objects.filter(pk=medium_orphan.pk).update(
            created_at=timezone.now() - timedelta(hours=12)
        )

        # Run with default (24 hours) - should preserve
        out = StringIO()
        call_command("cleanup_orphaned_installations", stdout=out)
        self.assertTrue(
            GitHubAppInstallation.objects.filter(pk=medium_orphan.pk).exists(),
            "12-hour-old orphan should be preserved with default 24-hour threshold",
        )

        # Run with custom threshold (6 hours) - should delete
        out = StringIO()
        call_command("cleanup_orphaned_installations", "--hours=6", stdout=out)
        self.assertFalse(
            GitHubAppInstallation.objects.filter(pk=medium_orphan.pk).exists(),
            "12-hour-old orphan should be deleted with 6-hour threshold",
        )
