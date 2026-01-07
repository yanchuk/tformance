"""Management command to cleanup orphaned GitHub App installations.

EC-8: Orphaned Installations Without Team
When users abandon the onboarding flow, installations remain in DB with team=None.
This command cleans them up to prevent unique constraint issues on retry.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.integrations.models import GitHubAppInstallation


class Command(BaseCommand):
    help = "Cleanup orphaned GitHub App installations (no team, older than threshold)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Delete orphans older than this many hours (default: 24)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        hours = options["hours"]
        threshold = timezone.now() - timedelta(hours=hours)

        # Find orphaned installations (no team, older than threshold)
        orphans = GitHubAppInstallation.objects.filter(
            team__isnull=True,
            created_at__lt=threshold,
        )

        count = orphans.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would delete {count} orphaned installations:"))
            for orphan in orphans:
                self.stdout.write(
                    f"  - {orphan.account_login} (ID: {orphan.installation_id}, created: {orphan.created_at})"
                )
        else:
            # Actually delete
            orphans.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {count} orphaned installations older than {hours} hours"))
