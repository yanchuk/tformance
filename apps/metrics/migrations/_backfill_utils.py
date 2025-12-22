"""Utility functions for migrations (prefixed with _ so Django ignores this file)."""

import re

from django.db import connection

BATCH_SIZE = 500

# Same regex as in apps.integrations.services.jira_utils
JIRA_KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9]+-\d+")


def extract_jira_key(title: str) -> str | None:
    """Extract JIRA key from PR title.

    Duplicated from jira_utils to avoid model imports in migrations.
    Uses re.search to find key anywhere in text (not just at start).
    """
    if not title:
        return None
    match = JIRA_KEY_PATTERN.search(title)
    return match.group(0) if match else None


def backfill_jira_key():
    """Backfill jira_key for existing PullRequests using raw SQL.

    Uses raw SQL to avoid model imports that cause column mismatch during migrations.

    Returns:
        int: Number of PullRequests updated
    """
    updated_count = 0

    with connection.cursor() as cursor:
        # Get PRs with empty jira_key - only select id and title to avoid column issues
        cursor.execute("SELECT id, title FROM metrics_pullrequest WHERE jira_key = '' OR jira_key IS NULL")
        rows = cursor.fetchall()

        # Process in batches
        updates = []
        for pr_id, title in rows:
            jira_key = extract_jira_key(title)
            if jira_key:
                updates.append((jira_key, pr_id))

            # Batch update when we reach BATCH_SIZE
            if len(updates) >= BATCH_SIZE:
                cursor.executemany("UPDATE metrics_pullrequest SET jira_key = %s WHERE id = %s", updates)
                updated_count += len(updates)
                updates = []

        # Update any remaining PRs
        if updates:
            cursor.executemany("UPDATE metrics_pullrequest SET jira_key = %s WHERE id = %s", updates)
            updated_count += len(updates)

    return updated_count
