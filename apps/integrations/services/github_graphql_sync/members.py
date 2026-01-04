"""Organization member sync functions for GitHub GraphQL sync.

Contains sync_github_members_graphql for syncing GitHub organization members.
"""

import logging
from typing import Any

# Import the parent package to enable test mocking at the package level
# Tests mock apps.integrations.services.github_graphql_sync.GitHubGraphQLClient
from ._processors import _process_member_async
from ._utils import MemberSyncResult, _get_integration_access_token

logger = logging.getLogger(__name__)


async def sync_github_members_graphql(integration, org_name: str) -> dict[str, Any]:
    """Sync organization members using GraphQL API.

    Fetches all members of a GitHub organization and creates/updates TeamMember records.
    More efficient than REST for fetching member lists.

    Args:
        integration: GitHubIntegration instance
        org_name: GitHub organization name

    Returns:
        dict: Sync counts with keys members_synced, members_created, members_updated, errors
    """
    result = MemberSyncResult()

    # Get info from model instance (cached, doesn't trigger DB query)
    integration_id = integration.id
    team_id = integration.team_id

    # Get access token (async-safe to avoid SynchronousOnlyOperation)
    access_token = await _get_integration_access_token(integration_id)
    if not access_token:
        result.errors.append("No access token available for integration")
        return result.to_dict()

    # Late import to access GitHubGraphQLClient through the package for test mocking
    # Tests mock apps.integrations.services.github_graphql_sync.GitHubGraphQLClient
    from apps.integrations.services import github_graphql_sync as _pkg

    # Create GraphQL client
    client = _pkg.GitHubGraphQLClient(access_token)

    try:
        cursor = None
        has_more = True

        while has_more:
            # Fetch page of members
            try:
                response = await client.fetch_org_members(org=org_name, cursor=cursor)
            except _pkg.GitHubGraphQLRateLimitError as e:
                result.errors.append(f"Rate limit exceeded: {e}")
                return result.to_dict()
            except _pkg.GitHubGraphQLError as e:
                result.errors.append(f"GraphQL error: {e}")
                return result.to_dict()

            # Extract member data
            organization_data = response.get("organization", {})
            members_data = organization_data.get("membersWithRole", {})
            member_nodes = members_data.get("nodes", [])
            page_info = members_data.get("pageInfo", {})

            # Process each member
            for member_data in member_nodes:
                try:
                    await _process_member_async(team_id, member_data, result)
                except Exception as e:
                    member_login = member_data.get("login", "unknown")
                    error_msg = f"Error processing member {member_login}: {type(e).__name__}: {e}"
                    logger.warning(error_msg)
                    result.errors.append(error_msg)

            # Check pagination
            has_more = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

    except Exception as e:
        error_msg = f"Unexpected error during member sync: {type(e).__name__}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)

    return result.to_dict()
