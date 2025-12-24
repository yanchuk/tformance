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

        logger.info(f"GraphQL: Fetched {len(prs)} PRs from {repo_full_name}")

        # Fetch check runs via REST fallback if enabled
        if self.fetch_check_runs and prs:
            self._add_check_runs_to_prs(prs, repo_full_name)

        return prs

    def _add_check_runs_to_prs(self, prs: list[FetchedPRFull], repo_full_name: str):
        """Add check runs to PRs using REST API fallback with parallel fetching.

        Uses commit SHA from GraphQL data - just 1 API call per PR instead of 3.
        Uses ThreadPoolExecutor for parallel API calls (4 workers to respect rate limits).

        Args:
            prs: List of FetchedPRFull objects to update
            repo_full_name: Repository in "owner/repo" format
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Filter PRs that have commits (need head commit SHA for check runs)
        prs_with_commits = [(pr, pr.commits[-1].sha) for pr in prs if pr.commits]
        if not prs_with_commits:
            logger.info("REST: No PRs with commits to fetch check runs for")
            return

        print(f"  🔄 Fetching check runs for {len(prs_with_commits)} PRs (REST API)...", end=" ", flush=True)
        logger.info(f"REST: Fetching check runs for {len(prs_with_commits)} PRs from {repo_full_name} (1 call/PR)")

        # Pre-cache the repo object before parallel execution
        self._get_cached_repo(repo_full_name)

        # Fetch check runs in parallel (4 workers to respect rate limits)
        pr_to_check_runs: dict[int, list[FetchedCheckRun]] = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_pr = {
                executor.submit(self._fetch_check_runs_for_commit, repo_full_name, sha): pr
                for pr, sha in prs_with_commits
            }

            for future in as_completed(future_to_pr):
                pr = future_to_pr[future]
                try:
                    check_runs = future.result()
                    pr_to_check_runs[pr.number] = check_runs
                except Exception as e:
                    logger.debug(f"Failed to fetch check runs for PR #{pr.number}: {e}")
                    pr_to_check_runs[pr.number] = []

        # Apply check runs to PRs
        for pr in prs:
            check_runs = pr_to_check_runs.get(pr.number, [])
            pr.check_runs.extend(check_runs)

        total_check_runs = sum(len(pr.check_runs) for pr in prs)
        print(f"done ({total_check_runs} check runs)")
        logger.info(f"REST: Fetched {total_check_runs} check runs for {len(prs_with_commits)} PRs")

    def fetch_prs_with_details(
        self,
        repo_full_name: str,
        since: datetime | None = None,
        max_prs: int = 100,
    ) -> list[FetchedPRFull]:
        """Fetch PRs using GraphQL (sync wrapper).

        Compatible with GitHubAuthenticatedFetcher interface.
        Uses local cache if enabled and valid.

        Args:
            repo_full_name: Repository in "owner/repo" format
            since: Only fetch PRs created after this date
            max_prs: Maximum number of PRs to fetch

        Returns:
            List of FetchedPRFull objects
        """
        since_date = since.date() if since else None

        # Try to load from cache
        if self.use_cache:
            cache = PRCache.load(repo_full_name, self.cache_dir)
            if cache and cache.is_valid(since_date):
                prs = self._deserialize_prs(cache.prs)
                # Limit to max_prs
                prs = prs[:max_prs]
                print(f"  📦 Loaded {len(prs)} PRs from cache ({cache.fetched_at.date()})")
                logger.info(f"Loaded {len(prs)} PRs from cache for {repo_full_name}")
                return prs

        # Fetch from GitHub
        prs = asyncio.run(self._fetch_prs_async(repo_full_name, since, max_prs))

        # Save to cache
        if self.use_cache and prs:
            cache = PRCache(
                repo=repo_full_name,
                fetched_at=datetime.now(UTC),
                since_date=since_date,
                prs=self._serialize_prs(prs),
            )
            cache.save(self.cache_dir)
            print(f"  💾 Saved {len(prs)} PRs to cache")
            logger.info(f"Saved {len(prs)} PRs to cache for {repo_full_name}")

        return prs

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
