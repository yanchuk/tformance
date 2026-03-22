"""Initialize PublicRepoSyncState for repos missing one.

Sets status to 'ready' if the repo has existing PublicRepoStats,
'pending_backfill' otherwise. Safe to run multiple times.

Usage:
    python manage.py init_public_repo_sync_state
"""

from django.core.management.base import BaseCommand

from apps.public.models import PublicRepoProfile, PublicRepoSyncState


class Command(BaseCommand):
    help = "Create PublicRepoSyncState for repos that are missing one"

    def handle(self, *args, **options):
        # Find profiles without sync state
        profiles_without_state = PublicRepoProfile.objects.filter(
            sync_state__isnull=True,
        ).select_related("stats")

        created = 0
        for profile in profiles_without_state:
            has_stats = hasattr(profile, "stats")
            status = "ready" if has_stats else "pending_backfill"
            PublicRepoSyncState.objects.create(
                repo_profile=profile,
                status=status,
            )
            created += 1

        self.stdout.write(f"Created {created} sync states")
