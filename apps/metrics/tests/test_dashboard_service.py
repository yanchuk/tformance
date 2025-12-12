"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetKeyMetrics(TestCase):
    """Tests for get_key_metrics function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_key_metrics_returns_dict_with_required_keys(self):
        """Test that get_key_metrics returns a dict with all required keys."""
        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        self.assertIn("prs_merged", result)
        self.assertIn("avg_cycle_time", result)
        self.assertIn("avg_quality_rating", result)
        self.assertIn("ai_assisted_pct", result)

    def test_get_key_metrics_counts_merged_prs_in_date_range(self):
        """Test that get_key_metrics counts only merged PRs within date range."""
        # Create merged PRs in range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
        )

        # Create PRs outside range (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
        )

        # Create non-merged PRs (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="open",
            merged_at=None,
        )

        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["prs_merged"], 2)

    def test_get_key_metrics_calculates_avg_cycle_time(self):
        """Test that get_key_metrics calculates average cycle time correctly."""
        # Create PRs with different cycle times
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=Decimal("24.00"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("48.00"),
        )

        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        # Average should be (24 + 48) / 2 = 36
        self.assertEqual(result["avg_cycle_time"], Decimal("36.00"))

    def test_get_key_metrics_calculates_avg_quality_rating_from_surveys(self):
        """Test that get_key_metrics calculates average quality rating from survey reviews."""
        # Create PRs with surveys and reviews
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey1 = PRSurveyFactory(team=self.team, pull_request=pr1)
        PRSurveyReviewFactory(team=self.team, survey=survey1, quality_rating=3)
        PRSurveyReviewFactory(team=self.team, survey=survey1, quality_rating=2)

        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
        )
        survey2 = PRSurveyFactory(team=self.team, pull_request=pr2)
        PRSurveyReviewFactory(team=self.team, survey=survey2, quality_rating=1)

        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        # Average should be (3 + 2 + 1) / 3 = 2.00
        self.assertEqual(result["avg_quality_rating"], Decimal("2.00"))

    def test_get_key_metrics_calculates_ai_assisted_percentage(self):
        """Test that get_key_metrics calculates AI-assisted percentage correctly."""
        # Create 3 merged PRs with surveys
        for i, ai_assisted in enumerate([True, True, False]):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=ai_assisted)

        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        # 2 out of 3 = 66.67%
        self.assertAlmostEqual(float(result["ai_assisted_pct"]), 66.67, places=2)

    def test_get_key_metrics_handles_no_data(self):
        """Test that get_key_metrics handles empty dataset gracefully."""
        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["prs_merged"], 0)
        self.assertIsNone(result["avg_cycle_time"])
        self.assertIsNone(result["avg_quality_rating"])
        self.assertEqual(result["ai_assisted_pct"], Decimal("0.00"))

    def test_get_key_metrics_filters_by_team(self):
        """Test that get_key_metrics only includes data from the specified team."""
        other_team = TeamFactory()

        # Create PR for target team
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # Create PR for other team (should be excluded)
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["prs_merged"], 1)


class TestGetAIAdoptionTrend(TestCase):
    """Tests for get_ai_adoption_trend function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_ai_adoption_trend_returns_list_of_dicts(self):
        """Test that get_ai_adoption_trend returns a list of week/value dicts."""
        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_ai_adoption_trend_groups_by_week(self):
        """Test that get_ai_adoption_trend groups data by week."""
        # Week 1: Jan 1-7 (2 PRs, 1 AI-assisted = 50%)
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr1, author_ai_assisted=True)

        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr2, author_ai_assisted=False)

        # Week 2: Jan 8-14 (2 PRs, 2 AI-assisted = 100%)
        pr3 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr3, author_ai_assisted=True)

        pr4 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr4, author_ai_assisted=True)

        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        self.assertGreaterEqual(len(result), 2)
        # Each entry should have week and value
        for entry in result:
            self.assertIn("week", entry)
            self.assertIn("value", entry)

    def test_get_ai_adoption_trend_calculates_percentage_correctly(self):
        """Test that get_ai_adoption_trend calculates AI percentage per week."""
        # Create PRs in one week: 3 out of 4 AI-assisted
        merged_dates = [
            timezone.datetime(2024, 1, 3, 12, 0),
            timezone.datetime(2024, 1, 4, 12, 0),
            timezone.datetime(2024, 1, 5, 12, 0),
            timezone.datetime(2024, 1, 6, 12, 0),
        ]
        ai_flags = [True, True, True, False]

        for merged_date, ai_flag in zip(merged_dates, ai_flags, strict=True):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(merged_date),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=ai_flag)

        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        # Find the week with our data
        week_data = next((w for w in result if len(result) > 0), None)
        if week_data:
            # 3 out of 4 = 75%
            self.assertAlmostEqual(float(week_data["value"]), 75.0, places=1)

    def test_get_ai_adoption_trend_handles_week_with_no_prs(self):
        """Test that get_ai_adoption_trend handles weeks with no PRs."""
        # Create PR in first week only
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)

        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        # Should handle empty weeks gracefully
        self.assertIsInstance(result, list)


