"""GitHub GraphQL-based repository history sync service.

Uses GraphQL API to fetch PR history in bulk, significantly reducing API calls
compared to REST (1 call per 50 PRs vs 6-7 calls per PR).
"""

import logging
import time
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
from apps.metrics.processors import _calculate_cycle_time_hours, _calculate_time_diff_hours
from apps.metrics.services.ai_detector import PATTERNS_VERSION, detect_ai_author, detect_ai_in_text

logger = logging.getLogger(__name__)


def _get_sync_logger():
    """Get sync logger lazily to allow mocking in tests."""
    from apps.utils.sync_logger import get_sync_logger

    return get_sync_logger(__name__)


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
    client = GitHubGraphQLClient(access_token)

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
        except GitHubGraphQLError as e:
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
def _update_sync_progress(tracked_repo_id: int, completed: int, total: int) -> None:
    """Update sync progress fields (async-safe).

    Args:
        tracked_repo_id: ID of the TrackedRepository
        completed: Number of PRs synced so far
        total: Total number of PRs to sync
    """
    progress = int((completed / total) * 100) if total > 0 else 0
    TrackedRepository.objects.filter(id=tracked_repo_id).update(  # noqa: TEAM001
        sync_progress=progress,
        sync_prs_completed=completed,
        sync_prs_total=total,
    )


@sync_to_async
def _get_access_token(tracked_repo_id: int) -> str | None:
    """Get access token for a tracked repository (async-safe).

    This wraps ORM access to avoid SynchronousOnlyOperation errors
    when called from async context.
    """
    try:
        tracked_repo = TrackedRepository.objects.select_related("integration__credential").get(id=tracked_repo_id)  # noqa: TEAM001 - ID from Celery task
        return tracked_repo.integration.credential.access_token
    except (TrackedRepository.DoesNotExist, AttributeError):
        return None


@sync_to_async(thread_sensitive=False)
def _process_pr_async(
    team_id: int,
    github_repo: str,
    pr_data: dict,
    cutoff_date,
    skip_before_date,
    result: SyncResult,
) -> bool:
    """Process a single PR from GraphQL response (async wrapper).

    Returns:
        True if PR was actually processed, False if skipped (outside date range).
    """
    from apps.teams.models import Team

    pr_number = pr_data.get("number", "unknown")
    logger.info(f"[SYNC_DEBUG] _process_pr_async() ENTRY: PR #{pr_number}, team_id={team_id}")

    try:
        team = Team.objects.get(id=team_id)
        logger.info(f"[SYNC_DEBUG] _process_pr_async() Team lookup OK: {team.name}")
    except Team.DoesNotExist:
        logger.error(f"[SYNC_DEBUG] _process_pr_async() Team NOT FOUND: {team_id}")
        raise

    result_val = _process_pr(team, github_repo, pr_data, cutoff_date, skip_before_date, result)
    logger.info(f"[SYNC_DEBUG] _process_pr_async() returned: {result_val}")
    return result_val


def _detect_pr_ai_involvement(author_login: str | None, title: str, body: str) -> tuple[bool, list[str]]:
    """Detect AI involvement in a PR from author and text.

    Args:
        author_login: GitHub login of PR author
        title: PR title
        body: PR body text

    Returns:
        Tuple of (is_ai_assisted, ai_tools_detected)
    """
    author_ai_result = detect_ai_author(author_login)
    text_ai_result = detect_ai_in_text(f"{title}\n{body}")

    # Combine AI detection results
    ai_tools = list(text_ai_result["ai_tools"])  # Copy to avoid mutation
    if author_ai_result["is_ai"] and author_ai_result["ai_type"] not in ai_tools:
        ai_tools.append(author_ai_result["ai_type"])
    is_ai_assisted = author_ai_result["is_ai"] or text_ai_result["is_ai_assisted"]

    return is_ai_assisted, ai_tools


def _update_pr_timing_metrics(pr: PullRequest) -> None:
    """Update timing metrics (cycle_time_hours) for a PR if applicable.

    Args:
        pr: PullRequest instance to update
    """
    if pr.merged_at:
        pr.cycle_time_hours = _calculate_cycle_time_hours(pr.pr_created_at, pr.merged_at)
        pr.save()


