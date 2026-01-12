"""GitHub sync service module for fetching and syncing data from GitHub repositories.

This module provides functions for:
- Fetching PRs, reviews, and other data from GitHub API
- Syncing GitHub data to the database
- Calculating PR iteration metrics and reviewer correlations

Usage:
    from apps.integrations.services.github_sync import (
        sync_repository_history,
        sync_repository_incremental,
        get_repository_pull_requests,
    )
"""

# Re-export Github for test mocking backward compatibility
from github import Github

from apps.integrations.services.github_oauth import GitHubOAuthError

# Client functions - data fetching from GitHub API
from apps.integrations.services.github_sync.client import (
    get_pull_request_reviews,
    get_repository_pull_requests,
    get_updated_pull_requests,
)

# Converter functions
from apps.integrations.services.github_sync.converters import convert_pr_to_dict

# Metrics calculation functions
from apps.integrations.services.github_sync.metrics import (
    calculate_pr_iteration_metrics,
    calculate_reviewer_correlations,
)

# Processor functions - per-entity sync operations
from apps.integrations.services.github_sync.processors import (
    sync_pr_check_runs,
    sync_pr_commits,
    sync_pr_files,
    sync_pr_issue_comments,
    sync_pr_review_comments,
    sync_pr_reviews,
    sync_repository_deployments,
)

# Sync orchestration functions
from apps.integrations.services.github_sync.sync import (
    _process_prs,
    sync_repository_history,
    sync_repository_incremental,
)

# Backward compatibility: keep old private function name accessible
_convert_pr_to_dict = convert_pr_to_dict
_sync_pr_reviews = sync_pr_reviews

__all__ = [
    # PyGithub classes (for test mocking backward compatibility)
    "Github",
    # Exceptions
    "GitHubOAuthError",
    # Client functions
    "get_repository_pull_requests",
    "get_pull_request_reviews",
    "get_updated_pull_requests",
    # Converters
    "convert_pr_to_dict",
    "_convert_pr_to_dict",  # Backward compatibility
    # Sync orchestration
    "_process_prs",  # Internal but needed for tests
    "sync_repository_history",
    "sync_repository_incremental",
    # Processors
    "sync_pr_commits",
    "sync_pr_check_runs",
    "sync_pr_files",
    "sync_repository_deployments",
    "sync_pr_issue_comments",
    "sync_pr_review_comments",
    "sync_pr_reviews",
    "_sync_pr_reviews",  # Backward compatibility
    # Metrics
    "calculate_pr_iteration_metrics",
    "calculate_reviewer_correlations",
]
