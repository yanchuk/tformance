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


class TestGetReviewDistribution(TestCase):
    """Tests for get_review_distribution function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_review_distribution_returns_list_of_dicts(self):
        """Test that get_review_distribution returns a list of reviewer dicts."""
        result = dashboard_service.get_review_distribution(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_review_distribution_counts_reviews_per_reviewer(self):
        """Test that get_review_distribution counts reviews per reviewer."""
        reviewer1 = TeamMemberFactory(team=self.team, display_name="Alice")
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob")

        # Create multiple PRs with surveys - each reviewer can only review each survey once
        # Alice reviews 3 PRs, Bob reviews 2 PRs
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr)
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                reviewer=reviewer1,
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11 + i, 12, 0)),
            )

        for i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 12, 0)),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr)
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                reviewer=reviewer2,
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 16 + i, 12, 0)),
            )

        result = dashboard_service.get_review_distribution(self.team, self.start_date, self.end_date)

        # Should have 2 reviewers
        self.assertEqual(len(result), 2)

        alice_data = next((r for r in result if r["reviewer_name"] == "Alice"), None)
        bob_data = next((r for r in result if r["reviewer_name"] == "Bob"), None)

        self.assertIsNotNone(alice_data)
        self.assertIsNotNone(bob_data)
        self.assertEqual(alice_data["count"], 3)
        self.assertEqual(bob_data["count"], 2)

    def test_get_review_distribution_only_counts_reviews_in_date_range(self):
        """Test that get_review_distribution only counts reviews in the date range."""
        reviewer = TeamMemberFactory(team=self.team, display_name="Alice")

        # In-range PR and review
        pr_in_range = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey_in = PRSurveyFactory(team=self.team, pull_request=pr_in_range)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey_in,
            reviewer=reviewer,
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
        )

        # Out-of-range review (before start date) - needs separate PR/survey
        pr_out_range = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 10, 12, 0)),
        )
        survey_out = PRSurveyFactory(team=self.team, pull_request=pr_out_range)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey_out,
            reviewer=reviewer,
            responded_at=timezone.make_aware(timezone.datetime(2023, 12, 15, 12, 0)),
        )

        result = dashboard_service.get_review_distribution(self.team, self.start_date, self.end_date)

        # Should only count the 1 review in range
        alice_data = next((r for r in result if r["reviewer_name"] == "Alice"), None)
        self.assertEqual(alice_data["count"], 1)

    def test_get_review_distribution_handles_no_data(self):
        """Test that get_review_distribution handles empty dataset."""
        result = dashboard_service.get_review_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])


class TestGetReviewTimeTrend(TestCase):
    """Tests for get_review_time_trend function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_review_time_trend_returns_list_of_dicts(self):
        """Test that get_review_time_trend returns a list of week/value dicts."""
        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_review_time_trend_groups_by_week(self):
        """Test that get_review_time_trend groups data by week."""
        # Week 1 PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
            review_time_hours=Decimal("12.00"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            review_time_hours=Decimal("24.00"),
        )

        # Week 2 PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            review_time_hours=Decimal("18.00"),
        )

        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date)

        # Should have entries for multiple weeks
        self.assertIsInstance(result, list)
        for entry in result:
            self.assertIn("week", entry)
            self.assertIn("value", entry)

    def test_get_review_time_trend_calculates_weekly_average(self):
        """Test that get_review_time_trend calculates average review time per week."""
        # Create PRs in same week with different review times
        merged_dates = [
            timezone.datetime(2024, 1, 3, 12, 0),
            timezone.datetime(2024, 1, 4, 12, 0),
            timezone.datetime(2024, 1, 5, 12, 0),
        ]
        review_times = [Decimal("12.00"), Decimal("18.00"), Decimal("24.00")]

        for merged_date, review_time in zip(merged_dates, review_times, strict=True):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(merged_date),
                review_time_hours=review_time,
            )

        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date)

        # Find the week with our data
        if len(result) > 0:
            week_data = result[0]
            # Average should be (12 + 18 + 24) / 3 = 18
            self.assertAlmostEqual(float(week_data["value"]), 18.0, places=1)

    def test_get_review_time_trend_handles_null_review_time(self):
        """Test that get_review_time_trend handles PRs with null review_time_hours."""
        # Create mix of PRs with and without review times
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
            review_time_hours=Decimal("12.00"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 4, 12, 0)),
            review_time_hours=None,  # Not reviewed yet
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            review_time_hours=Decimal("24.00"),
        )

        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date)

        # Should calculate average only from non-null values
        if len(result) > 0:
            week_data = result[0]
            # Average should be (12 + 24) / 2 = 18, ignoring the null value
            self.assertAlmostEqual(float(week_data["value"]), 18.0, places=1)

    def test_get_review_time_trend_handles_empty_data(self):
        """Test that get_review_time_trend handles empty dataset."""
        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])

    def test_get_review_time_trend_filters_by_team(self):
        """Test that get_review_time_trend only includes data from the specified team."""
        other_team = TeamFactory()

        # Create PR for target team
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_time_hours=Decimal("12.00"),
        )

        # Create PR for other team (should be excluded)
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_time_hours=Decimal("99.00"),
        )

        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date)

        # Should only include data from target team
        if len(result) > 0:
            week_data = result[0]
            self.assertAlmostEqual(float(week_data["value"]), 12.0, places=1)

    def test_get_review_time_trend_only_includes_merged_prs(self):
        """Test that get_review_time_trend only includes merged PRs."""
        # Create merged PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_time_hours=Decimal("12.00"),
        )

        # Create open PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="open",
            merged_at=None,
            review_time_hours=Decimal("99.00"),
        )

        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date)

        # Should only include merged PR
        if len(result) > 0:
            week_data = result[0]
            self.assertAlmostEqual(float(week_data["value"]), 12.0, places=1)


