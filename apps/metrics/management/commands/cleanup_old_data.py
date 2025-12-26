"""
Management command to clean up old data for storage optimization.

Supports data retention policies for time-series tables that grow continuously.
Default retention: 365 days for AIUsageDaily, 730 days for WeeklyMetrics.

Usage:
    python manage.py cleanup_old_data --dry-run
    python manage.py cleanup_old_data --days 365
    python manage.py cleanup_old_data --table aiusagedaily --days 180
    python manage.py cleanup_old_data --all
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.metrics.models import AIUsageDaily, WeeklyMetrics

# Default retention periods (in days)
DEFAULT_RETENTION = {
    "aiusagedaily": 365,  # 1 year for daily Copilot/Cursor metrics
    "weeklymetrics": 730,  # 2 years for weekly aggregations
}


class Command(BaseCommand):
    help = "Clean up old data from time-series tables to optimize storage"

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            choices=["aiusagedaily", "weeklymetrics", "all"],
            default="all",
            help="Which table to clean up (default: all)",
        )
        parser.add_argument(
            "--days",
            type=int,
            help="Retention period in days (overrides default)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview deletions without actually deleting",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10000,
            help="Delete in batches to avoid long locks (default: 10000)",
        )

    def handle(self, *args, **options):
        table = options["table"]
        custom_days = options["days"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be deleted\n"))

        tables_to_clean = ["aiusagedaily", "weeklymetrics"] if table == "all" else [table]

        total_deleted = 0

        for tbl in tables_to_clean:
            days = custom_days if custom_days else DEFAULT_RETENTION[tbl]
            deleted = self._cleanup_table(tbl, days, dry_run, batch_size)
            total_deleted += deleted

        # Show summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY RUN: Would delete {total_deleted:,} total rows"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Deleted {total_deleted:,} total rows"))

        # Suggest VACUUM if significant deletions
        if total_deleted > 10000 and not dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "TIP: Run VACUUM ANALYZE to reclaim disk space:\n"
                    "  python manage.py dbshell\n"
                    "  VACUUM ANALYZE metrics_aiusagedaily;\n"
                    "  VACUUM ANALYZE metrics_weeklymetrics;"
                )
            )

    def _cleanup_table(self, table_name: str, days: int, dry_run: bool, batch_size: int) -> int:
        """Clean up a specific table based on retention period."""
        cutoff_date = timezone.now().date() - timedelta(days=days)

        if table_name == "aiusagedaily":
            model = AIUsageDaily
            date_field = "date"
            queryset = model.objects.filter(date__lt=cutoff_date)
        elif table_name == "weeklymetrics":
            model = WeeklyMetrics
            date_field = "week_start"
            queryset = model.objects.filter(week_start__lt=cutoff_date)
        else:
            self.stderr.write(self.style.ERROR(f"Unknown table: {table_name}"))
            return 0

        # Count rows to delete
        count = queryset.count()

        self.stdout.write(
            f"\n{table_name}:\n  Retention: {days} days\n  Cutoff date: {cutoff_date}\n  Rows to delete: {count:,}"
        )

        if count == 0:
            self.stdout.write(self.style.SUCCESS("  No old data to clean up"))
            return 0

        if dry_run:
            # Show sample of what would be deleted
            sample = queryset.order_by(date_field)[:5]
            if sample:
                self.stdout.write("  Sample rows that would be deleted:")
                for row in sample:
                    date_val = getattr(row, date_field)
                    self.stdout.write(f"    - {date_val} (team_id={row.team_id})")
            return count

        # Delete in batches to avoid long table locks
        deleted_total = 0
        while True:
            # Get IDs to delete in this batch
            ids_to_delete = list(queryset.values_list("id", flat=True)[:batch_size])
            if not ids_to_delete:
                break

            # Delete batch
            deleted_count, _ = model.objects.filter(id__in=ids_to_delete).delete()
            deleted_total += deleted_count

            self.stdout.write(f"  Deleted batch: {deleted_count:,} (total: {deleted_total:,})")

        self.stdout.write(self.style.SUCCESS(f"  Completed: {deleted_total:,} rows deleted"))
        return deleted_total
