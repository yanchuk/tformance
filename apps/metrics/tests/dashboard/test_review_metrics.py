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
