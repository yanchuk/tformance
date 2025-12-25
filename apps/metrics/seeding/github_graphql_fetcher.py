"""
GraphQL-based GitHub fetcher for real project seeding.

Uses the existing GitHubGraphQLClient to fetch PR data ~10x faster than REST API.
Maps GraphQL responses to existing dataclasses for compatibility with RealProjectSeeder.

Usage:
    fetcher = GitHubGraphQLFetcher(token)
    prs = await fetcher.fetch_prs(repo, since, max_prs=100)
    contributors = await fetcher.get_contributors(repo, max_count=50)
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from django.utils import timezone

from apps.integrations.services.github_graphql import (
    GitHubGraphQLClient,
    GitHubGraphQLRateLimitError,
)

from .github_authenticated_fetcher import (
    ContributorInfo,
    FetchedCheckRun,
    FetchedCommit,
    FetchedFile,
    FetchedPRFull,
    FetchedReview,
)
from .pr_cache import PRCache

logger = logging.getLogger(__name__)


# GraphQL query for repository contributors
FETCH_CONTRIBUTORS_QUERY = """
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    mentionableUsers(first: 100, after: $cursor) {
      nodes {
        databaseId
        login
        name
        email
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


@dataclass
class GitHubGraphQLFetcher:
    """GraphQL-based fetcher for seeding.

    Provides same interface as GitHubAuthenticatedFetcher but uses GraphQL
    for ~10x faster data fetching.

    Attributes:
        token: GitHub token. If not provided, reads from GITHUB_SEEDING_TOKENS env.
        fetch_check_runs: If True, fetches check runs using REST API fallback.
            This adds ~3 API calls per PR but provides CI/CD data.
        use_cache: If True, caches fetched data locally and loads from cache on re-runs.
        cache_dir: Directory for cache files. Defaults to .seeding_cache.
        api_calls_made: Counter for API calls made.
    """

    token: str | None = None
    fetch_check_runs: bool = True  # Fetch check runs via REST fallback
    use_cache: bool = True  # Enable local caching
    cache_dir: Path = field(default_factory=lambda: Path(".seeding_cache"))
    api_calls_made: int = 0

    def __post_init__(self):
        """Initialize with token from env if not provided."""
        # Get token from env if not provided
        if not self.token:
            self.token = os.environ.get("GITHUB_SEEDING_TOKENS", "")

        # Handle comma-separated tokens (use first one for GraphQL)
        if self.token and "," in self.token:
            self.token = self.token.split(",")[0].strip()

        if not self.token:
            raise ValueError("GitHub token required. Set GITHUB_SEEDING_TOKENS env var.")

        self._client = GitHubGraphQLClient(self.token)
        self._rest_github = None  # Lazy-loaded PyGithub client for check runs
        self._repo_cache: dict = {}  # Cache for REST repo objects

    def _get_rest_client(self):
        """Lazy-load REST client for check runs fallback."""
        if self._rest_github is None:
            from github import Github

            self._rest_github = Github(self.token)
        return self._rest_github

    def _check_rest_rate_limit(self, warn_threshold: int = 100) -> int:
        """Check REST API rate limit and log warning if low.

        Per GitHub API best practices, monitor rate limit to avoid hitting limits.
        See: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

        Args:
            warn_threshold: Log warning if remaining points below this. Default: 100

        Returns:
            Remaining rate limit points
        """
        gh = self._get_rest_client()
        rate_limit = gh.get_rate_limit()
        self.api_calls_made += 1

        remaining = rate_limit.rate.remaining
        reset_timestamp = rate_limit.rate.reset.timestamp()

        if remaining < warn_threshold:
            from datetime import datetime

            reset_time = datetime.fromtimestamp(reset_timestamp)
            logger.warning(
                f"REST API rate limit low: {remaining} remaining (resets at {reset_time.strftime('%H:%M:%S')})"
            )

        return remaining

    def _get_cached_repo(self, repo_full_name: str):
        """Get repo object from cache or fetch it."""
        if repo_full_name not in self._repo_cache:
            gh = self._get_rest_client()
            self._repo_cache[repo_full_name] = gh.get_repo(repo_full_name)
            self.api_calls_made += 1
        return self._repo_cache[repo_full_name]

    def _fetch_check_runs_for_commit(self, repo_full_name: str, commit_sha: str) -> list[FetchedCheckRun]:
        """Fetch check runs for a commit using REST API.

        Uses commit SHA directly - just 1 API call instead of 3.

        Args:
            repo_full_name: Repository in "owner/repo" format
            commit_sha: Git commit SHA

        Returns:
            List of FetchedCheckRun objects
        """
        check_runs = []
        try:
            repo = self._get_cached_repo(repo_full_name)
            commit = repo.get_commit(commit_sha)
            self.api_calls_made += 1

            for check_run in commit.get_check_runs():
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
        except Exception as e:
            logger.debug(f"Failed to fetch check runs for {repo_full_name}@{commit_sha[:7]}: {e}")

        return check_runs

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse ISO datetime string to timezone-aware datetime."""
        if not dt_str:
            return None
        # Parse ISO format and make timezone-aware
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt

    def _map_pr(self, node: dict, repo_full_name: str) -> FetchedPRFull:
        """Map GraphQL PR node to FetchedPRFull dataclass."""
        # Determine state
        state = node.get("state", "OPEN").lower()
        is_merged = state == "merged"

        # Parse timestamps
        created_at = self._parse_datetime(node.get("createdAt"))
        merged_at = self._parse_datetime(node.get("mergedAt"))
        updated_at = self._parse_datetime(node.get("updatedAt"))
        closed_at = self._parse_datetime(node.get("closedAt"))

        # Get author
        author = node.get("author") or {}
        author_login = author.get("login")

        # Map labels (Phase 2)
        labels = []
        for label_node in (node.get("labels") or {}).get("nodes") or []:
            if label_node and label_node.get("name"):
                labels.append(label_node.get("name"))

        # Map milestone (Phase 2)
        milestone = node.get("milestone") or {}
        milestone_title = milestone.get("title")

        # Map assignees (Phase 2)
        assignees = []
        for assignee_node in (node.get("assignees") or {}).get("nodes") or []:
            if assignee_node and assignee_node.get("login"):
                assignees.append(assignee_node.get("login"))

        # Map linked issues (Phase 2)
        linked_issues = []
        for issue_node in (node.get("closingIssuesReferences") or {}).get("nodes") or []:
            if issue_node and issue_node.get("number"):
                linked_issues.append(issue_node.get("number"))

        # Map reviews
        reviews = []
        for review_node in (node.get("reviews") or {}).get("nodes") or []:
            if not review_node:
                continue
            reviewer = review_node.get("author") or {}
            reviews.append(
                FetchedReview(
                    github_review_id=review_node.get("databaseId", 0),
                    reviewer_login=reviewer.get("login", "unknown"),
                    state=review_node.get("state", "COMMENTED"),
                    submitted_at=self._parse_datetime(review_node.get("submittedAt")) or timezone.now(),
                    body=review_node.get("body"),
                )
            )

        # Map commits
        commits = []
        for commit_node in (node.get("commits") or {}).get("nodes") or []:
            if not commit_node:
                continue
            commit = commit_node.get("commit") or {}
            commit_author = commit.get("author") or {}
            user = commit_author.get("user") or {}
            commits.append(
                FetchedCommit(
                    sha=commit.get("oid", ""),
                    message=commit.get("message", "")[:500],
                    author_login=user.get("login"),
                    author_name=commit_author.get("name"),
                    committed_at=self._parse_datetime(commit_author.get("date")) or timezone.now(),
                    additions=commit.get("additions", 0),
                    deletions=commit.get("deletions", 0),
                )
            )

        # Map files
        files = []
        for file_node in (node.get("files") or {}).get("nodes") or []:
            if not file_node:
                continue
            # Map changeType to status
            change_type = file_node.get("changeType", "MODIFIED")
            status_map = {
                "ADDED": "added",
                "DELETED": "deleted",
                "MODIFIED": "modified",
                "RENAMED": "renamed",
                "COPIED": "copied",
            }
            files.append(
                FetchedFile(
                    filename=file_node.get("path", ""),
                    status=status_map.get(change_type, "modified"),
                    additions=file_node.get("additions", 0),
                    deletions=file_node.get("deletions", 0),
                )
            )

        # Note: cycle_time_hours, first_review_at, review_time_hours are computed properties
        # on FetchedPRFull, so we don't pass them here

        return FetchedPRFull(
            github_pr_id=node.get("number", 0),
            number=node.get("number", 0),
            github_repo=repo_full_name,
            title=node.get("title", ""),
            body=node.get("body"),
            state=state,
            is_merged=is_merged,
            is_draft=node.get("isDraft", False),
            created_at=created_at or timezone.now(),
            updated_at=updated_at or timezone.now(),
            merged_at=merged_at,
            closed_at=closed_at,
            additions=node.get("additions", 0),
            deletions=node.get("deletions", 0),
            changed_files=len(files),
            commits_count=len(commits),
            author_login=author_login or "unknown",
            author_id=0,  # Not available in GraphQL
            author_name=None,
            author_avatar_url=None,
            head_ref=node.get("headRefName", ""),
            base_ref=node.get("baseRefName", "main"),
            labels=labels,
            jira_key_from_title=None,  # Will be parsed by seeder
            jira_key_from_branch=None,
            reviews=reviews,
            commits=commits,
            files=files,
            check_runs=[],  # Not fetched via GraphQL
            milestone_title=milestone_title,
            assignees=assignees,
            linked_issues=linked_issues,
        )

    async def _fetch_prs_async(
        self,
        repo_full_name: str,
        since: datetime | None = None,
        max_prs: int = 100,
    ) -> list[FetchedPRFull]:
        """Fetch PRs using GraphQL (async).

        Args:
            repo_full_name: Repository in "owner/repo" format
            since: Only fetch PRs created after this date
            max_prs: Maximum number of PRs to fetch

        Returns:
            List of FetchedPRFull objects
        """
        owner, repo = repo_full_name.split("/")
        prs: list[FetchedPRFull] = []
        cursor = None
        page = 0

        logger.info(f"GraphQL: Fetching PRs from {repo_full_name} (max: {max_prs}, since: {since})")
        print(f"  📥 Fetching PRs from {repo_full_name}...")

        while len(prs) < max_prs:
            page += 1
            print(f"     Page {page}: fetching...", end=" ", flush=True)
            try:
                result = await self._client.fetch_prs_bulk(owner, repo, cursor)
                self.api_calls_made += 1
            except GitHubGraphQLRateLimitError as e:
                print("⚠️ Rate limit hit")
                logger.warning(f"Rate limit hit: {e}")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"GraphQL error fetching PRs: {e}")
                break

            pr_data = result.get("repository", {}).get("pullRequests", {})
            nodes = pr_data.get("nodes") or []
            print(f"got {len(nodes)} PRs (total: {len(prs) + len(nodes)})")

            for node in nodes:
                if len(prs) >= max_prs:
                    break

                pr = self._map_pr(node, repo_full_name)

                # Filter by date if specified
                if since and pr.created_at < since:
                    # PRs are ordered by created_at DESC, so we can stop here
                    print(f"  ✅ Reached date cutoff ({since.date()}), collected {len(prs)} PRs")
                    logger.debug(f"Reached PRs older than {since}, stopping")
                    # Fetch check runs for collected PRs before returning
                    if self.fetch_check_runs:
                        self._add_check_runs_to_prs(prs, repo_full_name)
                    return prs

                prs.append(pr)

            # Check pagination
            page_info = pr_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                print(f"  ✅ No more pages, collected {len(prs)} PRs")
                break
            cursor = page_info.get("endCursor")

            # Small delay between pages to be gentler on the API
            await asyncio.sleep(0.5)

        logger.info(f"GraphQL: Fetched {len(prs)} PRs from {repo_full_name}")

        # Fetch check runs via REST fallback if enabled
        if self.fetch_check_runs and prs:
            self._add_check_runs_to_prs(prs, repo_full_name)

        return prs

    def _add_check_runs_to_prs(self, prs: list[FetchedPRFull], repo_full_name: str):
        """Add check runs to PRs using REST API fallback with sequential fetching.

        Uses commit SHA from GraphQL data - just 1 API call per PR instead of 3.
        Fetches sequentially per GitHub API best practices to avoid secondary rate limits.
        See: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

        Args:
            prs: List of FetchedPRFull objects to update
            repo_full_name: Repository in "owner/repo" format
        """
        # Filter PRs that have commits (need head commit SHA for check runs)
        prs_with_commits = [(pr, pr.commits[-1].sha) for pr in prs if pr.commits]
        if not prs_with_commits:
            logger.info("REST: No PRs with commits to fetch check runs for")
            return

        # Check REST API rate limit before making calls
        remaining = self._check_rest_rate_limit()
        calls_needed = len(prs_with_commits) + 1  # +1 for repo cache

        if remaining < calls_needed:
            print(f"⚠️ Skipping check runs - only {remaining} REST API calls remaining, need {calls_needed}")
            logger.warning(f"Skipping check runs: {remaining} remaining < {calls_needed} needed")
            return

        print(
            f"  🔄 Fetching check runs for {len(prs_with_commits)} PRs (REST API, {remaining} remaining)...",
            end=" ",
            flush=True,
        )
        logger.info(f"REST: Fetching check runs for {len(prs_with_commits)} PRs from {repo_full_name} (1 call/PR)")

        # Pre-cache the repo object before sequential execution
        self._get_cached_repo(repo_full_name)

        # Fetch check runs sequentially per GitHub API best practices
        # "Make requests serially instead of concurrently" to avoid secondary rate limits
        for pr, sha in prs_with_commits:
            try:
                check_runs = self._fetch_check_runs_for_commit(repo_full_name, sha)
                pr.check_runs.extend(check_runs)
            except Exception as e:
                logger.debug(f"Failed to fetch check runs for PR #{pr.number}: {e}")

        total_check_runs = sum(len(pr.check_runs) for pr in prs)
        print(f"done ({total_check_runs} check runs)")
        logger.info(f"REST: Fetched {total_check_runs} check runs for {len(prs_with_commits)} PRs")

    def fetch_prs_with_details(
        self,
        repo_full_name: str,
        since: datetime | None = None,
        until: datetime | None = None,
        max_prs: int = 100,
    ) -> list[FetchedPRFull]:
        """Fetch PRs using GraphQL (sync wrapper).

        Compatible with GitHubAuthenticatedFetcher interface.
        Uses local cache if enabled and valid.

        Args:
            repo_full_name: Repository in "owner/repo" format
            since: Only fetch PRs created after this date
            until: Only fetch PRs created before this date (for batch imports)
            max_prs: Maximum number of PRs to fetch

        Returns:
            List of FetchedPRFull objects
        """
        since_date = since.date() if since else None
        until_date = until.date() if until else None

        # Fetch repo metadata to check if repo has changed (cheap ~1 point query)
        repo_pushed_at = None
        if self.use_cache:
            repo_pushed_at = asyncio.run(self._fetch_repo_pushed_at(repo_full_name))

        # Try to load from cache (with repo change detection)
        cache = None
        if self.use_cache:
            cache = PRCache.load(repo_full_name, self.cache_dir)
            if cache and cache.is_valid(since_date, repo_pushed_at=repo_pushed_at):
                prs = self._deserialize_prs(cache.prs)
                # Apply until filter for batch imports
                if until_date:
                    prs = [pr for pr in prs if pr.created_at.date() <= until_date]
                # Limit to max_prs
                prs = prs[:max_prs]
                print(f"  📦 Loaded {len(prs)} PRs from cache (unchanged since {cache.fetched_at.date()})")
                logger.info(f"Loaded {len(prs)} PRs from cache for {repo_full_name} (repo unchanged)")
                return prs
            elif cache:
                # Cache exists but is stale - use incremental sync
                print(f"  🔄 Repo has changed since cache, fetching updates since {cache.fetched_at.date()}...")
                logger.info(f"Cache stale for {repo_full_name} - using incremental sync")

                # Fetch only PRs updated since cache was created
                updated_prs = asyncio.run(self._fetch_updated_prs_async(repo_full_name, cache.fetched_at))

                if updated_prs:
                    # Merge with cached PRs
                    cached_prs = self._deserialize_prs(cache.prs)
                    prs = self._merge_prs(cached_prs, updated_prs)
                    print(f"  ✅ Merged {len(updated_prs)} updated PRs with {len(cached_prs)} cached PRs")
                    logger.info(f"Merged {len(updated_prs)} updated PRs with {len(cached_prs)} cached")
                else:
                    # No updates - use cached PRs
                    prs = self._deserialize_prs(cache.prs)
                    print(f"  📦 No updates found, using {len(prs)} cached PRs")
                    logger.info(f"No updated PRs found for {repo_full_name}, using cache")

                # Apply until filter for batch imports
                if until_date:
                    prs = [pr for pr in prs if pr.created_at.date() <= until_date]

                # Limit to max_prs
                prs = prs[:max_prs]

                # Save merged result to cache
                new_cache = PRCache(
                    repo=repo_full_name,
                    fetched_at=datetime.now(UTC),
                    since_date=since_date,
                    prs=self._serialize_prs(prs),
                    repo_pushed_at=repo_pushed_at,
                )
                new_cache.save(self.cache_dir)
                print(f"  💾 Saved {len(prs)} PRs to cache")
                logger.info(f"Saved merged {len(prs)} PRs to cache for {repo_full_name}")
                return prs

        # No cache - fetch from GitHub
        prs = asyncio.run(self._fetch_prs_async(repo_full_name, since, max_prs))

        # Save to cache (with repo_pushed_at for future validation)
        if self.use_cache and prs:
            cache = PRCache(
                repo=repo_full_name,
                fetched_at=datetime.now(UTC),
                since_date=since_date,
                prs=self._serialize_prs(prs),
                repo_pushed_at=repo_pushed_at,
            )
            cache.save(self.cache_dir)
            print(f"  💾 Saved {len(prs)} PRs to cache")
            logger.info(f"Saved {len(prs)} PRs to cache for {repo_full_name}")

        # Apply until filter for batch imports (filter by created_at)
        if until_date and prs:
            original_count = len(prs)
            prs = [pr for pr in prs if pr.created_at.date() <= until_date]
            if len(prs) < original_count:
                logger.info(f"Filtered to {len(prs)} PRs (created before {until_date})")

        return prs

    async def _fetch_repo_pushed_at(self, repo_full_name: str) -> datetime | None:
        """Fetch repository's pushedAt timestamp for cache validation.

        Lightweight query (~1 point) to check if repository has changed.
        Follows GitHub API best practices for conditional requests.

        Args:
            repo_full_name: Repository in "owner/repo" format

        Returns:
            datetime when repo was last pushed to, or None on error
        """
        owner, repo = repo_full_name.split("/")
        try:
            result = await self._client.fetch_repo_metadata(owner, repo)
            self.api_calls_made += 1

            pushed_at_str = result.get("repository", {}).get("pushedAt")
            if pushed_at_str:
                return self._parse_datetime(pushed_at_str)
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch repo metadata for {repo_full_name}: {e}")
            return None

    async def _fetch_updated_prs_async(
        self,
        repo_full_name: str,
        since: datetime,
    ) -> list[FetchedPRFull]:
        """Fetch PRs updated since a given datetime (async).

        Uses FETCH_PRS_UPDATED_QUERY ordered by UPDATED_AT DESC.
        Stops when encountering PRs older than `since`.

        Args:
            repo_full_name: Repository in "owner/repo" format
            since: Only fetch PRs updated after this datetime

        Returns:
            List of FetchedPRFull objects updated since `since`
        """
        owner, repo = repo_full_name.split("/")
        prs: list[FetchedPRFull] = []
        cursor = None

        logger.info(f"GraphQL: Fetching updated PRs from {repo_full_name} since {since}")

        while True:
            try:
                result = await self._client.fetch_prs_updated_since(owner, repo, since, cursor)
                self.api_calls_made += 1
            except GitHubGraphQLRateLimitError as e:
                logger.warning(f"Rate limit hit: {e}")
                break
            except Exception as e:
                logger.error(f"GraphQL error fetching updated PRs: {e}")
                break

            pr_data = result.get("repository", {}).get("pullRequests", {})
            nodes = pr_data.get("nodes") or []

            for node in nodes:
                pr = self._map_pr(node, repo_full_name)

                # PRs are ordered by updated_at DESC, so stop when we see old PRs
                if pr.updated_at < since:
                    logger.debug(f"Reached PRs older than {since}, stopping")
                    return prs

                prs.append(pr)

            # Check pagination
            page_info = pr_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        logger.info(f"GraphQL: Fetched {len(prs)} updated PRs from {repo_full_name}")
        return prs

    def _merge_prs(self, cached_prs: list[FetchedPRFull], updated_prs: list[FetchedPRFull]) -> list[FetchedPRFull]:
        """Merge updated PRs with cached PRs for incremental sync.

        - Replaces cached PRs with updated ones (by PR number)
        - Adds new PRs that weren't in cache
        - Sorts by updated_at DESC (most recent first)

        Args:
            cached_prs: PRs loaded from cache
            updated_prs: Newly fetched PRs (updated since cache was created)

        Returns:
            Merged list of PRs sorted by updated_at descending
        """
        # Create dict of cached PRs by number
        pr_dict = {pr.number: pr for pr in cached_prs}

        # Update/add PRs from updates
        for pr in updated_prs:
            pr_dict[pr.number] = pr

        # Sort by updated_at DESC
        return sorted(pr_dict.values(), key=lambda pr: pr.updated_at, reverse=True)

    def _serialize_prs(self, prs: list[FetchedPRFull]) -> list[dict]:
        """Serialize FetchedPRFull objects to dicts for caching."""
        from dataclasses import asdict

        result = []
        for pr in prs:
            data = asdict(pr)
            # Convert datetime to ISO format
            for dt_field in ["created_at", "updated_at", "merged_at", "closed_at", "first_review_at"]:
                if data.get(dt_field):
                    data[dt_field] = data[dt_field].isoformat()
            # Convert nested datetimes in reviews
            for review in data.get("reviews", []):
                if review.get("submitted_at"):
                    review["submitted_at"] = review["submitted_at"].isoformat()
            # Convert nested datetimes in commits
            for commit in data.get("commits", []):
                if commit.get("committed_at"):
                    commit["committed_at"] = commit["committed_at"].isoformat()
            # Convert nested datetimes in check_runs
            for check_run in data.get("check_runs", []):
                if check_run.get("started_at"):
                    check_run["started_at"] = check_run["started_at"].isoformat()
                if check_run.get("completed_at"):
                    check_run["completed_at"] = check_run["completed_at"].isoformat()
            result.append(data)
        return result

    def _deserialize_prs(self, data: list[dict]) -> list[FetchedPRFull]:
        """Deserialize dicts to FetchedPRFull objects from cache."""
        prs = []
        for pr_data in data:
            # Parse datetime fields
            for dt_field in ["created_at", "updated_at", "merged_at", "closed_at", "first_review_at"]:
                if pr_data.get(dt_field):
                    pr_data[dt_field] = datetime.fromisoformat(pr_data[dt_field])
            # Parse nested datetimes in reviews
            reviews = []
            for review_data in pr_data.get("reviews", []):
                if review_data.get("submitted_at"):
                    review_data["submitted_at"] = datetime.fromisoformat(review_data["submitted_at"])
                reviews.append(FetchedReview(**review_data))
            pr_data["reviews"] = reviews
            # Parse nested datetimes in commits
            commits = []
            for commit_data in pr_data.get("commits", []):
                if commit_data.get("committed_at"):
                    commit_data["committed_at"] = datetime.fromisoformat(commit_data["committed_at"])
                commits.append(FetchedCommit(**commit_data))
            pr_data["commits"] = commits
            # Parse nested files
            files = []
            for file_data in pr_data.get("files", []):
                files.append(FetchedFile(**file_data))
            pr_data["files"] = files
            # Parse nested check_runs
            check_runs = []
            for check_run_data in pr_data.get("check_runs", []):
                if check_run_data.get("started_at"):
                    check_run_data["started_at"] = datetime.fromisoformat(check_run_data["started_at"])
                if check_run_data.get("completed_at"):
                    check_run_data["completed_at"] = datetime.fromisoformat(check_run_data["completed_at"])
                check_runs.append(FetchedCheckRun(**check_run_data))
            pr_data["check_runs"] = check_runs

            prs.append(FetchedPRFull(**pr_data))
        return prs

    async def _fetch_contributors_async(
        self,
        repo_full_name: str,
        max_count: int = 50,
        since: datetime | None = None,
    ) -> list[ContributorInfo]:
        """Fetch contributors using GraphQL (async).

        Note: GraphQL doesn't have a direct contributors endpoint, so we use
        mentionableUsers which includes people who have interacted with the repo.

        Args:
            repo_full_name: Repository in "owner/repo" format
            max_count: Maximum number of contributors
            since: Unused (for interface compatibility)

        Returns:
            List of ContributorInfo objects
        """
        from gql import gql

        owner, repo = repo_full_name.split("/")
        contributors: list[ContributorInfo] = []
        cursor = None

        query = gql(FETCH_CONTRIBUTORS_QUERY)

        logger.info(f"GraphQL: Fetching contributors from {repo_full_name} (max: {max_count})")

        while len(contributors) < max_count:
            try:
                result = await self._client._execute(
                    query, variable_values={"owner": owner, "repo": repo, "cursor": cursor}
                )
                self.api_calls_made += 1
            except Exception as e:
                logger.error(f"GraphQL error fetching contributors: {e}")
                break

            users_data = result.get("repository", {}).get("mentionableUsers", {})
            nodes = users_data.get("nodes") or []

            for node in nodes:
                if len(contributors) >= max_count:
                    break

                contributors.append(
                    ContributorInfo(
                        github_id=node.get("databaseId", 0),
                        github_login=node.get("login", ""),
                        display_name=node.get("name"),
                        email=node.get("email"),
                        avatar_url=None,
                        pr_count=0,  # Not available from this query
                    )
                )

            # Check pagination
            page_info = users_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        logger.info(f"GraphQL: Fetched {len(contributors)} contributors from {repo_full_name}")
        return contributors

    def get_top_contributors(
        self,
        repo_full_name: str,
        max_count: int = 50,
        since: datetime | None = None,
    ) -> list[ContributorInfo]:
        """Fetch contributors using GraphQL (sync wrapper).

        Compatible with GitHubAuthenticatedFetcher interface.

        Args:
            repo_full_name: Repository in "owner/repo" format
            max_count: Maximum number of contributors
            since: Unused (for interface compatibility)

        Returns:
            List of ContributorInfo objects
        """
        return asyncio.run(self._fetch_contributors_async(repo_full_name, max_count, since))
