"""Shared constants for integration models and tasks."""

# Sync status constants used by GitHubIntegration and TrackedRepository
SYNC_STATUS_PENDING = "pending"
SYNC_STATUS_SYNCING = "syncing"
SYNC_STATUS_COMPLETE = "complete"
SYNC_STATUS_ERROR = "error"

SYNC_STATUS_CHOICES = [
    (SYNC_STATUS_PENDING, "Pending"),
    (SYNC_STATUS_SYNCING, "Syncing"),
    (SYNC_STATUS_COMPLETE, "Complete"),
    (SYNC_STATUS_ERROR, "Error"),
]
