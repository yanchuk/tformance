"""GitHub sync service for fetching data from GitHub repositories."""

from datetime import datetime

from github import Github, GithubException

from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.integrations.services.github_rate_limit import should_pause_for_rate_limit
from apps.integrations.services.jira_utils import extract_jira_key

__all__ = [
    "GitHubOAuthError",
    "get_repository_pull_requests",
    "get_pull_request_reviews",
    "get_updated_pull_requests",
    "sync_repository_history",
    "sync_repository_incremental",
    "sync_pr_commits",
    "sync_pr_check_runs",
    "sync_pr_files",
    "sync_repository_deployments",
    "sync_pr_issue_comments",
    "sync_pr_review_comments",
]


def _convert_pr_to_dict(pr) -> dict:
    """Convert PyGithub PullRequest object to dictionary with all required attributes.

    Args:
        pr: PyGithub PullRequest object

    Returns:
        Dictionary with PR data in standardized format
    """
    # Extract jira_key from title, fall back to branch name
    jira_key = extract_jira_key(pr.title) or extract_jira_key(pr.head.ref) or ""

    return {
        "id": pr.id,
        "number": pr.number,
        "title": pr.title,
        "state": pr.state,
        "merged": pr.merged,
        "merged_at": pr.merged_at.isoformat().replace("+00:00", "Z") if pr.merged_at else None,
        "created_at": pr.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": pr.updated_at.isoformat().replace("+00:00", "Z"),
        "additions": pr.additions,
        "deletions": pr.deletions,
        "commits": pr.commits,
        "changed_files": pr.changed_files,
        "user": {
            "id": pr.user.id,
            "login": pr.user.login,
        },
        "base": {
            "ref": pr.base.ref,
        },
        "head": {
            "ref": pr.head.ref,
            "sha": pr.head.sha,
        },
        "html_url": pr.html_url,
        "jira_key": jira_key,
    }


def get_repository_pull_requests(
    access_token: str,
    repo_full_name: str,
    state: str = "all",
    per_page: int = 100,
) -> list[dict]:
    """Fetch pull requests from a GitHub repository.

    Args:
        access_token: GitHub OAuth access token
        repo_full_name: Repository in "owner/repo" format
        state: PR state filter ("all", "open", "closed")
        per_page: Results per page (max 100, ignored - PyGithub handles pagination)

    Returns:
        List of PR dictionaries with all required attributes

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository
        repo = github.get_repo(repo_full_name)

        # Get pull requests - PyGithub returns PaginatedList that handles pagination automatically
        prs = repo.get_pulls(state=state)

        # Convert each PR to dict with all required attributes
        return [_convert_pr_to_dict(pr) for pr in prs]

    except GithubException as e:
        raise GitHubOAuthError(f"GitHub API error: {e.status}") from e


def get_updated_pull_requests(
    access_token: str,
    repo_full_name: str,
    since: datetime,
) -> list[dict]:
    """Fetch pull requests updated since a given datetime.

    GitHub's Pull Requests API doesn't have a 'since' parameter, so we use
    the Issues API which does have 'since' and filter to only return issues
    that are pull requests.

    Args:
        access_token: GitHub OAuth access token
        repo_full_name: Repository in "owner/repo" format
        since: Only return PRs updated at or after this datetime

    Returns:
        List of PR dictionaries with all required attributes (same format as get_repository_pull_requests)

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository
        repo = github.get_repo(repo_full_name)

        # Get issues updated since datetime (includes PRs)
        # PyGithub returns PaginatedList that handles pagination automatically
        issues = repo.get_issues(since=since, state="all")

        # Filter to only issues that are pull requests and fetch full PR details
        pr_list = []
        for issue in issues:
            # Check if issue is a pull request (has pull_request attribute)
            if issue.pull_request is None:
                continue

            # Fetch full PR details (Issues API doesn't include merged status, etc.)
            pr = repo.get_pull(issue.number)

            # Convert PR to dict with all required attributes (same format as get_repository_pull_requests)
            pr_list.append(_convert_pr_to_dict(pr))

        return pr_list

    except GithubException as e:
        raise GitHubOAuthError(f"GitHub API error: {e.status}") from e