def _process_pr(
    team,
    github_repo: str,
    pr_data: dict,
    cutoff_date,
    skip_before_date,
    result: SyncResult,
) -> bool:
    """Process a single PR from GraphQL response.

    Creates or updates PullRequest and related records (reviews, commits, files).

    Supports two-phase onboarding date filtering:
    - cutoff_date: Skip PRs older than this (e.g., 90 days ago)
    - skip_before_date: Skip PRs newer than this (e.g., 30 days ago for Phase 2)

    Returns:
        True if PR was actually processed, False if skipped (outside date range).
    """
    pr_number = pr_data.get("number")
    logger.info(
        f"[SYNC_DEBUG] _process_pr() ENTRY: PR #{pr_number}, cutoff={cutoff_date}, skip_before={skip_before_date}"
    )

    # Parse PR created date and check date range
    created_at = _parse_datetime(pr_data.get("createdAt"))
    logger.info(f"[SYNC_DEBUG] PR #{pr_number}: created_at={created_at}")
    if created_at and created_at < cutoff_date:
        logger.info(f"[SYNC_DEBUG] SKIPPING PR #{pr_number} - older than cutoff ({created_at} < {cutoff_date})")
        return False
    if skip_before_date and created_at and created_at > skip_before_date:
        logger.info(
            f"[SYNC_DEBUG] SKIPPING PR #{pr_number} - too recent for Phase 2 ({created_at} > {skip_before_date})"
        )
        return False

    # Get author
    author_data = pr_data.get("author")
    if not author_data:
        raise ValueError("PR has no author data")
    author_login = author_data.get("login")
    author = _get_team_member(team, author_login)

    # Map PR data to model fields (pr_number already extracted at start of function)
    title = pr_data.get("title", "")
    body = pr_data.get("body", "") or ""

    # Detect AI involvement
    is_ai_assisted, ai_tools = _detect_pr_ai_involvement(author_login, title, body)

    pr_defaults = {
        "title": title,
        "body": body,
        "state": _map_pr_state(pr_data.get("state", "OPEN")),
        "pr_created_at": created_at,
        "merged_at": _parse_datetime(pr_data.get("mergedAt")),
        "additions": pr_data.get("additions", 0),
        "deletions": pr_data.get("deletions", 0),
        "author": author,
        "is_ai_assisted": is_ai_assisted,
        "ai_tools_detected": ai_tools,
        "ai_detection_version": PATTERNS_VERSION,
    }

    # Create or update PR
    start_time = time.time()
    pr, created = PullRequest.objects.update_or_create(
        team=team,
        github_pr_id=pr_number,
        github_repo=github_repo,
        defaults=pr_defaults,
    )
    duration_ms = (time.time() - start_time) * 1000
    result.prs_synced += 1
    logger.debug(f"{'Created' if created else 'Updated'} PR #{pr_number}")

    # Log DB write for PR
    _get_sync_logger().info(
        "sync.db.write",
        extra={
            "entity_type": "pull_request",
            "was_created": 1 if created else 0,
            "was_updated": 0 if created else 1,
            "duration_ms": duration_ms,
        },
    )

    # Update timing metrics
    _update_pr_timing_metrics(pr)

    # Count nested data for logging
    reviews_nodes = pr_data.get("reviews", {}).get("nodes", [])
    commits_nodes = pr_data.get("commits", {}).get("nodes", [])
    files_nodes = pr_data.get("files", {}).get("nodes", [])

    # Log PR processed event
    _get_sync_logger().info(
        "sync.pr.processed",
        extra={
            "pr_id": pr.id,
            "pr_number": pr_number,
            "reviews_count": len(reviews_nodes),
            "commits_count": len(commits_nodes),
            "files_count": len(files_nodes),
        },
    )

    # Process nested data with debug logging
    logger.info(
        f"[SYNC_DEBUG] PR #{pr_number}: Processing {len(files_nodes)} files, "
        f"{len(commits_nodes)} commits, {len(reviews_nodes)} reviews"
    )

    try:
        _process_reviews(team, pr, reviews_nodes, result)
        logger.info(f"[SYNC_DEBUG] PR #{pr_number}: After _process_reviews, reviews_synced={result.reviews_synced}")
    except Exception as e:
        logger.error(f"[SYNC_DEBUG] PR #{pr_number}: _process_reviews FAILED: {type(e).__name__}: {e}")
        raise

    try:
        _process_commits(team, pr, github_repo, commits_nodes, result)
        logger.info(f"[SYNC_DEBUG] PR #{pr_number}: After _process_commits, commits_synced={result.commits_synced}")
    except Exception as e:
        logger.error(f"[SYNC_DEBUG] PR #{pr_number}: _process_commits FAILED: {type(e).__name__}: {e}")
        raise

    try:
        _process_files(team, pr, files_nodes, result)
        logger.info(f"[SYNC_DEBUG] PR #{pr_number}: After _process_files, files_synced={result.files_synced}")
    except Exception as e:
        logger.error(f"[SYNC_DEBUG] PR #{pr_number}: _process_files FAILED: {type(e).__name__}: {e}")
        raise

    return True