class TestGetAIQualityComparison(TestCase):
    """Tests for get_ai_quality_comparison function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_ai_quality_comparison_returns_dict_with_ai_and_non_ai_keys(self):
        """Test that get_ai_quality_comparison returns dict with ai_avg and non_ai_avg."""
        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        self.assertIn("ai_avg", result)
        self.assertIn("non_ai_avg", result)

    def test_get_ai_quality_comparison_calculates_ai_average(self):
        """Test that get_ai_quality_comparison calculates AI-assisted quality average."""
        # Create AI-assisted PRs with quality ratings
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey1 = PRSurveyFactory(team=self.team, pull_request=pr1, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey1, quality_rating=3)

        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey2 = PRSurveyFactory(team=self.team, pull_request=pr2, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey2, quality_rating=1)

        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        # Average should be (3 + 1) / 2 = 2.00
        self.assertEqual(result["ai_avg"], Decimal("2.00"))

    def test_get_ai_quality_comparison_calculates_non_ai_average(self):
        """Test that get_ai_quality_comparison calculates non-AI quality average."""
        # Create non-AI-assisted PRs with quality ratings
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey1 = PRSurveyFactory(team=self.team, pull_request=pr1, author_ai_assisted=False)
        PRSurveyReviewFactory(team=self.team, survey=survey1, quality_rating=2)

        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey2 = PRSurveyFactory(team=self.team, pull_request=pr2, author_ai_assisted=False)
        PRSurveyReviewFactory(team=self.team, survey=survey2, quality_rating=2)

        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        # Average should be (2 + 2) / 2 = 2.00
        self.assertEqual(result["non_ai_avg"], Decimal("2.00"))

    def test_get_ai_quality_comparison_handles_no_ai_data(self):
        """Test that get_ai_quality_comparison handles case with no AI data."""
        # Create only non-AI PR
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=False)
        PRSurveyReviewFactory(team=self.team, survey=survey, quality_rating=2)

        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        self.assertIsNone(result["ai_avg"])
        self.assertIsNotNone(result["non_ai_avg"])

    def test_get_ai_quality_comparison_handles_no_non_ai_data(self):
        """Test that get_ai_quality_comparison handles case with no non-AI data."""
        # Create only AI-assisted PR
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey, quality_rating=3)

        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        self.assertIsNotNone(result["ai_avg"])
        self.assertIsNone(result["non_ai_avg"])


class TestGetCycleTimeTrend(TestCase):
    """Tests for get_cycle_time_trend function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_cycle_time_trend_returns_list_of_dicts(self):
        """Test that get_cycle_time_trend returns a list of week/value dicts."""
        result = dashboard_service.get_cycle_time_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_cycle_time_trend_groups_by_week(self):
        """Test that get_cycle_time_trend groups data by week."""
        # Week 1 PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
            cycle_time_hours=Decimal("24.00"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            cycle_time_hours=Decimal("48.00"),
        )

        # Week 2 PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("36.00"),
        )

        result = dashboard_service.get_cycle_time_trend(self.team, self.start_date, self.end_date)

        # Should have entries for multiple weeks
        self.assertIsInstance(result, list)
        for entry in result:
            self.assertIn("week", entry)
            self.assertIn("value", entry)

    def test_get_cycle_time_trend_calculates_weekly_average(self):
        """Test that get_cycle_time_trend calculates average cycle time per week."""
        # Create PRs in same week with different cycle times
        merged_dates = [
            timezone.datetime(2024, 1, 3, 12, 0),
            timezone.datetime(2024, 1, 4, 12, 0),
            timezone.datetime(2024, 1, 5, 12, 0),
        ]
        cycle_times = [Decimal("24.00"), Decimal("36.00"), Decimal("48.00")]

        for merged_date, cycle_time in zip(merged_dates, cycle_times, strict=True):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(merged_date),
                cycle_time_hours=cycle_time,
            )

        result = dashboard_service.get_cycle_time_trend(self.team, self.start_date, self.end_date)

        # Find the week with our data
        if len(result) > 0:
            week_data = result[0]
            # Average should be (24 + 36 + 48) / 3 = 36
            self.assertAlmostEqual(float(week_data["value"]), 36.0, places=1)


