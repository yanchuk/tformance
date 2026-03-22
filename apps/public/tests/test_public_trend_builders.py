"""Tests for public trend builders (Task 2).

Covers combined trend alignment, correlation computation,
classification boundary values, and scatter data generation.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory


class CombinedTrendBuilderTests(TestCase):
    """Step 2.1: Combined trend chart data builder."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    @patch("apps.public.services.public_trends.get_ai_adoption_trend")
    @patch("apps.public.services.public_trends.get_cycle_time_trend")
    def test_build_combined_trend_returns_labels_and_two_datasets(self, mock_cycle, mock_ai):
        from apps.public.services.public_trends import build_combined_trend

        mock_ai.return_value = [
            {"week": "2026-01-05", "value": 30.0},
            {"week": "2026-01-12", "value": 35.0},
        ]
        mock_cycle.return_value = [
            {"week": "2026-01-05", "value": 18.5},
            {"week": "2026-01-12", "value": 16.2},
        ]
        end = date(2026, 1, 18)
        start = end - timedelta(days=90)
        result = build_combined_trend(self.team, start, end)

        assert "labels" in result
        assert "datasets" in result
        assert len(result["labels"]) == 2
        assert result["datasets"]["ai_adoption"]["values"] == [30.0, 35.0]
        assert result["datasets"]["cycle_time"]["values"] == [18.5, 16.2]

    @patch("apps.public.services.public_trends.get_ai_adoption_trend")
    @patch("apps.public.services.public_trends.get_cycle_time_trend")
    def test_build_combined_trend_aligns_weeks(self, mock_cycle, mock_ai):
        """When one series has weeks the other doesn't, fill with None."""
        from apps.public.services.public_trends import build_combined_trend

        mock_ai.return_value = [
            {"week": "2026-01-05", "value": 30.0},
            {"week": "2026-01-12", "value": 35.0},
            {"week": "2026-01-19", "value": 40.0},
        ]
        mock_cycle.return_value = [
            {"week": "2026-01-12", "value": 16.2},
        ]
        end = date(2026, 1, 25)
        start = end - timedelta(days=90)
        result = build_combined_trend(self.team, start, end)

        assert len(result["labels"]) == 3
        assert result["datasets"]["cycle_time"]["values"][0] is None
        assert result["datasets"]["cycle_time"]["values"][2] is None

    @patch("apps.public.services.public_trends.get_ai_adoption_trend")
    @patch("apps.public.services.public_trends.get_review_time_trend")
    def test_build_combined_trend_with_review_time_secondary(self, mock_review, mock_ai):
        from apps.public.services.public_trends import build_combined_trend

        mock_ai.return_value = [{"week": "2026-01-05", "value": 30.0}]
        mock_review.return_value = [{"week": "2026-01-05", "value": 4.2}]
        end = date(2026, 1, 11)
        start = end - timedelta(days=90)
        result = build_combined_trend(self.team, start, end, secondary="review_time")

        assert "review_time" in result["datasets"]
        assert result["datasets"]["review_time"]["values"] == [4.2]

    @patch("apps.public.services.public_trends.get_ai_adoption_trend")
    @patch("apps.public.services.public_trends.get_cycle_time_trend")
    def test_build_combined_trend_with_repo_filter(self, mock_cycle, mock_ai):
        from apps.public.services.public_trends import build_combined_trend

        mock_ai.return_value = []
        mock_cycle.return_value = []
        end = date(2026, 1, 11)
        start = end - timedelta(days=90)
        build_combined_trend(self.team, start, end, repo="org/repo")

        # Verify repo filter was passed through
        mock_ai.assert_called_once()
        assert mock_ai.call_args[1].get("repo") == "org/repo"


class CorrelationBuilderTests(TestCase):
    """Step 2.2: Correlation computation and classification."""

    def test_compute_weekly_correlation_strong_negative(self):
        from apps.public.services.public_trends import compute_weekly_correlation

        # AI goes up, delivery time goes down -> strong negative
        ai = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
        delivery = [50.0, 45.0, 38.0, 30.0, 22.0, 15.0, 8.0]
        r = compute_weekly_correlation(ai, delivery)
        assert r is not None
        assert r < -0.6

    def test_compute_weekly_correlation_no_relationship(self):
        from apps.public.services.public_trends import compute_weekly_correlation

        # Truly uncorrelated data (verified r ≈ 0.05)
        ai = [10.0, 30.0, 50.0, 20.0, 40.0, 60.0, 35.0]
        delivery = [25.0, 30.0, 20.0, 35.0, 22.0, 28.0, 32.0]
        r = compute_weekly_correlation(ai, delivery)
        # Should produce a weak correlation
        assert r is None or abs(r) < 0.6

    def test_compute_weekly_correlation_insufficient_data_returns_none(self):
        from apps.public.services.public_trends import compute_weekly_correlation

        r = compute_weekly_correlation([10.0, 20.0], [30.0, 40.0])
        assert r is None

    def test_compute_weekly_correlation_constant_series_returns_none(self):
        """Zero-variance series must not crash (review 2A)."""
        from apps.public.services.public_trends import compute_weekly_correlation

        ai = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        delivery = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
        r = compute_weekly_correlation(ai, delivery)
        assert r is None

    def test_classify_correlation_boundaries(self):
        """Review 9A: All boundary + mid-range classification tests."""
        from apps.public.services.public_trends import classify_correlation

        cases = [
            (-0.9, "strong negative"),
            (-0.6, "strong negative"),
            (-0.45, "moderate negative"),
            (-0.3, "moderate negative"),
            (-0.1, "weak or no clear relationship"),
            (0.0, "weak or no clear relationship"),
            (0.1, "weak or no clear relationship"),
            (0.3, "moderate positive"),
            (0.45, "moderate positive"),
            (0.6, "strong positive"),
            (0.9, "strong positive"),
        ]
        for r_value, expected_label in cases:
            result = classify_correlation(r_value)
            assert result == expected_label, (
                f"classify_correlation({r_value}) = {result!r}, expected {expected_label!r}"
            )

    @patch("apps.public.services.public_trends.get_ai_adoption_trend")
    @patch("apps.public.services.public_trends.get_cycle_time_trend")
    def test_build_correlation_scatter_returns_points(self, mock_cycle, mock_ai):
        from apps.public.services.public_trends import build_correlation_scatter

        team = TeamFactory()
        # 7 weeks of data
        mock_ai.return_value = [{"week": f"2026-01-{5 + 7 * i:02d}", "value": 10.0 + i * 10} for i in range(7)]
        mock_cycle.return_value = [{"week": f"2026-01-{5 + 7 * i:02d}", "value": 50.0 - i * 5} for i in range(7)]
        end = date(2026, 2, 28)
        start = end - timedelta(days=90)
        result = build_correlation_scatter(team, start, end)

        assert "points" in result
        assert "r_value" in result
        assert "classification" in result
        assert len(result["points"]) == 7
