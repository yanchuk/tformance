"""
Integration views - split into provider-specific modules.

All views are re-exported here for backward compatibility.
Import as: from apps.integrations.views import github_connect

Module Structure:
- helpers.py: Helper functions for OAuth and webhooks
- status.py: integrations_home, copilot_sync
- github.py: GitHub OAuth and management views
- jira.py: Jira OAuth and project management views
- slack.py: Slack OAuth and settings views
"""

# Status views
# GitHub views
from .github import (
    github_connect,
    github_disconnect,
    github_member_toggle,
    github_members,
    github_members_sync,
    github_members_sync_progress,
    github_repo_sync,
    github_repo_sync_progress,
    github_repo_toggle,
    github_repos,
    github_select_org,
)

# Jira views
from .jira import (
    jira_callback,
    jira_connect,
    jira_disconnect,
    jira_project_toggle,
    jira_projects_list,
    jira_select_site,
)

# Slack views
from .slack import (
    slack_callback,
    slack_connect,
    slack_disconnect,
    slack_settings,
)
from .status import (
    activate_copilot,
    copilot_sync,
    deactivate_copilot,
    integrations_home,
    track_integration_interest,
)

__all__ = [
    # Status
    "integrations_home",
    "activate_copilot",
    "deactivate_copilot",
    "copilot_sync",
    "track_integration_interest",
    # GitHub
    "github_connect",
    "github_disconnect",
    "github_select_org",
    "github_members",
    "github_members_sync",
    "github_members_sync_progress",
    "github_member_toggle",
    "github_repos",
    "github_repo_toggle",
    "github_repo_sync",
    "github_repo_sync_progress",
    # Jira
    "jira_connect",
    "jira_callback",
    "jira_disconnect",
    "jira_select_site",
    "jira_projects_list",
    "jira_project_toggle",
    # Slack
    "slack_connect",
    "slack_callback",
    "slack_disconnect",
    "slack_settings",
]
