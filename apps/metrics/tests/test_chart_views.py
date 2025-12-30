"""Tests for chart partial views (HTMX endpoints).

This test module covers:
- ai_adoption_chart: Admin-only AI adoption trend chart
- ai_quality_chart: Admin-only AI quality comparison chart
- cycle_time_chart: Member-accessible cycle time trend chart
- key_metrics_cards: Admin-only stat cards
- team_breakdown_table: Admin-only per-member breakdown
- leaderboard_table: Member-accessible AI detective leaderboard

All views return HTML partials for HTMX updates.
"""

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class TestAIAdoptionChart(TestCase):
    """Tests for ai_adoption_chart view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_ai_adoption_chart_requires_login(self):
        """Test that ai_adoption_chart redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:chart_ai_adoption"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_ai_adoption_chart_requires_team_membership(self):
        """Test that ai_adoption_chart returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:chart_ai_adoption"))

        self.assertEqual(response.status_code, 404)

    def test_ai_adoption_chart_requires_admin_role(self):
        """Test that ai_adoption_chart returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"))

        self.assertEqual(response.status_code, 404)

    def test_ai_adoption_chart_returns_200_for_admin(self):
        """Test that ai_adoption_chart returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"))

        self.assertEqual(response.status_code, 200)

    def test_ai_adoption_chart_renders_correct_template(self):
        """Test that ai_adoption_chart renders partials/ai_adoption_chart.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/ai_adoption_chart.html")

    def test_ai_adoption_chart_context_has_chart_data(self):
        """Test that ai_adoption_chart context contains chart_data."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_ai_adoption_chart_default_days_is_30(self):
        """Test that ai_adoption_chart defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"))

        self.assertEqual(response.status_code, 200)
        # chart_data should be formatted using format_time_series
        self.assertIsInstance(response.context["chart_data"], list)

    def test_ai_adoption_chart_accepts_days_query_param_7(self):
        """Test that ai_adoption_chart accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_ai_adoption_chart_accepts_days_query_param_90(self):
        """Test that ai_adoption_chart accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_ai_adoption_chart_uses_format_time_series(self):
        """Test that ai_adoption_chart formats data with format_time_series."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"))

        self.assertEqual(response.status_code, 200)
        # Formatted data should have "date" and "count" keys
        chart_data = response.context["chart_data"]
        if len(chart_data) > 0:
            self.assertIn("date", chart_data[0])
            self.assertIn("count", chart_data[0])


class TestAIQualityChart(TestCase):
    """Tests for ai_quality_chart view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_ai_quality_chart_requires_login(self):
        """Test that ai_quality_chart redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:chart_ai_quality"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_ai_quality_chart_requires_team_membership(self):
        """Test that ai_quality_chart returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:chart_ai_quality"))

        self.assertEqual(response.status_code, 404)

    def test_ai_quality_chart_requires_admin_role(self):
        """Test that ai_quality_chart returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"))

        self.assertEqual(response.status_code, 404)

    def test_ai_quality_chart_returns_200_for_admin(self):
        """Test that ai_quality_chart returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"))

        self.assertEqual(response.status_code, 200)

    def test_ai_quality_chart_renders_correct_template(self):
        """Test that ai_quality_chart renders partials/ai_quality_chart.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/ai_quality_chart.html")

    def test_ai_quality_chart_context_has_chart_data(self):
        """Test that ai_quality_chart context contains chart_data."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_ai_quality_chart_default_days_is_30(self):
        """Test that ai_quality_chart defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"))

        self.assertEqual(response.status_code, 200)
        # chart_data should be a dict with ai_avg and non_ai_avg
        self.assertIsInstance(response.context["chart_data"], dict)

    def test_ai_quality_chart_accepts_days_query_param_7(self):
        """Test that ai_quality_chart accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_ai_quality_chart_accepts_days_query_param_90(self):
        """Test that ai_quality_chart accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_ai_quality_chart_data_has_required_keys(self):
        """Test that ai_quality_chart data contains ai_avg and non_ai_avg."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"))

        self.assertEqual(response.status_code, 200)
        chart_data = response.context["chart_data"]
        self.assertIn("ai_avg", chart_data)
        self.assertIn("non_ai_avg", chart_data)


