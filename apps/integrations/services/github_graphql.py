"""GitHub GraphQL API client service."""

import logging
import time
from datetime import datetime

import aiohttp
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

logger = logging.getLogger(__name__)


def _get_sync_logger():
    """Get sync logger lazily to allow mocking in tests."""
    from apps.utils.sync_logger import get_sync_logger

    return get_sync_logger(__name__)


# GraphQL query templates
# Cost estimation: ~1 point per query (GitHub GraphQL has 5000 point/hour limit)

# GitHub GraphQL best practices:
# - Use first: 10-25 for queries with nested connections
# - Reduce nested limits for complex queries
# - See: https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api
#
# Query cost: ~1 point + (10 PRs * 0.1) = ~2 points per page
# Fetches 10 PRs with up to 25 reviews, 50 commits, 50 files each
# Reduced from 25 to 10 PRs per page to prevent timeouts on heavy repos
FETCH_PRS_BULK_QUERY = gql(
    """
    query($owner: String!, $repo: String!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        pullRequests(first: 10, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            number
            title
            body
            state
            createdAt
            mergedAt
            additions
            deletions
            isDraft
            author {
              login
            }
            labels(first: 10) {
              nodes {
                name
                color
              }
            }
            milestone {
              title
              number
              dueOn
            }
            assignees(first: 10) {
              nodes {
                login
              }
            }
            closingIssuesReferences(first: 5) {
              nodes {
                number
                title
              }
            }
            reviews(first: 25) {
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
            commits(first: 50) {
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
            files(first: 50) {
              nodes {
                path
                additions
                deletions
                changeType
              }
            }
          }
          totalCount
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

# Query cost: ~1 point + (10 PRs * 0.1) = ~2 points per page
# Fetches 10 PRs ordered by UPDATED_AT for incremental sync
# Uses same reduced limits as bulk query for consistency
# Reduced from 25 to 10 PRs per page to prevent timeouts on heavy repos
FETCH_PRS_UPDATED_QUERY = gql(
    """
    query($owner: String!, $repo: String!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        pullRequests(first: 10, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
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
            isDraft
            author {
              login
            }
            labels(first: 10) {
              nodes {
                name
                color
              }
            }
            milestone {
              title
              number
              dueOn
            }
            assignees(first: 10) {
              nodes {
                login
              }
            }
            closingIssuesReferences(first: 5) {
              nodes {
                number
                title
              }
            }
            reviews(first: 25) {
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
            commits(first: 50) {
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
            files(first: 50) {
              nodes {
                path
                additions
                deletions
                changeType
              }
            }
          }
          totalCount
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
          isDraft
          author {
            login
          }
          labels(first: 10) {
            nodes {
              name
              color
            }
          }
          milestone {
            title
            number
            dueOn
          }
          assignees(first: 10) {
            nodes {
              login
            }
          }
          closingIssuesReferences(first: 5) {
            nodes {
              number
              title
            }
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

# Query cost: ~1 point (lightweight query for cache validation)
# Fetches repository metadata to check if repo has changed since last sync
FETCH_REPO_METADATA_QUERY = gql(
    """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        pushedAt
        updatedAt
      }
      rateLimit {
        remaining
        resetAt
      }
    }
    """
)

# Query cost: ~1 point (search query for PR count in date range)
# Uses GitHub Search API to get accurate PR count within a date range
SEARCH_PR_COUNT_QUERY = gql(
    """
    query($searchQuery: String!) {
      search(query: $searchQuery, type: ISSUE, first: 1) {
        issueCount
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

    Rate limiting: Queries are checked after execution. When rate limit is low:
    - If wait_for_reset=True: waits until reset (up to max_wait_seconds)
    - If wait_for_reset=False: raises GitHubGraphQLRateLimitError
    """

    def __init__(
        self,
        access_token: str,
        timeout: int = 90,
        wait_for_reset: bool = True,
        max_wait_seconds: int = 3600,
    ) -> None:
        """Initialize GitHub GraphQL client with access token.

        Args:
            access_token: GitHub personal access token or OAuth token
            timeout: HTTP request timeout in seconds (default: 90)
            wait_for_reset: If True, wait when rate limit is low instead of raising error
            max_wait_seconds: Maximum seconds to wait for rate limit reset (default: 1 hour)
        """
        # Set 90-second timeout for complex queries with nested data
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        self.transport = AIOHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=timeout,
            client_session_args={"timeout": client_timeout},
        )
        self.wait_for_reset = wait_for_reset
        self.max_wait_seconds = max_wait_seconds
        logger.debug(f"Initialized GitHubGraphQLClient with {timeout}s timeout, wait_for_reset={wait_for_reset}")

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

    async def _check_rate_limit(self, result: dict, operation: str) -> None:
        """Check rate limit from query result and wait or raise error if threshold exceeded.

        If wait_for_reset=True and remaining < threshold, waits until reset (up to max_wait_seconds).
        If wait_for_reset=False or wait time exceeds max, raises GitHubGraphQLRateLimitError.

        Args:
            result: GraphQL query result containing rateLimit field
            operation: Name of operation being performed (for error context)

        Raises:
            GitHubGraphQLRateLimitError: When rate limit remaining < threshold and can't wait
        """
        from apps.integrations.services.github_rate_limit import wait_for_rate_limit_reset_async

        rate_limit = result.get("rateLimit", {})
        remaining = rate_limit.get("remaining", 0)
        reset_at = rate_limit.get("resetAt", "unknown")
        limit = rate_limit.get("limit", 5000)

        # Log rate limit status
        _get_sync_logger().info(
            "sync.api.rate_limit",
            extra={
                "remaining": remaining,
                "limit": limit,
                "reset_at": reset_at,
            },
        )

        if remaining < RATE_LIMIT_THRESHOLD:
            # Try to wait if enabled
            if self.wait_for_reset and reset_at != "unknown":
                start_wait = time.time()
                waited = await wait_for_rate_limit_reset_async(reset_at, self.max_wait_seconds)
                if waited:
                    wait_seconds = time.time() - start_wait
                    _get_sync_logger().info(
                        "sync.api.rate_wait",
                        extra={
                            "wait_seconds": wait_seconds,
                        },
                    )
                    logger.info(f"Rate limit recovered after waiting, continuing {operation}")
                    return

            # Either wait_for_reset is False, or wait would exceed max
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
                start_time = time.time()
                result = await self._execute(
                    FETCH_PRS_BULK_QUERY, variable_values={"owner": owner, "repo": repo, "cursor": cursor}
                )
                duration_ms = (time.time() - start_time) * 1000

                # Log GraphQL query timing
                rate_limit = result.get("rateLimit", {})
                points_cost = rate_limit.get("cost", 0)
                _get_sync_logger().info(
                    "sync.api.graphql",
                    extra={
                        "query_name": "fetch_prs_bulk",
                        "duration_ms": duration_ms,
                        "status": "success",
                        "points_cost": points_cost,
                    },
                )

                await self._check_rate_limit(result, f"fetch_prs_bulk({owner}/{repo})")

                pr_count = len(result.get("repository", {}).get("pullRequests", {}).get("nodes", []))
                logger.info(f"Fetched {pr_count} PRs from {owner}/{repo}")

                return result

            except GitHubGraphQLRateLimitError:
                raise
            except TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"⏳ Timeout, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...", flush=True)
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

                await self._check_rate_limit(result, f"fetch_single_pr({owner}/{repo}#{pr_number})")

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

                await self._check_rate_limit(result, f"fetch_org_members({org})")

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

                await self._check_rate_limit(result, f"fetch_prs_updated_since({owner}/{repo})")

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

    async def fetch_repo_metadata(self, owner: str, repo: str) -> dict:
        """Fetch repository metadata for cache validation.

        Lightweight query (~1 point) to check if repository has changed since last sync.
        Used to implement conditional requests per GitHub API best practices.

        Args:
            owner: Repository owner (organization or user)
            repo: Repository name

        Returns:
            dict: GraphQL response containing:
                - repository.pushedAt: When the repo was last pushed to
                - repository.updatedAt: When the repo was last updated
                - rateLimit: Current rate limit status

        Raises:
            GitHubGraphQLRateLimitError: When rate limit remaining < 100 points
            GitHubGraphQLError: On any other GraphQL query errors
        """
        logger.debug(f"Fetching repo metadata for {owner}/{repo}")

        try:
            result = await self._execute(FETCH_REPO_METADATA_QUERY, variable_values={"owner": owner, "repo": repo})

            await self._check_rate_limit(result, f"fetch_repo_metadata({owner}/{repo})")

            pushed_at = result.get("repository", {}).get("pushedAt")
            logger.info(f"Repo {owner}/{repo} last pushed at: {pushed_at}")

            return result

        except GitHubGraphQLRateLimitError:
            raise
        except Exception as e:
            error_msg = f"GraphQL query failed for {owner}/{repo} metadata: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            raise GitHubGraphQLError(error_msg) from e

    async def get_pr_count_in_date_range(
        self,
        owner: str,
        repo: str,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> int:
        """Get the count of PRs in a repository within a date range.

        Uses GitHub Search API to get accurate PR count within a date range.
        Unlike totalCount from pullRequests connection (which returns ALL PRs),
        this returns the exact count matching the date filter.

        Args:
            owner: Repository owner (organization or user)
            repo: Repository name
            since: Only count PRs created on or after this datetime (optional)
            until: Only count PRs created on or before this datetime (optional)

        Returns:
            int: Number of PRs matching the search criteria

        Raises:
            GitHubGraphQLRateLimitError: When rate limit remaining < 100 points
            GitHubGraphQLError: On any other GraphQL query errors
        """
        # Build search query: repo:owner/repo is:pr created:>=YYYY-MM-DD created:<=YYYY-MM-DD
        search_parts = [f"repo:{owner}/{repo}", "is:pr"]

        if since:
            since_str = since.strftime("%Y-%m-%d")
            search_parts.append(f"created:>={since_str}")

        if until:
            until_str = until.strftime("%Y-%m-%d")
            search_parts.append(f"created:<={until_str}")

        search_query = " ".join(search_parts)
        logger.debug(f"Searching PRs with query: {search_query}")

        try:
            result = await self._execute(SEARCH_PR_COUNT_QUERY, variable_values={"searchQuery": search_query})

            await self._check_rate_limit(result, f"get_pr_count_in_date_range({owner}/{repo})")

            issue_count = result.get("search", {}).get("issueCount", 0)
            logger.info(f"Found {issue_count} PRs in {owner}/{repo} matching date range")

            return issue_count

        except GitHubGraphQLRateLimitError:
            raise
        except Exception as e:
            error_msg = f"GraphQL search query failed for {owner}/{repo}: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            raise GitHubGraphQLError(error_msg) from e
