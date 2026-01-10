"""Type definitions for integration services.

This module provides TypedDict definitions for data structures used in
GitHub, Jira, and other integration services.

Usage:
    from apps.integrations.types import PRDict, SyncResult, GitHubUserInfo

    def _convert_pr_to_dict(pr: PullRequest) -> PRDict:
        ...
"""

from __future__ import annotations

from typing import TypedDict


# =============================================================================
# GitHub User Types
# =============================================================================
class GitHubUserInfo(TypedDict):
    """Basic GitHub user information.

    Attributes:
        id: GitHub user ID
        login: GitHub username
    """

    id: int
    login: str


class GitHubBranchInfo(TypedDict):
    """GitHub branch reference information.

    Attributes:
        ref: Branch name
        sha: Optional commit SHA (present for head, not for base)
    """

    ref: str


class GitHubHeadInfo(TypedDict):
    """GitHub PR head branch information.

    Attributes:
        ref: Branch name
        sha: Commit SHA
    """

    ref: str
    sha: str


# =============================================================================
# Pull Request Types
# =============================================================================
class PRDict(TypedDict):
    """Standardized PR data dictionary from _convert_pr_to_dict.

    This is the format returned by GitHub sync functions and used
    throughout the codebase for PR processing.

    Attributes:
        id: GitHub PR ID
        number: PR number in the repository
        title: PR title
        state: PR state (open, closed)
        merged: Whether the PR was merged
        merged_at: ISO format merge timestamp or None
        created_at: ISO format creation timestamp
        updated_at: ISO format last update timestamp
        additions: Lines added
        deletions: Lines deleted
        commits: Number of commits
        changed_files: Number of files changed
        user: Author information
        base: Base branch information
        head: Head branch information
        html_url: GitHub URL for the PR
        jira_key: Extracted Jira issue key or empty string
    """

    id: int
    number: int
    title: str
    state: str
    merged: bool
    merged_at: str | None
    created_at: str
    updated_at: str
    additions: int
    deletions: int
    commits: int
    changed_files: int
    user: GitHubUserInfo
    base: GitHubBranchInfo
    head: GitHubHeadInfo
    html_url: str
    jira_key: str


# =============================================================================
# Review Types
# =============================================================================
class ReviewDict(TypedDict):
    """GitHub PR review data.

    Attributes:
        id: Review ID
        user: Reviewer information
        state: Review state (APPROVED, CHANGES_REQUESTED, etc.)
        submitted_at: ISO format submission timestamp
        body: Review body text
    """

    id: int
    user: GitHubUserInfo
    state: str
    submitted_at: str | None
    body: str | None


# =============================================================================
# Sync Result Types
# =============================================================================
class SyncResult(TypedDict, total=False):
    """Result of a repository sync operation.

    Returned by sync_repository_history and sync_repository_incremental.

    Attributes:
        prs_created: Number of new PRs created
        prs_updated: Number of existing PRs updated
        reviews_synced: Number of reviews synced
        commits_synced: Number of commits synced
        check_runs_synced: Number of check runs synced
        files_synced: Number of files synced
        comments_synced: Number of comments synced
        deployments_synced: Number of deployments synced
        errors: List of error messages encountered
    """

    prs_created: int
    prs_updated: int
    reviews_synced: int
    commits_synced: int
    check_runs_synced: int
    files_synced: int
    comments_synced: int
    deployments_synced: int
    errors: list[str]


class PRSyncResult(TypedDict):
    """Result of syncing a single PR's related data.

    Attributes:
        reviews: Number of reviews synced
        commits: Number of commits synced
        check_runs: Number of check runs synced
        files: Number of files synced
        comments: Number of comments synced
    """

    reviews: int
    commits: int
    check_runs: int
    files: int
    comments: int
