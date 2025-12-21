"""
Tests for the Insight Engine.

The Insight Engine provides:
- InsightResult dataclass for rule outputs
- InsightRule abstract base class
- Rule registry for discovering rules
- compute_insights() function to run all rules
"""

from datetime import date

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import DailyInsight


class TestInsightResultDataclass(TestCase):
    """Tests for InsightResult dataclass."""

    def test_insight_result_creation(self):
        """Test that InsightResult can be created with required fields."""
        from apps.metrics.insights.engine import InsightResult

        result = InsightResult(
            category="trend",
            priority="high",
            title="Cycle time increasing",
            description="Average cycle time increased by 20% this week",
            metric_type="cycle_time",
        )

        self.assertEqual(result.category, "trend")
        self.assertEqual(result.priority, "high")
        self.assertEqual(result.title, "Cycle time increasing")
        self.assertEqual(result.description, "Average cycle time increased by 20% this week")
        self.assertEqual(result.metric_type, "cycle_time")

    def test_insight_result_default_values(self):
        """Test that InsightResult has correct default values for optional fields."""
        from apps.metrics.insights.engine import InsightResult

        result = InsightResult(
            category="anomaly",
            priority="medium",
            title="Unusual PR size",
            description="PR #123 is 10x larger than average",
            metric_type="pr_size",
        )

        self.assertIsNone(result.metric_value)
        self.assertEqual(result.comparison_period, "")

    def test_insight_result_with_metric_value(self):
        """Test that InsightResult can store metric_value as dict."""
        from apps.metrics.insights.engine import InsightResult

        result = InsightResult(
            category="comparison",
            priority="low",
            title="Performance comparison",
            description="Team A is 15% faster than Team B",
            metric_type="cycle_time",
            metric_value={"current": 24.5, "previous": 30.2},
        )

        self.assertEqual(result.metric_value, {"current": 24.5, "previous": 30.2})

    def test_insight_result_with_comparison_period(self):
        """Test that InsightResult can store comparison_period."""
        from apps.metrics.insights.engine import InsightResult

        result = InsightResult(
            category="trend",
            priority="high",
            title="Improving trend",
            description="Review time decreased week over week",
            metric_type="review_time",
            comparison_period="week_over_week",
        )

        self.assertEqual(result.comparison_period, "week_over_week")


class TestInsightRuleAbstractClass(TestCase):
    """Tests for InsightRule abstract base class."""

    def test_insight_rule_is_abstract(self):
        """Test that InsightRule cannot be instantiated directly."""
        from apps.metrics.insights.engine import InsightRule

        # Should raise TypeError because evaluate() is abstract
        with self.assertRaises(TypeError):
            InsightRule()

    def test_concrete_rule_can_be_created(self):
        """Test that a concrete subclass of InsightRule can be created."""
        from apps.metrics.insights.engine import InsightResult, InsightRule

        class TestRule(InsightRule):
            def evaluate(self, team, target_date):
                return [
                    InsightResult(
                        category="test",
                        priority="low",
                        title="Test insight",
                        description="This is a test",
                        metric_type="test_metric",
                    )
                ]

        rule = TestRule()
        team = TeamFactory()
        results = rule.evaluate(team, date.today())

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test insight")


class TestRuleRegistry(TestCase):
    """Tests for the rule registry."""

    def setUp(self):
        """Clear the registry before each test."""
        from apps.metrics.insights.engine import clear_rules

        clear_rules()

    def tearDown(self):
        """Clear the registry after each test."""
        from apps.metrics.insights.engine import clear_rules

        clear_rules()

    def test_registry_starts_empty(self):
        """Test that the rule registry starts empty."""
        from apps.metrics.insights.engine import get_all_rules

        rules = get_all_rules()
        self.assertEqual(len(rules), 0)

    def test_register_rule_adds_to_registry(self):
        """Test that register_rule adds a rule class to the registry."""
        from apps.metrics.insights.engine import InsightRule, get_all_rules, register_rule

        class SampleRule(InsightRule):
            def evaluate(self, team, target_date):
                return []

        register_rule(SampleRule)
        rules = get_all_rules()

        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0], SampleRule)

    def test_register_multiple_rules(self):
        """Test that multiple rules can be registered."""
        from apps.metrics.insights.engine import InsightRule, get_all_rules, register_rule

        class Rule1(InsightRule):
            def evaluate(self, team, target_date):
                return []

        class Rule2(InsightRule):
            def evaluate(self, team, target_date):
                return []

        register_rule(Rule1)
        register_rule(Rule2)
        rules = get_all_rules()

        self.assertEqual(len(rules), 2)
        self.assertIn(Rule1, rules)
        self.assertIn(Rule2, rules)

    def test_clear_rules_empties_registry(self):
        """Test that clear_rules empties the registry."""
        from apps.metrics.insights.engine import InsightRule, clear_rules, get_all_rules, register_rule

        class SampleRule(InsightRule):
            def evaluate(self, team, target_date):
                return []

        register_rule(SampleRule)
        self.assertEqual(len(get_all_rules()), 1)

        clear_rules()
        self.assertEqual(len(get_all_rules()), 0)