def get_pull_request_reviews(
    access_token: str,
    repo_full_name: str,
    pr_number: int,
) -> list[dict]:
    """Fetch reviews for a specific pull request.

    Args:
        access_token: GitHub OAuth access token
        repo_full_name: Repository in "owner/repo" format
        pr_number: Pull request number

    Returns:
        List of review dictionaries with all required attributes

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository and pull request
        repo = github.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)

        # Get reviews - PyGithub returns PaginatedList that handles pagination automatically
        reviews = pr.get_reviews()

        # Convert each review to dict with all required attributes
        review_list = []
        for review in reviews:
            review_dict = {
                "id": review.id,
                "user": {
                    "id": review.user.id,
                    "login": review.user.login,
                },
                "body": review.body,
                "state": review.state,
                "submitted_at": review.submitted_at.isoformat().replace("+00:00", "Z"),
            }
            review_list.append(review_dict)

        return review_list

    except GithubException as e:
        raise GitHubOAuthError(f"GitHub API error: {e.status}") from e


def _sync_pr_reviews(
    pr: "PullRequest",  # noqa: F821
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync reviews for a single pull request.

    Args:
        pr: PullRequest instance to sync reviews for
        pr_number: GitHub PR number
        access_token: Decrypted GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of reviews successfully synced
    """
    from apps.metrics.models import PRReview
    from apps.metrics.processors import (
        _calculate_time_diff_hours,
        _get_team_member_by_github_id,
        _parse_github_timestamp,
    )

    reviews_synced = 0

    try:
        reviews_data = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Track earliest review time for this PR
        earliest_review_at = None

        for review_data in reviews_data:
            try:
                # Create or update review record
                PRReview.objects.update_or_create(
                    team=team,
                    github_review_id=review_data["id"],
                    defaults={
                        "pull_request": pr,
                        "reviewer": _get_team_member_by_github_id(team, str(review_data["user"]["id"])),
                        "state": review_data["state"].lower(),
                        "submitted_at": _parse_github_timestamp(review_data["submitted_at"]),
                    },
                )
                reviews_synced += 1

                # Track earliest review time
                submitted_at = _parse_github_timestamp(review_data["submitted_at"])
                if submitted_at and (earliest_review_at is None or submitted_at < earliest_review_at):
                    earliest_review_at = submitted_at

            except Exception as e:
                # Log error but continue processing other reviews
                error_msg = f"Failed to sync review {review_data.get('id', 'unknown')} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

        # Update PR metrics if we found an earlier review
        if earliest_review_at and (pr.first_review_at is None or earliest_review_at < pr.first_review_at):
            pr.first_review_at = earliest_review_at
            pr.review_time_hours = _calculate_time_diff_hours(pr.pr_created_at, earliest_review_at)
            pr.save()

    except Exception as e:
        # Log error but continue processing other PRs
        error_msg = f"Failed to fetch reviews for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return reviews_synced