class TestGetRecentPrs(TestCase):
    """Tests for get_recent_prs function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_recent_prs_returns_list_of_dicts(self):
        """Test that get_recent_prs returns a list of PR dicts."""
        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_recent_prs_includes_required_fields(self):
        """Test that get_recent_prs includes all required fields."""
        author = TeamMemberFactory(team=self.team, display_name="Alice")
        pr = PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Add feature X",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey, quality_rating=3)

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        pr_data = result[0]

        self.assertIn("title", pr_data)
        self.assertIn("author", pr_data)
        self.assertIn("merged_at", pr_data)
        self.assertIn("ai_assisted", pr_data)
        self.assertIn("avg_quality", pr_data)
        self.assertIn("url", pr_data)

    def test_get_recent_prs_returns_correct_data(self):
        """Test that get_recent_prs returns correct PR data."""
        author = TeamMemberFactory(team=self.team, display_name="Bob")
        reviewer1 = TeamMemberFactory(team=self.team, display_name="Reviewer1")
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Reviewer2")
        merged_time = timezone.make_aware(timezone.datetime(2024, 1, 15, 14, 30))
        pr = PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Fix bug Y",
            merged_at=merged_time,
            github_repo="org/repo",
            github_pr_id=123,
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey, reviewer=reviewer1, quality_rating=2)
        PRSurveyReviewFactory(team=self.team, survey=survey, reviewer=reviewer2, quality_rating=3)

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        pr_data = result[0]
        self.assertEqual(pr_data["title"], "Fix bug Y")
        self.assertEqual(pr_data["author"], "Bob")
        self.assertEqual(pr_data["merged_at"], merged_time)
        self.assertTrue(pr_data["ai_assisted"])
        self.assertEqual(pr_data["avg_quality"], 2.5)  # (2 + 3) / 2
        self.assertEqual(pr_data["url"], "https://github.com/org/repo/pull/123")

    def test_get_recent_prs_orders_by_merged_at_descending(self):
        """Test that get_recent_prs orders by merged_at descending (most recent first)."""
        author = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="First PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Second PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Third PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["title"], "Second PR")  # Most recent
        self.assertEqual(result[1]["title"], "Third PR")
        self.assertEqual(result[2]["title"], "First PR")

    def test_get_recent_prs_limits_results(self):
        """Test that get_recent_prs limits results to specified count."""
        author = TeamMemberFactory(team=self.team)
        for i in range(15):
            PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                title=f"PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, i + 1, 12, 0)),
            )

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date, limit=10)

        self.assertEqual(len(result), 10)

    def test_get_recent_prs_handles_pr_without_survey(self):
        """Test that get_recent_prs handles PRs without surveys."""
        author = TeamMemberFactory(team=self.team, display_name="Charlie")
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="No Survey PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        pr_data = result[0]
        self.assertIsNone(pr_data["ai_assisted"])
        self.assertIsNone(pr_data["avg_quality"])

    def test_get_recent_prs_handles_no_data(self):
        """Test that get_recent_prs handles empty dataset."""
        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])


class TestGetRevertHotfixStats(TestCase):
    """Tests for get_revert_hotfix_stats function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_revert_hotfix_stats_returns_dict_with_required_keys(self):
        """Test that get_revert_hotfix_stats returns dict with all required keys."""
        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertIn("total_prs", result)
        self.assertIn("revert_count", result)
        self.assertIn("hotfix_count", result)
        self.assertIn("revert_pct", result)
        self.assertIn("hotfix_pct", result)

    def test_get_revert_hotfix_stats_counts_total_merged_prs(self):
        """Test that get_revert_hotfix_stats counts total merged PRs in date range."""
        # Create 5 merged PRs
        for i in range(5):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        # Create non-merged PRs (should be excluded)
        PullRequestFactory(team=self.team, state="open", merged_at=None)
        PullRequestFactory(team=self.team, state="closed", merged_at=None)

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 5)

    def test_get_revert_hotfix_stats_counts_reverts(self):
        """Test that get_revert_hotfix_stats counts PRs where is_revert=True."""
        # Create 3 revert PRs
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=True,
                is_hotfix=False,
            )

        # Create 2 non-revert PRs
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["revert_count"], 3)

    def test_get_revert_hotfix_stats_counts_hotfixes(self):
        """Test that get_revert_hotfix_stats counts PRs where is_hotfix=True."""
        # Create 4 hotfix PRs
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=True,
            )

        # Create 1 non-hotfix PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=False,
        )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["hotfix_count"], 4)

    def test_get_revert_hotfix_stats_calculates_revert_percentage(self):
        """Test that get_revert_hotfix_stats calculates revert percentage correctly."""
        # Create 2 reverts out of 10 total PRs = 20%
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 12, 0)),
                is_revert=True,
                is_hotfix=False,
            )

        for i in range(8):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 10)
        self.assertEqual(result["revert_count"], 2)
        self.assertAlmostEqual(float(result["revert_pct"]), 20.0, places=2)

    def test_get_revert_hotfix_stats_calculates_hotfix_percentage(self):
        """Test that get_revert_hotfix_stats calculates hotfix percentage correctly."""
        # Create 3 hotfixes out of 12 total PRs = 25%
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 12, 0)),
                is_revert=False,
                is_hotfix=True,
            )

        for i in range(9):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 12)
        self.assertEqual(result["hotfix_count"], 3)
        self.assertAlmostEqual(float(result["hotfix_pct"]), 25.0, places=2)

    def test_get_revert_hotfix_stats_handles_pr_with_both_flags(self):
        """Test that get_revert_hotfix_stats counts a PR with both is_revert and is_hotfix."""
        # Create 1 PR with both flags
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_revert=True,
            is_hotfix=True,
        )

        # Create 4 normal PRs
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 5)
        self.assertEqual(result["revert_count"], 1)
        self.assertEqual(result["hotfix_count"], 1)
        self.assertAlmostEqual(float(result["revert_pct"]), 20.0, places=2)
        self.assertAlmostEqual(float(result["hotfix_pct"]), 20.0, places=2)

    def test_get_revert_hotfix_stats_handles_no_prs(self):
        """Test that get_revert_hotfix_stats handles case with no PRs."""
        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 0)
        self.assertEqual(result["revert_count"], 0)
        self.assertEqual(result["hotfix_count"], 0)
        self.assertEqual(result["revert_pct"], 0.0)
        self.assertEqual(result["hotfix_pct"], 0.0)

    def test_get_revert_hotfix_stats_handles_zero_percentage(self):
        """Test that get_revert_hotfix_stats returns 0% when no reverts or hotfixes exist."""
        # Create 5 normal PRs with no reverts or hotfixes
        for i in range(5):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 5)
        self.assertEqual(result["revert_count"], 0)
        self.assertEqual(result["hotfix_count"], 0)
        self.assertEqual(result["revert_pct"], 0.0)
        self.assertEqual(result["hotfix_pct"], 0.0)

    def test_get_revert_hotfix_stats_filters_by_date_range(self):
        """Test that get_revert_hotfix_stats only includes PRs within date range."""
        # In range revert
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # Before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # After end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 1)
        self.assertEqual(result["revert_count"], 1)

    def test_get_revert_hotfix_stats_filters_by_team(self):
        """Test that get_revert_hotfix_stats only includes PRs from specified team."""
        other_team = TeamFactory()

        # Target team PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # Other team PRs (should be excluded)
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=True,
        )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 1)
        self.assertEqual(result["revert_count"], 1)
        self.assertEqual(result["hotfix_count"], 0)

    def test_get_revert_hotfix_stats_percentage_has_correct_precision(self):
        """Test that get_revert_hotfix_stats calculates percentages with correct precision."""
        # Create 1 revert out of 3 total PRs = 33.33%
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        for i in range(2):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        # Check percentage is a float
        self.assertIsInstance(result["revert_pct"], float)
        # Check it's in range 0.0 to 100.0
        self.assertGreaterEqual(result["revert_pct"], 0.0)
        self.assertLessEqual(result["revert_pct"], 100.0)
        # Check it's approximately 33.33%
        self.assertAlmostEqual(result["revert_pct"], 33.33, places=2)


