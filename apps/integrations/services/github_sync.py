"""GitHub sync service for fetching data from GitHub repositories.

This module is a facade that re-exports from the github_sync/ package.
All functionality has been modularized into separate files for better maintainability:

- github_sync/client.py - GitHub API client functions
- github_sync/converters.py - Data conversion utilities
- github_sync/processors.py - Per-entity sync operations
- github_sync/metrics.py - Metrics calculation functions
- github_sync/sync.py - Sync orchestration

Usage remains unchanged:
    from apps.integrations.services.github_sync import (
        sync_repository_history,
        sync_repository_incremental,
        get_repository_pull_requests,
    )
"""

# Re-export everything from the github_sync package for backward compatibility
from apps.integrations.services.github_sync import (
    Github,
    GitHubOAuthError,
    _convert_pr_to_dict,
    _process_prs,
    _sync_pr_reviews,
    calculate_pr_iteration_metrics,
    calculate_reviewer_correlations,
    convert_pr_to_dict,
    get_pull_request_reviews,
    get_repository_pull_requests,
    get_updated_pull_requests,
    sync_pr_check_runs,
    sync_pr_commits,
    sync_pr_files,
    sync_pr_issue_comments,
    sync_pr_review_comments,
    sync_pr_reviews,
    sync_repository_deployments,
    sync_repository_history,
    sync_repository_incremental,
)

__all__ = [
    # PyGithub classes (for test mocking backward compatibility)
    "Github",
    # Exceptions
    "GitHubOAuthError",
    # Client functions
    "get_repository_pull_requests",
    "get_pull_request_reviews",
    "get_updated_pull_requests",
    # Sync orchestration
    "_process_prs",
    "sync_repository_history",
    "sync_repository_incremental",
    # Processors
    "sync_pr_commits",
    "sync_pr_check_runs",
    "sync_pr_files",
    "sync_repository_deployments",
    "sync_pr_issue_comments",
    "sync_pr_review_comments",
    # Backward compatibility
    "_convert_pr_to_dict",
    "convert_pr_to_dict",
    "_sync_pr_reviews",
    "sync_pr_reviews",
    "calculate_pr_iteration_metrics",
    "calculate_reviewer_correlations",
]
