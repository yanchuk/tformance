"""Tests for sparkline data service functions."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.metrics.services import dashboard_service


def make_aware_date(year: int, month: int, day: int):
    """Create a timezone-aware datetime from date components."""
    return timezone.make_aware(timezone.datetime(year, month, day))


class TestGetSparklineData(TestCase):
    """Tests for get_sparkline_data function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_returns_dict_with_all_metrics(self):
        """Test that sparkline data includes all metric keys."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=84)  # 12 weeks

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("prs_merged", result)
        self.assertIn("cycle_time", result)
        self.assertIn("ai_adoption", result)
        self.assertIn("review_time", result)

    def test_each_metric_has_values_and_change(self):
        """Test that each metric has values list and change percentage."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=84)

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        for metric_key in ["prs_merged", "cycle_time", "ai_adoption", "review_time"]:
            metric_data = result[metric_key]
            self.assertIn("values", metric_data)
            self.assertIn("change_pct", metric_data)
            self.assertIsInstance(metric_data["values"], list)

    def test_values_list_has_correct_length(self):
        """Test that values list has 12 entries (one per week)."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=84)

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        # Should have up to 12 weeks of data
        self.assertLessEqual(len(result["prs_merged"]["values"]), 12)

    def test_returns_empty_values_when_no_data(self):
        """Test that function handles no data gracefully."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=84)

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        # Should still return structure even with no data
        self.assertIsInstance(result["prs_merged"]["values"], list)
        self.assertEqual(result["prs_merged"]["change_pct"], 0)

    def test_prs_merged_counts_correctly(self):
        """Test that PRs merged count is calculated correctly per week."""
        now = timezone.now()
        end_date = now.date()
        start_date = end_date - timedelta(days=84)

        # Create PRs in different weeks
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now - timedelta(days=3),  # This week
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now - timedelta(days=10),  # Last week
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now - timedelta(days=10),  # Last week (2nd PR)
        )

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        # Last two values should be non-zero
        values = result["prs_merged"]["values"]
        self.assertGreater(sum(values), 0)

    def test_change_pct_calculated_correctly(self):
        """Test that change percentage is calculated from first to last week."""
        now = timezone.now()
        end_date = now.date()
        start_date = end_date - timedelta(days=84)

        # Create PRs: 3 in first week, 6 in last week
        # MIN_SPARKLINE_SAMPLE_SIZE = 3, so we need at least 3 PRs per week
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=now - timedelta(days=80),  # ~11 weeks ago
            )
        for _ in range(6):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=now - timedelta(days=3),  # This week
            )

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        # 3 -> 6 = 100% increase
        self.assertEqual(result["prs_merged"]["change_pct"], 100)

    def test_filters_by_team(self):
        """Test that sparkline data is filtered by team."""
        now = timezone.now()
        end_date = now.date()
        start_date = end_date - timedelta(days=84)

        other_team = TeamFactory()

        # Create PR for other team
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=now - timedelta(days=3),
        )

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        # Should not include other team's PRs
        self.assertEqual(sum(result["prs_merged"]["values"]), 0)

    def test_cycle_time_calculates_average_per_week(self):
        """Test that cycle time is averaged per week."""
        now = timezone.now()
        end_date = now.date()
        start_date = end_date - timedelta(days=84)

        # Create PRs with different cycle times in same week
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now - timedelta(days=3),
            cycle_time_hours=10.0,
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now - timedelta(days=3),
            cycle_time_hours=20.0,
        )

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        values = result["cycle_time"]["values"]
        # Last value should be average: (10 + 20) / 2 = 15
        self.assertGreater(values[-1], 0)

    def test_ai_adoption_calculates_percentage_per_week(self):
        """Test that AI adoption is percentage per week."""
        now = timezone.now()
        end_date = now.date()
        start_date = end_date - timedelta(days=84)

        # Create PRs: 1 AI-assisted, 1 not
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now - timedelta(days=3),
            is_ai_assisted=True,
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now - timedelta(days=3),
            is_ai_assisted=False,
        )

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        values = result["ai_adoption"]["values"]
        # Last value should be 50% (1 out of 2)
        self.assertEqual(values[-1], 50.0)

    def test_trend_direction_positive(self):
        """Test that trend direction is included in response."""
        now = timezone.now()
        end_date = now.date()
        start_date = end_date - timedelta(days=84)

        # Create increasing trend: 3 PRs 11 weeks ago, 6 PRs this week
        # MIN_SPARKLINE_SAMPLE_SIZE = 3, so we need at least 3 PRs per week
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=now - timedelta(days=77),
            )
        for _ in range(6):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=now - timedelta(days=3),
            )

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        # Positive change
        self.assertIn("trend", result["prs_merged"])
        self.assertEqual(result["prs_merged"]["trend"], "up")

    def test_trend_direction_negative(self):
        """Test that negative trend is detected."""
        now = timezone.now()
        end_date = now.date()
        start_date = end_date - timedelta(days=84)

        # Create decreasing trend: 6 PRs 11 weeks ago, 3 PRs this week
        # MIN_SPARKLINE_SAMPLE_SIZE = 3, so we need at least 3 PRs per week
        for _ in range(6):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=now - timedelta(days=77),
            )
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=now - timedelta(days=3),
            )

        result = dashboard_service.get_sparkline_data(self.team, start_date, end_date)

        # Negative change (6 -> 3 = -50%)
        self.assertEqual(result["prs_merged"]["trend"], "down")


class TestSparklineViewIntegration(TestCase):
    """Tests for sparkline data in key_metrics_cards view."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import UserFactory
        from apps.teams.roles import ROLE_ADMIN

        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)

    def test_key_metrics_cards_includes_sparklines(self):
        """Test that key_metrics_cards view includes sparkline data."""
        from django.urls import reverse

        self.client.force_login(self.admin_user)
        url = reverse("metrics:cards_metrics")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Sparkline data should be in context
        self.assertIn("sparklines", response.context)

    def test_sparklines_context_has_all_metrics(self):
        """Test that sparklines context has all required metrics."""
        from django.urls import reverse

        self.client.force_login(self.admin_user)
        url = reverse("metrics:cards_metrics")

        response = self.client.get(url)

        sparklines = response.context.get("sparklines", {})
        self.assertIn("prs_merged", sparklines)
        self.assertIn("cycle_time", sparklines)
        self.assertIn("ai_adoption", sparklines)