def sync_pr_commits(
    pr: "PullRequest",  # noqa: F821
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync commits for a single pull request.

    Args:
        pr: PullRequest instance to sync commits for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of commits successfully synced
    """
    from apps.metrics.models import Commit
    from apps.metrics.processors import _get_team_member_by_github_id, _parse_github_timestamp

    commits_synced = 0

    try:
        # Create GitHub client and get PR
        github = Github(access_token)
        repo = github.get_repo(repo_full_name)
        github_pr = repo.get_pull(pr_number)

        # Iterate over commits
        for commit in github_pr.get_commits():
            try:
                # Extract commit data
                sha = commit.sha
                message = commit.commit.message
                committed_at = _parse_github_timestamp(commit.commit.author.date.isoformat().replace("+00:00", "Z"))
                additions = commit.stats.additions
                deletions = commit.stats.deletions

                # Look up author by github_id (may be None)
                author = None
                if commit.author is not None:
                    author = _get_team_member_by_github_id(team, str(commit.author.id))

                # Create or update commit record
                Commit.objects.update_or_create(
                    team=team,
                    github_sha=sha,
                    defaults={
                        "github_repo": repo_full_name,
                        "author": author,
                        "message": message,
                        "committed_at": committed_at,
                        "additions": additions,
                        "deletions": deletions,
                        "pull_request": pr,
                    },
                )
                commits_synced += 1

            except Exception as e:
                # Log error but continue processing other commits
                error_msg = f"Failed to sync commit {commit.sha[:8]} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error if we can't fetch commits at all
        error_msg = f"Failed to fetch commits for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return commits_synced


def sync_pr_check_runs(
    pr: "PullRequest",  # noqa: F821
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync CI/CD check runs for a pull request.

    Args:
        pr: PullRequest instance to sync check runs for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of check runs successfully synced
    """
    from apps.metrics.models import PRCheckRun

    check_runs_synced = 0

    try:
        # Create GitHub client and get PR
        github = Github(access_token)
        repo = github.get_repo(repo_full_name)
        github_pr = repo.get_pull(pr_number)

        # Get head commit SHA
        head_sha = github_pr.head.sha

        # Get commit object
        commit = repo.get_commit(head_sha)

        # Get check runs for this commit
        check_runs = commit.get_check_runs()

        # Iterate over check runs
        for check_run in check_runs:
            try:
                # Calculate duration if both timestamps present
                duration_seconds = None
                if check_run.started_at and check_run.completed_at:
                    duration = (check_run.completed_at - check_run.started_at).total_seconds()
                    duration_seconds = int(duration)

                # Create or update check run record
                PRCheckRun.objects.update_or_create(
                    team=team,
                    github_check_run_id=check_run.id,
                    defaults={
                        "pull_request": pr,
                        "name": check_run.name,
                        "status": check_run.status,
                        "conclusion": check_run.conclusion,
                        "started_at": check_run.started_at,
                        "completed_at": check_run.completed_at,
                        "duration_seconds": duration_seconds,
                    },
                )
                check_runs_synced += 1

            except Exception as e:
                # Log error but continue processing other check runs
                error_msg = f"Failed to sync check run {check_run.id} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error if we can't fetch check runs at all
        error_msg = f"Failed to fetch check runs for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return check_runs_synced


def sync_pr_files(
    pr: "PullRequest",  # noqa: F821
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync files changed in a PR from GitHub.

    Args:
        pr: PullRequest instance to sync files for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of files successfully synced
    """
    from apps.metrics.models import PRFile

    files_synced = 0

    try:
        # Create GitHub client and get PR
        github = Github(access_token)
        repo = github.get_repo(repo_full_name)
        github_pr = repo.get_pull(pr_number)

        # Fetch files from GitHub API
        files = github_pr.get_files()

        # Iterate over files
        for file in files:
            try:
                # Create or update file record
                PRFile.objects.update_or_create(
                    team=team,
                    pull_request=pr,
                    filename=file.filename,
                    defaults={
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "changes": file.changes,
                        "file_category": PRFile.categorize_file(file.filename),
                    },
                )
                files_synced += 1

            except Exception as e:
                # Log error but continue processing other files
                error_msg = f"Failed to sync file {file.filename} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error if we can't fetch files at all
        error_msg = f"Failed to fetch files for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return files_synced


def _process_prs(
    prs_data: list[dict],
    tracked_repo: "TrackedRepository",  # noqa: F821
    access_token: str,
) -> dict:
    """Process a list of PR data and sync to database.

    Args:
        prs_data: List of PR dictionaries from GitHub API
        tracked_repo: TrackedRepository instance to sync
        access_token: Decrypted GitHub access token

    Returns:
        Dict with sync stats for PRs, reviews, commits, check_runs, files, comments, rate_limited
    """
    from apps.metrics.models import PullRequest
    from apps.metrics.processors import _map_github_pr_to_fields

    # Create Github client for rate limit checks
    github = Github(access_token)

    prs_synced = 0
    reviews_synced = 0
    commits_synced = 0
    check_runs_synced = 0
    files_synced = 0
    comments_synced = 0
    errors = []
    rate_limited = False

    for pr_data in prs_data:
        try:
            # Extract identifying information
            github_pr_id = pr_data["id"]
            pr_number = pr_data["number"]

            # Map GitHub data to model fields
            pr_fields = _map_github_pr_to_fields(tracked_repo.team, pr_data)

            # Create or update the PR record
            pr, created = PullRequest.objects.update_or_create(
                team=tracked_repo.team,
                github_pr_id=github_pr_id,
                github_repo=tracked_repo.full_name,
                defaults=pr_fields,
            )
            prs_synced += 1

            # Sync reviews for this PR
            reviews_synced += _sync_pr_reviews(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Sync commits for this PR
            commits_synced += sync_pr_commits(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Sync check runs for this PR
            check_runs_synced += sync_pr_check_runs(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Sync files for this PR
            files_synced += sync_pr_files(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Sync comments for this PR (both issue and review comments)
            comments_synced += sync_pr_issue_comments(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )
            comments_synced += sync_pr_review_comments(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Calculate iteration metrics after all data is synced
            calculate_pr_iteration_metrics(pr)

            # Check rate limit after processing this PR
            rate_limit = github.get_rate_limit()
            core = rate_limit.core
            tracked_repo.rate_limit_remaining = core.remaining
            tracked_repo.rate_limit_reset_at = core.reset
            tracked_repo.save()

            # Stop processing if rate limited
            if should_pause_for_rate_limit(core.remaining):
                rate_limited = True
                break

        except Exception as e:
            # Log the error but continue processing other PRs
            pr_number = pr_data.get("number", "unknown")
            error_msg = f"Failed to sync PR #{pr_number}: {str(e)}"
            errors.append(error_msg)
            continue

    return {
        "prs_synced": prs_synced,
        "reviews_synced": reviews_synced,
        "commits_synced": commits_synced,
        "check_runs_synced": check_runs_synced,
        "files_synced": files_synced,
        "comments_synced": comments_synced,
        "errors": errors,
        "rate_limited": rate_limited,
    }


def sync_repository_history(
    tracked_repo: "TrackedRepository",  # noqa: F821
    days_back: int = 90,
) -> dict:
    """Sync historical PR data from a tracked repository.

    Args:
        tracked_repo: TrackedRepository instance to sync
        days_back: Number of days of history to sync (default 90, not yet implemented)

    Returns:
        Dict with sync stats for PRs, reviews, commits, check_runs, files, comments, deployments
    """
    from django.utils import timezone

    # EncryptedTextField auto-decrypts access_token
    access_token = tracked_repo.integration.credential.access_token

    # Fetch PRs from GitHub
    prs_data = get_repository_pull_requests(access_token, tracked_repo.full_name)

    # Process PRs and sync all related data
    result = _process_prs(prs_data, tracked_repo, access_token)

    # Sync deployments for this repository
    result["deployments_synced"] = sync_repository_deployments(
        repo_full_name=tracked_repo.full_name,
        access_token=access_token,
        team=tracked_repo.team,
        errors=result["errors"],
    )

    # Update last_sync_at
    tracked_repo.last_sync_at = timezone.now()
    tracked_repo.save()

    return result


def sync_repository_incremental(tracked_repo: "TrackedRepository") -> dict:  # noqa: F821
    """
    Perform incremental sync for a repository.

    Args:
        tracked_repo: TrackedRepository model instance

    Returns:
        Dict with sync stats for PRs, reviews, commits, check_runs, files, comments, deployments
    """
    # If last_sync_at is None, fall back to full sync
    if tracked_repo.last_sync_at is None:
        return sync_repository_history(tracked_repo)

    from django.utils import timezone

    # EncryptedTextField auto-decrypts access_token
    access_token = tracked_repo.integration.credential.access_token

    # Fetch updated PRs from GitHub since last sync
    prs_data = get_updated_pull_requests(access_token, tracked_repo.full_name, tracked_repo.last_sync_at)

    # Process PRs and sync all related data
    result = _process_prs(prs_data, tracked_repo, access_token)

    # Sync deployments for this repository
    result["deployments_synced"] = sync_repository_deployments(
        repo_full_name=tracked_repo.full_name,
        access_token=access_token,
        team=tracked_repo.team,
        errors=result["errors"],
    )

    # Update last_sync_at
    tracked_repo.last_sync_at = timezone.now()
    tracked_repo.save()

    return result


def sync_repository_deployments(
    repo_full_name: str,
    access_token: str,
    team,
    errors: list,
) -> int:
    """Sync deployments from a GitHub repository.

    Args:
        repo_full_name: Repository in "owner/repo" format
        access_token: GitHub OAuth access token
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of deployments successfully synced
    """
    from apps.metrics.models import Deployment
    from apps.metrics.processors import _get_team_member_by_github_id

    deployments_synced = 0

    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository
        repo = github.get_repo(repo_full_name)

        # Get deployments
        deployments = repo.get_deployments()

        # Process each deployment
        for deployment in deployments:
            try:
                # Get deployment statuses (first is latest)
                statuses = deployment.get_statuses()
                status_list = list(statuses)

                # Use first status if available, otherwise default to "pending"
                status = status_list[0].state if status_list else "pending"

                # Map creator to TeamMember if present
                creator = None
                if deployment.creator:
                    creator = _get_team_member_by_github_id(team, str(deployment.creator.id))

                # Create or update deployment record
                Deployment.objects.update_or_create(
                    team=team,
                    github_deployment_id=deployment.id,
                    defaults={
                        "github_repo": repo_full_name,
                        "environment": deployment.environment,
                        "status": status,
                        "creator": creator,
                        "deployed_at": deployment.created_at,
                        "sha": deployment.sha or "",  # GitHub deployment SHA
                    },
                )
                deployments_synced += 1

            except Exception as e:
                # Log error but continue processing other deployments
                error_msg = f"Failed to sync deployment {deployment.id} for {repo_full_name}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error for the entire repository
        error_msg = f"Failed to fetch deployments for {repo_full_name}: {str(e)}"
        errors.append(error_msg)

    return deployments_synced


def _sync_pr_comments(
    pr: "PullRequest",  # noqa: F821
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
    comment_type: str,
    get_comments_method: str,
) -> int:
    """Generic helper to sync PR comments from GitHub.

    Args:
        pr: PullRequest instance to sync comments for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to
        comment_type: Type of comment ("issue" or "review")
        get_comments_method: PyGithub PR method name to call ("get_issue_comments" or "get_review_comments")

    Returns:
        Number of comments successfully synced
    """
    from apps.metrics.models import PRComment
    from apps.metrics.processors import _get_team_member_by_github_id

    comments_synced = 0

    try:
        # Create GitHub client and get PR
        github = Github(access_token)
        repo = github.get_repo(repo_full_name)
        github_pr = repo.get_pull(pr_number)

        # Fetch comments using the specified method
        comments = getattr(github_pr, get_comments_method)()

        # Iterate over comments
        for comment in comments:
            try:
                # Map author to TeamMember
                author = None
                if comment.user:
                    author = _get_team_member_by_github_id(team, str(comment.user.id))

                # Build defaults dict with common fields
                defaults = {
                    "pull_request": pr,
                    "author": author,
                    "body": comment.body,
                    "comment_type": comment_type,
                    "comment_created_at": comment.created_at,
                    "comment_updated_at": comment.updated_at,
                }

                # Add review-specific fields or set them to None for issue comments
                if comment_type == "review":
                    defaults["path"] = comment.path
                    defaults["line"] = comment.line
                    defaults["in_reply_to_id"] = comment.in_reply_to_id
                else:
                    defaults["path"] = None
                    defaults["line"] = None
                    defaults["in_reply_to_id"] = None

                # Create or update comment record
                PRComment.objects.update_or_create(
                    team=team,
                    github_comment_id=comment.id,
                    defaults=defaults,
                )
                comments_synced += 1

            except Exception as e:
                # Log error but continue processing other comments
                error_msg = f"Failed to sync {comment_type} comment {comment.id} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error if we can't fetch comments at all
        error_msg = f"Failed to fetch {comment_type} comments for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return comments_synced


def sync_pr_issue_comments(
    pr: "PullRequest",  # noqa: F821
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync issue comments (general PR comments) from GitHub.

    Args:
        pr: PullRequest instance to sync comments for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of issue comments successfully synced
    """
    return _sync_pr_comments(
        pr=pr,
        pr_number=pr_number,
        access_token=access_token,
        repo_full_name=repo_full_name,
        team=team,
        errors=errors,
        comment_type="issue",
        get_comments_method="get_issue_comments",
    )


def sync_pr_review_comments(
    pr: "PullRequest",  # noqa: F821
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync review comments (inline code comments) from GitHub.

    Args:
        pr: PullRequest instance to sync comments for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of review comments successfully synced
    """
    return _sync_pr_comments(
        pr=pr,
        pr_number=pr_number,
        access_token=access_token,
        repo_full_name=repo_full_name,
        team=team,
        errors=errors,
        comment_type="review",
        get_comments_method="get_review_comments",
    )


def calculate_pr_iteration_metrics(pr: "PullRequest") -> None:  # noqa: F821
    """Calculate iteration metrics for a pull request from synced data.

    Updates the following fields on the PullRequest:
    - total_comments: Count of all comments on this PR
    - commits_after_first_review: Commits made after the first review
    - review_rounds: Number of changes_requested → commit cycles
    - avg_fix_response_hours: Average time from changes_requested to next commit

    Args:
        pr: PullRequest instance to calculate metrics for
    """
    from decimal import Decimal

    from apps.metrics.models import Commit, PRComment, PRReview

    # Count total comments
    pr.total_comments = PRComment.objects.filter(  # noqa: TEAM001 - filtering by PR which is team-scoped
        pull_request=pr
    ).count()

    # Get first review timestamp
    first_review = (
        PRReview.objects.filter(pull_request=pr)  # noqa: TEAM001 - filtering by PR which is team-scoped
        .order_by("submitted_at")
        .first()
    )

    if first_review and first_review.submitted_at:
        # Count commits after first review
        pr.commits_after_first_review = Commit.objects.filter(  # noqa: TEAM001 - filtering by PR which is team-scoped
            pull_request=pr, committed_at__gt=first_review.submitted_at
        ).count()
    else:
        pr.commits_after_first_review = 0

    # Get all changes_requested reviews and commits in chronological order
    changes_requested_reviews = (
        PRReview.objects.filter(  # noqa: TEAM001 - filtering by PR which is team-scoped
            pull_request=pr, state="changes_requested"
        )
        .order_by("submitted_at")
        .values_list("submitted_at", flat=True)
    )

    commits = (
        Commit.objects.filter(pull_request=pr)  # noqa: TEAM001 - filtering by PR which is team-scoped
        .exclude(committed_at__isnull=True)
        .order_by("committed_at")
        .values_list("committed_at", flat=True)
    )
    commits_list = list(commits)

    # Calculate review rounds and fix response times
    review_rounds = 0
    fix_response_times = []

    for review_time in changes_requested_reviews:
        if review_time is None:
            continue

        # Find the first commit after this review
        for commit_time in commits_list:
            if commit_time > review_time:
                # This is a review round
                review_rounds += 1
                # Calculate response time in hours
                response_time = (commit_time - review_time).total_seconds() / 3600
                fix_response_times.append(response_time)
                break

    pr.review_rounds = review_rounds

    # Calculate average fix response time
    if fix_response_times:
        avg_hours = sum(fix_response_times) / len(fix_response_times)
        pr.avg_fix_response_hours = Decimal(str(round(avg_hours, 2)))
    else:
        pr.avg_fix_response_hours = None

    pr.save(update_fields=["total_comments", "commits_after_first_review", "review_rounds", "avg_fix_response_hours"])


def calculate_reviewer_correlations(team) -> int:
    """Calculate reviewer correlation statistics for a team.

    Analyzes PRReview records to find pairs of reviewers who reviewed the same PRs
    and calculates their agreement/disagreement statistics.

    Args:
        team: Team instance to calculate correlations for

    Returns:
        Number of correlation records created/updated
    """
    from collections import defaultdict
    from itertools import combinations

    from apps.metrics.models import PRReview, ReviewerCorrelation

    # Get all reviews with definitive states (approved or changes_requested)
    reviews = (
        PRReview.objects.filter(team=team, state__in=["approved", "changes_requested"])
        .select_related("pull_request", "reviewer")
        .values("pull_request_id", "reviewer_id", "state")
    )

    # Group reviews by PR
    pr_reviews = defaultdict(dict)  # {pr_id: {reviewer_id: state}}
    for review in reviews:
        pr_id = review["pull_request_id"]
        reviewer_id = review["reviewer_id"]
        state = review["state"]
        # If multiple reviews by same reviewer on same PR, take the last one
        pr_reviews[pr_id][reviewer_id] = state

    # Count agreements/disagreements for each pair
    pair_stats = defaultdict(lambda: {"prs_reviewed_together": 0, "agreements": 0, "disagreements": 0})

    for _pr_id, reviewers in pr_reviews.items():
        # Get all reviewer pairs who reviewed this PR
        reviewer_ids = list(reviewers.keys())
        if len(reviewer_ids) < 2:
            continue

        for r1_id, r2_id in combinations(reviewer_ids, 2):
            # Ensure consistent ordering (smaller ID first)
            if r1_id > r2_id:
                r1_id, r2_id = r2_id, r1_id

            pair_key = (r1_id, r2_id)
            pair_stats[pair_key]["prs_reviewed_together"] += 1

            # Check agreement
            r1_state = reviewers[r1_id]
            r2_state = reviewers[r2_id]
            if r1_state == r2_state:
                pair_stats[pair_key]["agreements"] += 1
            else:
                pair_stats[pair_key]["disagreements"] += 1

    # Clear existing correlations for this team and create fresh ones
    ReviewerCorrelation.objects.filter(team=team).delete()

    correlations_created = 0
    for (r1_id, r2_id), stats in pair_stats.items():
        ReviewerCorrelation.objects.create(
            team=team,
            reviewer_1_id=r1_id,
            reviewer_2_id=r2_id,
            prs_reviewed_together=stats["prs_reviewed_together"],
            agreements=stats["agreements"],
            disagreements=stats["disagreements"],
        )
        correlations_created += 1

    return correlations_created