def _process_reviews(
    team,
    pr: PullRequest,
    review_nodes: list[dict],
    result: SyncResult,
) -> None:
    """Process PR reviews from GraphQL response."""
    earliest_review_at = None

    for review_data in review_nodes:
        review_id = review_data.get("databaseId")
        reviewer_login = review_data.get("author", {}).get("login") if review_data.get("author") else None
        reviewer = _get_team_member(team, reviewer_login)

        submitted_at = _parse_datetime(review_data.get("submittedAt"))

        # Track earliest review timestamp
        if submitted_at and (earliest_review_at is None or submitted_at < earliest_review_at):
            earliest_review_at = submitted_at

        review_defaults = {
            "state": _map_review_state(review_data.get("state", "COMMENTED")),
            "body": review_data.get("body", "") or "",
            "submitted_at": submitted_at,
            "reviewer": reviewer,
            "pull_request": pr,
        }

        logger.debug(f"[SYNC_DEBUG] Creating PRReview: team={team.id}, review_id={review_id}")
        try:
            if review_id:
                obj, created = PRReview.objects.update_or_create(
                    team=team,
                    github_review_id=review_id,
                    defaults=review_defaults,
                )
            else:
                # No GitHub ID, create by PR + reviewer + submitted_at
                obj, created = PRReview.objects.update_or_create(
                    team=team,
                    pull_request=pr,
                    reviewer=reviewer,
                    submitted_at=review_defaults["submitted_at"],
                    defaults=review_defaults,
                )
            logger.debug(f"[SYNC_DEBUG] PRReview {'created' if created else 'updated'}: id={obj.id}")
        except Exception as e:
            logger.error(
                f"[SYNC_DEBUG] PRReview update_or_create FAILED for review_id={review_id}: {type(e).__name__}: {e}"
            )
            raise
        result.reviews_synced += 1

    # Update PR's first_review_at and review_time_hours if we found an earlier review
    if earliest_review_at and (pr.first_review_at is None or earliest_review_at < pr.first_review_at):
        pr.first_review_at = earliest_review_at
        pr.review_time_hours = _calculate_time_diff_hours(pr.pr_created_at, earliest_review_at)
        pr.save()


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

        logger.debug(f"[SYNC_DEBUG] Creating Commit: team={team.id}, sha={sha[:8]}")
        try:
            obj, created = Commit.objects.update_or_create(
                team=team,
                github_sha=sha,
                defaults=commit_defaults,
            )
            logger.debug(f"[SYNC_DEBUG] Commit {'created' if created else 'updated'}: id={obj.id}")
        except Exception as e:
            logger.error(f"[SYNC_DEBUG] Commit update_or_create FAILED for {sha[:8]}: {type(e).__name__}: {e}")
            raise
        result.commits_synced += 1


