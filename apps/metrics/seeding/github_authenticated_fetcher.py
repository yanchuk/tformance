"""
Authenticated GitHub PR fetcher for real project demo data seeding.

Fetches comprehensive PR data from public repositories using authenticated
access (5000 requests/hour with PAT). Includes commits, reviews, files,
and check runs for realistic demo data.

Uses parallel fetching for PR details to improve performance.

Usage:
    fetcher = GitHubAuthenticatedFetcher()  # Uses GITHUB_SEEDING_TOKEN env var
    prs = fetcher.fetch_prs_with_details("posthog/posthog", max_prs=100)
    contributors = fetcher.get_top_contributors("posthog/posthog", max_count=15)

Environment:
    GITHUB_SEEDING_TOKEN: GitHub Personal Access Token with public_repo scope
    Generate at: https://github.com/settings/tokens
"""

import contextlib
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from django.utils import timezone
from github import Github, GithubException, RateLimitExceededException

from apps.metrics.seeding.github_token_pool import AllTokensExhaustedException, GitHubTokenPool

logger = logging.getLogger(__name__)

# Number of parallel threads for fetching PR details
# Keep low to avoid GitHub's secondary rate limits (abuse detection)
MAX_WORKERS = 3

# Delay between batches to avoid rate limiting (seconds)
BATCH_DELAY = 1.0

# Batch size for parallel fetching (process this many PRs then pause)
BATCH_SIZE = 10

# Max retries for 403 errors (secondary rate limit)
MAX_RETRIES = 3

