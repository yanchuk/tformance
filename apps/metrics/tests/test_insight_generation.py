"""Tests for insight generation functionality."""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.metrics.models import DailyInsight, IndustryBenchmark


class TestTrendInsightGeneration(TestCase):
    """Tests for trend-based insight generation."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear existing benchmarks to avoid conflicts
        IndustryBenchmark.objects.all().delete()

        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()

    def test_generate_cycle_time_increase_insight(self):
        """Test generating insight when cycle time increases significantly."""
        from apps.metrics.services import insight_service

        # Create PRs from last week with low cycle time
        # Last week is [insight_date - 14 days, insight_date - 7 days)
        # Use 10 days ago to be safely within the range
        last_week = timezone.now() - timedelta(days=10)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=last_week,
                cycle_time_hours=20.0,
            )

        # Create PRs from this week with high cycle time (50% increase)
        # This week is [insight_date - 7 days, insight_date + 1 day)
        # Use 3 days ago to be safely within the range
        this_week = timezone.now() - timedelta(days=3)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=this_week,
                cycle_time_hours=30.0,
            )

        insights = insight_service.generate_trend_insights(self.team, self.today)

        # Should generate a trend alert for cycle time increase
        cycle_time_insights = [i for i in insights if i.metric_type == "cycle_time"]
        self.assertEqual(len(cycle_time_insights), 1)
        self.assertEqual(cycle_time_insights[0].category, "trend")
        self.assertIn("increase", cycle_time_insights[0].title.lower())

    def test_generate_cycle_time_improvement_insight(self):
        """Test generating insight when cycle time improves significantly."""
        from apps.metrics.services import insight_service

        # Create PRs from last week with high cycle time
        # Last week is [insight_date - 14 days, insight_date - 7 days)
        # Use 10 days ago to be safely within the range
        last_week = timezone.now() - timedelta(days=10)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=last_week,
                cycle_time_hours=40.0,
            )

        # Create PRs from this week with low cycle time (25% improvement)
        # This week is [insight_date - 7 days, insight_date + 1 day)
        # Use 3 days ago to be safely within the range
        this_week = timezone.now() - timedelta(days=3)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=this_week,
                cycle_time_hours=30.0,
            )

        insights = insight_service.generate_trend_insights(self.team, self.today)

        # Should generate a positive trend insight
        cycle_time_insights = [i for i in insights if i.metric_type == "cycle_time"]
        self.assertEqual(len(cycle_time_insights), 1)
        self.assertIn("improve", cycle_time_insights[0].title.lower())

    def test_no_insight_for_small_changes(self):
        """Test that small changes don't generate insights."""
        from apps.metrics.services import insight_service

        # Create PRs with minimal change
        # Use 10 days ago for last week, 3 days ago for this week
        last_week = timezone.now() - timedelta(days=10)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=last_week,
                cycle_time_hours=20.0,
            )

        this_week = timezone.now() - timedelta(days=3)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=this_week,
                cycle_time_hours=21.0,  # Only 5% increase
            )

        insights = insight_service.generate_trend_insights(self.team, self.today)

        # Small changes should not generate insights
        cycle_time_insights = [i for i in insights if i.metric_type == "cycle_time"]
        self.assertEqual(len(cycle_time_insights), 0)

    def test_generate_ai_adoption_trend_insight(self):
        """Test generating insight for AI adoption changes."""
        from apps.metrics.services import insight_service

        # Create PRs from last week with no AI
        # Use 10 days ago for last week, 3 days ago for this week
        last_week = timezone.now() - timedelta(days=10)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=last_week,
                is_ai_assisted=False,
            )

        # Create PRs from this week with AI
        this_week = timezone.now() - timedelta(days=3)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=this_week,
                is_ai_assisted=True,
            )

        insights = insight_service.generate_trend_insights(self.team, self.today)

        # Should generate an AI adoption insight
        ai_insights = [i for i in insights if i.metric_type == "ai_adoption"]
        self.assertEqual(len(ai_insights), 1)
        self.assertIn("AI", ai_insights[0].title)