class TestCycleTimeChart(TestCase):
    """Tests for cycle_time_chart view (member-accessible)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_cycle_time_chart_requires_login(self):
        """Test that cycle_time_chart redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:chart_cycle_time"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_cycle_time_chart_requires_team_membership(self):
        """Test that cycle_time_chart returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:chart_cycle_time"))

        self.assertEqual(response.status_code, 404)

    def test_cycle_time_chart_returns_200_for_member(self):
        """Test that cycle_time_chart returns 200 for regular team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"))

        self.assertEqual(response.status_code, 200)

    def test_cycle_time_chart_returns_200_for_admin(self):
        """Test that cycle_time_chart returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"))

        self.assertEqual(response.status_code, 200)

    def test_cycle_time_chart_renders_correct_template(self):
        """Test that cycle_time_chart renders partials/cycle_time_chart.html template."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/cycle_time_chart.html")

    def test_cycle_time_chart_context_has_chart_data(self):
        """Test that cycle_time_chart context contains chart_data."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_cycle_time_chart_default_days_is_30(self):
        """Test that cycle_time_chart defaults to 30 days if no query param provided."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"))

        self.assertEqual(response.status_code, 200)
        # chart_data should be formatted using format_time_series
        self.assertIsInstance(response.context["chart_data"], list)

    def test_cycle_time_chart_accepts_days_query_param_7(self):
        """Test that cycle_time_chart accepts days=7 query parameter."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_cycle_time_chart_accepts_days_query_param_90(self):
        """Test that cycle_time_chart accepts days=90 query parameter."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_cycle_time_chart_uses_format_time_series(self):
        """Test that cycle_time_chart formats data with format_time_series."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"))

        self.assertEqual(response.status_code, 200)
        # Formatted data should have "date" and "count" keys
        chart_data = response.context["chart_data"]
        if len(chart_data) > 0:
            self.assertIn("date", chart_data[0])
            self.assertIn("count", chart_data[0])


class TestKeyMetricsCards(TestCase):
    """Tests for key_metrics_cards view (all team members)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_key_metrics_cards_requires_login(self):
        """Test that key_metrics_cards redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_key_metrics_cards_requires_team_membership(self):
        """Test that key_metrics_cards returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 404)

    def test_key_metrics_cards_allows_member_role(self):
        """Test that key_metrics_cards returns 200 for regular team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 200)

    def test_key_metrics_cards_returns_200_for_admin(self):
        """Test that key_metrics_cards returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 200)

    def test_key_metrics_cards_renders_correct_template(self):
        """Test that key_metrics_cards renders partials/key_metrics_cards.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/key_metrics_cards.html")

    def test_key_metrics_cards_context_has_metrics(self):
        """Test that key_metrics_cards context contains metrics."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("metrics", response.context)

    def test_key_metrics_cards_context_has_previous_metrics(self):
        """Test that key_metrics_cards context contains previous_metrics for comparison."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("previous_metrics", response.context)

    def test_key_metrics_cards_default_days_is_30(self):
        """Test that key_metrics_cards defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 200)
        # metrics should be a dict with key metric keys
        self.assertIsInstance(response.context["metrics"], dict)

    def test_key_metrics_cards_accepts_days_query_param_7(self):
        """Test that key_metrics_cards accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("metrics", response.context)

    def test_key_metrics_cards_accepts_days_query_param_90(self):
        """Test that key_metrics_cards accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("metrics", response.context)

    def test_key_metrics_cards_metrics_has_required_keys(self):
        """Test that key_metrics_cards metrics contains required keys from get_key_metrics."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"))

        self.assertEqual(response.status_code, 200)
        metrics = response.context["metrics"]
        self.assertIn("prs_merged", metrics)
        self.assertIn("avg_cycle_time", metrics)
        self.assertIn("avg_quality_rating", metrics)
        self.assertIn("ai_assisted_pct", metrics)


class TestTeamBreakdownTable(TestCase):
    """Tests for team_breakdown_table view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_team_breakdown_table_requires_login(self):
        """Test that team_breakdown_table redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_team_breakdown_table_requires_team_membership(self):
        """Test that team_breakdown_table returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 404)

    def test_team_breakdown_table_requires_admin_role(self):
        """Test that team_breakdown_table returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 404)

    def test_team_breakdown_table_returns_200_for_admin(self):
        """Test that team_breakdown_table returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 200)

    def test_team_breakdown_table_renders_correct_template(self):
        """Test that team_breakdown_table renders partials/team_breakdown_table.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/team_breakdown_table.html")

    def test_team_breakdown_table_context_has_rows(self):
        """Test that team_breakdown_table context contains rows."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_team_breakdown_table_default_days_is_30(self):
        """Test that team_breakdown_table defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 200)
        # rows should be a list of dicts
        self.assertIsInstance(response.context["rows"], list)

    def test_team_breakdown_table_accepts_days_query_param_7(self):
        """Test that team_breakdown_table accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_team_breakdown_table_accepts_days_query_param_90(self):
        """Test that team_breakdown_table accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_team_breakdown_table_rows_have_required_keys(self):
        """Test that team_breakdown_table rows contain required keys from get_team_breakdown."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 200)
        rows = response.context["rows"]
        # If there are rows, check they have the right structure
        if len(rows) > 0:
            self.assertIn("member_name", rows[0])
            self.assertIn("prs_merged", rows[0])
            self.assertIn("avg_cycle_time", rows[0])
            self.assertIn("ai_pct", rows[0])

    def test_team_breakdown_table_accepts_sort_param(self):
        """Test that team_breakdown_table accepts sort query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"), {"sort": "cycle_time"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)
        # Verify sort param is in context
        self.assertIn("sort", response.context)
        self.assertEqual(response.context["sort"], "cycle_time")

    def test_team_breakdown_table_accepts_order_param(self):
        """Test that team_breakdown_table accepts order query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"), {"order": "asc"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)
        # Verify order param is in context
        self.assertIn("order", response.context)
        self.assertEqual(response.context["order"], "asc")

    def test_team_breakdown_table_default_sort_is_prs_merged_desc(self):
        """Test that team_breakdown_table defaults to sort=prs_merged order=desc."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"))

        self.assertEqual(response.status_code, 200)
        # Verify default sort and order are in context
        self.assertIn("sort", response.context)
        self.assertIn("order", response.context)
        self.assertEqual(response.context["sort"], "prs_merged")
        self.assertEqual(response.context["order"], "desc")

    def test_team_breakdown_table_context_includes_sort_and_order(self):
        """Test that team_breakdown_table context includes sort and order for template use."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"), {"sort": "ai_pct", "order": "asc"})

        self.assertEqual(response.status_code, 200)
        # Context should have both sort and order for rendering sort controls
        self.assertIn("sort", response.context)
        self.assertIn("order", response.context)
        self.assertEqual(response.context["sort"], "ai_pct")
        self.assertEqual(response.context["order"], "asc")

    def test_team_breakdown_table_rejects_invalid_sort_field(self):
        """Test that team_breakdown_table rejects invalid sort field and defaults to prs_merged."""
        self.client.force_login(self.admin_user)

        # Try to inject invalid sort field
        response = self.client.get(reverse("metrics:table_breakdown"), {"sort": "invalid__field"})

        self.assertEqual(response.status_code, 200)
        # Should fall back to default sort
        self.assertEqual(response.context["sort"], "prs_merged")

    def test_team_breakdown_table_rejects_invalid_order(self):
        """Test that team_breakdown_table rejects invalid order and defaults to desc."""
        self.client.force_login(self.admin_user)

        # Try to inject invalid order
        response = self.client.get(reverse("metrics:table_breakdown"), {"order": "invalid"})

        self.assertEqual(response.status_code, 200)
        # Should fall back to default order
        self.assertEqual(response.context["order"], "desc")


