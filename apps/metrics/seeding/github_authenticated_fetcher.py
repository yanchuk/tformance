"""
Authenticated GitHub PR fetcher for real project demo data seeding.

Fetches comprehensive PR data from public repositories using authenticated
access (5000 requests/hour with PAT). Includes commits, reviews, files,
and check runs for realistic demo data.

Uses serial fetching to comply with GitHub API best practices:
https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

Usage:
    fetcher = GitHubAuthenticatedFetcher()  # Uses GITHUB_SEEDING_TOKENS env var
    prs = fetcher.fetch_prs_with_details("posthog/posthog", max_prs=100)
    contributors = fetcher.get_top_contributors("posthog/posthog", max_count=15)

Environment:
    GITHUB_SEEDING_TOKENS: Comma-separated list of GitHub PATs with public_repo scope
    Generate at: https://github.com/settings/tokens
"""

import contextlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from django.utils import timezone
from github import Auth, Github, GithubException, RateLimitExceededException

from apps.metrics.seeding.checkpoint import SeedingCheckpoint
from apps.metrics.seeding.github_token_pool import AllTokensExhaustedException, GitHubTokenPool

logger = logging.getLogger(__name__)


def is_secondary_rate_limit(exception: GithubException) -> bool:
    """Check if a GitHub exception is a secondary (abuse) rate limit.

    GitHub has two types of rate limits:
    1. Primary: Based on X-RateLimit-Remaining quota (5000/hour)
       - Returns 403 when quota exhausted
       - Has X-RateLimit-Remaining = 0

    2. Secondary (abuse detection): Triggered by rapid requests
       - Returns 403 even with quota remaining
       - Includes Retry-After header

    Args:
        exception: A GithubException to check.

    Returns:
        True if this is a secondary rate limit (has Retry-After header).
    """
    if exception.status != 403:
        return False

    headers = getattr(exception, "headers", {}) or {}
    return "Retry-After" in headers


# Max retries for 403 errors (secondary rate limit)
MAX_RETRIES = 3

# Initial backoff for retries (seconds, doubles each retry)
INITIAL_BACKOFF = 5.0

# Delay between requests for rate limit compliance (seconds)
REQUEST_DELAY = 0.1


@dataclass
class FetchedCommit:
    """Commit data from a GitHub PR."""

    sha: str
    message: str
    author_login: str | None
    author_name: str | None
    committed_at: datetime
    additions: int
    deletions: int


@dataclass
class FetchedReview:
    """Review data from a GitHub PR."""

    github_review_id: int
    reviewer_login: str
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
    submitted_at: datetime
    body: str | None


@dataclass
class FetchedFile:
    """File change data from a GitHub PR."""

    filename: str
    status: str  # added, removed, modified, renamed
    additions: int
    deletions: int
    patch: str | None = None


@dataclass
class FetchedCheckRun:
    """CI/CD check run data from a GitHub PR."""

    github_id: int
    name: str
    status: str  # queued, in_progress, completed
    conclusion: str | None  # success, failure, neutral, cancelled, skipped, timed_out
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class FetchedPRFull:
    """Complete PR data including all related entities."""

    # PR identifiers
    github_pr_id: int
    number: int
    github_repo: str

    # PR metadata
    title: str
    body: str | None
    state: str  # open, closed, merged
    is_merged: bool
    is_draft: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime
    merged_at: datetime | None
    closed_at: datetime | None

    # Size metrics
    additions: int
    deletions: int
    changed_files: int
    commits_count: int

    # Author info
    author_login: str
    author_id: int
    author_name: str | None
    author_avatar_url: str | None

    # Branch info
    head_ref: str  # Source branch name
    base_ref: str  # Target branch name (usually main)

    # Labels
    labels: list[str] = field(default_factory=list)

    # Related data
    commits: list[FetchedCommit] = field(default_factory=list)
    reviews: list[FetchedReview] = field(default_factory=list)
    files: list[FetchedFile] = field(default_factory=list)
    check_runs: list[FetchedCheckRun] = field(default_factory=list)

    # Extracted metadata
    jira_key_from_title: str | None = None
    jira_key_from_branch: str | None = None

    @property
    def first_review_at(self) -> datetime | None:
        """Get timestamp of first review."""
        if not self.reviews:
            return None
        return min(r.submitted_at for r in self.reviews)

    @property
    def review_time_hours(self) -> float | None:
        """Calculate hours from PR creation to first review."""
        first_review = self.first_review_at
        if not first_review:
            return None
        delta = first_review - self.created_at
        return delta.total_seconds() / 3600

    @property
    def cycle_time_hours(self) -> float | None:
        """Calculate hours from PR creation to merge."""
        if not self.merged_at:
            return None
        delta = self.merged_at - self.created_at
        return delta.total_seconds() / 3600


