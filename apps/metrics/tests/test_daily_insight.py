from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import TeamFactory
from apps.metrics.models import DailyInsight
from apps.teams.context import unset_current_team


class TestDailyInsightModel(TestCase):
    """Tests for DailyInsight model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_daily_insight_creation_with_all_required_fields(self):
        """Test that DailyInsight can be created with all required fields."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="high",
            title="Cycle time trending up",
            description="Team cycle time has increased by 15% this week",
            metric_type="cycle_time",
        )
        self.assertEqual(insight.category, "trend")
        self.assertEqual(insight.priority, "high")
        self.assertEqual(insight.title, "Cycle time trending up")
        self.assertEqual(insight.metric_type, "cycle_time")
        self.assertIsNotNone(insight.pk)

    def test_category_choice_trend(self):
        """Test that category choice 'trend' is valid."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="medium",
            title="Test trend",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertEqual(insight.category, "trend")

    def test_category_choice_anomaly(self):
        """Test that category choice 'anomaly' is valid."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="anomaly",
            priority="high",
            title="Test anomaly",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertEqual(insight.category, "anomaly")

    def test_category_choice_comparison(self):
        """Test that category choice 'comparison' is valid."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="comparison",
            priority="low",
            title="Test comparison",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertEqual(insight.category, "comparison")

    def test_category_choice_action(self):
        """Test that category choice 'action' is valid."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="action",
            priority="high",
            title="Test action",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertEqual(insight.category, "action")

    def test_category_invalid_choice_raises_error(self):
        """Test that invalid category choice raises validation error."""
        insight = DailyInsight(
            team=self.team,
            date=timezone.now().date(),
            category="invalid_category",
            priority="high",
            title="Test",
            description="Test description",
            metric_type="cycle_time",
        )
        with self.assertRaises(ValidationError):
            insight.full_clean()

    def test_priority_choice_high(self):
        """Test that priority choice 'high' is valid."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="high",
            title="Test high priority",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertEqual(insight.priority, "high")

    def test_priority_choice_medium(self):
        """Test that priority choice 'medium' is valid."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="medium",
            title="Test medium priority",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertEqual(insight.priority, "medium")

    def test_priority_choice_low(self):
        """Test that priority choice 'low' is valid."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="low",
            title="Test low priority",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertEqual(insight.priority, "low")

    def test_priority_invalid_choice_raises_error(self):
        """Test that invalid priority choice raises validation error."""
        insight = DailyInsight(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="critical",
            title="Test",
            description="Test description",
            metric_type="cycle_time",
        )
        with self.assertRaises(ValidationError):
            insight.full_clean()

    def test_default_ordering_date_desc_priority_category(self):
        """Test that default ordering is by -date, priority, category."""
        # Create insights with different dates and priorities
        from datetime import date, timedelta

        today = date.today()
        yesterday = today - timedelta(days=1)

        DailyInsight.objects.create(
            team=self.team,
            date=yesterday,
            category="trend",
            priority="high",
            title="Yesterday high",
            description="Test",
            metric_type="cycle_time",
        )
        DailyInsight.objects.create(
            team=self.team,
            date=today,
            category="action",
            priority="low",
            title="Today low",
            description="Test",
            metric_type="cycle_time",
        )
        DailyInsight.objects.create(
            team=self.team,
            date=today,
            category="trend",
            priority="high",
            title="Today high",
            description="Test",
            metric_type="cycle_time",
        )

        insights = list(DailyInsight.objects.all())
        # Should be ordered by: -date (today first), then priority, then category
        # Today's insights should come first
        self.assertEqual(insights[0].date, today)
        self.assertEqual(insights[1].date, today)
        self.assertEqual(insights[2].date, yesterday)

    def test_is_dismissed_defaults_to_false(self):
        """Test that is_dismissed defaults to False."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="medium",
            title="Test",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertFalse(insight.is_dismissed)

    def test_dismissed_at_defaults_to_null(self):
        """Test that dismissed_at defaults to None."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="medium",
            title="Test",
            description="Test description",
            metric_type="cycle_time",
        )
        self.assertIsNone(insight.dismissed_at)

    def test_metric_value_can_store_json_data(self):
        """Test that metric_value can store JSON data."""
        metric_data = {
            "current_value": 24.5,
            "previous_value": 18.2,
            "change_percent": 34.6,
            "affected_members": ["member1", "member2"],
        }
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="high",
            title="Cycle time increased",
            description="Test description",
            metric_type="cycle_time",
            metric_value=metric_data,
        )
        self.assertEqual(insight.metric_value, metric_data)
        self.assertEqual(insight.metric_value["current_value"], 24.5)
        self.assertEqual(len(insight.metric_value["affected_members"]), 2)

    def test_metric_value_can_be_null(self):
        """Test that metric_value can be null."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="action",
            priority="medium",
            title="Review your process",
            description="Consider improving code review turnaround",
            metric_type="review_time",
            metric_value=None,
        )
        self.assertIsNone(insight.metric_value)

    def test_comparison_period_can_be_blank(self):
        """Test that comparison_period can be blank."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="action",
            priority="low",
            title="Test",
            description="Test description",
            metric_type="cycle_time",
            comparison_period="",
        )
        self.assertEqual(insight.comparison_period, "")

    def test_comparison_period_week_over_week(self):
        """Test that comparison_period can store 'week_over_week'."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="comparison",
            priority="medium",
            title="Weekly comparison",
            description="Test description",
            metric_type="cycle_time",
            comparison_period="week_over_week",
        )
        self.assertEqual(insight.comparison_period, "week_over_week")

    def test_comparison_period_month_over_month(self):
        """Test that comparison_period can store 'month_over_month'."""
        insight = DailyInsight.objects.create(
            team=self.team,
            date=timezone.now().date(),
            category="comparison",
            priority="medium",
            title="Monthly comparison",
            description="Test description",
            metric_type="cycle_time",
            comparison_period="month_over_month",
        )
        self.assertEqual(insight.comparison_period, "month_over_month")

    def test_factory_creates_valid_instances(self):
        """Test that DailyInsightFactory creates valid instances."""
        from apps.metrics.factories import DailyInsightFactory

        insight = DailyInsightFactory(team=self.team)
        self.assertIsNotNone(insight.pk)
        self.assertEqual(insight.team, self.team)
        self.assertIn(insight.category, ["trend", "anomaly", "comparison", "action"])
        self.assertIn(insight.priority, ["high", "medium", "low"])
        self.assertIsNotNone(insight.title)
        self.assertIsNotNone(insight.description)
        self.assertIsNotNone(insight.metric_type)

    def test_date_index_exists(self):
        """Test that date field has database index."""
        # This test verifies the field has db_index=True
        field = DailyInsight._meta.get_field("date")
        self.assertTrue(field.db_index)

    def test_model_has_date_category_index(self):
        """Test that model has composite index on (date, category)."""
        # Check if the composite index exists in model's indexes
        indexes = DailyInsight._meta.indexes
        index_fields = [tuple(idx.fields) for idx in indexes]
        self.assertIn(("date", "category"), index_fields)

    def test_model_has_priority_is_dismissed_index(self):
        """Test that model has composite index on (priority, is_dismissed)."""
        indexes = DailyInsight._meta.indexes
        index_fields = [tuple(idx.fields) for idx in indexes]
        self.assertIn(("priority", "is_dismissed"), index_fields)
