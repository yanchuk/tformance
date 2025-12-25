"""Tests for industry benchmarks functionality."""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.metrics.models import IndustryBenchmark


class TestIndustryBenchmarkModel(TestCase):
    """Tests for IndustryBenchmark model."""

    def setUp(self):
        """Clear existing benchmarks to avoid conflicts with seeded data."""
        IndustryBenchmark.objects.all().delete()

    def test_create_benchmark(self):
        """Test creating an industry benchmark."""
        benchmark = IndustryBenchmark.objects.create(
            metric_name="cycle_time",
            team_size_bucket="small",
            p25=Decimal("12.0"),
            p50=Decimal("24.0"),
            p75=Decimal("48.0"),
            p90=Decimal("72.0"),
            source="DORA 2024",
            year=2024,
        )

        self.assertEqual(benchmark.metric_name, "cycle_time")
        self.assertEqual(benchmark.team_size_bucket, "small")
        self.assertEqual(benchmark.p50, Decimal("24.0"))

    def test_benchmark_str_representation(self):
        """Test string representation of benchmark."""
        benchmark = IndustryBenchmark.objects.create(
            metric_name="cycle_time",
            team_size_bucket="medium",
            p25=Decimal("12.0"),
            p50=Decimal("24.0"),
            p75=Decimal("48.0"),
            p90=Decimal("72.0"),
            source="DORA 2024",
            year=2024,
        )

        # Uses display names in __str__
        self.assertIn("Cycle Time", str(benchmark))
        self.assertIn("Medium", str(benchmark))
        self.assertIn("2024", str(benchmark))

    def test_benchmark_team_size_buckets(self):
        """Test all valid team size buckets."""
        buckets = ["small", "medium", "large", "enterprise"]

        for bucket in buckets:
            benchmark = IndustryBenchmark.objects.create(
                metric_name="cycle_time",
                team_size_bucket=bucket,
                p25=Decimal("12.0"),
                p50=Decimal("24.0"),
                p75=Decimal("48.0"),
                p90=Decimal("72.0"),
                source="DORA 2024",
                year=2024,
            )
            self.assertEqual(benchmark.team_size_bucket, bucket)

    def test_benchmark_metric_names(self):
        """Test all valid metric names."""
        metrics = ["cycle_time", "review_time", "pr_count", "ai_adoption", "deployment_freq"]

        for metric in metrics:
            benchmark = IndustryBenchmark.objects.create(
                metric_name=metric,
                team_size_bucket="small",
                p25=Decimal("10.0"),
                p50=Decimal("20.0"),
                p75=Decimal("30.0"),
                p90=Decimal("40.0"),
                source="DORA 2024",
                year=2024,
            )
            self.assertEqual(benchmark.metric_name, metric)

    def test_get_for_team_size(self):
        """Test getting benchmark by team size."""
        IndustryBenchmark.objects.create(
            metric_name="cycle_time",
            team_size_bucket="small",
            p25=Decimal("12.0"),
            p50=Decimal("24.0"),
            p75=Decimal("48.0"),
            p90=Decimal("72.0"),
            source="DORA 2024",
            year=2024,
        )
        IndustryBenchmark.objects.create(
            metric_name="cycle_time",
            team_size_bucket="large",
            p25=Decimal("24.0"),
            p50=Decimal("48.0"),
            p75=Decimal("96.0"),
            p90=Decimal("144.0"),
            source="DORA 2024",
            year=2024,
        )

        small_benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time", team_size_bucket="small")
        large_benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time", team_size_bucket="large")

        self.assertEqual(small_benchmark.p50, Decimal("24.0"))
        self.assertEqual(large_benchmark.p50, Decimal("48.0"))


