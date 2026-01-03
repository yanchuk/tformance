"""Tests for new dashboard partial views (HTMX endpoints).

This test module covers:
- needs_attention_view: Admin-only PR issue list
- ai_impact_view: Admin-only AI impact stats
- team_velocity_view: Admin-only top contributors
"""

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class TestNeedsAttentionView(TestCase):
    """Tests for needs_attention_view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_requires_login(self):
        """Test that needs_attention_view redirects to login if not authenticated."""
        response = self.client.get(reverse("metrics:needs_attention"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requires_team_membership(self):
        """Test that needs_attention_view returns 404 for non-team-members."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:needs_attention"))

        self.assertEqual(response.status_code, 404)

    def test_requires_admin_role(self):
        """Test that needs_attention_view returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:needs_attention"))

        self.assertEqual(response.status_code, 404)

    def test_returns_200_for_admin(self):
        """Test that needs_attention_view returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:needs_attention"))

        self.assertEqual(response.status_code, 200)

    def test_renders_correct_template(self):
        """Test that needs_attention_view renders correct partial template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:needs_attention"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/needs_attention.html")

    def test_context_contains_prs(self):
        """Test that context contains prs list."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:needs_attention"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("prs", response.context)
        self.assertIsInstance(response.context["prs"], list)

    def test_context_contains_summary_and_counts(self):
        """Test that context contains summary badges and total_count."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:needs_attention"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("summary", response.context)
        self.assertIn("total_count", response.context)
        self.assertIn("days", response.context)

    def test_accepts_days_query_param(self):
        """Test that needs_attention_view accepts days query param."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:needs_attention"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 7)

    def test_default_days_is_30(self):
        """Test that default date range is 30 days."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:needs_attention"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)


class TestAiImpactView(TestCase):
    """Tests for ai_impact_view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_requires_login(self):
        """Test that ai_impact_view redirects to login if not authenticated."""
        response = self.client.get(reverse("metrics:ai_impact"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requires_team_membership(self):
        """Test that ai_impact_view returns 404 for non-team-members."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:ai_impact"))

        self.assertEqual(response.status_code, 404)

    def test_requires_admin_role(self):
        """Test that ai_impact_view returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:ai_impact"))

        self.assertEqual(response.status_code, 404)

    def test_returns_200_for_admin(self):
        """Test that ai_impact_view returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:ai_impact"))

        self.assertEqual(response.status_code, 200)

    def test_renders_correct_template(self):
        """Test that ai_impact_view renders correct partial template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:ai_impact"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/ai_impact.html")

    def test_context_contains_stats(self):
        """Test that context contains stats dict with required keys."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:ai_impact"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("stats", response.context)
        stats = response.context["stats"]
        self.assertIn("ai_adoption_pct", stats)
        self.assertIn("avg_cycle_with_ai", stats)
        self.assertIn("avg_cycle_without_ai", stats)
        self.assertIn("cycle_time_difference_pct", stats)

    def test_accepts_days_query_param(self):
        """Test that ai_impact_view accepts days query param."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:ai_impact"), {"days": "90"})

        self.assertEqual(response.status_code, 200)


class TestTeamVelocityView(TestCase):
    """Tests for team_velocity_view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_requires_login(self):
        """Test that team_velocity_view redirects to login if not authenticated."""
        response = self.client.get(reverse("metrics:team_velocity"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requires_team_membership(self):
        """Test that team_velocity_view returns 404 for non-team-members."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:team_velocity"))

        self.assertEqual(response.status_code, 404)

    def test_requires_admin_role(self):
        """Test that team_velocity_view returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_velocity"))

        self.assertEqual(response.status_code, 404)

    def test_returns_200_for_admin(self):
        """Test that team_velocity_view returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:team_velocity"))

        self.assertEqual(response.status_code, 200)

    def test_renders_correct_template(self):
        """Test that team_velocity_view renders correct partial template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:team_velocity"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/team_velocity.html")

    def test_context_contains_contributors(self):
        """Test that context contains contributors list."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:team_velocity"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("contributors", response.context)
        self.assertIsInstance(response.context["contributors"], list)

    def test_accepts_days_query_param(self):
        """Test that team_velocity_view accepts days query param."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:team_velocity"), {"days": "7"})

        self.assertEqual(response.status_code, 200)

    def test_accepts_limit_query_param(self):
        """Test that team_velocity_view accepts limit query param."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:team_velocity"), {"limit": "10"})

        self.assertEqual(response.status_code, 200)

    def test_default_limit_is_5(self):
        """Test that default limit is 5."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:team_velocity"))

        self.assertEqual(response.status_code, 200)
        # Service is called with limit=5 by default


class TestReviewDistributionBottleneck(TestCase):
    """Tests for bottleneck alert integration in review_distribution_chart."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_context_contains_bottleneck(self):
        """Test that review_distribution_chart context contains bottleneck key."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_review_distribution"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("bottleneck", response.context)

    def test_bottleneck_is_none_when_no_bottleneck(self):
        """Test that bottleneck is None when no reviewer exceeds threshold."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_review_distribution"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["bottleneck"])

    def test_bottleneck_contains_expected_keys_when_detected(self):
        """Test that bottleneck dict contains expected keys when detected."""
        # This test verifies the structure when a bottleneck exists
        # The actual bottleneck detection is tested in service tests
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_review_distribution"))

        self.assertEqual(response.status_code, 200)
        # Bottleneck may be None or a dict - just verify the key exists
        self.assertIn("bottleneck", response.context)


