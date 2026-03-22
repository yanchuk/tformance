"""Public OSS repository sync using shared GitHub fetchers.

Uses GitHubTokenPool for PAT management and GitHubGraphQLFetcher
for PR data retrieval. Writes into existing PullRequest table
for the repo's associated team.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from apps.metrics.models import PullRequest
from apps.metrics.seeding.github_graphql_fetcher import GitHubGraphQLFetcher
from apps.metrics.seeding.github_token_pool import AllTokensExhaustedException, GitHubTokenPool
from apps.metrics.seeding.persistence import PRPersistenceService

logger = logging.getLogger(__name__)


def sync_public_repo(repo_profile, token_pool: GitHubTokenPool, *, days: int = 90, max_prs: int = 500) -> dict:
    """Sync a single public repo using the shared GitHub fetcher.

    Args:
        repo_profile: PublicRepoProfile instance.
        token_pool: GitHubTokenPool instance for PAT management.
        days: How many days of history to fetch.
        max_prs: Maximum PRs to fetch per sync.

    Returns:
        Dict with sync results (fetched, created, skipped).
    """
    github_repo = repo_profile.github_repo
    team = repo_profile.team

    # Get a token from the pool for the fetcher
    try:
        client = token_pool.get_best_client()
    except AllTokensExhaustedException:
        logger.warning("All tokens exhausted, cannot sync %s", github_repo)
        raise

    # Extract raw token from the PyGithub client
    token = _extract_token_from_client(client)

    # Configure fetcher — disable caching for public sync
    fetcher = GitHubGraphQLFetcher(
        token=token,
        fetch_check_runs=False,
        use_cache=False,
    )

    since = timezone.now() - timedelta(days=days)
    try:
        fetched_prs = fetcher.fetch_prs_with_details(
            github_repo,
            since=since,
            max_prs=max_prs,
        )
    except Exception:
        logger.exception("Failed to fetch PRs for %s", github_repo)
        return {"fetched": 0, "created": 0, "skipped": 0, "errors": 1}

    # Batch-fetch existing PR numbers to avoid N+1 existence checks
    merged_prs = [pr for pr in fetched_prs if pr.is_merged]
    existing_pr_ids = set(
        PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
            team=team,
            github_repo=github_repo,
            github_pr_id__in=[pr.number for pr in merged_prs],
        ).values_list("github_pr_id", flat=True)
    )

    # Use shared persistence service
    persistence = PRPersistenceService(team)
    persistence.build_member_cache(fetched_prs)

    created = 0
    skipped = 0

    for pr_data in fetched_prs:
        if not pr_data.is_merged:
            skipped += 1
            continue

        if pr_data.number in existing_pr_ids:
            skipped += 1
            continue

        try:
            persistence.create_pr(pr_data, github_repo)
            created += 1
        except Exception:
            logger.warning("Failed to persist PR #%s for %s", pr_data.number, github_repo)
            skipped += 1

    logger.info(
        "Synced %s: fetched=%d, created=%d, skipped=%d",
        github_repo,
        len(fetched_prs),
        created,
        skipped,
    )
    return {"fetched": len(fetched_prs), "created": created, "skipped": skipped, "errors": 0}


# Keep _build_member_cache as a module-level function for backward compatibility
# with existing test imports (test_public_sync_tasks.py uses it)
def _build_member_cache(team, fetched_prs: list) -> dict:
    """Pre-fetch/create all TeamMembers referenced in fetched PR data.

    Delegates to PRPersistenceService for member resolution.
    Kept for backward compatibility with existing tests.
    """
    persistence = PRPersistenceService(team)
    persistence.build_member_cache(fetched_prs)
    return persistence._member_cache


def _extract_token_from_client(client) -> str:
    """Extract the raw token string from a PyGithub client."""
    try:
        # PyGithub stores auth in the requester
        auth = client._Github__requester.auth
        if hasattr(auth, "token"):
            return auth.token
    except AttributeError:
        pass

    # Fallback: try authorization header
    try:
        header = client._Github__requester._Requester__authorizationHeader
        if header and header.startswith("token "):
            return header[6:]
    except AttributeError:
        pass

    raise ValueError("Cannot extract token from GitHub client")


def _persist_pr(team, pr_data, github_repo: str, member_cache: dict) -> PullRequest:
    """Persist a fetched PR and its related data into the database.

    Delegates to PRPersistenceService. Kept for backward compatibility
    with existing tests.
    """
    persistence = PRPersistenceService(team)
    persistence._member_cache = member_cache
    return persistence.create_pr(pr_data, github_repo)
