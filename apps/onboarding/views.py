"""Re-exports for onboarding views.

This file provides backward compatibility for imports from apps.onboarding.views.
All view functions are now defined in the views/ package.
"""

# ruff: noqa: F401 - these imports are re-exports for backward compatibility
from apps.onboarding.views import (
    _create_team_from_org,
    connect_jira,
    connect_slack,
    fetch_repos,
    github_app_callback,
    github_app_install,
    github_connect,
    jira_sync_status,
    onboarding_complete,
    onboarding_start,
    select_jira_projects,
    select_organization,
    select_repositories,
    skip_onboarding,
    start_sync,
    sync_progress,
    sync_status,
)