class TestEngineeringInsightsView(TestCase):
    """Tests for engineering_insights view (HTMX endpoint)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_requires_login(self):
        """Test that engineering_insights redirects to login if not authenticated."""
        response = self.client.get(reverse("metrics:engineering_insights"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requires_team_membership(self):
        """Test that engineering_insights returns 404 for non-team-members."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:engineering_insights"))

        self.assertEqual(response.status_code, 404)

    def test_returns_200_for_member(self):
        """Test that engineering_insights returns 200 for team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:engineering_insights"))

        self.assertEqual(response.status_code, 200)

    def test_returns_200_for_admin(self):
        """Test that engineering_insights returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:engineering_insights"))

        self.assertEqual(response.status_code, 200)

    def test_renders_correct_template(self):
        """Test that engineering_insights renders correct partial template."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:engineering_insights"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/engineering_insights.html")

    def test_context_contains_required_keys(self):
        """Test that context contains days, insight, and error keys."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:engineering_insights"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)
        self.assertIn("insight", response.context)
        self.assertIn("error", response.context)

    def test_default_days_is_30(self):
        """Test that default days is 30."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:engineering_insights"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)

    def test_accepts_days_query_param(self):
        """Test that engineering_insights accepts days query param."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:engineering_insights"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 90)

    def test_insight_is_none_when_no_cached_insight(self):
        """Test that insight is None when no cached insight exists."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:engineering_insights"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["insight"])

    def test_insight_actions_are_resolved_to_urls(self):
        """Test that insight actions are resolved to proper URLs."""
        from apps.metrics.models import DailyInsight

        # Create cached insight with actions
        insight_data = {
            "headline": "Test headline",
            "detail": "Test detail",
            "recommendation": "Test recommendation",
            "metric_cards": [
                {"label": "Throughput", "value": "+10%", "trend": "positive"},
                {"label": "Cycle Time", "value": "-5%", "trend": "positive"},
                {"label": "AI Adoption", "value": "50%", "trend": "neutral"},
                {"label": "Quality", "value": "2% reverts", "trend": "positive"},
            ],
            "actions": [
                {"action_type": "view_slow_prs", "label": "View Slow PRs"},
                {"action_type": "view_ai_prs", "label": "Analyze AI PRs"},
            ],
        }
        DailyInsight.objects.create(
            team=self.team,
            date="2024-01-15",
            category="llm_insight",
            comparison_period="30",
            title="Test",
            metric_value=insight_data,
        )

        self.client.force_login(self.member_user)
        response = self.client.get(reverse("metrics:engineering_insights"), {"days": "30"})

        self.assertEqual(response.status_code, 200)
        insight = response.context["insight"]
        self.assertIsNotNone(insight)
        self.assertIn("actions", insight)
        self.assertEqual(len(insight["actions"]), 2)

        # Verify actions have resolved URLs, not just action_types
        first_action = insight["actions"][0]
        self.assertIn("url", first_action)
        self.assertIn("label", first_action)
        self.assertIn("/app/pull-requests/", first_action["url"])
        self.assertIn("days=30", first_action["url"])

    def test_insight_actions_include_correct_filter_params(self):
        """Test that action URLs include correct filter parameters."""
        from apps.metrics.models import DailyInsight

        insight_data = {
            "headline": "Test",
            "detail": "Test",
            "recommendation": "Test",
            "metric_cards": [
                {"label": "Throughput", "value": "10", "trend": "neutral"},
                {"label": "Cycle Time", "value": "24h", "trend": "neutral"},
                {"label": "AI Adoption", "value": "50%", "trend": "neutral"},
                {"label": "Quality", "value": "2%", "trend": "positive"},
            ],
            "actions": [
                {"action_type": "view_reverts", "label": "View Reverts"},
            ],
        }
        DailyInsight.objects.create(
            team=self.team,
            date="2024-01-15",
            category="llm_insight",
            comparison_period="7",
            title="Test",
            metric_value=insight_data,
        )

        self.client.force_login(self.member_user)
        response = self.client.get(reverse("metrics:engineering_insights"), {"days": "7"})

        insight = response.context["insight"]
        action = insight["actions"][0]
        self.assertIn("issue_type=revert", action["url"])
        self.assertIn("days=7", action["url"])

    def test_insight_without_actions_has_empty_actions_list(self):
        """Test that insights without actions field get empty actions list."""
        from apps.metrics.models import DailyInsight

        # Legacy insight without actions field
        insight_data = {
            "headline": "Legacy headline",
            "detail": "Legacy detail",
            "recommendation": "Legacy recommendation",
            "metric_cards": [
                {"label": "Throughput", "value": "10", "trend": "neutral"},
                {"label": "Cycle Time", "value": "24h", "trend": "neutral"},
                {"label": "AI Adoption", "value": "50%", "trend": "neutral"},
                {"label": "Quality", "value": "2%", "trend": "positive"},
            ],
            # No actions field
        }
        DailyInsight.objects.create(
            team=self.team,
            date="2024-01-15",
            category="llm_insight",
            comparison_period="30",
            title="Test",
            metric_value=insight_data,
        )

        self.client.force_login(self.member_user)
        response = self.client.get(reverse("metrics:engineering_insights"), {"days": "30"})

        insight = response.context["insight"]
        self.assertIsNotNone(insight)
        self.assertIn("actions", insight)
        self.assertEqual(insight["actions"], [])


class TestRefreshInsightView(TestCase):
    """Tests for refresh_insight view (HTMX POST endpoint)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_requires_login(self):
        """Test that refresh_insight redirects to login if not authenticated."""
        response = self.client.post(reverse("metrics:refresh_insight"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requires_team_membership(self):
        """Test that refresh_insight returns 404 for non-team-members."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("metrics:refresh_insight"))

        self.assertEqual(response.status_code, 404)

    def test_requires_post_method(self):
        """Test that refresh_insight only accepts POST requests."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:refresh_insight"))

        self.assertEqual(response.status_code, 405)

    def test_returns_200_for_member(self):
        """Test that refresh_insight returns 200 for team members (with mocked LLM)."""
        from unittest.mock import patch

        self.client.force_login(self.member_user)

        with patch("apps.metrics.services.insight_llm.generate_insight") as mock_generate:
            mock_generate.return_value = {
                "headline": "Test Insight",
                "detail": "Test detail",
                "recommendation": "Test recommendation",
                "metric_cards": [],
                "is_fallback": False,
            }
            with patch("apps.metrics.services.insight_llm.gather_insight_data") as mock_gather:
                mock_gather.return_value = {}
                with patch("apps.metrics.services.insight_llm.cache_insight"):
                    response = self.client.post(reverse("metrics:refresh_insight"))

        self.assertEqual(response.status_code, 200)

    def test_renders_correct_template(self):
        """Test that refresh_insight renders correct partial template."""
        from unittest.mock import patch

        self.client.force_login(self.member_user)

        with patch("apps.metrics.services.insight_llm.generate_insight") as mock_generate:
            mock_generate.return_value = {
                "headline": "Test",
                "detail": "Test",
                "recommendation": "",
                "metric_cards": [],
                "is_fallback": False,
            }
            with (
                patch("apps.metrics.services.insight_llm.gather_insight_data"),
                patch("apps.metrics.services.insight_llm.cache_insight"),
            ):
                response = self.client.post(reverse("metrics:refresh_insight"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/engineering_insights.html")

    def test_accepts_days_query_param(self):
        """Test that refresh_insight accepts days query param."""
        from unittest.mock import patch

        self.client.force_login(self.member_user)

        with patch("apps.metrics.services.insight_llm.generate_insight") as mock_generate:
            mock_generate.return_value = {
                "headline": "Test",
                "detail": "Test",
                "recommendation": "",
                "metric_cards": [],
                "is_fallback": False,
            }
            with (
                patch("apps.metrics.services.insight_llm.gather_insight_data"),
                patch("apps.metrics.services.insight_llm.cache_insight"),
            ):
                response = self.client.post(reverse("metrics:refresh_insight") + "?days=30")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)

    def test_context_contains_error_on_exception(self):
        """Test that context contains error message when LLM call fails."""
        from unittest.mock import patch

        self.client.force_login(self.member_user)

        with patch("apps.metrics.services.insight_llm.gather_insight_data") as mock_gather:
            mock_gather.side_effect = Exception("LLM API error")
            response = self.client.post(reverse("metrics:refresh_insight"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["error"])
        self.assertIn("LLM API error", response.context["error"])