# Initial backoff for retries (seconds, doubles each retry)
INITIAL_BACKOFF = 5.0


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
    Token is read from GITHUB_SEEDING_TOKEN environment variable.

    Attributes:
        JIRA_KEY_PATTERN: Regex pattern for extracting Jira issue keys.
    """

    JIRA_KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9]+-\d+")

    def __init__(
        self,
        token: str | None = None,
        tokens: list[str] | None = None,
        progress_callback: Any | None = None,
    ):
        """Initialize the fetcher with authenticated client.

        Args:
            token: GitHub PAT. If None, reads from GITHUB_SEEDING_TOKEN env var.
            tokens: List of GitHub PATs for token pooling. If provided, uses GitHubTokenPool.
            progress_callback: Optional callback for progress updates.
                             Called as callback(step, current, total, message).

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
            self._client = Github(self.token)
        else:
            # Use environment variable (backward compatible)
            self.token = os.environ.get("GITHUB_SEEDING_TOKEN")
            if not self.token:
                raise ValueError(
                    "GitHub token required. Set GITHUB_SEEDING_TOKEN environment variable "
                    "or pass token parameter. Generate at: https://github.com/settings/tokens"
                )
            self._token_pool = GitHubTokenPool(tokens=[self.token])
            self._client = Github(self.token)

        self._cache: dict[str, Any] = {}
        self.api_calls_made = 0
        self.progress_callback = progress_callback

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
            repo = self._client.get_repo(repo_name)

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
                if login not in author_prs:
                    author_prs[login] = {
                        "github_id": pr.user.id,
                        "github_login": login,
                        "display_name": pr.user.name,
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
                    user = self._client.get_user(author["github_login"])
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

    def fetch_prs_with_details(
        self,
        repo_name: str,
        since: datetime | None = None,
        max_prs: int = 500,
        include_open: bool = False,
        parallel: bool = True,
    ) -> list[FetchedPRFull]:
        """Fetch PRs with complete details (commits, reviews, files, checks).

        Uses parallel fetching by default for improved performance.

        Args:
            repo_name: Repository in "owner/repo" format.
            since: Only fetch PRs updated after this date.
            max_prs: Maximum PRs to fetch.
            include_open: Include open PRs (default: only closed/merged).
            parallel: Use parallel fetching (default: True).

        Returns:
            List of FetchedPRFull with all related data.
        """
        since = since or (timezone.now() - timedelta(days=90))

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

                    pr_objects.append(pr)

                logger.info("Found %d PRs to fetch details for", len(pr_objects))

                if parallel and len(pr_objects) > 1:
                    return self._fetch_prs_parallel(pr_objects, repo_name)
                else:
                    return self._fetch_prs_sequential(pr_objects, repo_name)

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
                logger.error("Failed to fetch PRs from %s: %s", repo_name, e)
                return []

        # If we exhausted all retries, all tokens are rate-limited
        logger.error("All GitHub tokens exhausted after %d retries. Cannot fetch PRs.", retry_count)
        return []

    def _fetch_prs_parallel(self, pr_objects: list, repo_name: str) -> list[FetchedPRFull]:
        """Fetch PR details in parallel using ThreadPoolExecutor with rate limit handling.

        Processes PRs in batches with delays between batches to avoid GitHub's
        secondary rate limits (abuse detection). Includes retry logic for 403 errors.
        """
        fetched_prs: list[FetchedPRFull] = []
        total = len(pr_objects)
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(
            "Fetching %d PRs in parallel (workers: %d, batch size: %d)",
            total,
            MAX_WORKERS,
            BATCH_SIZE,
        )

        self._report_progress("fetch", 0, total, f"Starting to fetch {total} PRs...")

        # Process in batches to avoid overwhelming GitHub
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = pr_objects[batch_start:batch_end]
            batch_num = batch_start // BATCH_SIZE + 1

            logger.info(
                "Processing batch %d/%d (PRs %d-%d)",
                batch_num,
                total_batches,
                batch_start + 1,
                batch_end,
            )

            # Report progress before fetching batch
            self._report_progress(
                "fetch",
                batch_start,
                total,
                f"Fetching PRs {batch_start + 1}-{batch_end} of {total}...",
            )

            # Fetch batch with retry logic
            batch_results = self._fetch_batch_with_retry(batch, repo_name)
            fetched_prs.extend(batch_results)

            # Report progress after fetching batch
            self._report_progress(
                "fetch",
                batch_end,
                total,
                f"Fetched {batch_end}/{total} PRs ({len(fetched_prs)} successful)",
            )

            # Delay between batches to avoid secondary rate limits
            if batch_end < total:
                remaining = self.get_rate_limit_remaining()
                logger.debug(
                    "Batch complete. Rate limit: %d remaining. Waiting %.1fs...",
                    remaining,
                    BATCH_DELAY,
                )
                time.sleep(BATCH_DELAY)

        # Sort by created_at to maintain chronological order
        with contextlib.suppress(AttributeError, TypeError):
            fetched_prs.sort(key=lambda x: x.created_at, reverse=True)

        logger.info("Fetched %d PRs from %s (parallel)", len(fetched_prs), repo_name)
        return fetched_prs

    def _fetch_batch_with_retry(self, batch: list, repo_name: str) -> list[FetchedPRFull]:
        """Fetch a batch of PRs with retry logic for 403 errors."""
        results: list[FetchedPRFull] = []
        retry_count = 0
        backoff = INITIAL_BACKOFF

        while retry_count <= MAX_RETRIES:
            try:
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_pr = {executor.submit(self._fetch_pr_details, pr, repo_name): pr for pr in batch}

                    for future in as_completed(future_to_pr):
                        pr = future_to_pr[future]
                        try:
                            fetched_pr = future.result()
                            results.append(fetched_pr)
                        except GithubException as e:
                            if e.status == 403:
                                # Re-raise to trigger batch retry
                                raise
                            logger.warning("Failed to fetch PR #%d: %s", pr.number, e)
                        except Exception as e:
                            logger.warning("Unexpected error fetching PR #%d: %s", pr.number, e)

                # Success - return results
                return results

            except GithubException as e:
                if e.status == 403 and retry_count < MAX_RETRIES:
                    retry_count += 1
                    logger.warning(
                        "Rate limit hit (403). Retry %d/%d after %.1fs backoff...",
                        retry_count,
                        MAX_RETRIES,
                        backoff,
                    )
                    time.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                    results = []  # Clear partial results for retry
                else:
                    logger.error("Failed to fetch batch after %d retries: %s", retry_count, e)
                    break

        return results

    def _fetch_prs_sequential(self, pr_objects: list, repo_name: str) -> list[FetchedPRFull]:
        """Fetch PR details sequentially (fallback)."""
        fetched_prs: list[FetchedPRFull] = []
        total = len(pr_objects)

        for i, pr in enumerate(pr_objects):
            try:
                fetched_pr = self._fetch_pr_details(pr, repo_name)
                fetched_prs.append(fetched_pr)

                if (i + 1) % 50 == 0:
                    remaining = self.get_rate_limit_remaining()
                    logger.info(
                        "Processed %d/%d PRs (rate limit: %d remaining)",
                        i + 1,
                        total,
                        remaining,
                    )

            except GithubException as e:
                logger.warning("Failed to fetch PR #%d: %s", pr.number, e)
                continue

        logger.info("Fetched %d PRs from %s (sequential)", len(fetched_prs), repo_name)
        return fetched_prs

    def _fetch_pr_details(self, pr, repo_name: str) -> FetchedPRFull:
        """Fetch all details for a single PR.

        Uses parallel fetching for commits, reviews, files, and check runs.
        """
        # Determine state
        if pr.merged:
            state = "merged"
        elif pr.state == "closed":
            state = "closed"
        else:
            state = "open"

        # Fetch commits, reviews, files, check runs in parallel
        commits = []
        reviews = []
        files = []
        check_runs = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._fetch_commits, pr): "commits",
                executor.submit(self._fetch_reviews, pr): "reviews",
                executor.submit(self._fetch_files, pr): "files",
                executor.submit(self._fetch_check_runs, pr): "check_runs",
            }

            for future in as_completed(futures):
                data_type = futures[future]
                try:
                    result = future.result()
                    if data_type == "commits":
                        commits = result
                    elif data_type == "reviews":
                        reviews = result
                    elif data_type == "files":
                        files = result
                    elif data_type == "check_runs":
                        check_runs = result
                except Exception as e:
                    logger.debug("Failed to fetch %s for PR #%d: %s", data_type, pr.number, e)

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
