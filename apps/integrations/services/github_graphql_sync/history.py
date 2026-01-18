"""Full history sync functions for GitHub GraphQL sync.

Contains sync_repository_history_graphql and sync_repository_history_by_search.
"""

import logging
from datetime import timedelta
from typing import Any

from django.utils import timezone

# Import the parent package to enable test mocking at the package level
# Tests mock apps.integrations.services.github_graphql_sync.GitHubGraphQLClient
from apps.integrations.services import github_graphql_sync as _pkg

from ._processors import _process_pr_async, _process_pr_from_search_async
from ._utils import (
    SyncResult,
    _get_access_token,
    _increment_prs_processed,
    _set_prs_total,
    _update_sync_complete,
    _update_sync_progress,
    _update_sync_status,
)

logger = logging.getLogger(__name__)


async def sync_repository_history_graphql(
    tracked_repo,
    days_back: int = 90,
    skip_recent: int = 0,
) -> dict[str, Any]:
    """Sync repository PR history using GraphQL API.

    Fetches all PRs (with reviews, commits, files) in bulk using GraphQL pagination.
    Much faster than REST API for historical sync.

    Supports two-phase onboarding:
    - Phase 1: days_back=30, skip_recent=0 (sync recent 30 days)
    - Phase 2: days_back=90, skip_recent=30 (sync days 31-90, older data)

    Args:
        tracked_repo: TrackedRepository instance to sync
        days_back: Only sync PRs created within this many days (default 90)
        skip_recent: Skip PRs from the most recent N days (default 0)

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

    # Get repo info before async operations (these are cached on the model instance)
    tracked_repo_id = tracked_repo.id
    team_id = tracked_repo.team_id
    full_name = tracked_repo.full_name

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

    # Calculate date filters for two-phase support
    # cutoff_date: PRs older than this are skipped (e.g., 90 days ago)
    # skip_before_date: PRs newer than this are skipped (e.g., 30 days ago for Phase 2)
    now = timezone.now()
    cutoff_date = now - timedelta(days=days_back)
    skip_before_date = now - timedelta(days=skip_recent) if skip_recent > 0 else None

    # Create GraphQL client
    client = _pkg.GitHubGraphQLClient(access_token)

    # Update sync status to syncing
    await _update_sync_status(tracked_repo_id, "syncing")

    try:
        cursor = None
        has_more = True
        prs_processed = 0

        # Get accurate PR count for date range using Search API
        # This fixes the bug where totalCount returns ALL PRs, not just date-filtered ones
        try:
            logger.info(f"[SYNC_DEBUG] Calling get_pr_count_in_date_range for {owner}/{repo} since={cutoff_date}")
            total_prs = await client.get_pr_count_in_date_range(owner=owner, repo=repo, since=cutoff_date, until=None)
            logger.info(f"[SYNC_DEBUG] get_pr_count_in_date_range returned: {total_prs}")
        except _pkg.GitHubGraphQLError as e:
            # Fall back to 0 if search fails - progress will be estimated from first page
            logger.warning(f"[SYNC_DEBUG] Failed to get PR count for date range: {e}")
            total_prs = 0
        except Exception as e:
            # Catch ALL exceptions to see what's happening
            logger.error(f"[SYNC_DEBUG] UNEXPECTED exception in get_pr_count_in_date_range: {type(e).__name__}: {e}")
            total_prs = 0

        # Initialize progress with accurate total count
        if total_prs > 0:
            await _update_sync_progress(tracked_repo_id, 0, total_prs)

        while has_more:
            # Fetch page of PRs
            try:
                response = await client.fetch_prs_bulk(owner=owner, repo=repo, cursor=cursor)
            except _pkg.GitHubGraphQLRateLimitError as e:
                result.errors.append(f"Rate limit exceeded: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()
            except _pkg.GitHubGraphQLPermissionError as e:
                # Permission errors indicate the GitHub App lacks required permissions
                result.errors.append(
                    f"Permission error: The GitHub App may need 'Contents: Read' permission "
                    f"to access commit data for this repository. {e}"
                )
                logger.warning(
                    f"Permission error during sync for {owner}/{repo}: {e}. "
                    "User may need to update GitHub App permissions."
                )
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

            # Fall back to totalCount if get_pr_count_in_date_range failed
            if total_prs == 0:
                total_prs = pull_requests_data.get("totalCount", 0)
                logger.warning(f"[SYNC_DEBUG] FALLBACK to totalCount: {total_prs} (get_pr_count returned 0)")
                # Initialize progress with total count
                await _update_sync_progress(tracked_repo_id, 0, total_prs)

            # Process each PR
            logger.info(f"[SYNC_DEBUG] About to process {len(pr_nodes)} PRs from this page")
            for pr_data in pr_nodes:
                pr_num = pr_data.get("number", "?")
                logger.info(f"[SYNC_DEBUG] CALLING _process_pr_async for PR #{pr_num}")
                try:
                    was_processed = await _process_pr_async(
                        team_id, full_name, pr_data, cutoff_date, skip_before_date, result
                    )
                    logger.info(f"[SYNC_DEBUG] _process_pr_async returned {was_processed} for PR #{pr_num}")
                    if was_processed:
                        prs_processed += 1
                except Exception as e:
                    pr_number = pr_data.get("number", "unknown")
                    error_msg = f"Error processing PR #{pr_number}: {type(e).__name__}: {e}"
                    logger.warning(error_msg)
                    result.errors.append(error_msg)
                    # Don't increment prs_processed on error - PR wasn't successfully synced

            # Update progress after each batch
            await _update_sync_progress(tracked_repo_id, prs_processed, total_prs)

            # Check pagination
            has_more = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        # Update sync status to complete (also sets progress to 100%)
        await _update_sync_progress(tracked_repo_id, total_prs, total_prs)
        await _update_sync_complete(tracked_repo_id)

    except Exception as e:
        error_msg = f"Unexpected error during sync: {type(e).__name__}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        await _update_sync_status(tracked_repo_id, "error")

    return result.to_dict()


async def sync_repository_history_by_search(
    tracked_repo,
    days_back: int = 90,
    skip_recent: int = 0,
) -> dict[str, Any]:
    """Sync repository PR history using GitHub Search API.

    Uses Search API for date-filtered PR fetching, providing accurate progress tracking.
    Unlike `sync_repository_history_graphql`, this function:
    - Gets exact PR count from `issueCount` in search response (no separate count query)
    - Fetches ONLY PRs in the specified date range (no Python filtering)
    - Supports two-phase onboarding with precise date ranges

    Supports two-phase onboarding:
    - Phase 1: days_back=30, skip_recent=0 (sync recent 30 days)
    - Phase 2: days_back=90, skip_recent=30 (sync days 31-90, older data)

    Args:
        tracked_repo: TrackedRepository instance to sync
        days_back: Only sync PRs created within this many days (default 90)
        skip_recent: Skip PRs from the most recent N days (default 0)

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

    # Get repo info before async operations (these are cached on the model instance)
    tracked_repo_id = tracked_repo.id
    team_id = tracked_repo.team_id
    full_name = tracked_repo.full_name

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

    # Calculate date filters for Search API
    now = timezone.now()
    since_date = now - timedelta(days=days_back)

    # For Phase 2: Use date range to exclude recent PRs
    # Phase 1 (skip_recent=0): only `since` is set → query uses `created:>=DATE`
    # Phase 2 (skip_recent=30): both dates set → query uses `created:DATE1..DATE2`
    until_date = now - timedelta(days=skip_recent) if skip_recent > 0 else None

    # Create GraphQL client
    client = _pkg.GitHubGraphQLClient(access_token)

    # Update sync status to syncing
    await _update_sync_status(tracked_repo_id, "syncing")

    try:
        cursor = None
        has_more = True
        prs_processed = 0
        total_prs = 0

        while has_more:
            # Fetch page of PRs using Search API
            try:
                response = await client.search_prs_by_date_range(
                    owner=owner,
                    repo=repo,
                    since=since_date,
                    until=until_date,
                    cursor=cursor,
                )
            except _pkg.GitHubGraphQLRateLimitError as e:
                result.errors.append(f"Rate limit exceeded: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()
            except _pkg.GitHubGraphQLPermissionError as e:
                # Permission errors indicate the GitHub App lacks required permissions
                result.errors.append(
                    f"Permission error: The GitHub App may need 'Contents: Read' permission "
                    f"to access commit data for this repository. {e}"
                )
                logger.warning(
                    f"Permission error during sync for {full_name}: {e}. "
                    "User may need to update GitHub App permissions."
                )
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()
            except _pkg.GitHubGraphQLError as e:
                result.errors.append(f"GraphQL error: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()

            # Extract data from response
            pr_nodes = response.get("prs", [])

            # Set total from issueCount on first page (accurate count for progress!)
            if total_prs == 0:
                total_prs = response.get("issue_count", 0)
                logger.info(f"[SYNC_DEBUG] Search API returned issueCount: {total_prs}")
                # Initialize progress with accurate total count
                await _update_sync_progress(tracked_repo_id, 0, total_prs)
                # Also update TrackedRepository.prs_total
                await _set_prs_total(tracked_repo_id, total_prs)

            # Process each PR - no date filtering needed, Search API handles it
            for pr_data in pr_nodes:
                pr_num = pr_data.get("number", "?")
                logger.info(f"[SYNC_DEBUG] Processing PR #{pr_num} from Search API")
                try:
                    # Process without cutoff_date/skip_before_date - Search API already filtered
                    was_processed = await _process_pr_from_search_async(team_id, full_name, pr_data, result)
                    if was_processed:
                        prs_processed += 1
                        # Update prs_processed on TrackedRepository
                        await _increment_prs_processed(tracked_repo_id)
                except Exception as e:
                    pr_number = pr_data.get("number", "unknown")
                    error_msg = f"Error processing PR #{pr_number}: {type(e).__name__}: {e}"
                    logger.warning(error_msg)
                    result.errors.append(error_msg)

            # Update progress after each batch
            await _update_sync_progress(tracked_repo_id, prs_processed, total_prs)

            # Check pagination
            has_more = response.get("has_next_page", False)
            cursor = response.get("end_cursor")

        # Update sync status to complete (also sets progress to 100%)
        await _update_sync_progress(tracked_repo_id, total_prs, total_prs)
        await _update_sync_complete(tracked_repo_id)

    except Exception as e:
        error_msg = f"Unexpected error during search-based sync: {type(e).__name__}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        await _update_sync_status(tracked_repo_id, "error")

    return result.to_dict()
