"""Sync orchestrator for public repos.

Encapsulates backfill/incremental logic, checkpoint management,
and sync state transitions. The Celery task becomes a thin loop.
"""

import logging
import traceback
from datetime import timedelta
from typing import TypedDict

from django.utils import timezone

logger = logging.getLogger(__name__)


class CheckpointPayload(TypedDict, total=False):
    """Schema for checkpoint_payload JSON field."""

    resume_from_date: str  # ISO8601
    prs_fetched_so_far: int
    pages_completed: int


# Backfill PR cap — if fetched count equals this, backfill is incomplete
BACKFILL_PR_CAP = 2000
# Incremental PR cap
INCREMENTAL_PR_CAP = 500
# Gap threshold for missed window recovery
MISSED_WINDOW_DAYS = 30
# Overlap days for incremental sync
OVERLAP_DAYS = 7


class SyncOrchestrator:
    """Orchestrates sync for a single public repo, handling state transitions."""

    def __init__(self, token_pool):
        self.token_pool = token_pool

    def sync_repo(self, repo_profile) -> dict:
        """Sync a single repo, managing state transitions and error handling.

        Returns dict with sync results.
        """
        from apps.public.models import PublicRepoSyncState

        # Ensure sync state exists (pre-migration data safety)
        sync_state, _ = PublicRepoSyncState.objects.get_or_create(
            repo_profile=repo_profile,
        )

        now = timezone.now()
        sync_state.last_attempted_sync_at = now
        sync_state.save(update_fields=["last_attempted_sync_at"])

        try:
            days, max_prs = self._compute_sync_params(repo_profile, sync_state)
            from apps.public.public_sync import sync_public_repo

            result = sync_public_repo(
                repo_profile,
                self.token_pool,
                days=days,
                max_prs=max_prs,
            )
            self._update_sync_state_success(repo_profile, sync_state, result, now)
            return result
        except Exception:
            sync_state.status = "failed"
            sync_state.last_error = traceback.format_exc()
            sync_state.save(update_fields=["status", "last_error"])
            logger.exception("Sync failed for %s", repo_profile.github_repo)
            return {"fetched": 0, "created": 0, "skipped": 0, "errors": 1}

    def _compute_sync_params(self, repo_profile, sync_state) -> tuple[int, int]:
        """Determine days and max_prs based on sync state."""
        now = timezone.now()

        if sync_state.status == "pending_backfill":
            # Check for checkpoint resume
            checkpoint = sync_state.checkpoint_payload or {}
            if "resume_from_date" in checkpoint:
                from datetime import datetime

                resume_date = datetime.fromisoformat(checkpoint["resume_from_date"])
                days_since_resume = (now - resume_date).days
                return days_since_resume, BACKFILL_PR_CAP
            return repo_profile.initial_backfill_days, BACKFILL_PR_CAP

        # status == "ready" or "failed" (retry as incremental)
        if sync_state.last_synced_updated_at:
            gap = (now - sync_state.last_synced_updated_at).days
            if gap > MISSED_WINDOW_DAYS:
                # Missed window → bounded recovery
                return min(gap + OVERLAP_DAYS, repo_profile.initial_backfill_days), BACKFILL_PR_CAP
            return gap + OVERLAP_DAYS, INCREMENTAL_PR_CAP

        # No previous sync data — use default
        return 90, INCREMENTAL_PR_CAP

    def _update_sync_state_success(self, repo_profile, sync_state, result, now):
        """Update sync state after a successful sync."""
        fetched = result.get("fetched", 0)

        if sync_state.status == "pending_backfill":
            if fetched >= BACKFILL_PR_CAP:
                # Cap hit — store checkpoint for resume
                since = now - timedelta(days=repo_profile.initial_backfill_days)
                checkpoint = sync_state.checkpoint_payload or {}
                prs_so_far = checkpoint.get("prs_fetched_so_far", 0) + fetched
                sync_state.checkpoint_payload = CheckpointPayload(
                    resume_from_date=since.isoformat(),
                    prs_fetched_so_far=prs_so_far,
                )
                sync_state.last_attempted_sync_at = now
                sync_state.save(update_fields=["checkpoint_payload", "last_attempted_sync_at"])
            else:
                # Backfill complete
                sync_state.status = "ready"
                sync_state.last_backfill_completed_at = now
                sync_state.last_successful_sync_at = now
                sync_state.last_synced_updated_at = now
                sync_state.checkpoint_payload = {}
                sync_state.last_error = ""
                sync_state.save()
        else:
            # Incremental sync success
            sync_state.status = "ready"
            sync_state.last_successful_sync_at = now
            sync_state.last_synced_updated_at = now
            sync_state.last_error = ""
            sync_state.save(update_fields=["status", "last_successful_sync_at", "last_synced_updated_at", "last_error"])
