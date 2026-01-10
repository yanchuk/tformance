"""Tests for LLM-powered insight generation service.

Tests for insight_llm.py service functions including:
- gather_insight_data: Collect all metrics into single dict for LLM prompt
- build_insight_prompt: Render Jinja2 template with data
- generate_insight: Call GROQ API and parse response
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


class TestGatherInsightData(TestCase):
    """Tests for gather_insight_data function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_dict_with_all_domains(self):
        """Test that gather_insight_data returns dict with velocity, quality, team_health, ai_impact."""
        from apps.metrics.services.insight_llm import gather_insight_data

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        # Verify all required domains are present
        self.assertIn("velocity", result)
        self.assertIn("quality", result)
        self.assertIn("team_health", result)
        self.assertIn("ai_impact", result)
        self.assertIn("metadata", result)

    def test_velocity_domain_structure(self):
        """Test that velocity domain has correct structure from get_velocity_comparison."""
        from apps.metrics.services.insight_llm import gather_insight_data

        # Create some PRs to get non-empty data
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        # Velocity should have throughput, cycle_time, review_time
        self.assertIn("throughput", result["velocity"])
        self.assertIn("cycle_time", result["velocity"])
        self.assertIn("review_time", result["velocity"])

    def test_quality_domain_structure(self):
        """Test that quality domain has correct structure from get_quality_metrics."""
        from apps.metrics.services.insight_llm import gather_insight_data

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        # Quality should have revert, hotfix, review_rounds, large_pr metrics
        self.assertIn("revert_count", result["quality"])
        self.assertIn("revert_rate", result["quality"])
        self.assertIn("hotfix_count", result["quality"])
        self.assertIn("avg_review_rounds", result["quality"])
        self.assertIn("large_pr_pct", result["quality"])

    def test_team_health_domain_structure(self):
        """Test that team_health domain has correct structure from get_team_health_metrics."""
        from apps.metrics.services.insight_llm import gather_insight_data

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        # Team health should have active_contributors, distributions, bottleneck
        self.assertIn("active_contributors", result["team_health"])
        self.assertIn("pr_distribution", result["team_health"])
        self.assertIn("review_distribution", result["team_health"])
        self.assertIn("bottleneck", result["team_health"])

    def test_ai_impact_domain_structure(self):
        """Test that ai_impact domain has correct structure from get_ai_impact_stats."""
        from apps.metrics.services.insight_llm import gather_insight_data

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        # AI impact should have comparison stats
        self.assertIn("ai_pr_count", result["ai_impact"])
        self.assertIn("non_ai_pr_count", result["ai_impact"])
        self.assertIn("ai_adoption_pct", result["ai_impact"])

    def test_metadata_includes_period_info(self):
        """Test that metadata includes period info for context."""
        from apps.metrics.services.insight_llm import gather_insight_data

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        # Metadata should include period info
        self.assertIn("start_date", result["metadata"])
        self.assertIn("end_date", result["metadata"])
        self.assertIn("days", result["metadata"])
        self.assertIn("team_name", result["metadata"])

        # Verify values
        self.assertEqual(result["metadata"]["start_date"], "2024-01-01")
        self.assertEqual(result["metadata"]["end_date"], "2024-01-31")
        self.assertEqual(result["metadata"]["days"], 30)

    def test_handles_missing_data_gracefully(self):
        """Test that returns valid structure even with no PRs in period."""
        from apps.metrics.services.insight_llm import gather_insight_data

        # No PRs created - should still return valid structure
        result = gather_insight_data(self.team, self.start_date, self.end_date)

        # Should not raise exceptions and have valid structure
        self.assertIsInstance(result, dict)
        self.assertIn("velocity", result)
        self.assertIn("quality", result)
        self.assertIn("team_health", result)
        self.assertIn("ai_impact", result)

    def test_filters_by_repo_when_provided(self):
        """Test that optional repo filter is passed through to all functions."""
        from apps.metrics.services.insight_llm import gather_insight_data

        # Create PRs in different repos
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            github_repo="org/frontend",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            github_repo="org/backend",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            cycle_time_hours=Decimal("48.0"),
        )

        # Filter by frontend only
        result = gather_insight_data(self.team, self.start_date, self.end_date, repo="org/frontend")

        # Velocity should only count 1 PR from frontend
        self.assertEqual(result["velocity"]["throughput"]["current"], 1)