def _process_files(
    team,
    pr: PullRequest,
    file_nodes: list[dict],
    result: SyncResult,
) -> None:
    """Process PR files from GraphQL response."""
    # Log file processing for debugging sync issues
    sync_logger = _get_sync_logger()
    if file_nodes:
        sync_logger.debug(
            "sync.files.processing",
            extra={
                "pr_id": pr.id,
                "pr_number": pr.github_pr_id,
                "file_count": len(file_nodes),
            },
        )
    elif pr.additions > 0 or pr.deletions > 0:
        # Log warning when PR has code changes but no files - potential sync issue
        sync_logger.warning(
            "sync.files.missing",
            extra={
                "pr_id": pr.id,
                "pr_number": pr.github_pr_id,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "hint": "PR has code changes but files array is empty",
            },
        )

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

        logger.debug(f"[SYNC_DEBUG] Creating PRFile: team={team.id}, pr={pr.id}, filename={filename}")
        try:
            obj, created = PRFile.objects.update_or_create(
                team=team,
                pull_request=pr,
                filename=filename,
                defaults=file_defaults,
            )
            logger.debug(f"[SYNC_DEBUG] PRFile {'created' if created else 'updated'}: id={obj.id}")
        except Exception as e:
            logger.error(f"[SYNC_DEBUG] PRFile update_or_create FAILED for {filename}: {type(e).__name__}: {e}")
            raise
        result.files_synced += 1

    # Log completion of file processing
    if file_nodes:
        sync_logger.info(
            "sync.files.saved",
            extra={
                "pr_id": pr.id,
                "pr_number": pr.github_pr_id,
                "files_saved": len(file_nodes),
            },
        )


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
    client = GitHubGraphQLClient(access_token)

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
    title = pr_data.get("title", "")
    body = pr_data.get("body", "") or ""

    # Detect AI involvement
    is_ai_assisted, ai_tools = _detect_pr_ai_involvement(author_login, title, body)

    pr_defaults = {
        "title": title,
        "body": body,
        "state": _map_pr_state(pr_data.get("state", "OPEN")),
        "pr_created_at": created_at,
        "merged_at": _parse_datetime(pr_data.get("mergedAt")),
        "additions": pr_data.get("additions", 0),
        "deletions": pr_data.get("deletions", 0),
        "author": author,
        "is_ai_assisted": is_ai_assisted,
        "ai_tools_detected": ai_tools,
        "ai_detection_version": PATTERNS_VERSION,
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

    # Update timing metrics
    _update_pr_timing_metrics(pr)

    # Process nested data
    _process_reviews(team, pr, pr_data.get("reviews", {}).get("nodes", []), result)
    _process_commits(team, pr, github_repo, pr_data.get("commits", {}).get("nodes", []), result)
    _process_files(team, pr, pr_data.get("files", {}).get("nodes", []), result)


# =============================================================================
# Search API-based Repository Sync (Accurate Progress)
# =============================================================================


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
    client = GitHubGraphQLClient(access_token)

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
            except GitHubGraphQLRateLimitError as e:
                result.errors.append(f"Rate limit exceeded: {e}")
                await _update_sync_status(tracked_repo_id, "error")
                return result.to_dict()
            except GitHubGraphQLError as e:
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


@sync_to_async
def _set_prs_total(tracked_repo_id: int, total: int) -> None:
    """Set sync_prs_total on TrackedRepository (async-safe)."""
    TrackedRepository.objects.filter(id=tracked_repo_id).update(sync_prs_total=total)  # noqa: TEAM001


@sync_to_async
def _increment_prs_processed(tracked_repo_id: int) -> None:
    """Increment sync_prs_completed on TrackedRepository (async-safe).

    Uses F() expression for atomic increment.
    """
    from django.db.models import F

    TrackedRepository.objects.filter(id=tracked_repo_id).update(  # noqa: TEAM001
        sync_prs_completed=F("sync_prs_completed") + 1
    )


@sync_to_async(thread_sensitive=False)
def _process_pr_from_search_async(
    team_id: int,
    github_repo: str,
    pr_data: dict,
    result: SyncResult,
) -> bool:
    """Process a single PR from Search API response (async wrapper).

    Unlike _process_pr_async, this does NOT apply date filtering since
    the Search API already returns only PRs in the requested date range.

    Returns:
        True if PR was processed successfully.
    """
    from apps.teams.models import Team

    pr_number = pr_data.get("number", "unknown")
    logger.info(f"[SYNC_DEBUG] _process_pr_from_search_async() ENTRY: PR #{pr_number}, team_id={team_id}")

    try:
        team = Team.objects.get(id=team_id)
        logger.info(f"[SYNC_DEBUG] _process_pr_from_search_async() Team lookup OK: {team.name}")
    except Team.DoesNotExist:
        logger.error(f"[SYNC_DEBUG] _process_pr_from_search_async() Team NOT FOUND: {team_id}")
        raise

    return _process_pr_from_search(team, github_repo, pr_data, result)


def _process_pr_from_search(
    team,
    github_repo: str,
    pr_data: dict,
    result: SyncResult,
) -> bool:
    """Process a single PR from Search API response.

    Creates or updates PullRequest and related records (reviews, commits, files).
    Does NOT apply date filtering - Search API handles that.

    Returns:
        True if PR was processed successfully.
    """
    pr_number = pr_data.get("number")
    logger.info(f"[SYNC_DEBUG] _process_pr_from_search() ENTRY: PR #{pr_number}")

    # Parse PR created date
    created_at = _parse_datetime(pr_data.get("createdAt"))

    # Get author
    author_data = pr_data.get("author")
    if not author_data:
        raise ValueError("PR has no author data")
    author_login = author_data.get("login")
    author = _get_team_member(team, author_login)

    # Map PR data to model fields
    title = pr_data.get("title", "")
    body = pr_data.get("body", "") or ""

    # Detect AI involvement
    is_ai_assisted, ai_tools = _detect_pr_ai_involvement(author_login, title, body)

    pr_defaults = {
        "title": title,
        "body": body,
        "state": _map_pr_state(pr_data.get("state", "OPEN")),
        "pr_created_at": created_at,
        "merged_at": _parse_datetime(pr_data.get("mergedAt")),
        "additions": pr_data.get("additions", 0),
        "deletions": pr_data.get("deletions", 0),
        "author": author,
        "is_ai_assisted": is_ai_assisted,
        "ai_tools_detected": ai_tools,
        "ai_detection_version": PATTERNS_VERSION,
    }

    # Create or update PR
    start_time = time.time()
    pr, created = PullRequest.objects.update_or_create(
        team=team,
        github_pr_id=pr_number,
        github_repo=github_repo,
        defaults=pr_defaults,
    )
    duration_ms = (time.time() - start_time) * 1000
    result.prs_synced += 1
    logger.debug(f"{'Created' if created else 'Updated'} PR #{pr_number}")

    # Log DB write for PR
    _get_sync_logger().info(
        "sync.db.write",
        extra={
            "entity_type": "pull_request",
            "was_created": 1 if created else 0,
            "was_updated": 0 if created else 1,
            "duration_ms": duration_ms,
        },
    )

    # Update timing metrics
    _update_pr_timing_metrics(pr)

    # Count nested data for logging
    reviews_nodes = pr_data.get("reviews", {}).get("nodes", [])
    commits_nodes = pr_data.get("commits", {}).get("nodes", [])
    files_nodes = pr_data.get("files", {}).get("nodes", [])

    # Log PR processed event
    _get_sync_logger().info(
        "sync.pr.processed",
        extra={
            "pr_id": pr.id,
            "pr_number": pr_number,
            "reviews_count": len(reviews_nodes),
            "commits_count": len(commits_nodes),
            "files_count": len(files_nodes),
        },
    )

    # Process nested data
    _process_reviews(team, pr, reviews_nodes, result)
    _process_commits(team, pr, github_repo, commits_nodes, result)
    _process_files(team, pr, files_nodes, result)

    return True


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
        await _process_pr_nested_data_async(team_id, pr, full_name, pr_data, result)

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


@sync_to_async
def _get_integration_access_token(integration_id: int) -> str | None:
    """Get access token for a GitHub integration (async-safe)."""
    from apps.integrations.models import GitHubIntegration

    try:
        integration = GitHubIntegration.objects.select_related("credential").get(id=integration_id)  # noqa: TEAM001 - ID from Celery task
        return integration.credential.access_token
    except (GitHubIntegration.DoesNotExist, AttributeError):
        return None


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
