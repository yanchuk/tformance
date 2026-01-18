"""GitHub GraphQL-based repository history sync service.

Uses GraphQL API to fetch PR history in bulk, significantly reducing API calls
compared to REST (1 call per 50 PRs vs 6-7 calls per PR).

This package contains domain-focused modules for GitHub sync:
- history: Full historical sync functions
- incremental: Incremental (since last sync) functions
- pr_data: Single PR data fetch
- members: Organization member sync

All public functions are re-exported here for backward compatibility.
"""

# Re-export public functions for backward compatibility
# ruff: noqa: F401 - these imports are re-exports for backward compatibility
# Re-export GitHubGraphQLClient and exceptions for test mocking compatibility
# Tests mock these at apps.integrations.services.github_graphql_sync.*
from apps.integrations.services.github_graphql import (
    GitHubGraphQLClient,
    GitHubGraphQLError,
    GitHubGraphQLPermissionError,
    GitHubGraphQLRateLimitError,
)

# Re-export utility classes for external use
from ._utils import MemberSyncResult, SyncResult
from .history import sync_repository_history_by_search, sync_repository_history_graphql
from .incremental import sync_repository_incremental_graphql
from .members import sync_github_members_graphql
from .pr_data import fetch_pr_complete_data_graphql

__all__ = [
    # Main sync functions
    "sync_repository_history_graphql",
    "sync_repository_history_by_search",
    "sync_repository_incremental_graphql",
    "fetch_pr_complete_data_graphql",
    "sync_github_members_graphql",
    # Utility classes
    "SyncResult",
    "MemberSyncResult",
    # Re-exported for test mocking compatibility
    "GitHubGraphQLClient",
    "GitHubGraphQLError",
    "GitHubGraphQLPermissionError",
    "GitHubGraphQLRateLimitError",
]
