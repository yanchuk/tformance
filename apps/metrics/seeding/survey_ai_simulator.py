"""
Survey and AI usage simulator for real project demo data seeding.

Simulates:
1. PR surveys with author AI disclosure
2. Reviewer responses with AI guesses
3. Daily AI usage metrics per member

Usage:
    simulator = SurveyAISimulator(config, rng)
    survey = simulator.create_survey_with_responses(team, pr, reviewers)
    ai_records = simulator.generate_ai_usage_for_member(team, member, date_range)
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.metrics.models import AIUsageDaily, PRSurvey, PRSurveyReview, TeamMember

from .deterministic import DeterministicRandom
from .github_authenticated_fetcher import FetchedPRFull
from .real_projects import RealProjectConfig


@dataclass
class AIUsagePattern:
    """AI usage pattern for a team member."""

    base_active_hours: float
    base_suggestions_shown: int
    acceptance_rate: float
    primary_source: str


class SurveyAISimulator:
    """Simulates surveys and AI usage based on PR characteristics.

    Uses probabilistic heuristics to determine:
    - Whether a PR was AI-assisted (based on size, file types)
    - Reviewer accuracy in detecting AI usage
    - Daily AI usage patterns per member

    Attributes:
        config: Project configuration with base rates.
        rng: Deterministic random generator for reproducibility.
    """

    # File extensions that indicate code files (more likely to use AI)
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".cpp",
        ".c",
        ".rb",
        ".swift",
        ".kt",
        ".scala",
        ".php",
    }

    # Quality rating distribution (skewed positive)
    QUALITY_DISTRIBUTION = {
        3: 0.50,  # "Super" - 50%
        2: 0.35,  # "OK" - 35%
        1: 0.15,  # "Could be better" - 15%
    }

    # Reviewer accuracy range (60-75% correct guesses)
    REVIEWER_ACCURACY_MIN = 0.60
    REVIEWER_ACCURACY_MAX = 0.75

    # AI source distribution
    AI_SOURCES = {
        "copilot": 0.70,  # 70% use Copilot
        "cursor": 0.30,  # 30% use Cursor
    }

    def __init__(self, config: RealProjectConfig, rng: DeterministicRandom):
        """Initialize the survey/AI simulator.

        Args:
            config: Project configuration with base AI adoption rate.
            rng: Deterministic random generator for reproducibility.
        """
        self.config = config
        self.rng = rng
        self._member_patterns: dict[int, AIUsagePattern] = {}

    def calculate_ai_probability(self, pr: FetchedPRFull) -> float:
        """Calculate probability that a PR was AI-assisted.

        Factors:
        - Base adoption rate from config
        - PR size (larger PRs more likely to use AI)
        - Code file count (more code files = more likely)

        Args:
            pr: Fetched PR data.

        Returns:
            Probability between 0.0 and 1.0.
        """
        probability = self.config.ai_base_adoption_rate

        # Size modifier: +15% for PRs with >300 lines changed
        total_lines = pr.additions + pr.deletions
        if total_lines > 300:
            probability += 0.15
        elif total_lines > 150:
            probability += 0.08

        # File type modifier: +10% for PRs with >5 code files
        code_file_count = self._count_code_files(pr)
        if code_file_count > 5:
            probability += 0.10
        elif code_file_count > 3:
            probability += 0.05

        # Cap at 85% - not everyone uses AI even for large PRs
        return min(0.85, probability)

    def _count_code_files(self, pr: FetchedPRFull) -> int:
        """Count the number of code files changed in a PR.

        Args:
            pr: Fetched PR data.

        Returns:
            Number of code files changed.
        """
        count = 0
        for file in pr.files:
            for ext in self.CODE_EXTENSIONS:
                if file.filename.endswith(ext):
                    count += 1
                    break
        return count

    def determine_ai_assisted(self, pr: FetchedPRFull) -> bool:
        """Determine if a PR was AI-assisted based on probability.

        Args:
            pr: Fetched PR data.

        Returns:
            True if AI-assisted, False otherwise.
        """
        probability = self.calculate_ai_probability(pr)
        return self.rng.random() < probability

    def should_respond_to_survey(self) -> bool:
        """Determine if an author should respond to the survey.

        Uses the survey response rate from config.

        Returns:
            True if should respond, False otherwise.
        """
        return self.rng.random() < self.config.survey_response_rate

    def create_survey_with_responses(
        self,
        team: models.Model,
        pr: models.Model,
        author: TeamMember,
        reviewers: list[TeamMember],
        is_ai_assisted: bool,
    ):
        """Create a PR survey with author and reviewer responses.

        Args:
            team: Team model instance.
            pr: PullRequest model instance.
            author: Author's TeamMember.
            reviewers: List of reviewer TeamMembers.
            is_ai_assisted: Whether the PR was AI-assisted.

        Returns:
            Created PRSurvey instance.
        """
        # Determine if author responds
        author_responded = self.should_respond_to_survey()

        # Calculate response time (1-48 hours after PR created)
        response_delay_hours = self.rng.randint(1, 48)
        responded_at = pr.created_at + timedelta(hours=response_delay_hours) if author_responded else None

        # Create or update the survey (idempotent for re-runs)
        survey, _created = PRSurvey.objects.update_or_create(
            pull_request=pr,
            defaults={
                "team": team,
                "author": author,
                "author_ai_assisted": is_ai_assisted if author_responded else None,
                "author_responded_at": responded_at,
                "token": None,
                "token_expires_at": None,
            },
        )

        # Create reviewer responses
        for reviewer in reviewers:
            if reviewer == author:
                continue  # Skip author

            # Only some reviewers respond
            if self.rng.random() > 0.7:  # 70% response rate for reviewers
                continue

            self._create_reviewer_response(survey, reviewer, is_ai_assisted, author_responded)

        return survey

    def _create_reviewer_response(
        self,
        survey,
        reviewer: TeamMember,
        actual_ai_assisted: bool,
        author_disclosed: bool,
    ):
        """Create a reviewer's response to the survey.

        Args:
            survey: PRSurvey instance.
            reviewer: Reviewer's TeamMember.
            actual_ai_assisted: Whether the PR was actually AI-assisted.
            author_disclosed: Whether the author disclosed their AI usage.
        """
        # Determine quality rating (skewed positive)
        quality_rating = self.rng.weighted_choice(self.QUALITY_DISTRIBUTION)

        # Determine AI guess with reviewer accuracy range
        reviewer_accuracy = self.rng.uniform(self.REVIEWER_ACCURACY_MIN, self.REVIEWER_ACCURACY_MAX)

        # Reviewer guesses correctly based on accuracy
        ai_guess = actual_ai_assisted if self.rng.random() < reviewer_accuracy else not actual_ai_assisted

        # Calculate if guess was correct (only if author disclosed)
        guess_correct = ai_guess == actual_ai_assisted if author_disclosed else None

        # Response time (1-72 hours after survey created)
        response_delay_hours = self.rng.randint(1, 72)
        responded_at = survey.created_at + timedelta(hours=response_delay_hours)

        # Create or update the review (idempotent for re-runs)
        PRSurveyReview.objects.update_or_create(
            survey=survey,
            reviewer=reviewer,
            defaults={
                "team": survey.team,
                "quality_rating": quality_rating,
                "ai_guess": ai_guess,
                "guess_correct": guess_correct,
                "responded_at": responded_at,
            },
        )

    def get_or_create_member_pattern(self, member: TeamMember) -> AIUsagePattern:
        """Get or create consistent AI usage pattern for a member.

        Creates a stable pattern so the same member has consistent
        AI usage characteristics across all generated records.

        Args:
            member: TeamMember instance.

        Returns:
            AIUsagePattern for this member.
        """
        member_id = member.id
        if member_id in self._member_patterns:
            return self._member_patterns[member_id]

        # Generate consistent pattern for this member
        pattern = AIUsagePattern(
            base_active_hours=self.rng.uniform(2.0, 6.0),
            base_suggestions_shown=self.rng.randint(100, 400),
            acceptance_rate=self.rng.uniform(0.25, 0.45),
            primary_source=self.rng.weighted_choice(self.AI_SOURCES),
        )

        self._member_patterns[member_id] = pattern
        return pattern

    def generate_ai_usage_for_member(
        self,
        team: models.Model,
        member: TeamMember,
        start_date: timezone.datetime,
        end_date: timezone.datetime,
    ) -> list[AIUsageDaily]:
        """Generate daily AI usage records for a team member (in-memory).

        Creates record objects for workdays only (Mon-Fri) with consistent
        patterns per member but daily variation. Records are NOT saved to DB.

        Args:
            team: Team model instance.
            member: TeamMember instance.
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            List of unsaved AIUsageDaily instances.
        """
        pattern = self.get_or_create_member_pattern(member)
        records = []

        current_date = start_date
        while current_date <= end_date:
            # Skip weekends and some workdays (vacation, meetings, etc. - 85% work rate)
            if current_date.weekday() < 5 and self.rng.random() < 0.85:  # Mon-Fri, 85% of workdays
                record = self._build_daily_usage(team, member, current_date.date(), pattern)
                records.append(record)

            current_date += timedelta(days=1)

        return records

    def _build_daily_usage(
        self,
        team: models.Model,
        member: TeamMember,
        date,
        pattern: AIUsagePattern,
    ) -> AIUsageDaily:
        """Build a single day's AI usage record (in-memory, not saved).

        Args:
            team: Team model instance.
            member: TeamMember instance.
            date: Date for the record.
            pattern: Member's AI usage pattern.

        Returns:
            Unsaved AIUsageDaily instance.
        """
        # Add daily variation (0.7-1.3x base values)
        variation = self.rng.uniform(0.7, 1.3)

        active_hours = Decimal(str(round(pattern.base_active_hours * variation, 2)))
        suggestions_shown = int(pattern.base_suggestions_shown * variation)
        suggestions_accepted = int(suggestions_shown * pattern.acceptance_rate * self.rng.uniform(0.9, 1.1))

        # Calculate acceptance rate
        acceptance_rate = (
            Decimal(str(round(suggestions_accepted / suggestions_shown * 100, 2)))
            if suggestions_shown > 0
            else Decimal("0")
        )

        # Build record without saving (for bulk insert)
        return AIUsageDaily(
            team=team,
            member=member,
            date=date,
            source=pattern.primary_source,
            active_hours=active_hours,
            suggestions_shown=suggestions_shown,
            suggestions_accepted=suggestions_accepted,
            acceptance_rate=acceptance_rate,
        )

    def generate_team_ai_usage(
        self,
        team: models.Model,
        members: list[TeamMember],
        start_date: timezone.datetime,
        end_date: timezone.datetime,
        batch_size: int = 5000,
    ) -> int:
        """Generate AI usage records for all team members using bulk insert.

        Uses bulk_create with update_conflicts for 10-50x faster seeding.

        Args:
            team: Team model instance.
            members: List of TeamMember instances.
            start_date: Start of date range.
            end_date: End of date range.
            batch_size: Number of records per bulk insert (default 5000).

        Returns:
            Total number of records created/updated.
        """
        all_records: list[AIUsageDaily] = []
        total_created = 0

        for member in members:
            # Only some members use AI tools
            if self.rng.random() < self.config.ai_base_adoption_rate:
                records = self.generate_ai_usage_for_member(team, member, start_date, end_date)
                all_records.extend(records)

                # Bulk insert when batch is full
                if len(all_records) >= batch_size:
                    total_created += self._bulk_upsert_ai_usage(all_records)
                    all_records = []

        # Insert remaining records
        if all_records:
            total_created += self._bulk_upsert_ai_usage(all_records)

        return total_created

    def _bulk_upsert_ai_usage(self, records: list[AIUsageDaily]) -> int:
        """Bulk insert/update AI usage records.

        Uses PostgreSQL ON CONFLICT DO UPDATE for idempotent upserts.

        Args:
            records: List of AIUsageDaily instances to insert/update.

        Returns:
            Number of records processed.
        """
        if not records:
            return 0

        AIUsageDaily.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["team", "member", "date", "source"],
            update_fields=["active_hours", "suggestions_shown", "suggestions_accepted", "acceptance_rate"],
        )
        return len(records)
