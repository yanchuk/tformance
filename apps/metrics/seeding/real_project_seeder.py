"""
Real project seeder orchestrator.

Seeds demo data from real open source GitHub projects with simulated
Jira issues, surveys, and AI usage records.

Usage:
    from apps.metrics.seeding.real_project_seeder import RealProjectSeeder
    from apps.metrics.seeding.real_projects import get_project

    config = get_project("posthog")
    seeder = RealProjectSeeder(config, seed=42)
    stats = seeder.seed(team)
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Avg, Sum
from django.utils import timezone

from apps.metrics.factories import (
    CommitFactory,
    PRCheckRunFactory,
    PRFileFactory,
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
    WeeklyMetricsFactory,
)
from apps.metrics.models import PullRequest, TeamMember, WeeklyMetrics
from apps.teams.models import Team

from .deterministic import DeterministicRandom
from .github_authenticated_fetcher import ContributorInfo, FetchedPRFull, GitHubAuthenticatedFetcher
from .jira_simulator import JiraIssueSimulator
from .real_projects import RealProjectConfig
from .survey_ai_simulator import SurveyAISimulator

logger = logging.getLogger(__name__)


@dataclass
class RealProjectStats:
    """Statistics from a real project seeding run."""

    project_name: str = ""
    team_created: bool = False
    team_members_created: int = 0
    prs_created: int = 0
    reviews_created: int = 0
    commits_created: int = 0
    files_created: int = 0
    check_runs_created: int = 0
    jira_issues_created: int = 0
    surveys_created: int = 0
    survey_reviews_created: int = 0
    ai_usage_records: int = 0
    weekly_metrics_created: int = 0
    github_api_calls: int = 0


# Type for progress callback: (step_name, current, total, message)
# Using Any to avoid typing complexity with Callable
ProgressCallback = Any  # Callable[[str, int, int, str], None]


@dataclass
class RealProjectSeeder:
    """Seeds demo data from real GitHub projects.

    Orchestrates:
    1. Team creation (if needed)
    2. Team member creation from GitHub contributors
    3. PR creation with commits, reviews, files, check runs
    4. Jira issue simulation
    5. Survey and AI usage simulation
    6. WeeklyMetrics calculation

    Attributes:
        config: Project configuration.
        random_seed: Random seed for reproducibility.
        github_token: Optional GitHub PAT (uses env var if not provided).
        progress_callback: Optional callback for progress updates.
    """

    config: RealProjectConfig
    random_seed: int = 42
    github_token: str | None = None
    progress_callback: ProgressCallback | None = None

    # Internal state
    _rng: DeterministicRandom = field(init=False)
    _fetcher: GitHubAuthenticatedFetcher = field(init=False)
    _jira_simulator: JiraIssueSimulator = field(init=False)
    _survey_simulator: SurveyAISimulator = field(init=False)
    _stats: RealProjectStats = field(init=False)
    _members_by_github_id: dict[str, TeamMember] = field(default_factory=dict, init=False)
    _members_by_username: dict[str, TeamMember] = field(default_factory=dict, init=False)

    def __post_init__(self):
        """Initialize internal components."""
        self._rng = DeterministicRandom(self.random_seed)
        self._fetcher = GitHubAuthenticatedFetcher(
            self.github_token,
            progress_callback=self.progress_callback,
        )
        self._jira_simulator = JiraIssueSimulator(self.config.jira_project_key, self._rng)
        self._survey_simulator = SurveyAISimulator(self.config, self._rng)
        self._stats = RealProjectStats(project_name=self.config.team_name)

    def _report_progress(self, step: str, current: int, total: int, message: str):
        """Report progress via callback if available."""
        if self.progress_callback:
            self.progress_callback(step, current, total, message)

    def seed(self, existing_team: Team | None = None) -> RealProjectStats:
        """Seed complete demo data for this project.

        Each step commits independently so progress is saved incrementally.
        Duplicate records are skipped gracefully.

        Args:
            existing_team: Optional existing team to seed into.
                          If None, creates a new team.

        Returns:
            Statistics from the seeding run.
        """
        logger.info(f"Starting seed for project: {self.config.team_name}")
        total_steps = 7

        # Step 1: Get or create team (atomic)
        self._report_progress("seed", 1, total_steps, "Creating team...")
        with transaction.atomic():
            team = self._get_or_create_team(existing_team)

        # Step 2: Fetch contributors and create team members (atomic)
        self._report_progress("seed", 2, total_steps, "Fetching contributors...")
        contributors = self._fetch_contributors()
        with transaction.atomic():
            self._create_team_members(team, contributors)
        self._report_progress("seed", 2, total_steps, f"Created {len(contributors)} team members")

        # Step 3: Fetch PRs with all details (no transaction - just API calls)
        self._report_progress("seed", 3, total_steps, "Fetching PRs from GitHub...")
        prs_data = self._fetch_prs()
        self._report_progress("seed", 3, total_steps, f"Fetched {len(prs_data)} PRs")

        # Step 4: Create PR records with related data (per-PR transactions)
        self._report_progress("seed", 4, total_steps, "Creating PR records...")
        prs = self._create_prs(team, prs_data)
        self._report_progress("seed", 4, total_steps, f"Created {len(prs)} PRs with reviews/commits")

        # Step 5: Simulate Jira issues (atomic)
        self._report_progress("seed", 5, total_steps, "Simulating Jira issues...")
        with transaction.atomic():
            self._simulate_jira_issues(team, prs, prs_data)

        # Step 6: Simulate surveys and AI usage (atomic)
        self._report_progress("seed", 6, total_steps, "Simulating surveys and AI usage...")
        with transaction.atomic():
            self._simulate_surveys(team, prs, prs_data)
            self._generate_ai_usage(team)

        # Step 7: Calculate weekly metrics (atomic)
        self._report_progress("seed", 7, total_steps, "Calculating weekly metrics...")
        with transaction.atomic():
            self._calculate_weekly_metrics(team)

        self._report_progress("seed", total_steps, total_steps, "Complete!")
        logger.info(f"Completed seeding for {self.config.team_name}")
        self._log_stats()

        return self._stats

    def _get_or_create_team(self, existing_team: Team | None) -> Team:
        """Get existing team or create a new one.

        Args:
            existing_team: Optional existing team.

        Returns:
            Team instance.
        """
        if existing_team:
            logger.info(f"Using existing team: {existing_team.name}")
            return existing_team

        # Try to find existing team by slug
        try:
            team = Team.objects.get(slug=self.config.team_slug)
            logger.info(f"Found existing team: {team.name}")
            return team
        except Team.DoesNotExist:
            pass

        # Create new team
        team = TeamFactory(
            name=self.config.team_name,
            slug=self.config.team_slug,
        )
        self._stats.team_created = True
        logger.info(f"Created new team: {team.name}")
        return team

    def _fetch_contributors(self) -> list[ContributorInfo]:
        """Fetch top contributors from GitHub.

        Returns:
            List of contributor info.
        """
        logger.info(f"Fetching top {self.config.max_members} contributors...")

        days_ago = timezone.now() - timedelta(days=self.config.days_back)
        contributors = self._fetcher.get_top_contributors(
            self.config.repo_full_name,
            max_count=self.config.max_members,
            since=days_ago,
        )

        logger.info(f"Found {len(contributors)} contributors")
        return contributors

    def _create_team_members(self, team: Team, contributors: list[ContributorInfo]):
        """Create TeamMember records from contributors.

        Args:
            team: Team instance.
            contributors: List of contributor info.
        """
        logger.info(f"Creating {len(contributors)} team members...")

        for i, contributor in enumerate(contributors):
            # Check if member already exists
            existing = TeamMember.objects.filter(
                team=team,
                github_id=str(contributor.github_id),
            ).first()

            if existing:
                self._members_by_github_id[str(contributor.github_id)] = existing
                self._members_by_username[contributor.github_login.lower()] = existing
                continue

            # Assign role (first contributor is lead)
            role = "lead" if i == 0 else "developer"

            member = TeamMemberFactory(
                team=team,
                display_name=contributor.display_name or contributor.github_login,
                email=contributor.email or f"{contributor.github_login}@example.com",
                github_username=contributor.github_login,
                github_id=str(contributor.github_id),
                jira_account_id=f"jira-{contributor.github_id}",
                slack_user_id=f"U{contributor.github_id:08d}",
                role=role,
            )

            self._members_by_github_id[str(contributor.github_id)] = member
            self._members_by_username[contributor.github_login.lower()] = member
            self._stats.team_members_created += 1

        logger.info(f"Created {self._stats.team_members_created} new team members")

    def _fetch_prs(self) -> list[FetchedPRFull]:
        """Fetch PRs with all details from GitHub.

        Returns:
            List of PR data.
        """
        logger.info(f"Fetching up to {self.config.max_prs} PRs from last {self.config.days_back} days...")

        since = timezone.now() - timedelta(days=self.config.days_back)
        prs_data = self._fetcher.fetch_prs_with_details(
            self.config.repo_full_name,
            since=since,
            max_prs=self.config.max_prs,
        )

        self._stats.github_api_calls = self._fetcher.api_calls_made
        logger.info(f"Fetched {len(prs_data)} PRs (API calls: {self._stats.github_api_calls})")
        return prs_data

    def _find_member(self, login: str | None, github_id: int | None) -> TeamMember | None:
        """Find team member by GitHub username or ID.

        Args:
            login: GitHub username.
            github_id: GitHub user ID.

        Returns:
            TeamMember or None if not found.
        """
        if github_id and str(github_id) in self._members_by_github_id:
            return self._members_by_github_id[str(github_id)]
        if login and login.lower() in self._members_by_username:
            return self._members_by_username[login.lower()]
        return None

    def _create_prs(self, team: Team, prs_data: list[FetchedPRFull]) -> list[PullRequest]:
        """Create PullRequest records with all related data.

        Each PR is created in its own transaction for incremental saving.
        Skips PRs that already exist.

        Args:
            team: Team instance.
            prs_data: List of fetched PR data.

        Returns:
            List of created PullRequest instances.
        """
        logger.info(f"Creating {len(prs_data)} pull requests...")
        prs = []

        for i, pr_data in enumerate(prs_data):
            # Skip if PR already exists
            existing_pr = PullRequest.objects.filter(
                team=team,
                github_pr_id=pr_data.number,
                github_repo=self.config.repo_full_name,
            ).first()
            if existing_pr:
                prs.append(existing_pr)
                continue

            # Create PR in its own transaction
            try:
                with transaction.atomic():
                    pr = self._create_single_pr(team, pr_data)
                    if pr:
                        prs.append(pr)
            except Exception as e:
                logger.warning(f"Failed to create PR #{pr_data.number}: {e}")
                continue

            # Log progress every 50 PRs
            if (i + 1) % 50 == 0:
                logger.info(f"Created {i + 1}/{len(prs_data)} PRs...")

        logger.info(
            f"Created {self._stats.prs_created} PRs, "
            f"{self._stats.reviews_created} reviews, "
            f"{self._stats.commits_created} commits"
        )
        return prs

    def _create_single_pr(self, team: Team, pr_data: FetchedPRFull) -> PullRequest | None:
        """Create a single PR with all related records.

        Args:
            team: Team instance.
            pr_data: Fetched PR data.

        Returns:
            Created PullRequest or None if author not found.
        """
        # Find author
        author = self._find_member(pr_data.author_login, pr_data.author_id)
        if not author:
            # Skip PRs from non-team members
            return None

        # Determine state
        if pr_data.is_merged:
            state = "merged"
        elif pr_data.state == "closed":
            state = "closed"
        else:
            state = "open"

        # Calculate times
        cycle_time = Decimal(str(round(pr_data.cycle_time_hours, 2))) if pr_data.cycle_time_hours else None
        review_time = Decimal(str(round(pr_data.review_time_hours, 2))) if pr_data.review_time_hours else None

        # Create PR
        pr = PullRequestFactory(
            team=team,
            github_pr_id=pr_data.number,
            github_repo=self.config.repo_full_name,
            title=pr_data.title[:500],  # Limit title length
            author=author,
            state=state,
            pr_created_at=pr_data.created_at,
            merged_at=pr_data.merged_at,
            first_review_at=pr_data.first_review_at,
            cycle_time_hours=cycle_time,
            review_time_hours=review_time,
            additions=pr_data.additions,
            deletions=pr_data.deletions,
            jira_key=pr_data.jira_key_from_title or pr_data.jira_key_from_branch or "",
        )
        self._stats.prs_created += 1

        # Create related records
        self._create_pr_reviews(team, pr, pr_data)
        self._create_pr_commits(team, pr, pr_data)
        self._create_pr_files(team, pr, pr_data)
        self._create_pr_check_runs(team, pr, pr_data)

        return pr

    def _create_pr_reviews(self, team: Team, pr: PullRequest, pr_data: FetchedPRFull):
        """Create review records for a PR.

        Args:
            team: Team instance.
            pr: PullRequest instance.
            pr_data: Fetched PR data.
        """
        for review_data in pr_data.reviews:
            reviewer = self._find_member(review_data.reviewer_login, None)
            if not reviewer or reviewer == pr.author:
                continue

            PRReviewFactory(
                team=team,
                pull_request=pr,
                github_review_id=review_data.github_review_id,
                reviewer=reviewer,
                state=review_data.state.lower(),
                submitted_at=review_data.submitted_at,
            )
            self._stats.reviews_created += 1

    def _create_pr_commits(self, team: Team, pr: PullRequest, pr_data: FetchedPRFull):
        """Create commit records for a PR.

        Skips commits that already exist (same SHA can appear in multiple PRs).

        Args:
            team: Team instance.
            pr: PullRequest instance.
            pr_data: Fetched PR data.
        """
        from apps.metrics.models import Commit

        for commit_data in pr_data.commits:
            # Skip if commit already exists (same SHA can appear in multiple PRs)
            if Commit.objects.filter(team=team, github_sha=commit_data.sha).exists():
                continue

            author = self._find_member(commit_data.author_login, None)
            if not author:
                author = pr.author  # Default to PR author

            CommitFactory(
                team=team,
                github_sha=commit_data.sha,
                github_repo=self.config.repo_full_name,
                author=author,
                message=commit_data.message[:500],  # Limit message length
                committed_at=commit_data.committed_at,
                additions=commit_data.additions,
                deletions=commit_data.deletions,
                pull_request=pr,
            )
            self._stats.commits_created += 1

    def _create_pr_files(self, team: Team, pr: PullRequest, pr_data: FetchedPRFull):
        """Create file records for a PR.

        Args:
            team: Team instance.
            pr: PullRequest instance.
            pr_data: Fetched PR data.
        """
        from apps.metrics.models import PRFile

        for file_data in pr_data.files:
            # Compute changes from additions + deletions (not stored in FetchedFile)
            changes = file_data.additions + file_data.deletions

            PRFileFactory(
                team=team,
                pull_request=pr,
                filename=file_data.filename,
                status=file_data.status,
                additions=file_data.additions,
                deletions=file_data.deletions,
                changes=changes,
                file_category=PRFile.categorize_file(file_data.filename),
            )
            self._stats.files_created += 1

    def _create_pr_check_runs(self, team: Team, pr: PullRequest, pr_data: FetchedPRFull):
        """Create check run records for a PR.

        Skips check runs that already exist (same check run can appear in multiple PRs).

        Args:
            team: Team instance.
            pr: PullRequest instance.
            pr_data: Fetched PR data.
        """
        from apps.metrics.models import PRCheckRun

        for check_data in pr_data.check_runs:
            # Skip if check run already exists (same check can appear in multiple PRs)
            if PRCheckRun.objects.filter(team=team, github_check_run_id=check_data.github_id).exists():
                continue

            # Compute duration from timestamps if available
            duration_seconds = None
            if check_data.started_at and check_data.completed_at:
                duration_seconds = int((check_data.completed_at - check_data.started_at).total_seconds())

            PRCheckRunFactory(
                team=team,
                pull_request=pr,
                github_check_run_id=check_data.github_id,
                name=check_data.name,
                status=check_data.status,
                conclusion=check_data.conclusion,
                started_at=check_data.started_at,
                completed_at=check_data.completed_at,
                duration_seconds=duration_seconds,
            )
            self._stats.check_runs_created += 1

    def _simulate_jira_issues(
        self,
        team: Team,
        prs: list[PullRequest],
        prs_data: list[FetchedPRFull],
    ):
        """Simulate Jira issues for PRs.

        Args:
            team: Team instance.
            prs: List of PullRequest instances.
            prs_data: List of fetched PR data.
        """
        logger.info("Simulating Jira issues...")

        # Build PR data lookup
        pr_data_by_number = {pr.number: pr for pr in prs_data}

        for pr in prs:
            pr_data = pr_data_by_number.get(pr.github_pr_id)
            if not pr_data:
                continue

            # Get or generate Jira key
            jira_key = self._jira_simulator.extract_or_generate_jira_key(pr_data)

            # Create Jira issue
            self._jira_simulator.create_jira_issue(
                team=team,
                jira_key=jira_key,
                pr=pr_data,
                assignee=pr.author,
            )
            self._stats.jira_issues_created += 1

        logger.info(f"Created {self._stats.jira_issues_created} Jira issues")

    def _simulate_surveys(
        self,
        team: Team,
        prs: list[PullRequest],
        prs_data: list[FetchedPRFull],
    ):
        """Simulate surveys for merged PRs.

        Args:
            team: Team instance.
            prs: List of PullRequest instances.
            prs_data: List of fetched PR data.
        """
        logger.info("Simulating surveys...")

        # Build PR data lookup
        pr_data_by_number = {pr.number: pr for pr in prs_data}

        for pr in prs:
            # Only create surveys for merged PRs
            if pr.state != "merged":
                continue

            pr_data = pr_data_by_number.get(pr.github_pr_id)
            if not pr_data:
                continue

            # Determine if AI-assisted
            is_ai_assisted = self._survey_simulator.determine_ai_assisted(pr_data)

            # Get reviewers from PR reviews (team filter via PR's team)
            reviewers = list(
                TeamMember.objects.filter(  # noqa: TEAM001 - filtering via reviews_given__pull_request which is team-scoped
                    reviews_given__pull_request=pr,
                ).distinct()
            )

            # Create survey with responses
            survey = self._survey_simulator.create_survey_with_responses(
                team=team,
                pr=pr,
                author=pr.author,
                reviewers=reviewers,
                is_ai_assisted=is_ai_assisted,
            )
            self._stats.surveys_created += 1
            self._stats.survey_reviews_created += survey.reviews.count()

        logger.info(
            f"Created {self._stats.surveys_created} surveys, {self._stats.survey_reviews_created} survey reviews"
        )

    def _generate_ai_usage(self, team: Team):
        """Generate AI usage records for team members.

        Args:
            team: Team instance.
        """
        logger.info("Generating AI usage records...")

        members = list(TeamMember.objects.filter(team=team, is_active=True))
        start_date = timezone.now() - timedelta(days=self.config.days_back)
        end_date = timezone.now()

        records = self._survey_simulator.generate_team_ai_usage(
            team=team,
            members=members,
            start_date=start_date,
            end_date=end_date,
        )
        self._stats.ai_usage_records = len(records)

        logger.info(f"Created {self._stats.ai_usage_records} AI usage records")

    def _calculate_weekly_metrics(self, team: Team):
        """Calculate and store weekly metrics aggregates.

        Args:
            team: Team instance.
        """
        logger.info("Calculating weekly metrics...")

        members = TeamMember.objects.filter(team=team, is_active=True)

        for member in members:
            self._calculate_member_weekly_metrics(team, member)

        logger.info(f"Created {self._stats.weekly_metrics_created} weekly metrics records")

    def _calculate_member_weekly_metrics(self, team: Team, member: TeamMember):
        """Calculate weekly metrics for a single member.

        Args:
            team: Team instance.
            member: TeamMember instance.
        """
        # Get date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=self.config.days_back)

        # Calculate week start (Monday)
        current_week_start = start_date - timedelta(days=start_date.weekday())

        while current_week_start <= end_date:
            week_end = current_week_start + timedelta(days=6)

            # Get PRs merged this week by this member
            week_prs = PullRequest.objects.filter(
                team=team,
                author=member,
                state="merged",
                merged_at__date__gte=current_week_start,
                merged_at__date__lte=week_end,
            )

            if not week_prs.exists():
                current_week_start += timedelta(days=7)
                continue

            # Calculate aggregates
            prs_merged = week_prs.count()
            avg_cycle = week_prs.aggregate(avg=Avg("cycle_time_hours"))["avg"]
            avg_review = week_prs.aggregate(avg=Avg("review_time_hours"))["avg"]

            # Get commits
            from apps.metrics.models import Commit

            week_commits = Commit.objects.filter(
                team=team,
                author=member,
                committed_at__date__gte=current_week_start,
                committed_at__date__lte=week_end,
            )
            commits_count = week_commits.count()
            lines_stats = week_commits.aggregate(
                added=Sum("additions"),
                deleted=Sum("deletions"),
            )

            # Check for existing record
            existing = WeeklyMetrics.objects.filter(
                team=team,
                member=member,
                week_start=current_week_start,
            ).first()

            if existing:
                # Update existing
                existing.prs_merged = prs_merged
                existing.avg_cycle_time_hours = avg_cycle
                existing.avg_review_time_hours = avg_review
                existing.commits_count = commits_count
                existing.lines_added = lines_stats["added"] or 0
                existing.lines_removed = lines_stats["deleted"] or 0
                existing.save()
            else:
                # Create new
                WeeklyMetricsFactory(
                    team=team,
                    member=member,
                    week_start=current_week_start,
                    prs_merged=prs_merged,
                    avg_cycle_time_hours=avg_cycle,
                    avg_review_time_hours=avg_review,
                    commits_count=commits_count,
                    lines_added=lines_stats["added"] or 0,
                    lines_removed=lines_stats["deleted"] or 0,
                )
                self._stats.weekly_metrics_created += 1

            current_week_start += timedelta(days=7)

    def _log_stats(self):
        """Log final statistics."""
        logger.info("=" * 50)
        logger.info(f"Seeding Complete: {self._stats.project_name}")
        logger.info("=" * 50)
        logger.info(f"  Team created: {self._stats.team_created}")
        logger.info(f"  Team members: {self._stats.team_members_created}")
        logger.info(f"  PRs: {self._stats.prs_created}")
        logger.info(f"  Reviews: {self._stats.reviews_created}")
        logger.info(f"  Commits: {self._stats.commits_created}")
        logger.info(f"  Files: {self._stats.files_created}")
        logger.info(f"  Check runs: {self._stats.check_runs_created}")
        logger.info(f"  Jira issues: {self._stats.jira_issues_created}")
        logger.info(f"  Surveys: {self._stats.surveys_created}")
        logger.info(f"  Survey reviews: {self._stats.survey_reviews_created}")
        logger.info(f"  AI usage records: {self._stats.ai_usage_records}")
        logger.info(f"  Weekly metrics: {self._stats.weekly_metrics_created}")
        logger.info(f"  GitHub API calls: {self._stats.github_api_calls}")
        logger.info("=" * 50)


def clear_project_data(team_slug: str) -> bool:
    """Clear all seeded data for a project.

    Args:
        team_slug: The team slug to clear.

    Returns:
        True if team was found and cleared, False otherwise.
    """
    try:
        team = Team.objects.get(slug=team_slug)
    except Team.DoesNotExist:
        logger.warning(f"Team with slug '{team_slug}' not found")
        return False

    logger.info(f"Clearing data for team: {team.name}")

    # Delete all related data (CASCADE will handle most)
    from apps.metrics.models import (
        AIUsageDaily,
        Commit,
        JiraIssue,
        PRCheckRun,
        PRFile,
        PRReview,
        PRSurvey,
        PullRequest,
    )

    # Delete in reverse dependency order
    PRSurvey.objects.filter(team=team).delete()
    PRCheckRun.objects.filter(team=team).delete()
    PRFile.objects.filter(team=team).delete()
    PRReview.objects.filter(team=team).delete()
    Commit.objects.filter(team=team).delete()
    PullRequest.objects.filter(team=team).delete()
    JiraIssue.objects.filter(team=team).delete()
    AIUsageDaily.objects.filter(team=team).delete()
    WeeklyMetrics.objects.filter(team=team).delete()
    TeamMember.objects.filter(team=team).delete()

    logger.info(f"Cleared all data for team: {team.name}")
    return True
