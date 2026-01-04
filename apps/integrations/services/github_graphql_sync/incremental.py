"""Incremental sync functions for GitHub GraphQL sync.

Contains sync_repository_incremental_graphql for syncing only recently updated PRs.
"""

import logging
from typing import Any

# Import the parent package to enable test mocking at the package level
# Tests mock apps.integrations.services.github_graphql_sync.GitHubGraphQLClient
from ._processors import _process_pr_incremental_async
from ._utils import (
    SyncResult,
    _get_access_token,
    _parse_datetime,
    _update_sync_complete,
    _update_sync_progress,
    _update_sync_status,
)

logger = logging.getLogger(__name__)


async def sync_repository_incremental_graphql(tracked_repo) -> dict[str, Any]:
    """Sync repository PRs updated since last sync using GraphQL API.

    Fetches only PRs that have been updated since the last sync, making it
    much more efficient than full sync for ongoing updates.

    Args:
        tracked_repo: TrackedRepository instance to sync (must have last_sync_at set)

    Returns:
        Dict with sync results:
            - prs_synced: Number of PRs created/updated
            - reviews_synced: Number of reviews created/updated
            - commits_synced: Number of commits created/updated
            - files_synced: Number of files created/updated
            - comments_synced: Number of comments created/updated
            - errors: List of error messages
    """
    result = SyncResult()

    # Get repo info before async operations
    tracked_repo_id = tracked_repo.id
    team_id = tracked_repo.team_id
    full_name = tracked_repo.full_name
    since = tracked_repo.last_sync_at

    # Parse owner/repo from full_name
    try:
        owner, repo = full_name.split("/", 1)
    except ValueError:
        result.errors.append(f"Invalid repository full_name: {full_name}")
        await _update_sync_status(tracked_repo_id, "error")
        return result.to_dict()

    # Get access token from integration (async-safe to avoid SynchronousOnlyOperation)
    access_token = await _get_access_token(tracked_repo_id)
    if not access_token:
        result.errors.append("No access token available for repository")
        await _update_sync_status(tracked_repo_id, "error")
        return result.to_dict()

    # Create GraphQL client
    # Late import to access GitHubGraphQLClient through the package for test mocking
    # Tests mock apps.integrations.services.github_graphql_sync.GitHubGraphQLClient
    from apps.integrations.services import github_graphql_sync as _pkg

    client = _pkg.GitHubGraphQLClient(access_token)

    # Update sync status to syncing
    await _update_sync_status(tracked_repo_id, "syncing")

    try:
        cursor = None
        has_more = True
        prs_processed = 0
        # For incremental sync, we estimate total from first page
        # (totalCount is all PRs in repo, not just updated ones)
        estimated_total = 0

        while has_more:
            # Fetch page of updated PRs
            try:
                response = await client.fetch_prs_updated_since(owner=owner, repo=repo, since=since, cursor=cursor)
            except _pkg.GitHubGraphQLRateLimitError as e:
                result.errors.append(f"Rate limit exceeded: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()
            except _pkg.GitHubGraphQLError as e:
                result.errors.append(f"GraphQL error: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()

            # Extract PR data
            repository_data = response.get("repository", {})
            pull_requests_data = repository_data.get("pullRequests", {})
            pr_nodes = pull_requests_data.get("nodes", [])
            page_info = pull_requests_data.get("pageInfo", {})

            # Estimate total from first page (use page size * remaining pages estimate)
            if estimated_total == 0 and pr_nodes:
                # Rough estimate: if there's more pages, assume 2x current batch
                estimated_total = len(pr_nodes) * (2 if page_info.get("hasNextPage") else 1)
                await _update_sync_progress(tracked_repo_id, 0, estimated_total)

            # Process each PR - filter by updatedAt since PRs are ordered by UPDATED_AT desc
            all_older_than_since = True
            for pr_data in pr_nodes:
                pr_updated_at = _parse_datetime(pr_data.get("updatedAt"))
                if pr_updated_at and since and pr_updated_at < since:
                    # This PR and all subsequent ones are older than since, stop processing
                    continue
                all_older_than_since = False

                try:
                    await _process_pr_incremental_async(team_id, full_name, pr_data, result)
                    prs_processed += 1
                except Exception as e:
                    pr_number = pr_data.get("number", "unknown")
                    error_msg = f"Error processing PR #{pr_number}: {type(e).__name__}: {e}"
                    logger.warning(error_msg)
                    result.errors.append(error_msg)
                    prs_processed += 1  # Count even on error

            # Update progress after each batch
            # Adjust estimated total if we've processed more than expected
            if prs_processed > estimated_total:
                estimated_total = prs_processed + len(pr_nodes)
            await _update_sync_progress(tracked_repo_id, prs_processed, max(estimated_total, prs_processed))

            # Stop if all PRs in this page are older than since
            if all_older_than_since:
                break

            # Check pagination
            has_more = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        # Update sync status to complete (set progress to 100%)
        await _update_sync_progress(tracked_repo_id, prs_processed, prs_processed)
        await _update_sync_complete(tracked_repo_id)

    except Exception as e:
        error_msg = f"Unexpected error during incremental sync: {type(e).__name__}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        await _update_sync_status(tracked_repo_id, "error")

    return result.to_dict()