@dataclass
class ContributorInfo:
    """GitHub contributor information for TeamMember creation."""

    github_id: int
    github_login: str
    display_name: str | None
    email: str | None
    avatar_url: str | None
    pr_count: int = 0


class GitHubAuthenticatedFetcher:
    """Fetches comprehensive PR data with authenticated GitHub access.

    Uses a Personal Access Token (PAT) for 5000 requests/hour rate limit.
    Token is read from GITHUB_SEEDING_TOKENS environment variable (comma-separated).

    Attributes:
        JIRA_KEY_PATTERN: Regex pattern for extracting Jira issue keys.
    """

    JIRA_KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9]+-\d+")

    def __init__(
        self,
        token: str | None = None,
        tokens: list[str] | None = None,
        progress_callback: Any | None = None,
        checkpoint_file: str | None = None,
    ):
        """Initialize the fetcher with authenticated client.

        Args:
            token: GitHub PAT. If None, reads from GITHUB_SEEDING_TOKENS env var.
            tokens: List of GitHub PATs for token pooling. If provided, uses GitHubTokenPool.
            progress_callback: Optional callback for progress updates.
                             Called as callback(step, current, total, message).
            checkpoint_file: Optional path to checkpoint file for resume capability.

        Raises:
            ValueError: If no token is provided or found in environment, or if both token and tokens are provided.
        """
        # Validate that both token and tokens aren't provided
        if token is not None and tokens is not None:
            raise ValueError("Cannot provide both 'token' and 'tokens' parameters. Choose one.")

        # Initialize with token pool if tokens provided
        if tokens is not None:
            self._token_pool = GitHubTokenPool(tokens=tokens)
            self.token = tokens[0]  # Store first token for backward compatibility
            self._client = None  # Will be set lazily via _get_current_client()
        elif token is not None:
            # Single token mode (backward compatible)
            self.token = token
            self._token_pool = GitHubTokenPool(tokens=[token])
            self._client = Github(auth=Auth.Token(self.token))
        else:
            # Use environment variables - token pool handles both singular and plural
            self._token_pool = GitHubTokenPool()  # Loads from env vars
            self.token = self._token_pool._tokens[0].token  # Store first for backward compat
            self._client = None  # Will be set lazily via _get_current_client()

        self._cache: dict[str, Any] = {}
        self.api_calls_made = 0
        self.progress_callback = progress_callback
        self.checkpoint_file = checkpoint_file
        self._checkpoint: SeedingCheckpoint | None = None

        # Log rate limit status (only if single token mode)
        if self._client is not None:
            self._log_rate_limit()

    def _report_progress(self, step: str, current: int, total: int, message: str):
        """Report progress via callback if available."""
        if self.progress_callback:
            self.progress_callback(step, current, total, message)

    def _get_current_client(self) -> Github:
        """Get the current best client from the token pool.

        Returns:
            Github client with the most remaining quota.

        Raises:
            AllTokensExhaustedException: If all tokens are rate-limited.
        """
        client = self._token_pool.get_best_client()
        self._client = client  # Update for backward compatibility
        return client

    def _log_rate_limit(self):
        """Log current rate limit status."""
        try:
            rate_limit = self._client.get_rate_limit()
            remaining = rate_limit.rate.remaining
            limit = rate_limit.rate.limit
            reset_time = rate_limit.rate.reset

            logger.info(
                "GitHub API rate limit: %d/%d remaining, resets at %s",
                remaining,
                limit,
                reset_time.isoformat(),
            )

            if remaining < 100:
                logger.warning("Low rate limit remaining: %d", remaining)

        except GithubException as e:
            logger.warning("Failed to get rate limit: %s", e)

    def get_rate_limit_remaining(self) -> int:
        """Get remaining API requests before rate limit.

        Returns:
            Number of requests remaining across all tokens in the pool.
        """
        try:
            # Use token pool's total remaining when using multiple tokens
            return self._token_pool.total_remaining
        except GithubException:
            return 0

    def _extract_jira_key(self, text: str | None) -> str | None:
        """Extract Jira issue key from text (title or branch name)."""
        if not text:
            return None
        match = self.JIRA_KEY_PATTERN.search(text)
        return match.group() if match else None

    def get_top_contributors(
        self,
        repo_name: str,
        max_count: int = 15,
        since: datetime | None = None,
    ) -> list[ContributorInfo]:
        """Get top contributors by PR count for a repository.

        Args:
            repo_name: Repository in "owner/repo" format.
            max_count: Maximum contributors to return.
            since: Only count PRs after this date.

        Returns:
            List of ContributorInfo sorted by PR count descending.
        """
        cache_key = f"contributors:{repo_name}"
        if cache_key in self._cache:
            return self._cache[cache_key][:max_count]

        try:
            client = self._get_current_client()
            repo = client.get_repo(repo_name)

            # Get PRs to count per author
            since = since or (timezone.now() - timedelta(days=90))
            pulls = repo.get_pulls(state="all", sort="updated", direction="desc")

            # Count PRs per author
            author_prs: dict[str, dict] = {}

            for pr in pulls:
                # Stop if PR is older than since date
                if pr.created_at.replace(tzinfo=UTC) < since:
                    break

                if not pr.user:
                    continue

                login = pr.user.login

                # Skip bot users (they don't have user profiles)
                if login.endswith("[bot]") or login in ("Copilot", "dependabot"):
                    continue

                if login not in author_prs:
                    # Wrap in try/catch - accessing .name triggers API call that can 404
                    try:
                        display_name = pr.user.name
                    except GithubException:
                        display_name = None

                    author_prs[login] = {
                        "github_id": pr.user.id,
                        "github_login": login,
                        "display_name": display_name,
                        "avatar_url": pr.user.avatar_url,
                        "pr_count": 0,
                    }
                author_prs[login]["pr_count"] += 1

            # Sort by PR count and convert to ContributorInfo
            sorted_authors = sorted(
                author_prs.values(),
                key=lambda x: x["pr_count"],
                reverse=True,
            )

            contributors = []
            for author in sorted_authors[:max_count]:
                # Fetch full user details for name/email
                try:
                    user = client.get_user(author["github_login"])
                    contributors.append(
                        ContributorInfo(
                            github_id=author["github_id"],
                            github_login=author["github_login"],
                            display_name=user.name or author["github_login"],
                            email=user.email,
                            avatar_url=author["avatar_url"],
                            pr_count=author["pr_count"],
                        )
                    )
                except GithubException:
                    # Fall back to basic info if user fetch fails
                    contributors.append(
                        ContributorInfo(
                            github_id=author["github_id"],
                            github_login=author["github_login"],
                            display_name=author["display_name"] or author["github_login"],
                            email=None,
                            avatar_url=author["avatar_url"],
                            pr_count=author["pr_count"],
                        )
                    )

            self._cache[cache_key] = contributors
            logger.info("Found %d contributors in %s", len(contributors), repo_name)
            return contributors

        except RateLimitExceededException:
            logger.error("GitHub rate limit exceeded while fetching contributors")
            return []

        except GithubException as e:
            logger.error("Failed to fetch contributors from %s: %s", repo_name, e)
            return []

    def _load_checkpoint(self, repo_name: str) -> SeedingCheckpoint:
        """Load checkpoint for the given repo.

        Args:
            repo_name: Repository in "owner/repo" format.

        Returns:
            Loaded checkpoint or new empty checkpoint.
        """
        if self.checkpoint_file:
            self._checkpoint = SeedingCheckpoint.load(self.checkpoint_file, repo_name)
        else:
            self._checkpoint = SeedingCheckpoint(repo=repo_name)
        return self._checkpoint

    def _save_checkpoint(self) -> None:
        """Save current checkpoint to file if configured."""
        if self.checkpoint_file and self._checkpoint:
            self._checkpoint.save(self.checkpoint_file)

    def fetch_prs_with_details(
        self,
        repo_name: str,
        since: datetime | None = None,
        max_prs: int = 500,
        include_open: bool = False,
        parallel: bool = True,  # Deprecated: kept for backward compatibility, always uses serial
    ) -> list[FetchedPRFull]:
        """Fetch PRs with complete details (commits, reviews, files, checks).

        Uses serial fetching to comply with GitHub API best practices.
        Supports checkpointing for resume after rate limiting.

        Args:
            repo_name: Repository in "owner/repo" format.
            since: Only fetch PRs updated after this date.
            max_prs: Maximum PRs to fetch.
            include_open: Include open PRs (default: only closed/merged).
            parallel: Deprecated, ignored. Always uses serial fetching.

        Returns:
            List of FetchedPRFull with all related data.
        """
        since = since or (timezone.now() - timedelta(days=90))

        # Load checkpoint for resume capability
        checkpoint = self._load_checkpoint(repo_name)

        # Retry loop for token switching
        # Allow retries up to the number of tokens available (with a reasonable max)
        max_retries = 10  # Reasonable upper limit to prevent infinite loops
        retry_count = 0

        while retry_count < max_retries:
            try:
                client = self._get_current_client()
                repo = client.get_repo(repo_name)
                state = "all" if include_open else "closed"
                pulls = repo.get_pulls(state=state, sort="updated", direction="desc")

                # First pass: collect PR objects that match criteria
                pr_objects = []
                skipped_from_checkpoint = 0
                logger.info("Fetching PRs from %s (max: %d, since: %s)", repo_name, max_prs, since.date())

                for pr in pulls:
                    if len(pr_objects) >= max_prs:
                        break

                    # Skip if PR is older than since date
                    pr_updated = pr.updated_at.replace(tzinfo=UTC)
                    if pr_updated < since:
                        break

                    # Skip drafts
                    if pr.draft:
                        continue

                    # Skip PRs already in checkpoint
                    if checkpoint.is_fetched(pr.number):
                        skipped_from_checkpoint += 1
                        continue

                    pr_objects.append(pr)

                if skipped_from_checkpoint > 0:
                    logger.info(
                        "Skipped %d PRs from checkpoint, %d new PRs to fetch",
                        skipped_from_checkpoint,
                        len(pr_objects),
                    )
                else:
                    logger.info("Found %d PRs to fetch details for", len(pr_objects))

                # Update checkpoint with total PRs found
                checkpoint.total_prs_found = len(pr_objects) + skipped_from_checkpoint

                # Always use serial fetching per GitHub API best practices
                result = self._fetch_prs(pr_objects, repo_name)

                # Mark checkpoint as completed and save
                if self.checkpoint_file and self._checkpoint:
                    self._checkpoint.mark_completed(self.checkpoint_file)

                return result

            except RateLimitExceededException as e:
                # Extract reset time from exception headers
                reset_time = None
                if hasattr(e, "headers") and "X-RateLimit-Reset" in e.headers:
                    reset_timestamp = int(e.headers["X-RateLimit-Reset"])
                    reset_time = datetime.fromtimestamp(reset_timestamp, tz=UTC)
                else:
                    reset_time = datetime.now(UTC) + timedelta(hours=1)

                # Mark the client that hit the rate limit
                self._token_pool.mark_rate_limited(client, reset_time)
                logger.warning("Rate limit hit, switching to next token...")

                # Increment retry counter
                retry_count += 1
                # Loop will retry with new token

            except AllTokensExhaustedException:
                logger.error("All GitHub tokens are rate-limited. Cannot fetch PRs.")
                return []

            except GithubException as e:
                # Check if this is a secondary (abuse) rate limit
                if is_secondary_rate_limit(e):
                    headers = getattr(e, "headers", {}) or {}
                    retry_after = int(headers.get("Retry-After", 60))
                    logger.warning(
                        "Secondary rate limit (abuse detection) hit. Waiting %ds before retry...",
                        retry_after,
                    )
                    time.sleep(retry_after)
                    retry_count += 1
                    continue

                logger.error("Failed to fetch PRs from %s: %s", repo_name, e)
                return []

        # If we exhausted all retries, all tokens are rate-limited
        logger.error("All GitHub tokens exhausted after %d retries. Cannot fetch PRs.", retry_count)
        return []

    def _fetch_prs(self, pr_objects: list, repo_name: str) -> list[FetchedPRFull]:
        """Fetch PR details serially per GitHub API best practices.

        Makes requests one at a time to avoid triggering GitHub's abuse detection.
        Includes retry logic with exponential backoff for 403 errors.
        """
        fetched_prs: list[FetchedPRFull] = []
        total = len(pr_objects)

        logger.info("Fetching %d PRs serially (per GitHub API best practices)", total)
        self._report_progress("fetch", 0, total, f"Starting to fetch {total} PRs...")

        for i, pr in enumerate(pr_objects):
            retry_count = 0
            backoff = INITIAL_BACKOFF

            while retry_count <= MAX_RETRIES:
                try:
                    fetched_pr = self._fetch_pr_details(pr, repo_name)
                    fetched_prs.append(fetched_pr)

                    # Update checkpoint after each successful fetch
                    if self._checkpoint:
                        self._checkpoint.add_fetched_pr(fetched_pr.number)
                        self._save_checkpoint()

                    # Report progress every 10 PRs
                    if (i + 1) % 10 == 0 or i + 1 == total:
                        self._report_progress(
                            "fetch",
                            i + 1,
                            total,
                            f"Fetched {i + 1}/{total} PRs ({len(fetched_prs)} successful)",
                        )

                    # Log progress every 50 PRs
                    if (i + 1) % 50 == 0:
                        remaining = self.get_rate_limit_remaining()
                        logger.info(
                            "Processed %d/%d PRs (rate limit: %d remaining)",
                            i + 1,
                            total,
                            remaining,
                        )

                    # Small delay between requests for rate limit compliance
                    time.sleep(REQUEST_DELAY)
                    break  # Success, move to next PR

                except GithubException as e:
                    if e.status == 403 and retry_count < MAX_RETRIES:
                        # Check for retry-after header
                        headers = getattr(e, "headers", {}) or {}
                        retry_after = int(headers.get("Retry-After", backoff))
                        retry_count += 1
                        logger.warning(
                            "Rate limit hit on PR #%d. Retry %d/%d after %ds...",
                            pr.number,
                            retry_count,
                            MAX_RETRIES,
                            retry_after,
                        )
                        time.sleep(retry_after)
                        backoff *= 2  # Exponential backoff for next retry
                    else:
                        logger.warning("Failed to fetch PR #%d: %s", pr.number, e)
                        break  # Give up on this PR

        # Sort by created_at to maintain chronological order
        with contextlib.suppress(AttributeError, TypeError):
            fetched_prs.sort(key=lambda x: x.created_at, reverse=True)

        logger.info("Fetched %d PRs from %s (serial)", len(fetched_prs), repo_name)
        return fetched_prs

    def _fetch_pr_details(self, pr, repo_name: str) -> FetchedPRFull:
        """Fetch all details for a single PR.

        Fetches commits, reviews, files, and check runs serially per GitHub API best practices.
        """
        # Determine state
        if pr.merged:
            state = "merged"
        elif pr.state == "closed":
            state = "closed"
        else:
            state = "open"

        # Fetch commits, reviews, files, check runs serially
        commits = self._fetch_commits(pr)
        reviews = self._fetch_reviews(pr)
        files = self._fetch_files(pr)
        check_runs = self._fetch_check_runs(pr)

        # Extract Jira keys
        jira_from_title = self._extract_jira_key(pr.title)
        jira_from_branch = self._extract_jira_key(pr.head.ref)

        # Build timestamps with timezone
        created_at = pr.created_at.replace(tzinfo=UTC)
        updated_at = pr.updated_at.replace(tzinfo=UTC)
        merged_at = pr.merged_at.replace(tzinfo=UTC) if pr.merged_at else None
        closed_at = pr.closed_at.replace(tzinfo=UTC) if pr.closed_at else None

        return FetchedPRFull(
            github_pr_id=pr.id,
            number=pr.number,
            github_repo=repo_name,
            title=pr.title,
            body=pr.body,
            state=state,
            is_merged=pr.merged,
            is_draft=pr.draft,
            created_at=created_at,
            updated_at=updated_at,
            merged_at=merged_at,
            closed_at=closed_at,
            additions=pr.additions,
            deletions=pr.deletions,
            changed_files=pr.changed_files,
            commits_count=pr.commits,
            author_login=pr.user.login if pr.user else "unknown",
            author_id=pr.user.id if pr.user else 0,
            author_name=pr.user.name if pr.user else None,
            author_avatar_url=pr.user.avatar_url if pr.user else None,
            head_ref=pr.head.ref,
            base_ref=pr.base.ref,
            labels=[label.name for label in pr.labels],
            commits=commits,
            reviews=reviews,
            files=files,
            check_runs=check_runs,
            jira_key_from_title=jira_from_title,
            jira_key_from_branch=jira_from_branch,
        )

    def _fetch_commits(self, pr) -> list[FetchedCommit]:
        """Fetch commits for a PR."""
        commits = []
        try:
            for commit in pr.get_commits():
                author_login = commit.author.login if commit.author else None
                author_name = commit.commit.author.name if commit.commit.author else None
                committed_at = commit.commit.author.date if commit.commit.author else pr.created_at
                committed_at = committed_at.replace(tzinfo=UTC)

                commits.append(
                    FetchedCommit(
                        sha=commit.sha,
                        message=commit.commit.message,
                        author_login=author_login,
                        author_name=author_name,
                        committed_at=committed_at,
                        additions=commit.stats.additions if commit.stats else 0,
                        deletions=commit.stats.deletions if commit.stats else 0,
                    )
                )
        except GithubException as e:
            logger.debug("Failed to fetch commits for PR #%d: %s", pr.number, e)
        return commits

    def _fetch_reviews(self, pr) -> list[FetchedReview]:
        """Fetch reviews for a PR."""
        reviews = []
        try:
            for review in pr.get_reviews():
                if not review.user:
                    continue
                submitted_at = (
                    review.submitted_at.replace(tzinfo=UTC)
                    if review.submitted_at
                    else pr.created_at.replace(tzinfo=UTC)
                )

                reviews.append(
                    FetchedReview(
                        github_review_id=review.id,
                        reviewer_login=review.user.login,
                        state=review.state,  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
                        submitted_at=submitted_at,
                        body=review.body,
                    )
                )
        except GithubException as e:
            logger.debug("Failed to fetch reviews for PR #%d: %s", pr.number, e)
        return reviews

    def _fetch_files(self, pr) -> list[FetchedFile]:
        """Fetch file changes for a PR."""
        files = []
        try:
            for file in pr.get_files():
                files.append(
                    FetchedFile(
                        filename=file.filename,
                        status=file.status,  # added, removed, modified, renamed
                        additions=file.additions,
                        deletions=file.deletions,
                        patch=None,  # Skip patch content to save memory
                    )
                )
        except GithubException as e:
            logger.debug("Failed to fetch files for PR #%d: %s", pr.number, e)
        return files

    def _fetch_check_runs(self, pr) -> list[FetchedCheckRun]:
        """Fetch CI check runs for PR head commit."""
        check_runs = []
        try:
            # Get the head commit
            commits = list(pr.get_commits())
            if not commits:
                return []

            head_commit = commits[-1]

            # Get check runs for the head commit
            for check_run in head_commit.get_check_runs():
                started_at = check_run.started_at.replace(tzinfo=UTC) if check_run.started_at else None
                completed_at = check_run.completed_at.replace(tzinfo=UTC) if check_run.completed_at else None

                check_runs.append(
                    FetchedCheckRun(
                        github_id=check_run.id,
                        name=check_run.name,
                        status=check_run.status,
                        conclusion=check_run.conclusion,
                        started_at=started_at,
                        completed_at=completed_at,
                    )
                )
        except GithubException as e:
            logger.debug("Failed to fetch check runs for PR #%d: %s", pr.number, e)
        return check_runs

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