class TestBenchmarkService(TestCase):
    """Tests for benchmark service functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear existing benchmarks to avoid conflicts with seeded data
        IndustryBenchmark.objects.all().delete()

        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

        # Create benchmark data
        IndustryBenchmark.objects.create(
            metric_name="cycle_time",
            team_size_bucket="small",
            p25=Decimal("12.0"),
            p50=Decimal("24.0"),
            p75=Decimal("48.0"),
            p90=Decimal("72.0"),
            source="DORA 2024",
            year=2024,
        )

    def test_get_team_size_bucket_small(self):
        """Test team size bucket detection for small teams."""
        from apps.metrics.services import benchmark_service

        # Small team: 1-10 members
        bucket = benchmark_service.get_team_size_bucket(self.team)
        self.assertEqual(bucket, "small")

    def test_get_team_size_bucket_medium(self):
        """Test team size bucket detection for medium teams."""
        from apps.metrics.services import benchmark_service

        # Medium team: 11-50 members
        for _ in range(15):
            TeamMemberFactory(team=self.team)

        bucket = benchmark_service.get_team_size_bucket(self.team)
        self.assertEqual(bucket, "medium")

    def test_get_team_size_bucket_large(self):
        """Test team size bucket detection for large teams."""
        from apps.metrics.services import benchmark_service

        # Large team: 51-200 members
        for _ in range(60):
            TeamMemberFactory(team=self.team)

        bucket = benchmark_service.get_team_size_bucket(self.team)
        self.assertEqual(bucket, "large")

    def test_get_team_size_bucket_enterprise(self):
        """Test team size bucket detection for enterprise teams."""
        from apps.metrics.services import benchmark_service

        # Enterprise team: 201+ members
        for _ in range(210):
            TeamMemberFactory(team=self.team)

        bucket = benchmark_service.get_team_size_bucket(self.team)
        self.assertEqual(bucket, "enterprise")

    def test_calculate_percentile_below_p25(self):
        """Test percentile calculation for values below p25."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 6 hours is below p25 (12 hours)
        percentile = benchmark_service.calculate_percentile(Decimal("6.0"), benchmark)

        # Should be in top 25% (below p25 means better than 75%)
        self.assertGreater(percentile, 75)

    def test_calculate_percentile_at_p50(self):
        """Test percentile calculation for values at p50."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 24 hours is exactly at p50
        percentile = benchmark_service.calculate_percentile(Decimal("24.0"), benchmark)

        self.assertEqual(percentile, 50)

    def test_calculate_percentile_between_p50_and_p75(self):
        """Test percentile calculation for values between p50 and p75."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 36 hours is between p50 (24) and p75 (48)
        percentile = benchmark_service.calculate_percentile(Decimal("36.0"), benchmark)

        self.assertGreater(percentile, 25)
        self.assertLess(percentile, 50)

    def test_calculate_percentile_above_p90(self):
        """Test percentile calculation for values above p90."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 100 hours is above p90 (72 hours)
        percentile = benchmark_service.calculate_percentile(Decimal("100.0"), benchmark)

        # Should be in bottom 10%
        self.assertLess(percentile, 10)

    def test_get_benchmark_for_team(self):
        """Test getting benchmark comparison for a team."""
        from apps.metrics.services import benchmark_service

        now = timezone.now()
        # Create some PRs with cycle time
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now,
            cycle_time_hours=20.0,
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=now,
            cycle_time_hours=28.0,
        )

        result = benchmark_service.get_benchmark_for_team(self.team, "cycle_time")

        self.assertIn("team_value", result)
        self.assertIn("percentile", result)
        self.assertIn("benchmark", result)
        self.assertIn("interpretation", result)

    def test_get_benchmark_interpretation_elite(self):
        """Test benchmark interpretation for elite performance."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 6 hours is elite (below p25)
        interpretation = benchmark_service.get_interpretation(Decimal("6.0"), benchmark)

        self.assertIn("Elite", interpretation)

    def test_get_benchmark_interpretation_high(self):
        """Test benchmark interpretation for high performance."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 18 hours is high (between p25 and p50)
        interpretation = benchmark_service.get_interpretation(Decimal("18.0"), benchmark)

        self.assertIn("High", interpretation)

    def test_get_benchmark_interpretation_medium(self):
        """Test benchmark interpretation for medium performance."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 36 hours is medium (between p50 and p75)
        interpretation = benchmark_service.get_interpretation(Decimal("36.0"), benchmark)

        self.assertIn("Medium", interpretation)

    def test_get_benchmark_interpretation_low(self):
        """Test benchmark interpretation for low performance."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 60 hours is low (between p75 and p90)
        interpretation = benchmark_service.get_interpretation(Decimal("60.0"), benchmark)

        self.assertIn("Low", interpretation)

    def test_get_benchmark_interpretation_needs_improvement(self):
        """Test benchmark interpretation for needs improvement."""
        from apps.metrics.services import benchmark_service

        benchmark = IndustryBenchmark.objects.get(metric_name="cycle_time")
        # Value of 100 hours needs improvement (above p90)
        interpretation = benchmark_service.get_interpretation(Decimal("100.0"), benchmark)

        self.assertIn("Needs", interpretation)

    def test_get_all_benchmarks_for_team(self):
        """Test getting all benchmarks for a team."""
        from apps.metrics.services import benchmark_service

        # Create benchmarks for other metrics
        IndustryBenchmark.objects.create(
            metric_name="review_time",
            team_size_bucket="small",
            p25=Decimal("2.0"),
            p50=Decimal("4.0"),
            p75=Decimal("8.0"),
            p90=Decimal("16.0"),
            source="DORA 2024",
            year=2024,
        )

        result = benchmark_service.get_all_benchmarks_for_team(self.team)

        self.assertIn("cycle_time", result)
        self.assertIn("review_time", result)


class TestBenchmarkViewIntegration(TestCase):
    """Tests for benchmark views."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import UserFactory
        from apps.teams.roles import ROLE_ADMIN

        # Clear existing benchmarks to avoid conflicts with seeded data
        IndustryBenchmark.objects.all().delete()

        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})

        # Create benchmark data
        IndustryBenchmark.objects.create(
            metric_name="cycle_time",
            team_size_bucket="small",
            p25=Decimal("12.0"),
            p50=Decimal("24.0"),
            p75=Decimal("48.0"),
            p90=Decimal("72.0"),
            source="DORA 2024",
            year=2024,
        )

    def test_benchmark_api_returns_200(self):
        """Test benchmark API endpoint returns 200."""
        from django.urls import reverse

        self.client.force_login(self.admin_user)
        url = reverse("metrics:benchmark_data", kwargs={"metric": "cycle_time"})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_benchmark_api_returns_json(self):
        """Test benchmark API endpoint returns JSON."""
        import json

        from django.urls import reverse

        self.client.force_login(self.admin_user)
        url = reverse("metrics:benchmark_data", kwargs={"metric": "cycle_time"})

        response = self.client.get(url)
        data = json.loads(response.content)

        self.assertIn("team_value", data)
        self.assertIn("percentile", data)
        self.assertIn("benchmark", data)

    def test_benchmark_api_requires_login(self):
        """Test benchmark API requires authentication."""
        from django.urls import reverse

        url = reverse("metrics:benchmark_data", kwargs={"metric": "cycle_time"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)  # Redirect to login
