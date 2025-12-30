"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, override_settings
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
        self.assertIn("avg_review_time", result)
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

    def test_get_key_metrics_calculates_avg_review_time(self):
        """Test that get_key_metrics calculates average review time correctly."""
        # Create PRs with different review times
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_time_hours=Decimal("4.00"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            review_time_hours=Decimal("8.00"),
        )

        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        # Average should be (4 + 8) / 2 = 6
        self.assertEqual(result["avg_review_time"], Decimal("6.00"))

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
        self.assertIsNone(result["avg_review_time"])
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


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class TestGetKeyMetricsCache(TestCase):
    """Tests for get_key_metrics caching behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_get_key_metrics_caches_result(self):
        """Test that get_key_metrics caches the result."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # First call - should compute and cache
        result1 = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        # Verify cache is populated
        cache_key = dashboard_service._get_key_metrics_cache_key(self.team.id, self.start_date, self.end_date)
        cached_value = cache.get(cache_key)
        self.assertIsNotNone(cached_value)
        self.assertEqual(cached_value["prs_merged"], 1)

        # Second call should return same result
        result2 = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)
        self.assertEqual(result1, result2)

    def test_get_key_metrics_cache_hit_uses_no_queries(self):
        """Test that cache hit returns result without database queries."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # First call - populates cache
        dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        # Second call - should hit cache with 0 queries
        with self.assertNumQueries(0):
            result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["prs_merged"], 1)

    def test_get_key_metrics_different_teams_have_separate_cache(self):
        """Test that different teams have separate cache entries."""
        team2 = TeamFactory()

        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PullRequestFactory(
            team=team2,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PullRequestFactory(
            team=team2,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )

        result1 = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)
        result2 = dashboard_service.get_key_metrics(team2, self.start_date, self.end_date)

        self.assertEqual(result1["prs_merged"], 1)
        self.assertEqual(result2["prs_merged"], 2)

    def test_get_key_metrics_different_dates_have_separate_cache(self):
        """Test that different date ranges have separate cache entries."""
        # PRs in January
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        # PRs in February
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 16, 12, 0)),
        )

        result_jan = dashboard_service.get_key_metrics(self.team, date(2024, 1, 1), date(2024, 1, 31))
        result_feb = dashboard_service.get_key_metrics(self.team, date(2024, 2, 1), date(2024, 2, 29))

        self.assertEqual(result_jan["prs_merged"], 1)
        self.assertEqual(result_feb["prs_merged"], 2)
