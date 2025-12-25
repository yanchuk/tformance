"""Django signals for integrations app.

Provides extensibility points for onboarding sync events.
"""

from django.dispatch import Signal

# Signal sent when onboarding sync starts for a team
# Arguments: team_id, repo_ids
onboarding_sync_started = Signal()

# Signal sent when onboarding sync completes for a team
# Arguments: team_id, repos_synced, total_prs, failed_repos
onboarding_sync_completed = Signal()

# Signal sent when a single repository sync completes
# Arguments: team_id, repo_id, prs_synced
repository_sync_completed = Signal()
