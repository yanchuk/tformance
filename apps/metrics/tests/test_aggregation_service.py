"""
Tests for WeeklyMetrics aggregation service.

These tests verify the aggregation of weekly metrics per team member.
"""

from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    CommitFactory,
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.models import WeeklyMetrics
from apps.metrics.services.aggregation_service import (
    aggregate_team_weekly_metrics,
    compute_member_weekly_metrics,
    get_week_boundaries,
)


class TestGetWeekBoundaries(TestCase):
    """Tests for get_week_boundaries function."""

    def test_get_week_boundaries_returns_monday_to_sunday(self):
        """Test that week boundaries are returned as Monday to Sunday."""
        # Given a Wednesday (2025-12-18)
        test_date = date(2025, 12, 17)

        # When getting week boundaries
        week_start, week_end = get_week_boundaries(test_date)

        # Then it should return the Monday and Sunday of that week
        self.assertEqual(week_start, date(2025, 12, 15))  # Monday
        self.assertEqual(week_end, date(2025, 12, 21))  # Sunday
        self.assertEqual(week_start.weekday(), 0)  # Monday is 0
        self.assertEqual(week_end.weekday(), 6)  # Sunday is 6

    def test_get_week_boundaries_when_date_is_monday(self):
        """Test that when the date is Monday, it returns that Monday as start."""
        # Given a Monday
        test_date = date(2025, 12, 15)

        # When getting week boundaries
        week_start, week_end = get_week_boundaries(test_date)

        # Then it should return that Monday as the start
        self.assertEqual(week_start, date(2025, 12, 15))
        self.assertEqual(week_end, date(2025, 12, 21))

    def test_get_week_boundaries_when_date_is_sunday(self):
        """Test that when the date is Sunday, it returns the previous Monday."""
        # Given a Sunday
        test_date = date(2025, 12, 21)

        # When getting week boundaries
        week_start, week_end = get_week_boundaries(test_date)

        # Then it should return the Monday of that week
        self.assertEqual(week_start, date(2025, 12, 15))
        self.assertEqual(week_end, date(2025, 12, 21))


