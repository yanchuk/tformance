"""Single PR data fetch functions for GitHub GraphQL sync.

Contains fetch_pr_complete_data_graphql for fetching complete data for a single PR.
"""

import logging
from typing import Any

# Import the parent package to enable test mocking at the package level
# Tests mock apps.integrations.services.github_graphql_sync.GitHubGraphQLClient
from ._processors import _process_pr_nested_data_async
from ._utils import SyncResult, _get_access_token

logger = logging.getLogger(__name__)


async def fetch_pr_complete_data_graphql(pr, tracked_repo) -> dict[str, Any]:
    """Fetch and sync complete PR data using GraphQL API.

    Fetches a single PR with its commits, files, and reviews via GraphQL.
    This is more efficient than REST for getting PR nested data.

    Note: Does not fetch check_runs or comments (use REST for those).

    Args:
        pr: PullRequest model instance
        tracked_repo: TrackedRepository model instance

    Returns:
        dict: Sync counts with keys commits_synced, files_synced, reviews_synced, errors
    """
    result = SyncResult()

    # Get info from model instance (cached, doesn't trigger DB query)
    tracked_repo_id = tracked_repo.id
    full_name = tracked_repo.full_name
    team_id = tracked_repo.team_id

    # Parse repo owner and name from full_name
    owner, repo = full_name.split("/")

    # Get access token (async-safe to avoid SynchronousOnlyOperation)
    access_token = await _get_access_token(tracked_repo_id)
    if not access_token:
        result.errors.append("No access token available for repository")
        return result.to_dict()

    # Late import to access GitHubGraphQLClient through the package for test mocking
    # Tests mock apps.integrations.services.github_graphql_sync.GitHubGraphQLClient
    from apps.integrations.services import github_graphql_sync as _pkg

    try:
        # Initialize GraphQL client and fetch PR data
        client = _pkg.GitHubGraphQLClient(access_token)
        response = await client.fetch_single_pr(owner, repo, pr.github_pr_id)

        # Extract PR data from response
        pr_data = response.get("repository", {}).get("pullRequest")

        if not pr_data:
            error_msg = f"PR #{pr.github_pr_id} not found in GraphQL response"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            return result.to_dict()

        # Process nested data (commits, files, reviews)
        await _process_pr_nested_data_async(team_id, pr, full_name, pr_data, result)

    except _pkg.GitHubGraphQLRateLimitError as e:
        error_msg = f"Rate limit error fetching PR #{pr.github_pr_id}: {e}"
        logger.warning(error_msg)
        result.errors.append(error_msg)

    except _pkg.GitHubGraphQLError as e:
        error_msg = f"GraphQL error fetching PR #{pr.github_pr_id}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)

    except Exception as e:
        error_msg = f"Unexpected error fetching PR #{pr.github_pr_id}: {type(e).__name__}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)

    return result.to_dict()