class TestBuildInsightPrompt(TestCase):
    """Tests for build_insight_prompt function."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_data = {
            "velocity": {
                "throughput": {"current": 10, "previous": 8, "pct_change": 25.0},
                "cycle_time": {"current": Decimal("24.0"), "previous": Decimal("30.0"), "pct_change": -20.0},
                "review_time": {"current": Decimal("4.0"), "previous": Decimal("5.0"), "pct_change": -20.0},
            },
            "quality": {
                "revert_count": 1,
                "revert_rate": 10.0,
                "hotfix_count": 0,
                "hotfix_rate": 0.0,
                "avg_review_rounds": 1.5,
                "large_pr_pct": 20.0,
            },
            "team_health": {
                "active_contributors": 5,
                "pr_distribution": {"top_contributor_pct": 40.0, "is_concentrated": False},
                "review_distribution": {"avg_reviews_per_reviewer": 3.0, "max_reviews": 5},
                "bottleneck": None,
            },
            "ai_impact": {
                "ai_pr_count": 6,
                "non_ai_pr_count": 4,
                "ai_adoption_pct": 60.0,
                "ai_avg_cycle_time": Decimal("20.0"),
                "non_ai_avg_cycle_time": Decimal("30.0"),
                "cycle_time_difference_pct": Decimal("-33.3"),
            },
            "metadata": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "days": 30,
                "team_name": "Engineering",
            },
        }

    def test_renders_template_with_data(self):
        """Test that build_insight_prompt renders Jinja2 template."""
        from apps.metrics.services.insight_llm import build_insight_prompt

        result = build_insight_prompt(self.sample_data)

        # Should return a non-empty string
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 100)

    def test_includes_velocity_data_in_prompt(self):
        """Test that prompt includes velocity metrics."""
        from apps.metrics.services.insight_llm import build_insight_prompt

        result = build_insight_prompt(self.sample_data)

        # Should include velocity data in some form
        self.assertIn("throughput", result.lower())
        self.assertIn("cycle", result.lower())

    def test_includes_team_name_in_prompt(self):
        """Test that prompt includes team name for context."""
        from apps.metrics.services.insight_llm import build_insight_prompt

        result = build_insight_prompt(self.sample_data)

        # Should include team name
        self.assertIn("Engineering", result)


class TestGenerateInsight(TestCase):
    """Tests for generate_insight function.

    Tests GROQ API integration with mocked responses.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.sample_data = {
            "velocity": {
                "throughput": {"current": 10, "previous": 8, "pct_change": 25.0},
                "cycle_time": {"current": Decimal("24.0"), "previous": Decimal("30.0"), "pct_change": -20.0},
                "review_time": {"current": Decimal("4.0"), "previous": Decimal("5.0"), "pct_change": -20.0},
            },
            "quality": {
                "revert_count": 1,
                "revert_rate": 10.0,
                "hotfix_count": 0,
                "hotfix_rate": 0.0,
                "avg_review_rounds": 1.5,
                "large_pr_pct": 20.0,
            },
            "team_health": {
                "active_contributors": 5,
                "pr_distribution": {"top_contributor_pct": 40.0, "is_concentrated": False},
                "review_distribution": {"avg_reviews_per_reviewer": 3.0, "max_reviews": 5},
                "bottleneck": None,
            },
            "ai_impact": {
                "ai_pr_count": 6,
                "non_ai_pr_count": 4,
                "ai_adoption_pct": 60.0,
                "ai_avg_cycle_time": Decimal("20.0"),
                "non_ai_avg_cycle_time": Decimal("30.0"),
                "cycle_time_difference_pct": Decimal("-33.3"),
            },
            "metadata": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "days": 30,
                "team_name": "Engineering",
            },
        }

        # Expected response format from LLM
        self.mock_llm_response = {
            "headline": "Velocity up 25% with strong AI adoption driving faster cycles",
            "detail": "The team merged 10 PRs this period, up from 8 last period. "
            "AI-assisted PRs show 33% faster cycle times. "
            "No review bottlenecks detected.",
            "recommendation": "Continue current AI tool adoption while monitoring code quality metrics.",
            "metric_cards": [
                {"label": "Throughput", "value": "+25%", "trend": "positive"},
                {"label": "Cycle Time", "value": "-20%", "trend": "positive"},
                {"label": "AI Adoption", "value": "60%", "trend": "neutral"},
                {"label": "Quality", "value": "10% reverts", "trend": "warning"},
            ],
        }

    @patch("apps.metrics.services.insight_llm.Groq")
    def test_calls_groq_api(self, mock_groq_class):
        """Test that generate_insight calls GROQ API with correct parameters."""
        import json

        from apps.metrics.services.insight_llm import generate_insight

        # Configure mock
        mock_client = mock_groq_class.return_value
        mock_client.chat.completions.create.return_value.choices = [
            type("Choice", (), {"message": type("Message", (), {"content": json.dumps(self.mock_llm_response)})()})()
        ]

        # Call function
        generate_insight(self.sample_data)

        # Verify GROQ client was called
        mock_groq_class.assert_called_once()
        mock_client.chat.completions.create.assert_called_once()

        # Verify call parameters
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "openai/gpt-oss-120b")
        self.assertEqual(len(call_kwargs["messages"]), 2)  # system + user
        self.assertIn("json", call_kwargs["response_format"]["type"].lower())

    @patch("apps.metrics.services.insight_llm.Groq")
    def test_parses_json_response(self, mock_groq_class):
        """Test that generate_insight correctly parses JSON response."""
        import json

        from apps.metrics.services.insight_llm import generate_insight

        # Configure mock to return valid JSON
        mock_client = mock_groq_class.return_value
        mock_client.chat.completions.create.return_value.choices = [
            type("Choice", (), {"message": type("Message", (), {"content": json.dumps(self.mock_llm_response)})()})()
        ]

        # Call function
        result = generate_insight(self.sample_data)

        # Verify response is parsed correctly
        self.assertIsInstance(result, dict)
        self.assertIn("headline", result)
        self.assertIn("detail", result)
        self.assertIn("recommendation", result)
        self.assertIn("metric_cards", result)
        self.assertEqual(result["headline"], self.mock_llm_response["headline"])
        self.assertEqual(len(result["metric_cards"]), 4)

    @patch("apps.metrics.services.insight_llm.Groq")
    def test_falls_back_on_api_error(self, mock_groq_class):
        """Test that generate_insight falls back to rule-based on API error."""
        from apps.metrics.services.insight_llm import generate_insight

        # Configure mock to raise exception
        mock_client = mock_groq_class.return_value
        mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")

        # Call function - should not raise
        result = generate_insight(self.sample_data)

        # Verify fallback response is returned
        self.assertIsInstance(result, dict)
        self.assertIn("headline", result)
        self.assertIn("is_fallback", result)
        self.assertTrue(result["is_fallback"])

    @patch("apps.metrics.services.insight_llm.Groq")
    def test_falls_back_on_invalid_json(self, mock_groq_class):
        """Test that generate_insight falls back when LLM returns invalid JSON."""
        from apps.metrics.services.insight_llm import generate_insight

        # Configure mock to return invalid JSON
        mock_client = mock_groq_class.return_value
        mock_client.chat.completions.create.return_value.choices = [
            type("Choice", (), {"message": type("Message", (), {"content": "This is not valid JSON"})()})()
        ]

        # Call function - should not raise
        result = generate_insight(self.sample_data)

        # Verify fallback response is returned
        self.assertIsInstance(result, dict)
        self.assertIn("is_fallback", result)
        self.assertTrue(result["is_fallback"])

    @patch("apps.metrics.services.insight_llm.Groq")
    def test_falls_back_on_invalid_schema(self, mock_groq_class):
        """Test that generate_insight falls back when LLM returns valid JSON that doesn't match schema.

        This is a critical test - the LLM might return valid JSON that parses successfully
        but doesn't conform to the expected INSIGHT_RESPONSE_SCHEMA (e.g., missing required
        fields, wrong types, invalid enum values). We should validate and fall back gracefully.
        """
        import json

        from apps.metrics.services.insight_llm import generate_insight

        # Valid JSON but MISSING required fields (headline, detail, recommendation)
        # and has wrong structure for metric_cards
        invalid_schema_response = {
            "title": "Wrong field name",  # Should be 'headline'
            "body": "Wrong field name",  # Should be 'detail'
            "suggestion": "Wrong field name",  # Should be 'recommendation'
            "cards": [],  # Wrong field name and wrong count (should be 'metric_cards' with exactly 4 items)
        }

        # Configure mock to return valid JSON that doesn't match schema
        mock_client = mock_groq_class.return_value
        mock_client.chat.completions.create.return_value.choices = [
            type(
                "Choice",
                (),
                {"message": type("Message", (), {"content": json.dumps(invalid_schema_response)})()},
            )()
        ]

        # Call function - should not raise
        result = generate_insight(self.sample_data)

        # Verify fallback response is returned due to schema validation failure
        self.assertIsInstance(result, dict)
        self.assertIn("is_fallback", result)
        self.assertTrue(result["is_fallback"], "Expected fallback due to invalid schema, but got LLM response")