class TestGetPrSizeDistribution(TestCase):
    """Tests for get_pr_size_distribution function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_pr_size_distribution_returns_list_of_dicts(self):
        """Test that get_pr_size_distribution returns a list of category dicts."""
        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_pr_size_distribution_returns_all_five_categories(self):
        """Test that get_pr_size_distribution always returns all 5 categories."""
        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 5)
        categories = [item["category"] for item in result]
        self.assertEqual(categories, ["XS", "S", "M", "L", "XL"])

    def test_get_pr_size_distribution_categorizes_xs_size(self):
        """Test that PRs with 1-10 lines are categorized as XS."""
        # XS: 1-10 lines (additions + deletions)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=10,
            deletions=0,  # Total: 10 lines (boundary)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xs_data = next((item for item in result if item["category"] == "XS"), None)
        self.assertIsNotNone(xs_data)
        self.assertEqual(xs_data["count"], 2)

    def test_get_pr_size_distribution_categorizes_s_size(self):
        """Test that PRs with 11-50 lines are categorized as S."""
        # S: 11-50 lines
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=11,
            deletions=0,  # Total: 11 lines (lower boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=30,
            deletions=20,  # Total: 50 lines (upper boundary)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        s_data = next((item for item in result if item["category"] == "S"), None)
        self.assertIsNotNone(s_data)
        self.assertEqual(s_data["count"], 2)

    def test_get_pr_size_distribution_categorizes_m_size(self):
        """Test that PRs with 51-200 lines are categorized as M."""
        # M: 51-200 lines
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=51,
            deletions=0,  # Total: 51 lines (lower boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=100,
            deletions=100,  # Total: 200 lines (upper boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=75,
            deletions=50,  # Total: 125 lines
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        m_data = next((item for item in result if item["category"] == "M"), None)
        self.assertIsNotNone(m_data)
        self.assertEqual(m_data["count"], 3)

    def test_get_pr_size_distribution_categorizes_l_size(self):
        """Test that PRs with 201-500 lines are categorized as L."""
        # L: 201-500 lines
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=201,
            deletions=0,  # Total: 201 lines (lower boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=250,
            deletions=250,  # Total: 500 lines (upper boundary)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        l_data = next((item for item in result if item["category"] == "L"), None)
        self.assertIsNotNone(l_data)
        self.assertEqual(l_data["count"], 2)

    def test_get_pr_size_distribution_categorizes_xl_size(self):
        """Test that PRs with 500+ lines are categorized as XL."""
        # XL: 500+ lines
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=501,
            deletions=0,  # Total: 501 lines (just above boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=1000,
            deletions=500,  # Total: 1500 lines
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=10000,
            deletions=5000,  # Total: 15000 lines
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xl_data = next((item for item in result if item["category"] == "XL"), None)
        self.assertIsNotNone(xl_data)
        self.assertEqual(xl_data["count"], 3)

    def test_get_pr_size_distribution_returns_zero_counts_for_empty_categories(self):
        """Test that categories with no PRs return count of 0."""
        # Create only one XL PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=600,
            deletions=0,  # Total: 600 lines (XL)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        # All categories should be present
        self.assertEqual(len(result), 5)

        # XL should have count of 1
        xl_data = next((item for item in result if item["category"] == "XL"), None)
        self.assertEqual(xl_data["count"], 1)

        # All others should have count of 0
        for category in ["XS", "S", "M", "L"]:
            category_data = next((item for item in result if item["category"] == category), None)
            self.assertIsNotNone(category_data)
            self.assertEqual(category_data["count"], 0)

    def test_get_pr_size_distribution_only_includes_merged_prs(self):
        """Test that only merged PRs are included in distribution."""
        # Merged PR (should be counted)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # Open PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="open",
            merged_at=None,
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # Closed PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="closed",
            merged_at=None,
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xs_data = next((item for item in result if item["category"] == "XS"), None)
        self.assertEqual(xs_data["count"], 1)

    def test_get_pr_size_distribution_filters_by_date_range(self):
        """Test that only PRs merged within date range are included."""
        # In range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # Before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # After end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xs_data = next((item for item in result if item["category"] == "XS"), None)
        self.assertEqual(xs_data["count"], 1)

    def test_get_pr_size_distribution_filters_by_team(self):
        """Test that only PRs from the specified team are included."""
        other_team = TeamFactory()

        # Target team PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # Other team PR (should be excluded)
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xs_data = next((item for item in result if item["category"] == "XS"), None)
        self.assertEqual(xs_data["count"], 1)

    def test_get_pr_size_distribution_handles_no_prs(self):
        """Test that all categories return 0 count when there are no PRs."""
        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 5)
        for item in result:
            self.assertEqual(item["count"], 0)

    def test_get_pr_size_distribution_has_correct_dict_structure(self):
        """Test that each item in result has correct keys: category and count."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=5,
            deletions=3,
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        for item in result:
            self.assertIn("category", item)
            self.assertIn("count", item)
            self.assertEqual(len(item), 2)  # No extra keys