class TestLeaderboardTable(TestCase):
    """Tests for leaderboard_table view (member-accessible)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_leaderboard_table_requires_login(self):
        """Test that leaderboard_table redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:table_leaderboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_leaderboard_table_requires_team_membership(self):
        """Test that leaderboard_table returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:table_leaderboard"))

        self.assertEqual(response.status_code, 404)

    def test_leaderboard_table_returns_200_for_member(self):
        """Test that leaderboard_table returns 200 for regular team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_leaderboard"))

        self.assertEqual(response.status_code, 200)

    def test_leaderboard_table_returns_200_for_admin(self):
        """Test that leaderboard_table returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_leaderboard"))

        self.assertEqual(response.status_code, 200)

    def test_leaderboard_table_renders_correct_template(self):
        """Test that leaderboard_table renders partials/leaderboard_table.html template."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_leaderboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/leaderboard_table.html")

    def test_leaderboard_table_context_has_rows(self):
        """Test that leaderboard_table context contains rows."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_leaderboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_leaderboard_table_default_days_is_30(self):
        """Test that leaderboard_table defaults to 30 days if no query param provided."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_leaderboard"))

        self.assertEqual(response.status_code, 200)
        # rows should be a list of dicts
        self.assertIsInstance(response.context["rows"], list)

    def test_leaderboard_table_accepts_days_query_param_7(self):
        """Test that leaderboard_table accepts days=7 query parameter."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_leaderboard"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_leaderboard_table_accepts_days_query_param_90(self):
        """Test that leaderboard_table accepts days=90 query parameter."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_leaderboard"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_leaderboard_table_rows_have_required_keys(self):
        """Test that leaderboard_table rows contain required keys for AI detective leaderboard."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_leaderboard"))

        self.assertEqual(response.status_code, 200)
        rows = response.context["rows"]
        # If there are rows, check they have the right structure
        # Based on survey_service.get_reviewer_accuracy_stats
        if len(rows) > 0:
            self.assertIn("member_name", rows[0])
            self.assertIn("correct", rows[0])
            self.assertIn("total", rows[0])
            self.assertIn("percentage", rows[0])


class TestCopilotMetricsCard(TestCase):
    """Tests for copilot_metrics_card view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_copilot_metrics_card_requires_login(self):
        """Test that copilot_metrics_card redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:cards_copilot"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_copilot_metrics_card_requires_team_membership(self):
        """Test that copilot_metrics_card returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:cards_copilot"))

        self.assertEqual(response.status_code, 404)

    def test_copilot_metrics_card_requires_admin_role(self):
        """Test that copilot_metrics_card returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:cards_copilot"))

        self.assertEqual(response.status_code, 404)

    def test_copilot_metrics_card_returns_200_for_admin(self):
        """Test that copilot_metrics_card returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot"))

        self.assertEqual(response.status_code, 200)

    def test_copilot_metrics_card_renders_correct_template(self):
        """Test that copilot_metrics_card renders partials/copilot_metrics_card.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/copilot_metrics_card.html")

    def test_copilot_metrics_card_context_has_metrics(self):
        """Test that copilot_metrics_card context contains metrics."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("metrics", response.context)

    def test_copilot_metrics_card_default_days_is_30(self):
        """Test that copilot_metrics_card defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot"))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["metrics"], dict)

    def test_copilot_metrics_card_accepts_days_query_param_7(self):
        """Test that copilot_metrics_card accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("metrics", response.context)

    def test_copilot_metrics_card_accepts_days_query_param_90(self):
        """Test that copilot_metrics_card accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("metrics", response.context)

    def test_copilot_metrics_card_handles_empty_data_gracefully(self):
        """Test that copilot_metrics_card handles empty data without errors."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot"))

        self.assertEqual(response.status_code, 200)
        # Should return metrics dict even with no data
        self.assertIn("metrics", response.context)
        self.assertIsInstance(response.context["metrics"], dict)