class TestCacheInsight(TestCase):
    """Tests for cache_insight function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.insight_data = {
            "headline": "Velocity up 25% with strong AI adoption",
            "detail": "The team merged 10 PRs this period.",
            "recommendation": "Continue current practices.",
            "metric_cards": [
                {"label": "Throughput", "value": "+25%", "trend": "positive"},
                {"label": "Cycle Time", "value": "-20%", "trend": "positive"},
                {"label": "AI Adoption", "value": "60%", "trend": "neutral"},
                {"label": "Quality", "value": "10% reverts", "trend": "warning"},
            ],
            "is_fallback": False,
        }
        self.target_date = date(2024, 1, 15)

    def test_creates_daily_insight(self):
        """Test that cache_insight creates a DailyInsight record."""
        from apps.metrics.models import DailyInsight
        from apps.metrics.services.insight_llm import cache_insight

        result = cache_insight(
            team=self.team,
            insight=self.insight_data,
            target_date=self.target_date,
            days=7,
        )

        # Verify a DailyInsight was created
        self.assertIsInstance(result, DailyInsight)
        self.assertEqual(result.team, self.team)
        self.assertEqual(result.date, self.target_date)
        self.assertEqual(result.category, "llm_insight")
        self.assertEqual(result.comparison_period, "7")  # days as string
        self.assertEqual(result.title, self.insight_data["headline"])

    def test_stores_full_response_in_metric_value(self):
        """Test that the full LLM response is stored in metric_value."""
        from apps.metrics.services.insight_llm import cache_insight

        result = cache_insight(
            team=self.team,
            insight=self.insight_data,
            target_date=self.target_date,
            days=30,
        )

        # Verify metric_value contains the full response
        self.assertIsInstance(result.metric_value, dict)
        self.assertIn("headline", result.metric_value)
        self.assertIn("detail", result.metric_value)
        self.assertIn("recommendation", result.metric_value)
        self.assertIn("metric_cards", result.metric_value)
        self.assertEqual(result.metric_value["headline"], self.insight_data["headline"])

    def test_updates_existing_insight(self):
        """Test that cache_insight updates existing record for same team/date/days."""
        from apps.metrics.models import DailyInsight
        from apps.metrics.services.insight_llm import cache_insight

        # Create first insight
        first = cache_insight(
            team=self.team,
            insight=self.insight_data,
            target_date=self.target_date,
            days=7,
        )

        # Create updated insight data
        updated_data = {
            **self.insight_data,
            "headline": "Updated headline",
        }

        # Update with new data
        second = cache_insight(
            team=self.team,
            insight=updated_data,
            target_date=self.target_date,
            days=7,
        )

        # Should update existing, not create new
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.metric_value["headline"], "Updated headline")

        # Verify only one record exists
        count = DailyInsight.objects.filter(
            team=self.team,
            date=self.target_date,
            category="llm_insight",
            comparison_period="7",
        ).count()
        self.assertEqual(count, 1)

    def test_different_days_are_separate(self):
        """Test that 7-day and 30-day insights are stored separately."""
        from apps.metrics.models import DailyInsight
        from apps.metrics.services.insight_llm import cache_insight

        # Create 7-day insight
        seven_day = cache_insight(
            team=self.team,
            insight=self.insight_data,
            target_date=self.target_date,
            days=7,
        )

        # Create 30-day insight
        thirty_day_data = {**self.insight_data, "headline": "30-day headline"}
        thirty_day = cache_insight(
            team=self.team,
            insight=thirty_day_data,
            target_date=self.target_date,
            days=30,
        )

        # Should be different records
        self.assertNotEqual(seven_day.id, thirty_day.id)
        self.assertEqual(seven_day.comparison_period, "7")
        self.assertEqual(thirty_day.comparison_period, "30")

        # Verify both exist
        count = DailyInsight.objects.filter(
            team=self.team,
            date=self.target_date,
            category="llm_insight",
        ).count()
        self.assertEqual(count, 2)


class TestResolveActionUrl(TestCase):
    """Tests for resolve_action_url function.

    Tests that action_type + days are converted to proper PR list URLs.
    """

    def test_view_ai_prs_action(self):
        """Test that view_ai_prs action generates correct URL."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "view_ai_prs", "label": "View AI PRs"}
        result = resolve_action_url(action, days=30)

        self.assertEqual(result, "/app/pull-requests/?days=30&ai=yes")

    def test_view_non_ai_prs_action(self):
        """Test that view_non_ai_prs action generates correct URL."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "view_non_ai_prs", "label": "View Non-AI PRs"}
        result = resolve_action_url(action, days=30)

        self.assertEqual(result, "/app/pull-requests/?days=30&ai=no")

    def test_view_slow_prs_action(self):
        """Test that view_slow_prs action generates correct URL."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "view_slow_prs", "label": "View Slow PRs"}
        result = resolve_action_url(action, days=7)

        self.assertEqual(result, "/app/pull-requests/?days=7&issue_type=long_cycle")

    def test_view_reverts_action(self):
        """Test that view_reverts action generates correct URL."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "view_reverts", "label": "View Reverts"}
        result = resolve_action_url(action, days=90)

        self.assertEqual(result, "/app/pull-requests/?days=90&issue_type=revert")

    def test_view_large_prs_action(self):
        """Test that view_large_prs action generates correct URL."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "view_large_prs", "label": "View Large PRs"}
        result = resolve_action_url(action, days=30)

        self.assertEqual(result, "/app/pull-requests/?days=30&issue_type=large_pr")

    def test_view_contributors_action(self):
        """Test that view_contributors action goes to analytics team page."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "view_contributors", "label": "View Contributors"}
        result = resolve_action_url(action, days=30)

        # Should go to analytics team page, not PR list
        self.assertEqual(result, "/app/metrics/analytics/team/?days=30")

    def test_view_review_bottlenecks_action(self):
        """Test that view_review_bottlenecks action filters open PRs by review time."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "view_review_bottlenecks", "label": "View Bottlenecks"}
        result = resolve_action_url(action, days=30)

        # Should go to PR list filtered by open state, sorted by review time
        self.assertIn("/app/pull-requests/", result)
        self.assertIn("state=open", result)
        self.assertIn("sort=review_time", result)
        self.assertIn("order=desc", result)

    def test_unknown_action_type_returns_base_url(self):
        """Test that unknown action_type returns base PR list URL."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "unknown_action", "label": "Unknown"}
        result = resolve_action_url(action, days=30)

        # Should still return valid URL with just days parameter
        self.assertEqual(result, "/app/pull-requests/?days=30")

    def test_different_days_values(self):
        """Test that days parameter is correctly included in URL."""
        from apps.metrics.services.insight_llm import resolve_action_url

        action = {"action_type": "view_ai_prs", "label": "View AI PRs"}

        # Test 7 days
        result_7 = resolve_action_url(action, days=7)
        self.assertIn("days=7", result_7)

        # Test 90 days
        result_90 = resolve_action_url(action, days=90)
        self.assertIn("days=90", result_90)


class TestInsightJsonSchemaActions(TestCase):
    """Tests for actions field in INSIGHT_JSON_SCHEMA."""

    def test_schema_includes_actions_field(self):
        """Test that INSIGHT_JSON_SCHEMA includes actions field."""
        from apps.metrics.services.insight_llm import INSIGHT_JSON_SCHEMA

        self.assertIn("actions", INSIGHT_JSON_SCHEMA["properties"])

    def test_actions_field_is_array(self):
        """Test that actions field is defined as an array."""
        from apps.metrics.services.insight_llm import INSIGHT_JSON_SCHEMA

        actions_schema = INSIGHT_JSON_SCHEMA["properties"]["actions"]
        self.assertEqual(actions_schema["type"], "array")

    def test_actions_item_has_required_fields(self):
        """Test that action items require action_type and label."""
        from apps.metrics.services.insight_llm import INSIGHT_JSON_SCHEMA

        item_schema = INSIGHT_JSON_SCHEMA["properties"]["actions"]["items"]
        self.assertIn("action_type", item_schema["properties"])
        self.assertIn("label", item_schema["properties"])
        self.assertIn("action_type", item_schema["required"])
        self.assertIn("label", item_schema["required"])

    def test_action_type_has_valid_enum(self):
        """Test that action_type uses enum with predefined values."""
        from apps.metrics.services.insight_llm import INSIGHT_JSON_SCHEMA

        action_type_schema = INSIGHT_JSON_SCHEMA["properties"]["actions"]["items"]["properties"]["action_type"]
        self.assertIn("enum", action_type_schema)
        expected_types = {
            "view_ai_prs",
            "view_non_ai_prs",
            "view_slow_prs",
            "view_reverts",
            "view_large_prs",
            "view_contributors",
            "view_review_bottlenecks",
        }
        self.assertEqual(set(action_type_schema["enum"]), expected_types)

    def test_actions_min_max_items(self):
        """Test that actions array has 2-3 items constraint."""
        from apps.metrics.services.insight_llm import INSIGHT_JSON_SCHEMA

        actions_schema = INSIGHT_JSON_SCHEMA["properties"]["actions"]
        self.assertEqual(actions_schema["minItems"], 2)
        self.assertEqual(actions_schema["maxItems"], 3)


class TestGatherInsightDataWithJira(TestCase):
    """Tests for Jira data in gather_insight_data function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_gather_insight_data_includes_jira_when_connected(self):
        """Should include jira section when JiraIntegration exists."""
        from apps.integrations.factories import (
            IntegrationCredentialFactory,
            JiraIntegrationFactory,
        )
        from apps.metrics.services.insight_llm import gather_insight_data

        # Create Jira integration
        credential = IntegrationCredentialFactory(team=self.team, provider="jira")
        JiraIntegrationFactory(team=self.team, credential=credential)

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        self.assertIn("jira", result)
        self.assertIsNotNone(result["jira"])

    def test_gather_insight_data_excludes_jira_when_not_connected(self):
        """Should set jira=None when no JiraIntegration."""
        from apps.metrics.services.insight_llm import gather_insight_data

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        self.assertIn("jira", result)
        self.assertIsNone(result["jira"])

    def test_gather_insight_data_jira_has_sprint_metrics(self):
        """Jira section should include sprint_metrics with issues and points."""
        from apps.integrations.factories import (
            IntegrationCredentialFactory,
            JiraIntegrationFactory,
        )
        from apps.metrics.factories import JiraIssueFactory
        from apps.metrics.services.insight_llm import gather_insight_data

        # Create Jira integration and issues
        credential = IntegrationCredentialFactory(team=self.team, provider="jira")
        JiraIntegrationFactory(team=self.team, credential=credential)
        JiraIssueFactory(
            team=self.team,
            assignee=self.member1,
            status="Done",
            resolved_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        self.assertIn("sprint_metrics", result["jira"])
        self.assertIn("issues_resolved", result["jira"]["sprint_metrics"])

    def test_gather_insight_data_jira_has_pr_correlation(self):
        """Jira section should include pr_correlation with linkage rate."""
        from apps.integrations.factories import (
            IntegrationCredentialFactory,
            JiraIntegrationFactory,
        )
        from apps.metrics.services.insight_llm import gather_insight_data

        # Create Jira integration
        credential = IntegrationCredentialFactory(team=self.team, provider="jira")
        JiraIntegrationFactory(team=self.team, credential=credential)

        # Create PRs with/without Jira links
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            jira_key="PROJ-123",
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = gather_insight_data(self.team, self.start_date, self.end_date)

        self.assertIn("pr_correlation", result["jira"])
        self.assertIn("linkage_rate", result["jira"]["pr_correlation"])