class TestComputeInsights(TestCase):
    """Tests for the compute_insights function."""

    def setUp(self):
        """Set up test fixtures and clear registry."""
        from apps.metrics.insights.engine import clear_rules

        self.team = TeamFactory()
        self.target_date = date.today()
        clear_rules()

    def tearDown(self):
        """Clear the registry after each test."""
        from apps.metrics.insights.engine import clear_rules

        clear_rules()

    def test_compute_insights_with_no_rules_returns_empty_list(self):
        """Test that compute_insights returns empty list when no rules are registered."""
        from apps.metrics.insights.engine import compute_insights

        insights = compute_insights(self.team, self.target_date)

        self.assertEqual(len(insights), 0)
        self.assertIsInstance(insights, list)

    def test_compute_insights_runs_registered_rules(self):
        """Test that compute_insights runs all registered rules."""
        from apps.metrics.insights.engine import InsightResult, InsightRule, compute_insights, register_rule

        class Rule1(InsightRule):
            def evaluate(self, team, target_date):
                return [
                    InsightResult(
                        category="trend",
                        priority="high",
                        title="Rule 1 result",
                        description="First rule found this",
                        metric_type="cycle_time",
                    )
                ]

        class Rule2(InsightRule):
            def evaluate(self, team, target_date):
                return [
                    InsightResult(
                        category="anomaly",
                        priority="medium",
                        title="Rule 2 result",
                        description="Second rule found this",
                        metric_type="review_time",
                    )
                ]

        register_rule(Rule1)
        register_rule(Rule2)

        insights = compute_insights(self.team, self.target_date)

        self.assertEqual(len(insights), 2)

    def test_compute_insights_saves_to_daily_insight_model(self):
        """Test that compute_insights saves results to DailyInsight model."""
        from apps.metrics.insights.engine import InsightResult, InsightRule, compute_insights, register_rule

        class TestRule(InsightRule):
            def evaluate(self, team, target_date):
                return [
                    InsightResult(
                        category="trend",
                        priority="high",
                        title="Cycle time increasing",
                        description="Average cycle time is up",
                        metric_type="cycle_time",
                        metric_value={"current": 48.5, "previous": 36.2},
                        comparison_period="week_over_week",
                    )
                ]

        register_rule(TestRule)

        # Should be no insights before
        self.assertEqual(DailyInsight.objects.filter(team=self.team, date=self.target_date).count(), 0)

        compute_insights(self.team, self.target_date)

        # Should have created 1 insight
        self.assertEqual(DailyInsight.objects.filter(team=self.team, date=self.target_date).count(), 1)

        # Check the insight was saved correctly
        saved_insight = DailyInsight.objects.get(team=self.team, date=self.target_date)
        self.assertEqual(saved_insight.category, "trend")
        self.assertEqual(saved_insight.priority, "high")
        self.assertEqual(saved_insight.title, "Cycle time increasing")
        self.assertEqual(saved_insight.description, "Average cycle time is up")
        self.assertEqual(saved_insight.metric_type, "cycle_time")
        self.assertEqual(saved_insight.metric_value, {"current": 48.5, "previous": 36.2})
        self.assertEqual(saved_insight.comparison_period, "week_over_week")

    def test_compute_insights_returns_created_instances(self):
        """Test that compute_insights returns a list of created DailyInsight instances."""
        from apps.metrics.insights.engine import InsightResult, InsightRule, compute_insights, register_rule

        class TestRule(InsightRule):
            def evaluate(self, team, target_date):
                return [
                    InsightResult(
                        category="action",
                        priority="high",
                        title="Action required",
                        description="Please review this",
                        metric_type="review_time",
                    )
                ]

        register_rule(TestRule)

        insights = compute_insights(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertIsInstance(insights[0], DailyInsight)
        self.assertEqual(insights[0].team, self.team)
        self.assertEqual(insights[0].date, self.target_date)
        self.assertIsNotNone(insights[0].pk)

    def test_compute_insights_handles_rule_exceptions_gracefully(self):
        """Test that compute_insights continues when a rule raises an exception."""
        from apps.metrics.insights.engine import InsightResult, InsightRule, compute_insights, register_rule

        class BrokenRule(InsightRule):
            def evaluate(self, team, target_date):
                raise ValueError("This rule is broken")

        class WorkingRule(InsightRule):
            def evaluate(self, team, target_date):
                return [
                    InsightResult(
                        category="trend",
                        priority="low",
                        title="Working rule",
                        description="This one works",
                        metric_type="cycle_time",
                    )
                ]

        register_rule(BrokenRule)
        register_rule(WorkingRule)

        # Should not raise an exception
        insights = compute_insights(self.team, self.target_date)

        # Should have created the insight from the working rule
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].title, "Working rule")

    def test_compute_insights_passes_correct_team_and_date(self):
        """Test that compute_insights passes the correct team and date to rules."""
        from apps.metrics.insights.engine import InsightRule, compute_insights, register_rule

        received_team = None
        received_date = None

        class TestRule(InsightRule):
            def evaluate(self, team, target_date):
                nonlocal received_team, received_date
                received_team = team
                received_date = target_date
                return []

        register_rule(TestRule)

        compute_insights(self.team, self.target_date)

        self.assertEqual(received_team, self.team)
        self.assertEqual(received_date, self.target_date)

    def test_compute_insights_with_rule_returning_multiple_results(self):
        """Test that a single rule can return multiple insights."""
        from apps.metrics.insights.engine import InsightResult, InsightRule, compute_insights, register_rule

        class MultiResultRule(InsightRule):
            def evaluate(self, team, target_date):
                return [
                    InsightResult(
                        category="trend",
                        priority="high",
                        title="First insight",
                        description="First description",
                        metric_type="cycle_time",
                    ),
                    InsightResult(
                        category="anomaly",
                        priority="medium",
                        title="Second insight",
                        description="Second description",
                        metric_type="review_time",
                    ),
                    InsightResult(
                        category="action",
                        priority="low",
                        title="Third insight",
                        description="Third description",
                        metric_type="pr_size",
                    ),
                ]

        register_rule(MultiResultRule)

        insights = compute_insights(self.team, self.target_date)

        self.assertEqual(len(insights), 3)
        self.assertEqual(insights[0].title, "First insight")
        self.assertEqual(insights[1].title, "Second insight")
        self.assertEqual(insights[2].title, "Third insight")
