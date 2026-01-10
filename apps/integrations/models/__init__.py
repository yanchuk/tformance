"""Integration models package.

This package contains models for external integrations:
- credentials.py: IntegrationCredential (OAuth tokens)
- github.py: GitHubIntegration, GitHubAppInstallation, TrackedRepository
- jira.py: JiraIntegration, TrackedJiraProject
- slack.py: SlackIntegration

All models are re-exported here for backward compatibility.
External imports should use:
    from apps.integrations.models import GitHubIntegration
"""

from .credentials import IntegrationCredential
from .github import GitHubAppInstallation, GitHubIntegration, TrackedRepository
from .jira import JiraIntegration, TrackedJiraProject
from .slack import SlackIntegration

__all__ = [
    "IntegrationCredential",
    "GitHubIntegration",
    "GitHubAppInstallation",
    "TrackedRepository",
    "JiraIntegration",
    "TrackedJiraProject",
    "SlackIntegration",
]
