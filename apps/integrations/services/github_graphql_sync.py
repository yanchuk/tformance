"""GitHub GraphQL-based repository history sync service.

Uses GraphQL API to fetch PR history in bulk, significantly reducing API calls
compared to REST (1 call per 50 PRs vs 6-7 calls per PR).

NOTE: This file re-exports all functions from the github_graphql_sync/ subpackage
for backward compatibility. All actual implementations are in domain-focused
modules under apps/integrations/services/github_graphql_sync/.
"""

# Re-export everything from the github_graphql_sync package for backward compatibility
# ruff: noqa: F401 - these imports are re-exports for backward compatibility
from apps.integrations.services.github_graphql_sync import (
    GitHubGraphQLClient,
    MemberSyncResult,
    SyncResult,
    fetch_pr_complete_data_graphql,
    sync_github_members_graphql,
    sync_repository_history_by_search,
    sync_repository_history_graphql,
    sync_repository_incremental_graphql,
)

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
]
