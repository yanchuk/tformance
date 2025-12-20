"""
Data generator for scenario-based demo data seeding.

Orchestrates the creation of coherent demo data based on scenario
parameters, optionally incorporating real PR metadata from GitHub.

Usage:
    from apps.metrics.seeding import get_scenario
    from apps.metrics.seeding.data_generator import ScenarioDataGenerator

    scenario = get_scenario("ai-success")
    generator = ScenarioDataGenerator(scenario, seed=42)
    stats = generator.generate(team)
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.metrics.factories import (
    AIUsageDailyFactory,
    CommitFactory,
    PRReviewFactory,
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamMemberFactory,
    WeeklyMetricsFactory,
)
from apps.metrics.models import TeamMember

from .deterministic import DeterministicRandom
from .github_fetcher import FetchedPR, GitHubPublicFetcher
from .scenarios.base import BaseScenario, MemberArchetype

logger = logging.getLogger(__name__)


@dataclass
class GeneratorStats:
    """Statistics from a data generation run."""

    team_members_created: int = 0
    prs_created: int = 0
    reviews_created: int = 0
    commits_created: int = 0
    surveys_created: int = 0
    ai_usage_records: int = 0
    weekly_metrics_created: int = 0
    github_prs_used: int = 0
    factory_prs_used: int = 0


@dataclass
class MemberWithArchetype:
    """A team member paired with their archetype definition."""

    member: TeamMember
    archetype: MemberArchetype


@dataclass
class ScenarioDataGenerator:
    """Generates demo data based on a scenario definition.

    Creates coherent data across all models, respecting:
    - Weekly parameter progression from the scenario
    - Member archetypes and their behaviors
    - Reviewer selection weights
    - Temporal relationships between entities

    Attributes:
        scenario: The scenario defining data patterns.
        seed: Random seed for reproducibility.
        fetch_github: Whether to fetch real PR data from GitHub.
        github_percentage: Fraction of PRs to source from GitHub (0.0-1.0).
    """

    scenario: BaseScenario
    seed: int = 42
    fetch_github: bool = True
    github_percentage: float = 0.25

    # Internal state
    _rng: DeterministicRandom = field(init=False)
    _github_prs: list[FetchedPR] = field(default_factory=list, init=False)
    _members: list[MemberWithArchetype] = field(default_factory=list, init=False)
    _stats: GeneratorStats = field(default_factory=GeneratorStats, init=False)

    def __post_init__(self):
        """Initialize random generator and fetch GitHub data if enabled."""
        self._rng = DeterministicRandom(self.seed)
        self._stats = GeneratorStats()

        if self.fetch_github:
            self._prefetch_github_data()

    def _prefetch_github_data(self):
        """Fetch PR data from GitHub for later use."""
        fetcher = GitHubPublicFetcher()
        repos = self.scenario.config.github_source_repos

        for repo in repos:
            prs = fetcher.fetch_prs(repo, limit=20)
            self._github_prs.extend(prs)

        logger.info("Pre-fetched %d PRs from GitHub", len(self._github_prs))

    def generate(self, team: models.Model) -> GeneratorStats:
        """Generate all demo data for a team.

        Args:
            team: The Team model instance to generate data for.

        Returns:
            GeneratorStats with counts of created objects.
        """
        logger.info(
            "Generating data for scenario '%s' with seed %d",
            self.scenario.config.name,
            self.seed,
        )

        # Step 1: Create team members based on archetypes
        self._create_team_members(team)

        # Step 2: Generate data for each week
        config = self.scenario.config
        for week in range(config.weeks):
            self._generate_week(team, week)

        # Step 3: Calculate coherent weekly metrics
        self._calculate_weekly_metrics(team)

        logger.info(
            "Generation complete: %d members, %d PRs, %d reviews",
            self._stats.team_members_created,
            self._stats.prs_created,
            self._stats.reviews_created,
        )

        return self._stats

    def _create_team_members(self, team: models.Model):
        """Create team members based on scenario archetypes."""
        archetypes = self.scenario.get_member_archetypes()

        for archetype in archetypes:
            for i in range(archetype.count):
                member = TeamMemberFactory(
                    team=team,
                    role="lead" if i == 0 and archetype.name == "bottleneck_reviewer" else "developer",
                )
                self._members.append(MemberWithArchetype(member=member, archetype=archetype))
                self._stats.team_members_created += 1

        logger.debug("Created %d team members", len(self._members))

    def _generate_week(self, team: models.Model, week: int):
        """Generate all data for a specific week."""
        params = self.scenario.get_weekly_params(week)
        config = self.scenario.config

        # Calculate week boundaries
        weeks_ago = config.weeks - week - 1
        week_start = timezone.now() - timedelta(weeks=weeks_ago + 1)
        week_end = timezone.now() - timedelta(weeks=weeks_ago)

        # Generate PRs for each member
        for member_data in self._members:
            self._generate_member_week(team, member_data, week, params, week_start, week_end)

    def _generate_member_week(
        self,
        team: models.Model,
        member_data: MemberWithArchetype,
        week: int,
        params: dict,
        week_start,
        week_end,
    ):
        """Generate a week's worth of data for a single member."""
        config = self.scenario.config
        archetype = member_data.archetype
        member = member_data.member

        # Calculate PR count with archetype modifier
        min_prs, max_prs = config.prs_per_member_per_week
        base_prs = self._rng.randint(min_prs, max_prs)
        pr_count = max(1, int(base_prs * archetype.pr_volume_modifier))

        for _ in range(pr_count):
            self._create_pr_with_related(
                team,
                member_data,
                week,
                params,
                week_start,
                week_end,
            )

        # Generate AI usage for members who use AI
        base_ai_rate = float(params["ai_adoption_rate"])
        member_ai_rate = min(1.0, max(0.0, base_ai_rate + archetype.ai_adoption_modifier))

        if self._rng.should_happen(member_ai_rate):
            self._create_ai_usage(team, member, week_start)

    def _create_pr_with_related(
        self,
        team: models.Model,
        member_data: MemberWithArchetype,
        week: int,
        params: dict,
        week_start,
        week_end,
    ):
        """Create a PR and related objects (reviews, commits, surveys)."""
        member = member_data.member
        archetype = member_data.archetype

        # Decide if this PR uses GitHub data
        use_github = self._github_prs and self._rng.should_happen(self.github_percentage)

        if use_github:
            github_pr = self._rng.choice(self._github_prs)
            self._stats.github_prs_used += 1
        else:
            github_pr = None
            self._stats.factory_prs_used += 1

        # Determine PR state
        state_dist = self.scenario.get_pr_state_distribution(week)
        state = self._rng.weighted_choice(state_dist)

        # Calculate AI-assisted based on adoption rate + archetype
        base_ai_rate = float(params["ai_adoption_rate"])
        member_ai_rate = min(1.0, max(0.0, base_ai_rate + archetype.ai_adoption_modifier))
        is_ai_assisted = self._rng.should_happen(member_ai_rate)

        # Create the PR
        pr_created_at = self._rng.datetime_in_range(week_start, week_end)

        # Calculate timing based on scenario params
        avg_review_hours = float(params["avg_review_time_hours"])
        avg_cycle_hours = float(params["avg_cycle_time_hours"])

        # Add some variance
        review_hours = max(0.5, self._rng.gauss(avg_review_hours, avg_review_hours * 0.3))
        cycle_hours = max(review_hours + 1, self._rng.gauss(avg_cycle_hours, avg_cycle_hours * 0.3))

        first_review_at = pr_created_at + timedelta(hours=review_hours) if state != "open" else None
        merged_at = pr_created_at + timedelta(hours=cycle_hours) if state == "merged" else None

        # Determine if revert based on scenario params
        revert_rate = float(params["revert_rate"])
        is_revert = self._rng.should_happen(revert_rate)

        pr = PullRequestFactory(
            team=team,
            author=member,
            state=state,
            pr_created_at=pr_created_at,
            first_review_at=first_review_at,
            merged_at=merged_at,
            cycle_time_hours=Decimal(str(round(cycle_hours, 2))) if merged_at else None,
            review_time_hours=Decimal(str(round(review_hours, 2))) if first_review_at else None,
            title=github_pr.title if github_pr else PullRequestFactory._meta.model._meta.get_field("title").default,
            additions=github_pr.additions if github_pr else self._rng.randint(10, 500),
            deletions=github_pr.deletions if github_pr else self._rng.randint(5, 200),
            is_revert=is_revert,
        )
        self._stats.prs_created += 1

        # Create reviews
        if state != "open":
            self._create_reviews(team, pr, week, params)

        # Create commits
        commits_count = github_pr.commits_count if github_pr else self._rng.randint(1, 5)
        for _ in range(commits_count):
            commit_end = first_review_at or pr_created_at + timedelta(hours=2)
            CommitFactory(
                team=team,
                author=member,
                pull_request=pr,
                committed_at=self._rng.datetime_in_range(pr_created_at, commit_end),
            )
            self._stats.commits_created += 1

        # Create survey for merged PRs
        if state == "merged" and self._rng.should_happen(0.7):  # 70% survey response
            self._create_survey(team, pr, is_ai_assisted, week)

    def _create_reviews(self, team: models.Model, pr, week: int, params: dict):
        """Create reviews for a PR based on scenario weights."""
        reviewer_weights = self.scenario.get_reviewer_selection_weights(week)
        review_dist = self.scenario.get_review_state_distribution(week)

        # Get available reviewers (not the PR author)
        available = [m for m in self._members if m.member != pr.author]
        if not available:
            return

        # Determine number of reviews (1-3)
        num_reviews = self._rng.randint(1, min(3, len(available)))

        for _ in range(num_reviews):
            # Select reviewer based on weights if defined
            if reviewer_weights:
                # Weight selection by archetype - use index as hashable key
                weighted_reviewers = {}
                for idx, m in enumerate(available):
                    weight = reviewer_weights.get(m.archetype.name, 0.5)
                    weighted_reviewers[idx] = weight

                selected_idx = self._rng.weighted_choice(weighted_reviewers)
                reviewer_data = available[selected_idx]
            else:
                reviewer_data = self._rng.choice(available)

            # Determine review state
            review_state = self._rng.weighted_choice(review_dist)

            PRReviewFactory(
                team=team,
                pull_request=pr,
                reviewer=reviewer_data.member,
                state=review_state,
                submitted_at=pr.first_review_at or pr.pr_created_at + timedelta(hours=1),
            )
            self._stats.reviews_created += 1

            # Remove from available to avoid duplicate reviews
            available = [m for m in available if m != reviewer_data]
            if not available:
                break

    def _create_survey(self, team: models.Model, pr, is_ai_assisted: bool, week: int):
        """Create a survey and reviewer responses for a PR."""
        survey = PRSurveyFactory(
            team=team,
            pull_request=pr,
            author=pr.author,
            author_ai_assisted=is_ai_assisted,
            author_responded_at=pr.merged_at + timedelta(hours=self._rng.randint(1, 24)) if pr.merged_at else None,
        )
        self._stats.surveys_created += 1

        # Create reviewer responses
        available_reviewers = [m for m in self._members if m.member != pr.author]
        num_responses = self._rng.randint(1, min(3, len(available_reviewers)))

        for reviewer_data in self._rng.sample(available_reviewers, num_responses):
            # Guess accuracy based on author's archetype (how detectable is their AI use)
            author_archetype = next(
                (m.archetype for m in self._members if m.member == pr.author),
                None,
            )

            if author_archetype:
                min_acc, max_acc = self.scenario.get_guess_accuracy_for_archetype(author_archetype.name)
                guess_correct = self._rng.should_happen((min_acc + max_acc) / 2)
                ai_guess = is_ai_assisted if guess_correct else not is_ai_assisted
            else:
                ai_guess = self._rng.choice([True, False])
                guess_correct = ai_guess == is_ai_assisted

            # Quality rating based on scenario params
            quality_rating = self._rng.choice([1, 2, 2, 3, 3, 3])  # Skew positive

            PRSurveyReviewFactory(
                team=team,
                survey=survey,
                reviewer=reviewer_data.member,
                ai_guess=ai_guess,
                guess_correct=guess_correct,
                quality_rating=quality_rating,
            )

    def _create_ai_usage(self, team: models.Model, member: TeamMember, week_start):
        """Create AI usage records for a member's week."""
        # Create usage for 3-5 days in the week
        days = self._rng.randint(3, 5)
        for day_offset in self._rng.sample(range(7), days):
            usage_date = (week_start + timedelta(days=day_offset)).date()

            AIUsageDailyFactory(
                team=team,
                member=member,
                date=usage_date,
                source=self._rng.choice(["copilot", "copilot", "cursor"]),
            )
            self._stats.ai_usage_records += 1

    def _calculate_weekly_metrics(self, team: models.Model):
        """Calculate WeeklyMetrics from generated data.

        Creates aggregate metrics that accurately reflect the generated PRs.
        """
        from apps.metrics.models import PullRequest

        config = self.scenario.config

        for week in range(config.weeks):
            weeks_ago = config.weeks - week - 1
            week_start = (timezone.now() - timedelta(weeks=weeks_ago + 1)).date()
            # Adjust to Monday
            week_start = week_start - timedelta(days=week_start.weekday())

            for member_data in self._members:
                member = member_data.member

                # Query actual PR data for this member/week
                member_prs = PullRequest.objects.filter(
                    team=team,
                    author=member,
                    pr_created_at__date__gte=week_start,
                    pr_created_at__date__lt=week_start + timedelta(days=7),
                )

                merged_prs = member_prs.filter(state="merged")
                prs_merged = merged_prs.count()

                if prs_merged == 0:
                    continue  # Skip weeks with no merged PRs

                # Calculate actual averages
                cycle_times = [p.cycle_time_hours for p in merged_prs if p.cycle_time_hours]
                review_times = [p.review_time_hours for p in merged_prs if p.review_time_hours]

                avg_cycle = sum(cycle_times, Decimal("0")) / len(cycle_times) if cycle_times else Decimal("0")
                avg_review = sum(review_times, Decimal("0")) / len(review_times) if review_times else Decimal("0")

                lines_added = sum(p.additions or 0 for p in merged_prs)
                lines_removed = sum(p.deletions or 0 for p in merged_prs)
                reverts = merged_prs.filter(is_revert=True).count()

                WeeklyMetricsFactory(
                    team=team,
                    member=member,
                    week_start=week_start,
                    prs_merged=prs_merged,
                    avg_cycle_time_hours=avg_cycle,
                    avg_review_time_hours=avg_review,
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    revert_count=reverts,
                    commits_count=self._rng.randint(prs_merged * 2, prs_merged * 5),
                )
                self._stats.weekly_metrics_created += 1