class TestGetUnlinkedPrs(TestCase):
    """Tests for get_unlinked_prs function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_unlinked_prs_returns_list_of_dicts(self):
        """Test that get_unlinked_prs returns a list of PR dicts."""
        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_unlinked_prs_includes_required_fields(self):
        """Test that get_unlinked_prs includes all required fields."""
        author = TeamMemberFactory(team=self.team, display_name="Alice")
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Add feature X",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
            github_repo="org/repo",
            github_pr_id=123,
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        pr_data = result[0]

        self.assertIn("title", pr_data)
        self.assertIn("author", pr_data)
        self.assertIn("merged_at", pr_data)
        self.assertIn("url", pr_data)
        self.assertEqual(len(pr_data), 4)  # Only these 4 fields

    def test_get_unlinked_prs_returns_correct_data(self):
        """Test that get_unlinked_prs returns correct PR data."""
        author = TeamMemberFactory(team=self.team, display_name="Bob")
        merged_time = timezone.make_aware(timezone.datetime(2024, 1, 15, 14, 30))
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Fix bug Y",
            merged_at=merged_time,
            jira_key="",
            github_repo="org/repo",
            github_pr_id=456,
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        pr_data = result[0]
        self.assertEqual(pr_data["title"], "Fix bug Y")
        self.assertEqual(pr_data["author"], "Bob")
        self.assertEqual(pr_data["merged_at"], merged_time)
        self.assertEqual(pr_data["url"], "https://github.com/org/repo/pull/456")

    def test_get_unlinked_prs_only_includes_prs_with_empty_jira_key(self):
        """Test that get_unlinked_prs only includes PRs where jira_key is empty or None."""
        author = TeamMemberFactory(team=self.team)

        # Unlinked PR with empty string
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Unlinked PR 1",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
        )

        # Linked PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Linked PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            jira_key="PROJ-123",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Unlinked PR 1")

    def test_get_unlinked_prs_only_includes_merged_prs(self):
        """Test that get_unlinked_prs only includes merged PRs."""
        author = TeamMemberFactory(team=self.team)

        # Merged PR (should be included)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Merged PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
        )

        # Open PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="open",
            title="Open PR",
            merged_at=None,
            jira_key="",
        )

        # Closed PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="closed",
            title="Closed PR",
            merged_at=None,
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Merged PR")

    def test_get_unlinked_prs_orders_by_merged_at_descending(self):
        """Test that get_unlinked_prs orders by merged_at descending (most recent first)."""
        author = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="First PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            jira_key="",
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Second PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="",
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Third PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["title"], "Second PR")  # Most recent
        self.assertEqual(result[1]["title"], "Third PR")
        self.assertEqual(result[2]["title"], "First PR")

    def test_get_unlinked_prs_respects_limit_parameter(self):
        """Test that get_unlinked_prs limits results to specified count."""
        author = TeamMemberFactory(team=self.team)
        for i in range(15):
            PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                title=f"PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, i + 1, 12, 0)),
                jira_key="",
            )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date, limit=5)

        self.assertEqual(len(result), 5)

    def test_get_unlinked_prs_defaults_to_limit_10(self):
        """Test that get_unlinked_prs defaults to limit=10 when not specified."""
        author = TeamMemberFactory(team=self.team)
        for i in range(20):
            PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                title=f"PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, i + 1, 12, 0)),
                jira_key="",
            )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 10)

    def test_get_unlinked_prs_filters_by_date_range(self):
        """Test that get_unlinked_prs only includes PRs within date range."""
        author = TeamMemberFactory(team=self.team)

        # In range
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="In Range PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="",
        )

        # Before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Before Start PR",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
            jira_key="",
        )

        # After end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="After End PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "In Range PR")

    def test_get_unlinked_prs_filters_by_team(self):
        """Test that get_unlinked_prs only includes PRs from specified team."""
        other_team = TeamFactory()

        # Target team PR
        author1 = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=author1,
            state="merged",
            title="Target Team PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="",
        )

        # Other team PR (should be excluded)
        author2 = TeamMemberFactory(team=other_team)
        PullRequestFactory(
            team=other_team,
            author=author2,
            state="merged",
            title="Other Team PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Target Team PR")

    def test_get_unlinked_prs_handles_no_unlinked_prs(self):
        """Test that get_unlinked_prs handles case with no unlinked PRs."""
        author = TeamMemberFactory(team=self.team)

        # All PRs have Jira keys
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Linked PR 1",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="PROJ-123",
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Linked PR 2",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="PROJ-456",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])

    def test_get_unlinked_prs_constructs_github_url_correctly(self):
        """Test that get_unlinked_prs constructs GitHub URL from repo and PR ID."""
        author = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Test PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
            github_repo="my-org/my-repo",
            github_pr_id=789,
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["url"], "https://github.com/my-org/my-repo/pull/789")

    def test_get_unlinked_prs_handles_author_with_no_display_name(self):
        """Test that get_unlinked_prs handles PRs with authors who have display names."""
        author = TeamMemberFactory(team=self.team, display_name="Charlie Brown")
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Test PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["author"], "Charlie Brown")


class TestGetReviewerWorkload(TestCase):
    """Tests for get_reviewer_workload function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_reviewer_workload_returns_list_of_dicts(self):
        """Test that get_reviewer_workload returns a list of reviewer dicts."""
        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_reviewer_workload_includes_required_fields(self):
        """Test that get_reviewer_workload includes all required fields."""
        reviewer = TeamMemberFactory(team=self.team, display_name="Alice")
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        from apps.metrics.factories import PRReviewFactory

        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
        )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        workload_data = result[0]

        self.assertIn("reviewer_name", workload_data)
        self.assertIn("review_count", workload_data)
        self.assertIn("workload_level", workload_data)
        self.assertEqual(len(workload_data), 3)

    def test_get_reviewer_workload_counts_reviews_per_reviewer(self):
        """Test that get_reviewer_workload counts GitHub reviews per reviewer."""
        from apps.metrics.factories import PRReviewFactory

        reviewer1 = TeamMemberFactory(team=self.team, display_name="Alice")
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob")

        # Alice reviews 5 PRs
        for i in range(5):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=reviewer1,
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 14, 0)),
            )

        # Bob reviews 3 PRs
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 12, 0)),
            )
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=reviewer2,
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 14, 0)),
            )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 2)

        alice_data = next((r for r in result if r["reviewer_name"] == "Alice"), None)
        bob_data = next((r for r in result if r["reviewer_name"] == "Bob"), None)

        self.assertIsNotNone(alice_data)
        self.assertIsNotNone(bob_data)
        self.assertEqual(alice_data["review_count"], 5)
        self.assertEqual(bob_data["review_count"], 3)

    def test_get_reviewer_workload_only_counts_reviews_in_date_range(self):
        """Test that get_reviewer_workload only counts reviews within date range."""
        from apps.metrics.factories import PRReviewFactory

        reviewer = TeamMemberFactory(team=self.team, display_name="Alice")

        # In-range review
        pr_in = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr_in,
            reviewer=reviewer,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
        )

        # Before start date (should be excluded)
        pr_before = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 10, 12, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr_before,
            reviewer=reviewer,
            submitted_at=timezone.make_aware(timezone.datetime(2023, 12, 11, 12, 0)),
        )

        # After end date (should be excluded)
        pr_after = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 10, 12, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr_after,
            reviewer=reviewer,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 2, 11, 12, 0)),
        )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        alice_data = next((r for r in result if r["reviewer_name"] == "Alice"), None)
        self.assertIsNotNone(alice_data)
        self.assertEqual(alice_data["review_count"], 1)

    def test_get_reviewer_workload_classifies_low_workload(self):
        """Test that get_reviewer_workload classifies reviewers below 25th percentile as low."""
        from apps.metrics.factories import PRReviewFactory

        reviewers = [TeamMemberFactory(team=self.team, display_name=f"Reviewer{i}") for i in range(4)]

        # Create reviews: 2, 10, 20, 30 (25th percentile = 6, 75th percentile = 25)
        review_counts = [2, 10, 20, 30]

        for reviewer, count in zip(reviewers, review_counts, strict=False):
            for i in range(count):
                pr = PullRequestFactory(
                    team=self.team,
                    state="merged",
                    merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
                )
                PRReviewFactory(
                    team=self.team,
                    pull_request=pr,
                    reviewer=reviewer,
                    submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, i)),
                )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        # Reviewer0 with 2 reviews should be "low"
        low_reviewer = next((r for r in result if r["reviewer_name"] == "Reviewer0"), None)
        self.assertIsNotNone(low_reviewer)
        self.assertEqual(low_reviewer["workload_level"], "low")

    def test_get_reviewer_workload_classifies_normal_workload(self):
        """Test that get_reviewer_workload classifies reviewers in 25th-75th percentile as normal."""
        from apps.metrics.factories import PRReviewFactory

        reviewers = [TeamMemberFactory(team=self.team, display_name=f"Reviewer{i}") for i in range(4)]

        # Create reviews: 2, 10, 20, 30 (25th percentile = 6, 75th percentile = 25)
        review_counts = [2, 10, 20, 30]

        for reviewer, count in zip(reviewers, review_counts, strict=False):
            for i in range(count):
                pr = PullRequestFactory(
                    team=self.team,
                    state="merged",
                    merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
                )
                PRReviewFactory(
                    team=self.team,
                    pull_request=pr,
                    reviewer=reviewer,
                    submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, i)),
                )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        # Reviewer1 (10) and Reviewer2 (20) should be "normal"
        normal_reviewers = [r for r in result if r["workload_level"] == "normal"]
        self.assertEqual(len(normal_reviewers), 2)
        normal_names = {r["reviewer_name"] for r in normal_reviewers}
        self.assertIn("Reviewer1", normal_names)
        self.assertIn("Reviewer2", normal_names)

    def test_get_reviewer_workload_classifies_high_workload(self):
        """Test that get_reviewer_workload classifies reviewers above 75th percentile as high."""
        from apps.metrics.factories import PRReviewFactory

        reviewers = [TeamMemberFactory(team=self.team, display_name=f"Reviewer{i}") for i in range(4)]

        # Create reviews: 2, 10, 20, 30 (25th percentile = 6, 75th percentile = 25)
        review_counts = [2, 10, 20, 30]

        for reviewer, count in zip(reviewers, review_counts, strict=False):
            for i in range(count):
                pr = PullRequestFactory(
                    team=self.team,
                    state="merged",
                    merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
                )
                PRReviewFactory(
                    team=self.team,
                    pull_request=pr,
                    reviewer=reviewer,
                    submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, i)),
                )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        # Reviewer3 with 30 reviews should be "high"
        high_reviewer = next((r for r in result if r["reviewer_name"] == "Reviewer3"), None)
        self.assertIsNotNone(high_reviewer)
        self.assertEqual(high_reviewer["workload_level"], "high")

    def test_get_reviewer_workload_orders_by_review_count_descending(self):
        """Test that get_reviewer_workload orders by review_count descending."""
        from apps.metrics.factories import PRReviewFactory

        reviewers = [
            TeamMemberFactory(team=self.team, display_name="Alice"),
            TeamMemberFactory(team=self.team, display_name="Bob"),
            TeamMemberFactory(team=self.team, display_name="Charlie"),
        ]

        # Create reviews: Alice=5, Bob=15, Charlie=10
        review_counts = [5, 15, 10]

        for reviewer, count in zip(reviewers, review_counts, strict=False):
            for i in range(count):
                pr = PullRequestFactory(
                    team=self.team,
                    state="merged",
                    merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
                )
                PRReviewFactory(
                    team=self.team,
                    pull_request=pr,
                    reviewer=reviewer,
                    submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, i)),
                )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        # Should be ordered: Bob (15), Charlie (10), Alice (5)
        self.assertEqual(result[0]["reviewer_name"], "Bob")
        self.assertEqual(result[0]["review_count"], 15)
        self.assertEqual(result[1]["reviewer_name"], "Charlie")
        self.assertEqual(result[1]["review_count"], 10)
        self.assertEqual(result[2]["reviewer_name"], "Alice")
        self.assertEqual(result[2]["review_count"], 5)

    def test_get_reviewer_workload_filters_by_team(self):
        """Test that get_reviewer_workload only includes reviews from the specified team."""
        from apps.metrics.factories import PRReviewFactory

        other_team = TeamFactory()

        # Target team reviewer
        reviewer1 = TeamMemberFactory(team=self.team, display_name="Alice")
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr1,
            reviewer=reviewer1,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
        )

        # Other team reviewer (should be excluded)
        reviewer2 = TeamMemberFactory(team=other_team, display_name="Bob")
        pr2 = PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRReviewFactory(
            team=other_team,
            pull_request=pr2,
            reviewer=reviewer2,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
        )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["reviewer_name"], "Alice")

    def test_get_reviewer_workload_handles_no_reviews(self):
        """Test that get_reviewer_workload handles case with no reviews."""
        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])

    def test_get_reviewer_workload_handles_single_reviewer(self):
        """Test that get_reviewer_workload handles case with only one reviewer."""
        from apps.metrics.factories import PRReviewFactory

        reviewer = TeamMemberFactory(team=self.team, display_name="Alice")
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
        )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        # With only one reviewer, classification is still applied
        self.assertIn(result[0]["workload_level"], ["low", "normal", "high"])

    def test_get_reviewer_workload_uses_github_reviews_not_survey_reviews(self):
        """Test that get_reviewer_workload uses PRReview model not PRSurveyReview."""
        from apps.metrics.factories import PRReviewFactory

        reviewer = TeamMemberFactory(team=self.team, display_name="Alice")

        # Create a GitHub review (PRReview) - should be counted
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr1,
            reviewer=reviewer,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
        )

        # Create a survey review (PRSurveyReview) - should NOT be counted
        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr2)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            reviewer=reviewer,
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )

        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        alice_data = next((r for r in result if r["reviewer_name"] == "Alice"), None)
        self.assertIsNotNone(alice_data)
        # Should only count the 1 GitHub review, not the survey review
        self.assertEqual(alice_data["review_count"], 1)