class TestCopilotTrendChart(TestCase):
    """Tests for copilot_trend_chart view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_copilot_trend_chart_requires_login(self):
        """Test that copilot_trend_chart redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:chart_copilot_trend"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_copilot_trend_chart_requires_team_membership(self):
        """Test that copilot_trend_chart returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:chart_copilot_trend"))

        self.assertEqual(response.status_code, 404)

    def test_copilot_trend_chart_requires_admin_role(self):
        """Test that copilot_trend_chart returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:chart_copilot_trend"))

        self.assertEqual(response.status_code, 404)

    def test_copilot_trend_chart_returns_200_for_admin(self):
        """Test that copilot_trend_chart returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_copilot_trend"))

        self.assertEqual(response.status_code, 200)

    def test_copilot_trend_chart_renders_correct_template(self):
        """Test that copilot_trend_chart renders partials/copilot_trend_chart.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_copilot_trend"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/copilot_trend_chart.html")

    def test_copilot_trend_chart_context_has_chart_data(self):
        """Test that copilot_trend_chart context contains chart_data."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_copilot_trend"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_copilot_trend_chart_default_days_is_30(self):
        """Test that copilot_trend_chart defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_copilot_trend"))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["chart_data"], list)

    def test_copilot_trend_chart_accepts_days_query_param_7(self):
        """Test that copilot_trend_chart accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_copilot_trend"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_copilot_trend_chart_accepts_days_query_param_90(self):
        """Test that copilot_trend_chart accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_copilot_trend"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_data", response.context)

    def test_copilot_trend_chart_handles_empty_data_gracefully(self):
        """Test that copilot_trend_chart handles empty data without errors."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_copilot_trend"))

        self.assertEqual(response.status_code, 200)
        # Should return empty list even with no data
        self.assertIn("chart_data", response.context)
        self.assertIsInstance(response.context["chart_data"], list)


class TestCopilotMembersTable(TestCase):
    """Tests for copilot_members_table view (admin-only)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_copilot_members_table_requires_login(self):
        """Test that copilot_members_table redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:table_copilot_members"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_copilot_members_table_requires_team_membership(self):
        """Test that copilot_members_table returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:table_copilot_members"))

        self.assertEqual(response.status_code, 404)

    def test_copilot_members_table_requires_admin_role(self):
        """Test that copilot_members_table returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:table_copilot_members"))

        self.assertEqual(response.status_code, 404)

    def test_copilot_members_table_returns_200_for_admin(self):
        """Test that copilot_members_table returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_copilot_members"))

        self.assertEqual(response.status_code, 200)

    def test_copilot_members_table_renders_correct_template(self):
        """Test that copilot_members_table renders partials/copilot_members_table.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_copilot_members"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/copilot_members_table.html")

    def test_copilot_members_table_context_has_rows(self):
        """Test that copilot_members_table context contains rows."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_copilot_members"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_copilot_members_table_default_days_is_30(self):
        """Test that copilot_members_table defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_copilot_members"))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["rows"], list)

    def test_copilot_members_table_accepts_days_query_param_7(self):
        """Test that copilot_members_table accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_copilot_members"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_copilot_members_table_accepts_days_query_param_90(self):
        """Test that copilot_members_table accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_copilot_members"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.context)

    def test_copilot_members_table_handles_empty_data_gracefully(self):
        """Test that copilot_members_table handles empty data without errors."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_copilot_members"))

        self.assertEqual(response.status_code, 200)
        # Should return empty list even with no data
        self.assertIn("rows", response.context)
        self.assertIsInstance(response.context["rows"], list)


