"""Utility functions for migrations (prefixed with _ so Django ignores this file)."""

from django.db import transaction

from apps.integrations.services.jira_utils import extract_jira_key
from apps.metrics.models import PullRequest

BATCH_SIZE = 500


def backfill_jira_key():
    """Backfill jira_key for existing PullRequests using batch updates.

    Returns:
        int: Number of PullRequests updated
    """
    updated_count = 0

    with transaction.atomic():
        # Query PRs with empty jira_key in batches
        prs_to_update = []
        for pr in PullRequest.objects.filter(jira_key="").iterator(chunk_size=BATCH_SIZE):
            jira_key = extract_jira_key(pr.title)
            if jira_key:
                pr.jira_key = jira_key
                prs_to_update.append(pr)

            # Batch update when we reach BATCH_SIZE
            if len(prs_to_update) >= BATCH_SIZE:
                PullRequest.objects.bulk_update(prs_to_update, ["jira_key"])
                updated_count += len(prs_to_update)
                prs_to_update = []

        # Update any remaining PRs
        if prs_to_update:
            PullRequest.objects.bulk_update(prs_to_update, ["jira_key"])
            updated_count += len(prs_to_update)

    return updated_count
