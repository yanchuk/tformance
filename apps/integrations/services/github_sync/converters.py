"""Converters for transforming PyGithub objects to standardized dictionaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.integrations.services.jira_utils import extract_jira_key
from apps.integrations.types import PRDict

if TYPE_CHECKING:
    from github.PullRequest import PullRequest as GHPullRequest


def convert_pr_to_dict(pr: GHPullRequest) -> PRDict:
    """Convert PyGithub PullRequest object to dictionary with all required attributes.

    Args:
        pr: PyGithub PullRequest object

    Returns:
        Dictionary with PR data in standardized format
    """
    # Extract jira_key from title, fall back to branch name
    jira_key = extract_jira_key(pr.title) or extract_jira_key(pr.head.ref) or ""

    return {
        "id": pr.id,
        "number": pr.number,
        "title": pr.title,
        "state": pr.state,
        "merged": pr.merged,
        "merged_at": pr.merged_at.isoformat().replace("+00:00", "Z") if pr.merged_at else None,
        "created_at": pr.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": pr.updated_at.isoformat().replace("+00:00", "Z"),
        "additions": pr.additions,
        "deletions": pr.deletions,
        "commits": pr.commits,
        "changed_files": pr.changed_files,
        "user": {
            "id": pr.user.id,
            "login": pr.user.login,
        },
        "base": {
            "ref": pr.base.ref,
        },
        "head": {
            "ref": pr.head.ref,
            "sha": pr.head.sha,
        },
        "html_url": pr.html_url,
        "jira_key": jira_key,
    }
