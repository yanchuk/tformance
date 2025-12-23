"""GitHub GraphQL API client service."""

import logging

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

logger = logging.getLogger(__name__)

# GraphQL query templates
# Cost estimation: ~1 point per query (GitHub GraphQL has 5000 point/hour limit)

# Query cost: ~1 point + (50 PRs * 0.1) = ~6 points per page
# Fetches 50 PRs with up to 50 reviews, 100 commits, 100 files each
FETCH_PRS_BULK_QUERY = gql(
    """
    query($owner: String!, $repo: String!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        pullRequests(first: 50, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            number
            title
            body
            state
            createdAt
            mergedAt
            additions
            deletions
            author {
              login
            }
            reviews(first: 50) {
              nodes {
                databaseId
                state
                body
                submittedAt
                author {
                  login
                }
              }
            }
            commits(first: 100) {
              nodes {
                commit {
                  oid
                  message
                  additions
                  deletions
                  author {
                    date
                    user {
                      login
                    }
                  }
                }
              }
            }
            files(first: 100) {
              nodes {
                path
                additions
                deletions
                changeType
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
      rateLimit {
        remaining
        resetAt
      }
    }
    """
)

# Query cost: ~1 point + (50 PRs * 0.1) = ~6 points per page
# Fetches 50 PRs ordered by UPDATED_AT for incremental sync
FETCH_PRS_UPDATED_QUERY = gql(
    """
    query($owner: String!, $repo: String!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        pullRequests(first: 50, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            number
            title
            body
            state
            createdAt
            updatedAt
            mergedAt
            additions
            deletions
            author {
              login
            }
            reviews(first: 50) {
              nodes {
                databaseId
                state
                body
                submittedAt
                author {
                  login
                }
              }
            }
            commits(first: 100) {
              nodes {
                commit {
                  oid
                  message
                  additions
                  deletions
                  author {
                    date
                    user {
                      login
                    }
                  }
                }
              }
            }
            files(first: 100) {
              nodes {
                path
                additions
                deletions
                changeType
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
      rateLimit {
        remaining
        resetAt
      }
    }
    """
)

# Query cost: ~1 point for single PR
FETCH_SINGLE_PR_QUERY = gql(
    """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          number
          title
          body
          state
          createdAt
          mergedAt
          additions
          deletions
          author {
            login
          }
          reviews(first: 50) {
            nodes {
              databaseId
              state
              body
              submittedAt
              author {
                login
              }
            }
          }
          commits(first: 100) {
            nodes {
              commit {
                oid
                message
                additions
                deletions
                author {
                  date
                  user {
                    login
                  }
                }
              }
            }
          }
          files(first: 100) {
            nodes {
              path
              additions
              deletions
              changeType
            }
          }
        }
      }
      rateLimit {
        remaining
        resetAt
      }
    }
    """
)

# Query cost: ~1 point + (100 members * 0.1) = ~11 points per page
FETCH_ORG_MEMBERS_QUERY = gql(
    """
    query($org: String!, $cursor: String) {
      organization(login: $org) {
        membersWithRole(first: 100, after: $cursor) {
          nodes {
            databaseId
            login
            name
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
      rateLimit {
        remaining
        resetAt
      }
    }
    """
)

# Rate limit threshold - raise error if remaining points drop below this
RATE_LIMIT_THRESHOLD = 100


class GitHubGraphQLError(Exception):
    """Base exception for GitHub GraphQL errors."""

    pass


class GitHubGraphQLRateLimitError(GitHubGraphQLError):
    """Exception raised when GitHub GraphQL rate limit is exceeded."""

    pass


class GitHubGraphQLTimeoutError(GitHubGraphQLError):
    """Exception raised when GitHub GraphQL request times out."""

    pass