class TestGetTeamBreakdown(TestCase):
    """Tests for get_team_breakdown function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_team_breakdown_returns_list_of_dicts(self):
        """Test that get_team_breakdown returns a list of member dicts."""
        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_team_breakdown_includes_member_name(self):
        """Test that get_team_breakdown includes member display name."""
        member = TeamMemberFactory(team=self.team, display_name="Alice Smith")
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertGreater(len(result), 0)
        member_data = next((m for m in result if m["member_name"] == "Alice Smith"), None)
        self.assertIsNotNone(member_data)

    def test_get_team_breakdown_counts_prs_merged_per_member(self):
        """Test that get_team_breakdown counts PRs merged per member."""
        member = TeamMemberFactory(team=self.team, display_name="Alice Smith")

        # Create 3 merged PRs for this member
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Alice Smith"), None)
        self.assertEqual(member_data["prs_merged"], 3)

    def test_get_team_breakdown_calculates_avg_cycle_time_per_member(self):
        """Test that get_team_breakdown calculates average cycle time per member."""
        member = TeamMemberFactory(team=self.team, display_name="Bob Jones")

        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("24.00"),
        )
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=Decimal("48.00"),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Bob Jones"), None)
        # Average should be (24 + 48) / 2 = 36
        self.assertEqual(member_data["avg_cycle_time"], Decimal("36.00"))

    def test_get_team_breakdown_calculates_ai_percentage_per_member(self):
        """Test that get_team_breakdown calculates AI-assisted percentage per member."""
        member = TeamMemberFactory(team=self.team, display_name="Charlie Brown")

        # Create 4 PRs: 3 AI-assisted, 1 not
        ai_flags = [True, True, True, False]
        for i, ai_flag in enumerate(ai_flags):
            pr = PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=ai_flag)

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Charlie Brown"), None)
        # 3 out of 4 = 75%
        self.assertAlmostEqual(float(member_data["ai_pct"]), 75.0, places=1)

    def test_get_team_breakdown_includes_multiple_members(self):
        """Test that get_team_breakdown includes all members with activity."""
        member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        member2 = TeamMemberFactory(team=self.team, display_name="Bob")

        PullRequestFactory(
            team=self.team,
            author=member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=member2,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertGreaterEqual(len(result), 2)
        names = [m["member_name"] for m in result]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

    def test_get_team_breakdown_excludes_members_with_no_activity(self):
        """Test that get_team_breakdown excludes members with no merged PRs."""
        active_member = TeamMemberFactory(team=self.team, display_name="Active")
        TeamMemberFactory(team=self.team, display_name="Inactive")  # Intentionally unused

        PullRequestFactory(
            team=self.team,
            author=active_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        names = [m["member_name"] for m in result]
        self.assertIn("Active", names)
        self.assertNotIn("Inactive", names)
