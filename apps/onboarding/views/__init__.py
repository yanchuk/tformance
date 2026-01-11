"""Views for the onboarding wizard.

Users without a team are directed here after signup to:
1. Connect their GitHub account
2. Select their organization (which creates the team)
3. Select repositories to track
4. Optionally connect Jira and Slack

This package contains domain-focused view modules:
- start: Initial start page, skip functionality, and completion
- github: GitHub OAuth, organization/repository selection, sync progress
- jira: Jira OAuth and project selection
- slack: Slack OAuth and configuration

All public views are re-exported here for backward compatibility.
"""

# ruff: noqa: F401 - these imports are re-exports for backward compatibility
# Re-export external dependencies used by tests that patch at apps.onboarding.views.*
from apps.integrations.onboarding_pipeline import start_onboarding_pipeline
from apps.integrations.services import github_oauth

from .copilot import connect_copilot
from .github import (
    _create_team_from_org,
    fetch_repos,
    github_app_callback,
    github_app_install,
    github_connect,
    select_organization,
    select_repositories,
    start_sync,
    sync_progress,
    sync_status,
)
from .jira import (
    connect_jira,
    jira_sync_status,
    select_jira_projects,
)
from .slack import connect_slack
from .start import (
    onboarding_complete,
    onboarding_start,
    skip_onboarding,
)

__all__ = [
    # Start/completion views
    "onboarding_start",
    "skip_onboarding",
    "onboarding_complete",
    # GitHub views
    "github_connect",
    "github_app_install",
    "github_app_callback",
    "select_organization",
    "_create_team_from_org",
    "select_repositories",
    "fetch_repos",
    "sync_progress",
    "start_sync",
    "sync_status",
    # Jira views
    "connect_jira",
    "select_jira_projects",
    "jira_sync_status",
    # Slack views
    "connect_slack",
    # Copilot views
    "connect_copilot",
]