class GitHubGraphQLClient:
    """Client for interacting with GitHub GraphQL API.

    This client uses the GitHub GraphQL API v4 which has a point-based rate limit
    (5000 points/hour). Connection pooling is handled by aiohttp transport.

    Rate limiting: Queries are checked after execution and raise GitHubGraphQLRateLimitError
    when remaining points drop below threshold to prevent hitting hard limit.
    """

    def __init__(self, access_token: str) -> None:
        """Initialize GitHub GraphQL client with access token.

        Args:
            access_token: GitHub personal access token or OAuth token
        """
        self.transport = AIOHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        logger.debug("Initialized GitHubGraphQLClient")

    async def _execute(self, query, variable_values: dict) -> dict:
        """Execute a GraphQL query using async context manager.

        Args:
            query: GraphQL query object
            variable_values: Variables to pass to the query

        Returns:
            dict: Query result
        """
        async with Client(transport=self.transport, fetch_schema_from_transport=False) as session:
            return await session.execute(query, variable_values=variable_values)

    def _check_rate_limit(self, result: dict, operation: str) -> None:
        """Check rate limit from query result and raise error if threshold exceeded.

        Args:
            result: GraphQL query result containing rateLimit field
            operation: Name of operation being performed (for error context)

        Raises:
            GitHubGraphQLRateLimitError: When rate limit remaining < threshold
        """
        rate_limit = result.get("rateLimit", {})
        remaining = rate_limit.get("remaining", 0)
        reset_at = rate_limit.get("resetAt", "unknown")

        if remaining < RATE_LIMIT_THRESHOLD:
            error_msg = (
                f"GitHub GraphQL rate limit low during {operation}: {remaining} points remaining (resets at {reset_at})"
            )
            logger.warning(error_msg)
            raise GitHubGraphQLRateLimitError(error_msg)

        logger.debug(f"{operation}: {remaining} rate limit points remaining")

    async def fetch_prs_bulk(self, owner: str, repo: str, cursor: str | None = None, max_retries: int = 3) -> dict:
        """Fetch pull requests in bulk with pagination support and retry logic.

        Args:
            owner: Repository owner (organization or user)
            repo: Repository name
            cursor: Pagination cursor for subsequent pages (optional)
            max_retries: Maximum number of retry attempts on timeout (default: 3)

        Returns:
            dict: GraphQL response containing:
                - repository.pullRequests.nodes: List of PR data
                - repository.pullRequests.pageInfo: Pagination info
                - rateLimit: Current rate limit status

        Raises:
            GitHubGraphQLRateLimitError: When rate limit remaining < 100 points
            GitHubGraphQLTimeoutError: When request times out after max retries
            GitHubGraphQLError: On any other GraphQL query errors
        """
        import asyncio

        logger.debug(f"Fetching PRs for {owner}/{repo} (cursor: {cursor})")

        last_error = None
        for attempt in range(max_retries):
            try:
                result = await self._execute(
                    FETCH_PRS_BULK_QUERY, variable_values={"owner": owner, "repo": repo, "cursor": cursor}
                )

                self._check_rate_limit(result, f"fetch_prs_bulk({owner}/{repo})")

                pr_count = len(result.get("repository", {}).get("pullRequests", {}).get("nodes", []))
                logger.info(f"Fetched {pr_count} PRs from {owner}/{repo}")

                return result

            except GitHubGraphQLRateLimitError:
                raise
            except TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Timeout fetching PRs for {owner}/{repo}, attempt {attempt + 1}/{max_retries}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"GraphQL request timed out for {owner}/{repo} after {max_retries} attempts"
                    logger.error(error_msg)
                    raise GitHubGraphQLTimeoutError(error_msg) from e
            except Exception as e:
                error_msg = f"GraphQL query failed for {owner}/{repo}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                raise GitHubGraphQLError(error_msg) from e

        # Should not reach here, but just in case
        raise GitHubGraphQLTimeoutError(
            f"GraphQL request timed out for {owner}/{repo} after {max_retries} attempts"
        ) from last_error

    async def fetch_single_pr(self, owner: str, repo: str, pr_number: int, max_retries: int = 3) -> dict:
        """Fetch a single pull request by number with retry logic.

        Args:
            owner: Repository owner (organization or user)
            repo: Repository name
            pr_number: Pull request number
            max_retries: Maximum number of retry attempts on timeout (default: 3)

        Returns:
            dict: GraphQL response containing:
                - repository.pullRequest: PR data with reviews, commits, files
                - rateLimit: Current rate limit status

        Raises:
            GitHubGraphQLRateLimitError: When rate limit remaining < 100 points
            GitHubGraphQLTimeoutError: When request times out after max retries
            GitHubGraphQLError: On any other GraphQL query errors
        """
        import asyncio

        logger.debug(f"Fetching PR #{pr_number} from {owner}/{repo}")

        for attempt in range(max_retries):
            try:
                result = await self._execute(
                    FETCH_SINGLE_PR_QUERY, variable_values={"owner": owner, "repo": repo, "number": pr_number}
                )

                self._check_rate_limit(result, f"fetch_single_pr({owner}/{repo}#{pr_number})")

                logger.info(f"Fetched PR #{pr_number} from {owner}/{repo}")

                return result

            except GitHubGraphQLRateLimitError:
                raise
            except TimeoutError as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(f"Timeout fetching PR #{pr_number}, attempt {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"GraphQL request timed out for {owner}/{repo}#{pr_number} after {max_retries} attempts"
                    raise GitHubGraphQLTimeoutError(error_msg) from e
            except Exception as e:
                error_msg = f"GraphQL query failed for {owner}/{repo}#{pr_number}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                raise GitHubGraphQLError(error_msg) from e

        # Should not reach here
        raise GitHubGraphQLTimeoutError(
            f"GraphQL request timed out for {owner}/{repo}#{pr_number} after {max_retries} attempts"
        )

    async def fetch_org_members(self, org: str, cursor: str | None = None, max_retries: int = 3) -> dict:
        """Fetch organization members with pagination support and retry logic.

        Args:
            org: Organization name
            cursor: Pagination cursor for subsequent pages (optional)
            max_retries: Maximum number of retry attempts on timeout (default: 3)

        Returns:
            dict: GraphQL response containing:
                - organization.membersWithRole.nodes: List of member data
                - organization.membersWithRole.pageInfo: Pagination info
                - rateLimit: Current rate limit status

        Raises:
            GitHubGraphQLRateLimitError: When rate limit remaining < 100 points
            GitHubGraphQLTimeoutError: When request times out after max retries
            GitHubGraphQLError: On any other GraphQL query errors
        """
        import asyncio

        logger.debug(f"Fetching members for org {org} (cursor: {cursor})")

        for attempt in range(max_retries):
            try:
                result = await self._execute(FETCH_ORG_MEMBERS_QUERY, variable_values={"org": org, "cursor": cursor})

                self._check_rate_limit(result, f"fetch_org_members({org})")

                member_count = len(result.get("organization", {}).get("membersWithRole", {}).get("nodes", []))
                logger.info(f"Fetched {member_count} members from org {org}")

                return result

            except GitHubGraphQLRateLimitError:
                raise
            except TimeoutError as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(f"Timeout fetching members for {org}, attempt {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"GraphQL request timed out for org {org} after {max_retries} attempts"
                    logger.error(error_msg)
                    raise GitHubGraphQLTimeoutError(error_msg) from e
            except Exception as e:
                error_msg = f"GraphQL query failed for org {org}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                raise GitHubGraphQLError(error_msg) from e

        # Should not reach here
        raise GitHubGraphQLTimeoutError(f"GraphQL request timed out for org {org} after {max_retries} attempts")

    async def fetch_prs_updated_since(
        self,
        owner: str,
        repo: str,
        since,  # datetime object
        cursor: str | None = None,
        max_retries: int = 3,
    ) -> dict:
        """Fetch pull requests updated since a given datetime.

        Uses UPDATED_AT ordering for incremental sync. Caller should stop pagination
        when encountering PRs with updatedAt older than `since`.

        Args:
            owner: Repository owner (organization or user)
            repo: Repository name
            since: Only return PRs updated at or after this datetime
            cursor: Pagination cursor for subsequent pages (optional)
            max_retries: Maximum number of retry attempts on timeout (default: 3)

        Returns:
            dict: GraphQL response containing:
                - repository.pullRequests.nodes: List of PR data with updatedAt field
                - repository.pullRequests.pageInfo: Pagination info
                - rateLimit: Current rate limit status

        Raises:
            GitHubGraphQLRateLimitError: When rate limit remaining < 100 points
            GitHubGraphQLTimeoutError: When request times out after max retries
            GitHubGraphQLError: On any other GraphQL query errors
        """
        import asyncio

        logger.debug(f"Fetching PRs updated since {since} for {owner}/{repo} (cursor: {cursor})")

        last_error = None
        for attempt in range(max_retries):
            try:
                result = await self._execute(
                    FETCH_PRS_UPDATED_QUERY, variable_values={"owner": owner, "repo": repo, "cursor": cursor}
                )

                self._check_rate_limit(result, f"fetch_prs_updated_since({owner}/{repo})")

                pr_count = len(result.get("repository", {}).get("pullRequests", {}).get("nodes", []))
                logger.info(f"Fetched {pr_count} updated PRs from {owner}/{repo}")

                return result

            except GitHubGraphQLRateLimitError:
                raise
            except TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Timeout fetching updated PRs for {owner}/{repo}, attempt {attempt + 1}/{max_retries}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"GraphQL request timed out for {owner}/{repo} after {max_retries} attempts"
                    logger.error(error_msg)
                    raise GitHubGraphQLTimeoutError(error_msg) from e
            except Exception as e:
                error_msg = f"GraphQL query failed for {owner}/{repo}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                raise GitHubGraphQLError(error_msg) from e

        # Should not reach here, but just in case
        raise GitHubGraphQLTimeoutError(
            f"GraphQL request timed out for {owner}/{repo} after {max_retries} attempts"
        ) from last_error