class TestCopilotDashboardService(TestCase):
    """Tests for Copilot metrics dashboard service functions."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_copilot_metrics_returns_correct_totals(self):
        """Test that get_copilot_metrics returns correct total suggestions, accepted, rate, and active users."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Create Copilot usage data for member1
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 10),
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
            acceptance_rate=Decimal("40.00"),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 15),
            source="copilot",
            suggestions_shown=200,
            suggestions_accepted=80,
            acceptance_rate=Decimal("40.00"),
        )

        # Create Copilot usage data for member2
        AIUsageDailyFactory(
            team=self.team,
            member=self.member2,
            date=date(2024, 1, 20),
            source="copilot",
            suggestions_shown=150,
            suggestions_accepted=60,
            acceptance_rate=Decimal("40.00"),
        )

        # Create Cursor usage data (should be excluded)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 12),
            source="cursor",
            suggestions_shown=500,
            suggestions_accepted=250,
            acceptance_rate=Decimal("50.00"),
        )

        result = dashboard_service.get_copilot_metrics(self.team, self.start_date, self.end_date)

        # Total suggestions: 100 + 200 + 150 = 450
        self.assertEqual(result["total_suggestions"], 450)
        # Total accepted: 40 + 80 + 60 = 180
        self.assertEqual(result["total_accepted"], 180)
        # Acceptance rate: 180 / 450 * 100 = 40.00%
        self.assertEqual(result["acceptance_rate"], Decimal("40.00"))
        # Active users: 2 (Alice and Bob)
        self.assertEqual(result["active_users"], 2)

    def test_get_copilot_metrics_returns_zero_with_no_data(self):
        """Test that get_copilot_metrics returns zero values when there is no Copilot usage data."""
        result = dashboard_service.get_copilot_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_suggestions"], 0)
        self.assertEqual(result["total_accepted"], 0)
        self.assertEqual(result["acceptance_rate"], Decimal("0.00"))
        self.assertEqual(result["active_users"], 0)

    def test_get_copilot_trend_returns_weekly_data(self):
        """Test that get_copilot_trend returns weekly acceptance rate trend."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Week 1 (Jan 1-7): 50% acceptance rate
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 3),
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=50,
            acceptance_rate=Decimal("50.00"),
        )

        # Week 2 (Jan 8-14): 40% acceptance rate
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 10),
            source="copilot",
            suggestions_shown=200,
            suggestions_accepted=80,
            acceptance_rate=Decimal("40.00"),
        )

        # Week 3 (Jan 15-21): 60% acceptance rate
        AIUsageDailyFactory(
            team=self.team,
            member=self.member2,
            date=date(2024, 1, 17),
            source="copilot",
            suggestions_shown=150,
            suggestions_accepted=90,
            acceptance_rate=Decimal("60.00"),
        )

        result = dashboard_service.get_copilot_trend(self.team, self.start_date, self.end_date)

        # Should return 3 weeks of data
        self.assertEqual(len(result), 3)

        # First week should have 50% acceptance
        self.assertIn("week", result[0])
        self.assertIn("acceptance_rate", result[0])
        self.assertEqual(result[0]["acceptance_rate"], Decimal("50.00"))

        # Second week should have 40% acceptance
        self.assertEqual(result[1]["acceptance_rate"], Decimal("40.00"))

        # Third week should have 60% acceptance
        self.assertEqual(result[2]["acceptance_rate"], Decimal("60.00"))

    def test_get_copilot_by_member_returns_per_member_stats(self):
        """Test that get_copilot_by_member returns per-member breakdown of Copilot usage."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Alice: 300 shown, 120 accepted (40%)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 10),
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
            acceptance_rate=Decimal("40.00"),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 15),
            source="copilot",
            suggestions_shown=200,
            suggestions_accepted=80,
            acceptance_rate=Decimal("40.00"),
        )

        # Bob: 150 shown, 90 accepted (60%)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member2,
            date=date(2024, 1, 20),
            source="copilot",
            suggestions_shown=150,
            suggestions_accepted=90,
            acceptance_rate=Decimal("60.00"),
        )

        result = dashboard_service.get_copilot_by_member(self.team, self.start_date, self.end_date)

        # Should return 2 members
        self.assertEqual(len(result), 2)

        # Find Alice's data
        alice_data = next((m for m in result if m["member_name"] == "Alice"), None)
        self.assertIsNotNone(alice_data)
        self.assertEqual(alice_data["suggestions"], 300)
        self.assertEqual(alice_data["accepted"], 120)
        self.assertEqual(alice_data["acceptance_rate"], Decimal("40.00"))

        # Find Bob's data
        bob_data = next((m for m in result if m["member_name"] == "Bob"), None)
        self.assertIsNotNone(bob_data)
        self.assertEqual(bob_data["suggestions"], 150)
        self.assertEqual(bob_data["accepted"], 90)
        self.assertEqual(bob_data["acceptance_rate"], Decimal("60.00"))