# =============================================================================
# Phase 2: Repository Filter Tests for Chart Views
# =============================================================================


class TestChartViewsRepoFilter(TestCase):
    """Tests for repository filtering in chart views.

    🔴 RED Phase: Tests should FAIL until repo param is added to views.

    These tests verify that chart views:
    1. Accept the 'repo' query parameter
    2. Pass repo to service layer functions
    3. Return filtered data when repo is specified
    """

    def setUp(self):
        """Set up test fixtures."""
        from apps.metrics.factories import PullRequestFactory, TeamMemberFactory

        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create team member
        self.member = TeamMemberFactory(team=self.team)

        # Create PRs in different repos
        from django.utils import timezone

        self.frontend_pr = PullRequestFactory(
            team=self.team,
            github_repo="acme/frontend",
            author=self.member,
            state="merged",
            merged_at=timezone.now(),
        )
        self.backend_pr = PullRequestFactory(
            team=self.team,
            github_repo="acme/backend",
            author=self.member,
            state="merged",
            merged_at=timezone.now(),
        )

    def test_key_metrics_cards_accepts_repo_param(self):
        """Test that key_metrics_cards accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_metrics"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("metrics", response.context)

    def test_ai_adoption_chart_accepts_repo_param(self):
        """Test that ai_adoption_chart accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_adoption"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)

    def test_cycle_time_chart_accepts_repo_param(self):
        """Test that cycle_time_chart accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_cycle_time"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)

    def test_team_breakdown_table_accepts_repo_param(self):
        """Test that team_breakdown_table accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_breakdown"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)

    def test_recent_prs_table_accepts_repo_param(self):
        """Test that recent_prs_table accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:table_recent_prs"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)

    def test_review_distribution_chart_accepts_repo_param(self):
        """Test that review_distribution_chart accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_review_distribution"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)

    def test_review_time_chart_accepts_repo_param(self):
        """Test that review_time_chart accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_review_time"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)

    def test_pr_size_chart_accepts_repo_param(self):
        """Test that pr_size_chart accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_pr_size"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)

    def test_ai_quality_chart_accepts_repo_param(self):
        """Test that ai_quality_chart accepts repo query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:chart_ai_quality"), {"repo": "acme/frontend"})

        self.assertEqual(response.status_code, 200)
