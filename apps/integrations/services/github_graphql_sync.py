"""GitHub GraphQL-based repository history sync service.

Uses GraphQL API to fetch PR history in bulk, significantly reducing API calls
compared to REST (1 call per 50 PRs vs 6-7 calls per PR).
"""

import logging
from datetime import timedelta
from typing import Any

from asgiref.sync import sync_to_async
from dateutil import parser as date_parser
from django.utils import timezone

from apps.integrations.models import TrackedRepository
from apps.integrations.services.github_graphql import (
    GitHubGraphQLClient,
    GitHubGraphQLError,
    GitHubGraphQLRateLimitError,
)
from apps.metrics.models import Commit, PRFile, PRReview, PullRequest, TeamMember

logger = logging.getLogger(__name__)


class SyncResult:
    """Track sync progress and errors."""

    def __init__(self) -> None:
        self.prs_synced = 0
        self.reviews_synced = 0
        self.commits_synced = 0
        self.files_synced = 0
        self.comments_synced = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for return value."""
        return {
            "prs_synced": self.prs_synced,
            "reviews_synced": self.reviews_synced,
            "commits_synced": self.commits_synced,
            "files_synced": self.files_synced,
            "comments_synced": self.comments_synced,
            "errors": self.errors,
        }


def _parse_datetime(dt_string: str | None):
    """Parse ISO datetime string to timezone-aware datetime."""
    if not dt_string:
        return None
    return date_parser.isoparse(dt_string)


def _map_pr_state(graphql_state: str) -> str:
    """Map GraphQL PR state to model state (lowercase)."""
    state_mapping = {
        "OPEN": "open",
        "MERGED": "merged",
        "CLOSED": "closed",
    }
    return state_mapping.get(graphql_state, graphql_state.lower())


def _map_review_state(graphql_state: str) -> str:
    """Map GraphQL review state to model state (lowercase)."""
    state_mapping = {
        "APPROVED": "approved",
        "CHANGES_REQUESTED": "changes_requested",
        "COMMENTED": "commented",
        "DISMISSED": "commented",  # Map dismissed to commented
        "PENDING": "commented",
    }
    return state_mapping.get(graphql_state, graphql_state.lower())


def _map_file_status(graphql_change_type: str) -> str:
    """Map GraphQL file changeType to model status (lowercase).

    GraphQL uses UPPERCASE changeType enum values: ADDED, CHANGED, COPIED, DELETED, MODIFIED, RENAMED
    """
    status_mapping = {
        "ADDED": "added",
        "CHANGED": "modified",
        "COPIED": "added",
        "DELETED": "removed",
        "MODIFIED": "modified",
        "REMOVED": "removed",
        "RENAMED": "renamed",
        # Handle lowercase too (for backwards compatibility)
        "added": "added",
        "modified": "modified",
        "removed": "removed",
        "renamed": "renamed",
    }
    return status_mapping.get(graphql_change_type, "modified")


def _get_team_member(team, github_login: str | None) -> TeamMember | None:
    """Get TeamMember by GitHub login, or None if not found."""
    if not github_login:
        return None
    try:
        return TeamMember.objects.get(team=team, github_id=github_login)
    except TeamMember.DoesNotExist:
        return None


async def sync_repository_history_graphql(
    tracked_repo,
    days_back: int = 90,
) -> dict[str, Any]:
    """Sync repository PR history using GraphQL API.

    Fetches all PRs (with reviews, commits, files) in bulk using GraphQL pagination.
    Much faster than REST API for historical sync.

    Args:
        tracked_repo: TrackedRepository instance to sync
        days_back: Only sync PRs created within this many days (default 90)

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

    # Get access token from integration
    try:
        access_token = tracked_repo.integration.credential.access_token
    except AttributeError:
        result.errors.append("No access token available for repository")
        await _update_sync_status(tracked_repo_id, "error")
        return result.to_dict()

    # Calculate cutoff date for filtering
    cutoff_date = timezone.now() - timedelta(days=days_back)

    # Create GraphQL client
    client = GitHubGraphQLClient(access_token)

    # Update sync status to syncing
    await _update_sync_status(tracked_repo_id, "syncing")

    try:
        cursor = None
        has_more = True

        while has_more:
            # Fetch page of PRs
            try:
                response = await client.fetch_prs_bulk(owner=owner, repo=repo, cursor=cursor)
            except GitHubGraphQLRateLimitError as e:
                result.errors.append(f"Rate limit exceeded: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()
            except GitHubGraphQLError as e:
                result.errors.append(f"GraphQL error: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()

            # Extract PR data
            repository_data = response.get("repository", {})
            pull_requests_data = repository_data.get("pullRequests", {})
            pr_nodes = pull_requests_data.get("nodes", [])
            page_info = pull_requests_data.get("pageInfo", {})

            # Process each PR
            for pr_data in pr_nodes:
                try:
                    await _process_pr_async(team_id, full_name, pr_data, cutoff_date, result)
                except Exception as e:
                    pr_number = pr_data.get("number", "unknown")
                    error_msg = f"Error processing PR #{pr_number}: {type(e).__name__}: {e}"
                    logger.warning(error_msg)
                    result.errors.append(error_msg)

            # Check pagination
            has_more = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        # Update sync status to complete
        await _update_sync_complete(tracked_repo_id)

    except Exception as e:
        error_msg = f"Unexpected error during sync: {type(e).__name__}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        await _update_sync_status(tracked_repo_id, "error")

    return result.to_dict()


@sync_to_async
def _update_sync_status(tracked_repo_id: int, status: str) -> None:
    """Update sync status (async-safe)."""
    TrackedRepository.objects.filter(id=tracked_repo_id).update(sync_status=status)  # noqa: TEAM001


@sync_to_async
def _update_sync_complete(tracked_repo_id: int) -> None:
    """Update sync status to complete with timestamp (async-safe)."""
    TrackedRepository.objects.filter(id=tracked_repo_id).update(  # noqa: TEAM001
        sync_status="complete",
        last_sync_at=timezone.now(),
    )


@sync_to_async
def _process_pr_async(team_id: int, github_repo: str, pr_data: dict, cutoff_date, result: SyncResult) -> None:
    """Process a single PR from GraphQL response (async wrapper)."""
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)
    _process_pr(team, github_repo, pr_data, cutoff_date, result)


def _process_pr(
    team,
    github_repo: str,
    pr_data: dict,
    cutoff_date,
    result: SyncResult,
) -> None:
    """Process a single PR from GraphQL response.

    Creates or updates PullRequest and related records (reviews, commits, files).
    """
    # Parse PR created date and check cutoff
    created_at = _parse_datetime(pr_data.get("createdAt"))
    if created_at and created_at < cutoff_date:
        logger.debug(f"Skipping PR #{pr_data.get('number')} - older than cutoff")
        return

    # Get author
    author_data = pr_data.get("author")
    if not author_data:
        raise ValueError("PR has no author data")
    author_login = author_data.get("login")
    author = _get_team_member(team, author_login)

    # Map PR data to model fields
    pr_number = pr_data.get("number")
    pr_defaults = {
        "title": pr_data.get("title", ""),
        "body": pr_data.get("body", "") or "",
        "state": _map_pr_state(pr_data.get("state", "OPEN")),
        "pr_created_at": created_at,
        "merged_at": _parse_datetime(pr_data.get("mergedAt")),
        "additions": pr_data.get("additions", 0),
        "deletions": pr_data.get("deletions", 0),
        "author": author,
    }

    # Create or update PR
    pr, created = PullRequest.objects.update_or_create(
        team=team,
        github_pr_id=pr_number,
        github_repo=github_repo,
        defaults=pr_defaults,
    )
    result.prs_synced += 1
    logger.debug(f"{'Created' if created else 'Updated'} PR #{pr_number}")

    # Process nested data
    _process_reviews(team, pr, pr_data.get("reviews", {}).get("nodes", []), result)
    _process_commits(team, pr, github_repo, pr_data.get("commits", {}).get("nodes", []), result)
    _process_files(team, pr, pr_data.get("files", {}).get("nodes", []), result)


def _process_reviews(
    team,
    pr: PullRequest,
    review_nodes: list[dict],
    result: SyncResult,
) -> None:
    """Process PR reviews from GraphQL response."""
    for review_data in review_nodes:
        review_id = review_data.get("databaseId")
        reviewer_login = review_data.get("author", {}).get("login") if review_data.get("author") else None
        reviewer = _get_team_member(team, reviewer_login)

        review_defaults = {
            "state": _map_review_state(review_data.get("state", "COMMENTED")),
            "body": review_data.get("body", "") or "",
            "submitted_at": _parse_datetime(review_data.get("submittedAt")),
            "reviewer": reviewer,
            "pull_request": pr,
        }

        if review_id:
            PRReview.objects.update_or_create(
                team=team,
                github_review_id=review_id,
                defaults=review_defaults,
            )
        else:
            # No GitHub ID, create by PR + reviewer + submitted_at
            PRReview.objects.update_or_create(
                team=team,
                pull_request=pr,
                reviewer=reviewer,
                submitted_at=review_defaults["submitted_at"],
                defaults=review_defaults,
            )
        result.reviews_synced += 1


def _process_commits(
    team,
    pr: PullRequest,
    github_repo: str,
    commit_nodes: list[dict],
    result: SyncResult,
) -> None:
    """Process PR commits from GraphQL response."""
    for commit_node in commit_nodes:
        commit_data = commit_node.get("commit", {})
        sha = commit_data.get("oid")
        if not sha:
            continue

        author_data = commit_data.get("author", {})
        author_user = author_data.get("user", {}) if author_data else {}
        author_login = author_user.get("login") if author_user else None
        author = _get_team_member(team, author_login)

        commit_defaults = {
            "message": commit_data.get("message", ""),
            "committed_at": _parse_datetime(author_data.get("date")) if author_data else None,
            "additions": commit_data.get("additions", 0),
            "deletions": commit_data.get("deletions", 0),
            "author": author,
            "pull_request": pr,
            "github_repo": github_repo,
        }

        Commit.objects.update_or_create(
            team=team,
            github_sha=sha,
            defaults=commit_defaults,
        )
        result.commits_synced += 1


def _process_files(
    team,
    pr: PullRequest,
    file_nodes: list[dict],
    result: SyncResult,
) -> None:
    """Process PR files from GraphQL response."""
    for file_data in file_nodes:
        filename = file_data.get("path")
        if not filename:
            continue

        # GraphQL uses changeType, REST uses status - handle both
        change_type = file_data.get("changeType") or file_data.get("status", "MODIFIED")

        file_defaults = {
            "status": _map_file_status(change_type),
            "additions": file_data.get("additions", 0),
            "deletions": file_data.get("deletions", 0),
            "changes": file_data.get("additions", 0) + file_data.get("deletions", 0),
            "file_category": PRFile.categorize_file(filename),
        }

        PRFile.objects.update_or_create(
            team=team,
            pull_request=pr,
            filename=filename,
            defaults=file_defaults,
        )
        result.files_synced += 1


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

    # Get access token from integration
    try:
        access_token = tracked_repo.integration.credential.access_token
    except AttributeError:
        result.errors.append("No access token available for repository")
        await _update_sync_status(tracked_repo_id, "error")
        return result.to_dict()

    # Create GraphQL client
    client = GitHubGraphQLClient(access_token)

    # Update sync status to syncing
    await _update_sync_status(tracked_repo_id, "syncing")

    try:
        cursor = None
        has_more = True

        while has_more:
            # Fetch page of updated PRs
            try:
                response = await client.fetch_prs_updated_since(owner=owner, repo=repo, since=since, cursor=cursor)
            except GitHubGraphQLRateLimitError as e:
                result.errors.append(f"Rate limit exceeded: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()
            except GitHubGraphQLError as e:
                result.errors.append(f"GraphQL error: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()

            # Extract PR data
            repository_data = response.get("repository", {})
            pull_requests_data = repository_data.get("pullRequests", {})
            pr_nodes = pull_requests_data.get("nodes", [])
            page_info = pull_requests_data.get("pageInfo", {})

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
                except Exception as e:
                    pr_number = pr_data.get("number", "unknown")
                    error_msg = f"Error processing PR #{pr_number}: {type(e).__name__}: {e}"
                    logger.warning(error_msg)
                    result.errors.append(error_msg)

            # Stop if all PRs in this page are older than since
            if all_older_than_since:
                break

            # Check pagination
            has_more = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        # Update sync status to complete
        await _update_sync_complete(tracked_repo_id)

    except Exception as e:
        error_msg = f"Unexpected error during incremental sync: {type(e).__name__}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        await _update_sync_status(tracked_repo_id, "error")

    return result.to_dict()


@sync_to_async
def _process_pr_incremental_async(team_id: int, github_repo: str, pr_data: dict, result: SyncResult) -> None:
    """Process a single PR from GraphQL response for incremental sync (async wrapper).

    Unlike full sync, incremental sync does not filter by date - it processes all PRs
    that are returned since they're already filtered by the API.
    """
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)
    _process_pr_incremental(team, github_repo, pr_data, result)


def _process_pr_incremental(
    team,
    github_repo: str,
    pr_data: dict,
    result: SyncResult,
) -> None:
    """Process a single PR from GraphQL response for incremental sync.

    Creates or updates PullRequest and related records (reviews, commits, files).
    Does not apply date filtering as PRs are pre-filtered by the API.
    """
    # Parse PR created date
    created_at = _parse_datetime(pr_data.get("createdAt"))

    # Get author
    author_data = pr_data.get("author")
    author_login = author_data.get("login") if author_data else None
    author = _get_team_member(team, author_login)

    # Map PR data to model fields
    pr_number = pr_data.get("number")
    pr_defaults = {
        "title": pr_data.get("title", ""),
        "body": pr_data.get("body", "") or "",
        "state": _map_pr_state(pr_data.get("state", "OPEN")),
        "pr_created_at": created_at,
        "merged_at": _parse_datetime(pr_data.get("mergedAt")),
        "additions": pr_data.get("additions", 0),
        "deletions": pr_data.get("deletions", 0),
        "author": author,
    }

    # Create or update PR
    pr, created = PullRequest.objects.update_or_create(
        team=team,
        github_pr_id=pr_number,
        github_repo=github_repo,
        defaults=pr_defaults,
    )
    result.prs_synced += 1
    logger.debug(f"{'Created' if created else 'Updated'} PR #{pr_number}")

    # Process nested data
    _process_reviews(team, pr, pr_data.get("reviews", {}).get("nodes", []), result)
    _process_commits(team, pr, github_repo, pr_data.get("commits", {}).get("nodes", []), result)
    _process_files(team, pr, pr_data.get("files", {}).get("nodes", []), result)


# =============================================================================
# Phase 4: Single PR Complete Data Fetch
# =============================================================================


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

    # Parse repo owner and name from full_name
    owner, repo = tracked_repo.full_name.split("/")
    access_token = tracked_repo.integration.credential.access_token
    team = tracked_repo.team

    try:
        # Initialize GraphQL client and fetch PR data
        client = GitHubGraphQLClient(access_token)
        response = await client.fetch_single_pr(owner, repo, pr.github_pr_id)

        # Extract PR data from response
        pr_data = response.get("repository", {}).get("pullRequest")

        if not pr_data:
            error_msg = f"PR #{pr.github_pr_id} not found in GraphQL response"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            return result.to_dict()

        # Process nested data (commits, files, reviews)
        await _process_pr_nested_data_async(team.id, pr, tracked_repo.full_name, pr_data, result)

    except GitHubGraphQLRateLimitError as e:
        error_msg = f"Rate limit error fetching PR #{pr.github_pr_id}: {e}"
        logger.warning(error_msg)
        result.errors.append(error_msg)

    except GitHubGraphQLError as e:
        error_msg = f"GraphQL error fetching PR #{pr.github_pr_id}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)

    except Exception as e:
        error_msg = f"Unexpected error fetching PR #{pr.github_pr_id}: {type(e).__name__}: {e}"
        logger.error(error_msg)
        result.errors.append(error_msg)

    return result.to_dict()


@sync_to_async
def _process_pr_nested_data_async(team_id: int, pr, github_repo: str, pr_data: dict, result: SyncResult) -> None:
    """Process PR nested data (commits, files, reviews) from GraphQL response.

    Unlike full sync, this processes data for an existing PR and doesn't create/update
    the PR itself - just its nested data.
    """
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)

    # Process nested data using existing helpers
    _process_reviews(team, pr, pr_data.get("reviews", {}).get("nodes", []), result)
    _process_commits(team, pr, github_repo, pr_data.get("commits", {}).get("nodes", []), result)
    _process_files(team, pr, pr_data.get("files", {}).get("nodes", []), result)


# =============================================================================
# Phase 5: Organization Member Sync
# =============================================================================


class MemberSyncResult:
    """Track member sync progress and errors."""

    def __init__(self) -> None:
        self.members_synced = 0
        self.members_created = 0
        self.members_updated = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for return value."""
        return {
            "members_synced": self.members_synced,
            "members_created": self.members_created,
            "members_updated": self.members_updated,
            "errors": self.errors,
        }


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

    # Get team info before async operations
    team_id = integration.team_id
    access_token = integration.credential.access_token

    # Create GraphQL client
    client = GitHubGraphQLClient(access_token)

    try:
        cursor = None
        has_more = True

        while has_more:
            # Fetch page of members
            try:
                response = await client.fetch_org_members(org=org_name, cursor=cursor)
            except GitHubGraphQLRateLimitError as e:
                result.errors.append(f"Rate limit exceeded: {e}")
                return result.to_dict()
            except GitHubGraphQLError as e:
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


@sync_to_async
def _process_member_async(team_id: int, member_data: dict, result: MemberSyncResult) -> None:
    """Process a single organization member from GraphQL response (async wrapper)."""
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)
    _process_member(team, member_data, result)


def _process_member(team, member_data: dict, result: MemberSyncResult) -> None:
    """Process a single organization member from GraphQL response.

    Creates or updates TeamMember record.
    """
    # Extract member fields
    github_id = str(member_data.get("databaseId"))
    github_username = member_data.get("login")
    display_name = member_data.get("name") or github_username  # Fallback to login if no name

    # Create or update TeamMember
    member, created = TeamMember.objects.update_or_create(
        team=team,
        github_id=github_id,
        defaults={
            "github_username": github_username,
            "display_name": display_name,
        },
    )

    result.members_synced += 1
    if created:
        result.members_created += 1
        logger.debug(f"Created TeamMember: {github_username}")
    else:
        result.members_updated += 1
        logger.debug(f"Updated TeamMember: {github_username}")
