"""Backfill jira_key for existing PullRequests.

This module re-exports the backfill function and serves as the actual migration.
"""

from django.db import migrations

from apps.metrics.migrations._backfill_utils import backfill_jira_key  # noqa: F401


def forward_backfill(apps, schema_editor):
    """Run the backfill function."""
    backfill_jira_key()


def reverse_backfill(apps, schema_editor):
    """Reverse migration - clear jira_key fields that were backfilled.

    Note: This is a no-op because we cannot reliably distinguish between
    backfilled values and manually entered values. The jira_key field
    remains safe to rollback since it's extracted from PR titles.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0011_pullrequest_jira_key'),
    ]

    operations = [
        migrations.RunPython(
            forward_backfill,
            reverse_backfill,
        ),
    ]