class TestBenchmarkInsightGeneration(TestCase):
    """Tests for benchmark-based insight generation."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear existing benchmarks
        IndustryBenchmark.objects.all().delete()

        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()

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

    def test_generate_elite_performance_insight(self):
        """Test generating insight when team has elite performance."""
        from apps.metrics.services import insight_service

        # Create PRs with elite cycle time (below p25)
        # Pass author= to avoid creating extra TeamMembers (which affects team size bucket)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now(),
                cycle_time_hours=8.0,  # Well below p25 of 12
            )

        insights = insight_service.generate_benchmark_insights(self.team, self.today)

        # Should generate an elite performance insight
        self.assertGreater(len(insights), 0)
        self.assertTrue(any("elite" in i.title.lower() or "top" in i.title.lower() for i in insights))

    def test_generate_needs_improvement_insight(self):
        """Test generating insight when team needs improvement."""
        from apps.metrics.services import insight_service

        # Create PRs with poor cycle time (above p90)
        # Pass author= to avoid creating extra TeamMembers (which affects team size bucket)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now(),
                cycle_time_hours=100.0,  # Above p90 of 72
            )

        insights = insight_service.generate_benchmark_insights(self.team, self.today)

        # Should generate an improvement recommendation
        self.assertGreater(len(insights), 0)
        self.assertTrue(any("improve" in i.title.lower() or "opportunity" in i.title.lower() for i in insights))

    def test_no_benchmark_insight_for_average_performance(self):
        """Test that average performance doesn't generate benchmark insight."""
        from apps.metrics.services import insight_service

        # Create PRs with average cycle time (around p50)
        # Pass author= to avoid creating extra TeamMembers (which affects team size bucket)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now(),
                cycle_time_hours=24.0,  # Exactly at p50
            )

        insights = insight_service.generate_benchmark_insights(self.team, self.today)

        # Average performance should not generate special insights
        benchmark_insights = [i for i in insights if i.category == "comparison"]
        self.assertEqual(len(benchmark_insights), 0)


class TestAchievementInsightGeneration(TestCase):
    """Tests for achievement-based insight generation."""

    def setUp(self):
        """Set up test fixtures."""
        IndustryBenchmark.objects.all().delete()
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()

    def test_generate_ai_adoption_milestone_insight(self):
        """Test generating insight when AI adoption reaches milestone."""
        from apps.metrics.services import insight_service

        # Create 10 PRs, 5 with AI (50% adoption)
        for i in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now(),
                is_ai_assisted=(i < 5),
            )

        insights = insight_service.generate_achievement_insights(self.team, self.today)

        # Should generate an AI adoption milestone insight
        ai_insights = [i for i in insights if "AI" in i.title or "ai" in i.metric_type]
        self.assertEqual(len(ai_insights), 1)
        self.assertIn("50%", ai_insights[0].title)

    def test_generate_pr_count_milestone_insight(self):
        """Test generating insight when PR count reaches milestone."""
        from apps.metrics.services import insight_service

        # Create 100 PRs for the team
        for _ in range(100):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now(),
            )

        insights = insight_service.generate_achievement_insights(self.team, self.today)

        # Should generate a PR count milestone insight
        pr_insights = [i for i in insights if "PR" in i.title or "pr_count" in i.metric_type]
        self.assertGreater(len(pr_insights), 0)


class TestGenerateAllInsights(TestCase):
    """Tests for the main insight generation function."""

    def setUp(self):
        """Set up test fixtures."""
        IndustryBenchmark.objects.all().delete()
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()

    def test_generate_all_insights_saves_to_database(self):
        """Test that generate_all_insights saves insights to database."""
        from apps.metrics.services import insight_service

        # Create 10 PRs with 50% AI adoption to hit the 50% milestone
        for i in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now(),
                is_ai_assisted=(i < 5),  # First 5 are AI-assisted = 50%
            )

        initial_count = DailyInsight.objects.filter(team=self.team).count()
        insight_service.generate_all_insights(self.team, self.today)
        final_count = DailyInsight.objects.filter(team=self.team).count()

        # Should have created at least one insight
        self.assertGreater(final_count, initial_count)

    def test_generate_all_insights_clears_old_insights(self):
        """Test that generating insights for a day replaces old ones."""
        from apps.metrics.services import insight_service

        # Create 10 PRs with 50% AI adoption to hit the 50% milestone
        for i in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now(),
                is_ai_assisted=(i < 5),
            )

        # Generate insights twice
        insight_service.generate_all_insights(self.team, self.today)
        first_count = DailyInsight.objects.filter(team=self.team, date=self.today).count()

        insight_service.generate_all_insights(self.team, self.today)
        second_count = DailyInsight.objects.filter(team=self.team, date=self.today).count()

        # Should not duplicate insights
        self.assertEqual(first_count, second_count)

    def test_generate_all_insights_respects_dismissed(self):
        """Test that dismissed insights are not regenerated."""
        from apps.metrics.services import insight_service

        # Create 10 PRs with 50% AI adoption to hit the 50% milestone
        for i in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now(),
                is_ai_assisted=(i < 5),
            )

        # Generate insights and dismiss one
        insight_service.generate_all_insights(self.team, self.today)
        insight = DailyInsight.objects.filter(team=self.team, date=self.today).first()
        if insight:
            insight.is_dismissed = True
            insight.dismissed_at = timezone.now()
            insight.save()

            # Regenerate - dismissed insight should remain
            insight_service.generate_all_insights(self.team, self.today)

            dismissed_insight = DailyInsight.objects.get(id=insight.id)
            self.assertTrue(dismissed_insight.is_dismissed)
