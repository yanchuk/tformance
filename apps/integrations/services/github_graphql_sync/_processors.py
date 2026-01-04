"""PR processing functions for GitHub GraphQL sync.

Contains functions to process PRs, reviews, commits, and files from GraphQL responses.
"""

import logging
import time

from asgiref.sync import sync_to_async

from apps.metrics.models import Commit, PRFile, PRReview, PullRequest, TeamMember
from apps.metrics.processors import _calculate_cycle_time_hours, _calculate_time_diff_hours
from apps.metrics.services.ai_detector import PATTERNS_VERSION, detect_ai_author, detect_ai_in_text

from ._utils import (
    MemberSyncResult,
    SyncResult,
    _get_sync_logger,
    _get_team_member,
    _map_file_status,
    _map_pr_state,
    _map_review_state,
    _parse_datetime,
)

logger = logging.getLogger(__name__)


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


@sync_to_async
def _process_pr_incremental_async(team_id: int, github_repo: str, pr_data: dict, result: SyncResult) -> None:
    """Process a single PR from GraphQL response for incremental sync (async wrapper).

    Unlike full sync, incremental sync does not filter by date - it processes all PRs
    that are returned since they're already filtered by the API.
    """
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)
    _process_pr_incremental(team, github_repo, pr_data, result)


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


@sync_to_async
def _process_member_async(team_id: int, member_data: dict, result: MemberSyncResult) -> None:
    """Process a single organization member from GraphQL response (async wrapper)."""
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)
    _process_member(team, member_data, result)


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