class TestComputeMemberWeeklyMetrics(TestCase):
    """Tests for compute_member_weekly_metrics function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.week_start = date(2025, 12, 15)  # Monday
        self.week_end = date(2025, 12, 21)  # Sunday

    def test_compute_member_weekly_metrics_with_no_data_returns_zeros(self):
        """Test that with no data, the function returns zero values."""
        # Given a member with no activity
        # When computing weekly metrics
        metrics = compute_member_weekly_metrics(self.team, self.member, self.week_start, self.week_end)

        # Then all metrics should be zero or None
        self.assertEqual(metrics["prs_merged"], 0)
        self.assertIsNone(metrics["avg_cycle_time_hours"])
        self.assertIsNone(metrics["avg_review_time_hours"])
        self.assertEqual(metrics["commits_count"], 0)
        self.assertEqual(metrics["lines_added"], 0)
        self.assertEqual(metrics["lines_removed"], 0)
        self.assertEqual(metrics["revert_count"], 0)
        self.assertEqual(metrics["hotfix_count"], 0)
        self.assertEqual(metrics["ai_assisted_prs"], 0)
        self.assertIsNone(metrics["avg_quality_rating"])
        self.assertEqual(metrics["surveys_completed"], 0)
        self.assertIsNone(metrics["guess_accuracy"])

    def test_compute_member_weekly_metrics_with_full_data(self):
        """Test computing metrics with all types of data present."""
        # Given merged PRs in the week
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 16, 10, 0)),
            pr_created_at=timezone.make_aware(datetime(2025, 12, 16, 2, 0)),
            cycle_time_hours=Decimal("8.00"),
            review_time_hours=Decimal("2.00"),
            additions=100,
            deletions=50,
            is_revert=False,
            is_hotfix=False,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 18, 14, 0)),
            pr_created_at=timezone.make_aware(datetime(2025, 12, 18, 2, 0)),
            cycle_time_hours=Decimal("12.00"),
            review_time_hours=Decimal("4.00"),
            additions=200,
            deletions=100,
            is_revert=True,
            is_hotfix=True,
        )

        # Given commits in the week
        CommitFactory.create_batch(
            3,
            team=self.team,
            author=self.member,
            committed_at=timezone.make_aware(datetime(2025, 12, 17, 10, 0)),
        )

        # When computing weekly metrics
        metrics = compute_member_weekly_metrics(self.team, self.member, self.week_start, self.week_end)

        # Then metrics should be aggregated correctly
        self.assertEqual(metrics["prs_merged"], 2)
        self.assertEqual(metrics["avg_cycle_time_hours"], Decimal("10.00"))  # (8+12)/2
        self.assertEqual(metrics["avg_review_time_hours"], Decimal("3.00"))  # (2+4)/2
        self.assertEqual(metrics["commits_count"], 3)
        self.assertEqual(metrics["lines_added"], 300)  # 100+200
        self.assertEqual(metrics["lines_removed"], 150)  # 50+100
        self.assertEqual(metrics["revert_count"], 1)
        self.assertEqual(metrics["hotfix_count"], 1)

    def test_compute_member_weekly_metrics_calculates_ai_metrics_correctly(self):
        """Test that AI metrics from surveys are calculated correctly."""
        # Given PRs with surveys
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 16, 10, 0)),
        )
        pr2 = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 17, 10, 0)),
        )
        pr3 = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 18, 10, 0)),
        )

        # Given surveys with responses
        survey1 = PRSurveyFactory(
            team=self.team,
            pull_request=pr1,
            author=self.member,
            author_ai_assisted=True,
            author_responded_at=timezone.now(),
        )
        survey2 = PRSurveyFactory(
            team=self.team,
            pull_request=pr2,
            author=self.member,
            author_ai_assisted=False,
            author_responded_at=timezone.now(),
        )
        # Survey 3 has no response (author_responded_at is None)
        PRSurveyFactory(
            team=self.team,
            pull_request=pr3,
            author=self.member,
            author_ai_assisted=None,
            author_responded_at=None,
        )

        # Given survey reviews with quality ratings
        reviewer1 = TeamMemberFactory(team=self.team)
        reviewer2 = TeamMemberFactory(team=self.team)

        PRSurveyReviewFactory(
            team=self.team,
            survey=survey1,
            reviewer=reviewer1,
            quality_rating=3,
            ai_guess=True,
            guess_correct=True,
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey2,
            reviewer=reviewer2,
            quality_rating=2,
            ai_guess=True,
            guess_correct=False,
        )

        # When computing weekly metrics
        metrics = compute_member_weekly_metrics(self.team, self.member, self.week_start, self.week_end)

        # Then AI metrics should be calculated correctly
        self.assertEqual(metrics["ai_assisted_prs"], 1)  # Only pr1
        self.assertEqual(metrics["surveys_completed"], 2)  # pr1 and pr2
        self.assertEqual(metrics["avg_quality_rating"], Decimal("2.50"))  # (3+2)/2
        self.assertEqual(metrics["guess_accuracy"], Decimal("50.00"))  # 1/2 = 50%

    def test_compute_member_weekly_metrics_excludes_data_outside_week(self):
        """Test that data outside the week boundaries is excluded."""
        # Given a PR merged before the week
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 14, 10, 0)),  # Sunday before
        )

        # Given a PR merged after the week
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 22, 10, 0)),  # Monday after
        )

        # Given a PR merged during the week
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 16, 10, 0)),  # Tuesday in week
        )

        # When computing weekly metrics
        metrics = compute_member_weekly_metrics(self.team, self.member, self.week_start, self.week_end)

        # Then only the PR in the week should be counted
        self.assertEqual(metrics["prs_merged"], 1)

    def test_compute_member_weekly_metrics_only_counts_merged_prs(self):
        """Test that only merged PRs are counted, not open or closed."""
        # Given PRs in different states
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 16, 10, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="open",
            merged_at=None,
            pr_created_at=timezone.make_aware(datetime(2025, 12, 16, 10, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="closed",
            merged_at=None,
            pr_created_at=timezone.make_aware(datetime(2025, 12, 16, 10, 0)),
        )

        # When computing weekly metrics
        metrics = compute_member_weekly_metrics(self.team, self.member, self.week_start, self.week_end)

        # Then only merged PRs should be counted
        self.assertEqual(metrics["prs_merged"], 1)


class TestAggregateTeamWeeklyMetrics(TestCase):
    """Tests for aggregate_team_weekly_metrics function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.week_start = date(2025, 12, 15)  # Monday

    def test_aggregate_team_weekly_metrics_creates_records_for_all_members(self):
        """Test that the function creates WeeklyMetrics for all active members."""
        # Given multiple active team members
        member1 = TeamMemberFactory(team=self.team, is_active=True)
        member2 = TeamMemberFactory(team=self.team, is_active=True)
        member3 = TeamMemberFactory(team=self.team, is_active=True)

        # When aggregating team metrics
        results = aggregate_team_weekly_metrics(self.team, self.week_start)

        # Then a WeeklyMetrics record should be created for each member
        self.assertEqual(len(results), 3)
        self.assertEqual(WeeklyMetrics.objects.filter(team=self.team).count(), 3)

        # And all members should have records
        member_ids = {wm.member_id for wm in results}
        self.assertEqual(member_ids, {member1.id, member2.id, member3.id})

    def test_aggregate_team_weekly_metrics_updates_existing_records(self):
        """Test that running aggregation twice updates existing records."""
        # Given an existing WeeklyMetrics record
        member = TeamMemberFactory(team=self.team, is_active=True)
        existing = WeeklyMetrics.objects.create(
            team=self.team,
            member=member,
            week_start=self.week_start,
            prs_merged=5,
        )

        # Given new data that would change the metrics
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(datetime(2025, 12, 16, 10, 0)),
        )

        # When aggregating again
        results = aggregate_team_weekly_metrics(self.team, self.week_start)

        # Then the existing record should be updated, not duplicated
        self.assertEqual(len(results), 1)
        self.assertEqual(WeeklyMetrics.objects.filter(team=self.team).count(), 1)

        # And the metrics should be recalculated
        updated = WeeklyMetrics.objects.get(id=existing.id)
        self.assertEqual(updated.prs_merged, 1)  # Recalculated from actual data

    def test_aggregate_team_weekly_metrics_only_includes_active_members(self):
        """Test that inactive members are excluded from aggregation."""
        # Given both active and inactive members
        active_member = TeamMemberFactory(team=self.team, is_active=True)
        TeamMemberFactory(team=self.team, is_active=False)

        # When aggregating team metrics
        results = aggregate_team_weekly_metrics(self.team, self.week_start)

        # Then only active members should have records
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].member, active_member)

    def test_aggregate_team_weekly_metrics_handles_empty_team(self):
        """Test that aggregation handles teams with no active members."""
        # Given a team with no active members
        TeamMemberFactory(team=self.team, is_active=False)

        # When aggregating team metrics
        results = aggregate_team_weekly_metrics(self.team, self.week_start)

        # Then no records should be created
        self.assertEqual(len(results), 0)
        self.assertEqual(WeeklyMetrics.for_team.count(), 0)