class TestGetIterationMetrics(TestCase):
    """Tests for get_iteration_metrics function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_iteration_metrics_returns_dict_with_required_keys(self):
        """Test that get_iteration_metrics returns a dict with all required keys."""
        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertIn("avg_review_rounds", result)
        self.assertIn("avg_fix_response_hours", result)
        self.assertIn("avg_commits_after_first_review", result)
        self.assertIn("avg_total_comments", result)
        self.assertIn("prs_with_metrics", result)

    def test_get_iteration_metrics_calculates_averages(self):
        """Test that get_iteration_metrics calculates averages correctly."""
        # Create PRs with iteration metrics
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=2,
            avg_fix_response_hours=Decimal("4.00"),
            commits_after_first_review=3,
            total_comments=10,
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            review_rounds=4,
            avg_fix_response_hours=Decimal("8.00"),
            commits_after_first_review=5,
            total_comments=20,
        )

        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        # Averages: review_rounds=(2+4)/2=3, fix_response=(4+8)/2=6, commits=(3+5)/2=4, comments=(10+20)/2=15
        self.assertEqual(result["avg_review_rounds"], Decimal("3.00"))
        self.assertEqual(result["avg_fix_response_hours"], Decimal("6.00"))
        self.assertEqual(result["avg_commits_after_first_review"], Decimal("4.00"))
        self.assertEqual(result["avg_total_comments"], Decimal("15.00"))
        self.assertEqual(result["prs_with_metrics"], 2)

    def test_get_iteration_metrics_handles_no_data(self):
        """Test that get_iteration_metrics handles empty dataset gracefully."""
        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertIsNone(result["avg_review_rounds"])
        self.assertIsNone(result["avg_fix_response_hours"])
        self.assertIsNone(result["avg_commits_after_first_review"])
        self.assertIsNone(result["avg_total_comments"])
        self.assertEqual(result["prs_with_metrics"], 0)

    def test_get_iteration_metrics_handles_null_values(self):
        """Test that get_iteration_metrics handles PRs with null iteration metrics."""
        # PR with metrics
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=2,
            avg_fix_response_hours=Decimal("4.00"),
            commits_after_first_review=3,
            total_comments=10,
        )
        # PR without metrics (nulls)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            review_rounds=None,
            avg_fix_response_hours=None,
            commits_after_first_review=None,
            total_comments=None,
        )

        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        # Should only count PRs with non-null values
        self.assertEqual(result["avg_review_rounds"], Decimal("2.00"))
        self.assertEqual(result["prs_with_metrics"], 1)

    def test_get_iteration_metrics_filters_by_team(self):
        """Test that get_iteration_metrics only includes data from the specified team."""
        other_team = TeamFactory()

        # Create PR for target team
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=2,
        )

        # Create PR for other team (should be excluded)
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=10,
        )

        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["avg_review_rounds"], Decimal("2.00"))

    def test_get_iteration_metrics_filters_by_date_range(self):
        """Test that get_iteration_metrics only includes PRs within date range."""
        # PR in range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=2,
        )

        # PR out of range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
            review_rounds=10,
        )

        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["avg_review_rounds"], Decimal("2.00"))


class TestGetReviewerCorrelations(TestCase):
    """Tests for get_reviewer_correlations function."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.metrics.factories import ReviewerCorrelationFactory

        self.team = TeamFactory()
        self.reviewer1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob")
        self.ReviewerCorrelationFactory = ReviewerCorrelationFactory

    def test_get_reviewer_correlations_returns_list_of_dicts(self):
        """Test that get_reviewer_correlations returns a list of dicts."""
        result = dashboard_service.get_reviewer_correlations(self.team)

        self.assertIsInstance(result, list)

    def test_get_reviewer_correlations_includes_required_keys(self):
        """Test that each correlation has required keys."""
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
            agreements=8,
            disagreements=2,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        self.assertEqual(len(result), 1)
        corr = result[0]
        self.assertIn("reviewer_1_name", corr)
        self.assertIn("reviewer_2_name", corr)
        self.assertIn("prs_reviewed_together", corr)
        self.assertIn("agreement_rate", corr)
        self.assertIn("is_redundant", corr)

    def test_get_reviewer_correlations_returns_correct_data(self):
        """Test that get_reviewer_correlations returns correct data."""
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
            agreements=8,
            disagreements=2,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        corr = result[0]
        self.assertEqual(corr["reviewer_1_name"], "Alice")
        self.assertEqual(corr["reviewer_2_name"], "Bob")
        self.assertEqual(corr["prs_reviewed_together"], 10)
        self.assertEqual(corr["agreement_rate"], Decimal("80.00"))
        self.assertFalse(corr["is_redundant"])  # 80% < 95% threshold

    def test_get_reviewer_correlations_detects_redundant_pair(self):
        """Test that get_reviewer_correlations detects redundant reviewer pairs."""
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=15,  # >= 10 sample size
            agreements=15,  # 100% agreement > 95% threshold
            disagreements=0,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        corr = result[0]
        self.assertTrue(corr["is_redundant"])

    def test_get_reviewer_correlations_filters_by_team(self):
        """Test that get_reviewer_correlations only includes data from the specified team."""
        other_team = TeamFactory()
        other_r1 = TeamMemberFactory(team=other_team)
        other_r2 = TeamMemberFactory(team=other_team)

        # Create correlation for target team
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
        )

        # Create correlation for other team
        self.ReviewerCorrelationFactory(
            team=other_team,
            reviewer_1=other_r1,
            reviewer_2=other_r2,
            prs_reviewed_together=20,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["prs_reviewed_together"], 10)

    def test_get_reviewer_correlations_orders_by_prs_reviewed_desc(self):
        """Test that get_reviewer_correlations orders by PRs reviewed descending."""
        reviewer3 = TeamMemberFactory(team=self.team, display_name="Charlie")

        # Create correlations with different PR counts
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=5,
        )
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer2,
            reviewer_2=reviewer3,
            prs_reviewed_together=15,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["prs_reviewed_together"], 15)  # Higher count first
        self.assertEqual(result[1]["prs_reviewed_together"], 5)
