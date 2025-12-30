"""Tests for trends analytics views."""

from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class TestTrendsOverviewView(TestCase):
    """Tests for trends_overview view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()

    def test_trends_overview_requires_login(self):
        """Test that trends overview requires authentication."""
        url = reverse("metrics:trends_overview")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_trends_overview_requires_admin(self):
        """Test that trends overview requires admin role."""
        self.client.force_login(self.member_user)
        url = reverse("metrics:trends_overview")
        response = self.client.get(url)
        # Returns 404 for non-admin team members
        self.assertEqual(response.status_code, 404)

    def test_trends_overview_returns_200(self):
        """Test that trends overview page returns 200."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_trends_overview_uses_correct_template(self):
        """Test that trends overview uses the correct template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")
        response = self.client.get(url)
        self.assertTemplateUsed(response, "metrics/analytics/trends.html")

    def test_trends_overview_context_has_required_keys(self):
        """Test that context contains required keys."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")
        response = self.client.get(url)

        self.assertIn("active_page", response.context)
        self.assertEqual(response.context["active_page"], "trends")
        self.assertIn("days", response.context)
        self.assertIn("start_date", response.context)
        self.assertIn("end_date", response.context)
        self.assertIn("granularity", response.context)

    def test_trends_overview_with_preset_param(self):
        """Test that preset parameter is processed correctly."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")
        response = self.client.get(f"{url}?preset=this_year")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["preset"], "this_year")

    def test_trends_overview_with_custom_date_range(self):
        """Test that custom date range is processed correctly."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")
        response = self.client.get(f"{url}?start=2024-01-01&end=2024-12-31")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["start_date"], date(2024, 1, 1))
        self.assertEqual(response.context["end_date"], date(2024, 12, 31))

    def test_trends_overview_htmx_returns_partial(self):
        """Test that HTMX request returns partial content."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        # Partial should not have full HTML structure
        self.assertNotContains(response, "<html")


class TestTrendChartDataView(TestCase):
    """Tests for trend chart data endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()

    def test_trend_chart_data_returns_200(self):
        """Test that trend chart data endpoint returns 200."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_trend")
        response = self.client.get(f"{url}?metric=cycle_time")
        self.assertEqual(response.status_code, 200)

    def test_trend_chart_data_returns_json(self):
        """Test that endpoint returns JSON response."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_trend")
        response = self.client.get(f"{url}?metric=cycle_time")
        self.assertEqual(response["Content-Type"], "application/json")

    def test_trend_chart_data_has_labels_and_data(self):
        """Test that response contains required chart.js data structure."""
        # Create some PRs with cycle time
        PullRequestFactory(team=self.team, state="merged", cycle_time_hours=10.0)

        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_trend")
        response = self.client.get(f"{url}?metric=cycle_time&days=30")
        data = response.json()

        self.assertIn("labels", data)
        self.assertIn("datasets", data)
        self.assertIsInstance(data["labels"], list)
        self.assertIsInstance(data["datasets"], list)

    def test_trend_chart_data_with_comparison(self):
        """Test that comparison data is included when preset=yoy."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_trend")
        response = self.client.get(f"{url}?metric=cycle_time&preset=yoy")
        data = response.json()

        # Should have 2 datasets (current + comparison)
        self.assertEqual(len(data["datasets"]), 2)

    def test_trend_chart_data_supports_all_metrics(self):
        """Test that all metric types are supported."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_trend")

        for metric in ["cycle_time", "review_time", "pr_count", "ai_adoption"]:
            response = self.client.get(f"{url}?metric={metric}")
            self.assertEqual(response.status_code, 200, f"Failed for metric: {metric}")

    def test_trend_chart_data_respects_granularity(self):
        """Test that granularity parameter is respected."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_trend")

        # Monthly granularity
        response = self.client.get(f"{url}?metric=cycle_time&preset=this_year")
        self.assertEqual(response.status_code, 200)
        # Long ranges should have monthly granularity
        data = response.json()
        self.assertIn("granularity", data)


class TestWideTrendChartView(TestCase):
    """Tests for wide trend chart partial view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()

    def test_wide_chart_partial_returns_200(self):
        """Test that wide chart partial returns 200."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_wide_trend")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_wide_chart_partial_uses_correct_template(self):
        """Test that wide chart partial uses correct template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_wide_trend")
        response = self.client.get(url)
        self.assertTemplateUsed(response, "metrics/analytics/trends/wide_chart.html")

    def test_wide_chart_partial_has_chart_data(self):
        """Test that context contains chart data."""
        PullRequestFactory(team=self.team, state="merged", cycle_time_hours=15.0)

        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_wide_trend")
        response = self.client.get(f"{url}?metric=cycle_time")

        self.assertIn("chart_data", response.context)
        self.assertIn("metric", response.context)

    def test_wide_chart_respects_metric_param(self):
        """Test that metric parameter is respected."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_wide_trend")
        response = self.client.get(f"{url}?metric=ai_adoption")

        self.assertEqual(response.context["metric"], "ai_adoption")


class TestTrendsTabNavigation(TestCase):
    """Tests for trends tab integration in analytics navigation."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

    def test_trends_link_in_analytics_navigation(self):
        """Test that Trends tab appears in analytics navigation."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_overview")
        response = self.client.get(url)

        # Check that trends link is in the response
        trends_url = reverse("metrics:trends_overview")
        self.assertContains(response, trends_url)

    def test_trends_tab_active_state(self):
        """Test that trends tab shows active state on trends page."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")
        response = self.client.get(url)

        # Check that active_page is 'trends'
        self.assertEqual(response.context["active_page"], "trends")


class TestTrendsURLParameters(TestCase):
    """Tests for URL parameter handling in trends views."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

    def test_granularity_parameter_in_context(self):
        """Test that granularity parameter is passed to context."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        # Test monthly granularity
        response = self.client.get(f"{url}?granularity=monthly")
        self.assertEqual(response.context["granularity"], "monthly")

        # Test weekly granularity
        response = self.client.get(f"{url}?granularity=weekly")
        self.assertEqual(response.context["granularity"], "weekly")

    def test_metrics_parameter_in_context(self):
        """Test that metrics parameter is passed to context."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        # Single metric
        response = self.client.get(f"{url}?metrics=cycle_time")
        self.assertIn("cycle_time", response.context["selected_metrics"])

        # Multiple metrics
        response = self.client.get(f"{url}?metrics=cycle_time,review_time")
        self.assertIn("cycle_time", response.context["selected_metrics"])
        self.assertIn("review_time", response.context["selected_metrics"])

    def test_preset_and_granularity_both_in_context(self):
        """Test that preset and granularity can be used together."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        response = self.client.get(f"{url}?preset=this_year&granularity=monthly")
        self.assertEqual(response.context["preset"], "this_year")
        self.assertEqual(response.context["granularity"], "monthly")

    def test_all_parameters_preserved(self):
        """Test that all parameters are available in context."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        response = self.client.get(f"{url}?preset=this_year&granularity=monthly&metrics=cycle_time,ai_adoption")

        self.assertEqual(response.context["preset"], "this_year")
        self.assertEqual(response.context["granularity"], "monthly")
        self.assertIn("cycle_time", response.context["selected_metrics"])
        self.assertIn("ai_adoption", response.context["selected_metrics"])

    def test_invalid_granularity_defaults_to_auto(self):
        """Test that invalid granularity parameter is handled gracefully."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        response = self.client.get(f"{url}?granularity=invalid")
        # Should still return 200 and have a valid granularity
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.context["granularity"], ["weekly", "monthly"])

    def test_wide_chart_respects_all_parameters(self):
        """Test that wide chart partial respects all URL parameters."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_wide_trend")

        response = self.client.get(f"{url}?preset=this_year&granularity=monthly&metrics=cycle_time,review_time")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["granularity"], "monthly")
        self.assertIn("cycle_time", response.context["metrics"])
        self.assertIn("review_time", response.context["metrics"])

    def test_days_parameter_overrides_preset(self):
        """Test that days parameter takes precedence when both present."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        # When days is present, it should be used for calculations
        response = self.client.get(f"{url}?days=30")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)


class TestTrendsDefaultBehavior(TestCase):
    """Tests for default behavior when no parameters are provided."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

    def test_trends_defaults_to_365_days_when_no_params(self):
        """Test that trends page defaults to 365 days (12 months) when no params."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        # No date params
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 365)

    def test_trends_defaults_to_monthly_granularity_when_no_params(self):
        """Test that trends page defaults to monthly granularity when no params."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        response = self.client.get(url)
        self.assertEqual(response.context["granularity"], "monthly")

    def test_trends_respects_explicit_params_over_defaults(self):
        """Test that explicit params override the 365 day default."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:trends_overview")

        # With explicit days param
        response = self.client.get(f"{url}?days=30")
        self.assertEqual(response.context["days"], 30)

        # With explicit preset param
        response = self.client.get(f"{url}?preset=this_quarter")
        self.assertEqual(response.context["preset"], "this_quarter")


class TestTechConfig(TestCase):
    """Tests for TECH_CONFIG configuration."""

    def test_tech_config_includes_chore_category(self):
        """Test that TECH_CONFIG includes 'chore' category."""
        from apps.metrics.views.trends_views import TECH_CONFIG

        self.assertIn("chore", TECH_CONFIG)
        self.assertIn("name", TECH_CONFIG["chore"])
        self.assertIn("color", TECH_CONFIG["chore"])

    def test_tech_config_includes_ci_category(self):
        """Test that TECH_CONFIG includes 'ci' category."""
        from apps.metrics.views.trends_views import TECH_CONFIG

        self.assertIn("ci", TECH_CONFIG)
        self.assertIn("name", TECH_CONFIG["ci"])
        self.assertIn("color", TECH_CONFIG["ci"])

    def test_tech_config_has_all_expected_categories(self):
        """Test that TECH_CONFIG has all expected tech categories."""
        from apps.metrics.views.trends_views import TECH_CONFIG

        expected = [
            "frontend",
            "backend",
            "devops",
            "mobile",
            "data",
            "test",
            "docs",
            "config",
            "javascript",
            "other",
            "chore",
            "ci",
        ]
        for category in expected:
            self.assertIn(category, TECH_CONFIG, f"Missing category: {category}")


class TestTechBreakdownChartAIFilter(TestCase):
    """Tests for AI Assisted filter on tech breakdown chart view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

    def test_tech_chart_accepts_ai_filter_parameter(self):
        """Test that tech chart view accepts ai_filter query parameter."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")
        response = self.client.get(f"{url}?ai_filter=yes")
        self.assertEqual(response.status_code, 200)

    def test_tech_chart_passes_ai_filter_to_context(self):
        """Test that ai_filter parameter is passed to template context."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")
        response = self.client.get(f"{url}?ai_filter=no")
        self.assertIn("ai_filter", response.context)
        self.assertEqual(response.context["ai_filter"], "no")

    def test_tech_chart_defaults_ai_filter_to_all(self):
        """Test that ai_filter defaults to 'all' when not provided."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")
        response = self.client.get(url)
        self.assertIn("ai_filter", response.context)
        self.assertEqual(response.context["ai_filter"], "all")

    def test_tech_chart_validates_ai_filter_values(self):
        """Test that invalid ai_filter values are handled gracefully."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")
        response = self.client.get(f"{url}?ai_filter=invalid")
        # Should still return 200, defaulting to 'all'
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["ai_filter"], "all")


class TestTechBreakdownChartGranularity(TestCase):
    """Tests for granularity handling in tech breakdown chart view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()

        # Create some merged PRs with tech categories for the test data
        # Use dates within last 30 days for weekly granularity
        from datetime import timedelta

        from django.utils import timezone

        from apps.metrics.factories import PRFileFactory

        now = timezone.now()
        for i in range(5):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                pr_created_at=now - timedelta(days=i + 1),
                merged_at=now - timedelta(days=i),
            )
            # Add a file to each PR so tech categories are populated
            PRFileFactory(team=self.team, pull_request=pr, filename=f"src/components/Component{i}.tsx")

    def test_tech_chart_accepts_granularity_parameter(self):
        """Test that tech chart view accepts granularity query parameter."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")
        response = self.client.get(f"{url}?granularity=weekly")
        self.assertEqual(response.status_code, 200)

    def test_tech_chart_passes_granularity_to_context(self):
        """Test that granularity parameter is passed to template context."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")

        # Test weekly granularity
        response = self.client.get(f"{url}?granularity=weekly&days=30")
        self.assertIn("granularity", response.context)
        self.assertEqual(response.context["granularity"], "weekly")

        # Test monthly granularity
        response = self.client.get(f"{url}?granularity=monthly&days=30")
        self.assertIn("granularity", response.context)
        self.assertEqual(response.context["granularity"], "monthly")

    def test_tech_chart_weekly_returns_weekly_labels(self):
        """Test that weekly granularity returns week-formatted labels in chart data."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")
        response = self.client.get(f"{url}?granularity=weekly&days=30")

        self.assertEqual(response.status_code, 200)
        chart_data = response.context["chart_data"]

        # Labels should be week format (e.g., "2024-W01")
        if chart_data["labels"]:
            for label in chart_data["labels"]:
                self.assertRegex(label, r"^\d{4}-W\d{2}$", f"Weekly label '{label}' should match format YYYY-WNN")

    def test_tech_chart_monthly_returns_monthly_labels(self):
        """Test that monthly granularity returns month-formatted labels in chart data."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")
        response = self.client.get(f"{url}?granularity=monthly&days=365")

        self.assertEqual(response.status_code, 200)
        chart_data = response.context["chart_data"]

        # Labels should be month format (e.g., "2024-01")
        if chart_data["labels"]:
            for label in chart_data["labels"]:
                self.assertRegex(label, r"^\d{4}-\d{2}$", f"Monthly label '{label}' should match format YYYY-MM")

    def test_tech_chart_different_granularity_different_labels(self):
        """Test that weekly and monthly granularity produce different label formats."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_tech_breakdown")

        # Get weekly data
        weekly_response = self.client.get(f"{url}?granularity=weekly&days=30")
        weekly_labels = weekly_response.context["chart_data"]["labels"]

        # Get monthly data
        monthly_response = self.client.get(f"{url}?granularity=monthly&days=30")
        monthly_labels = monthly_response.context["chart_data"]["labels"]

        # If we have data in both, labels should have different formats
        if weekly_labels and monthly_labels:
            # Weekly: "2024-W01", Monthly: "2024-01"
            self.assertNotEqual(
                weekly_labels[0], monthly_labels[0], "Weekly and monthly labels should have different formats"
            )


class TestPRTypeBreakdownChartGranularity(TestCase):
    """Tests for granularity handling in PR type breakdown chart view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()

        # Create some merged PRs for the test data
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()
        for i in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                pr_created_at=now - timedelta(days=i + 1),
                merged_at=now - timedelta(days=i),
            )

    def test_pr_type_chart_accepts_granularity_parameter(self):
        """Test that PR type chart view accepts granularity query parameter."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_pr_type_breakdown")
        response = self.client.get(f"{url}?granularity=weekly")
        self.assertEqual(response.status_code, 200)

    def test_pr_type_chart_passes_granularity_to_context(self):
        """Test that granularity parameter is passed to template context."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_pr_type_breakdown")

        # Test weekly granularity
        response = self.client.get(f"{url}?granularity=weekly&days=30")
        self.assertIn("granularity", response.context)
        self.assertEqual(response.context["granularity"], "weekly")

        # Test monthly granularity
        response = self.client.get(f"{url}?granularity=monthly&days=30")
        self.assertIn("granularity", response.context)
        self.assertEqual(response.context["granularity"], "monthly")

    def test_pr_type_chart_weekly_returns_weekly_labels(self):
        """Test that weekly granularity returns week-formatted labels in chart data."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_pr_type_breakdown")
        response = self.client.get(f"{url}?granularity=weekly&days=30")

        self.assertEqual(response.status_code, 200)
        chart_data = response.context["chart_data"]

        # Labels should be week format (e.g., "2024-W01")
        if chart_data["labels"]:
            for label in chart_data["labels"]:
                self.assertRegex(label, r"^\d{4}-W\d{2}$", f"Weekly label '{label}' should match format YYYY-WNN")

    def test_pr_type_chart_monthly_returns_monthly_labels(self):
        """Test that monthly granularity returns month-formatted labels in chart data."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_pr_type_breakdown")
        response = self.client.get(f"{url}?granularity=monthly&days=365")

        self.assertEqual(response.status_code, 200)
        chart_data = response.context["chart_data"]

        # Labels should be month format (e.g., "2024-01")
        if chart_data["labels"]:
            for label in chart_data["labels"]:
                self.assertRegex(label, r"^\d{4}-\d{2}$", f"Monthly label '{label}' should match format YYYY-MM")

    def test_pr_type_chart_different_granularity_different_labels(self):
        """Test that weekly and monthly granularity produce different label formats."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:chart_pr_type_breakdown")

        # Get weekly data
        weekly_response = self.client.get(f"{url}?granularity=weekly&days=30")
        weekly_labels = weekly_response.context["chart_data"]["labels"]

        # Get monthly data
        monthly_response = self.client.get(f"{url}?granularity=monthly&days=30")
        monthly_labels = monthly_response.context["chart_data"]["labels"]

        # If we have data in both, labels should have different formats
        if weekly_labels and monthly_labels:
            # Weekly: "2024-W01", Monthly: "2024-01"
            self.assertNotEqual(
                weekly_labels[0], monthly_labels[0], "Weekly and monthly labels should have different formats"
            )


class TestGranularityToggleIntegration(TestCase):
    """Integration tests verifying granularity toggle works across all trend chart endpoints.

    These tests document the expected API contract for the granularity toggle feature.
    When the user clicks "Weekly" or "Monthly" in the UI, the frontend must pass
    the `granularity` parameter to these endpoints for charts to update correctly.

    Bug context: The frontend was not passing granularity to PR Type and Tech
    breakdown charts when the toggle was clicked. These tests verify the backend
    correctly handles granularity and returns different data for each setting.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()

        # Create merged PRs with files for testing
        from datetime import timedelta

        from django.utils import timezone

        from apps.metrics.factories import PRFileFactory

        now = timezone.now()
        for i in range(5):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                pr_created_at=now - timedelta(days=i + 1),
                merged_at=now - timedelta(days=i),
            )
            PRFileFactory(team=self.team, pull_request=pr, filename=f"src/app{i}.py")

    def test_all_chart_endpoints_support_granularity_parameter(self):
        """Test that all trend chart endpoints accept and use granularity parameter.

        This verifies the backend API contract that the frontend relies on.
        """
        self.client.force_login(self.admin_user)

        endpoints = [
            ("metrics:chart_pr_type_breakdown", "pr_type_chart"),
            ("metrics:chart_tech_breakdown", "tech_chart"),
            ("metrics:chart_wide_trend", "wide_trend_chart"),
        ]

        for url_name, chart_name in endpoints:
            url = reverse(url_name)

            # Test weekly granularity
            response = self.client.get(f"{url}?granularity=weekly&days=30")
            self.assertEqual(response.status_code, 200, f"{chart_name} should accept weekly granularity")
            self.assertEqual(
                response.context["granularity"],
                "weekly",
                f"{chart_name} should return weekly in context",
            )

            # Test monthly granularity
            response = self.client.get(f"{url}?granularity=monthly&days=30")
            self.assertEqual(response.status_code, 200, f"{chart_name} should accept monthly granularity")
            self.assertEqual(
                response.context["granularity"],
                "monthly",
                f"{chart_name} should return monthly in context",
            )

    def test_granularity_changes_chart_data_format(self):
        """Test that different granularity settings produce appropriately grouped data.

        This is the key test for the bug fix - when granularity changes, the
        chart data labels should reflect the new grouping (weekly vs monthly format).
        """
        self.client.force_login(self.admin_user)

        # Test for both chart types affected by the bug
        for url_name in ["metrics:chart_pr_type_breakdown", "metrics:chart_tech_breakdown"]:
            url = reverse(url_name)

            # Weekly should return YYYY-WNN formatted labels
            weekly = self.client.get(f"{url}?granularity=weekly&days=30")
            weekly_data = weekly.context["chart_data"]

            # Monthly should return YYYY-MM formatted labels
            monthly = self.client.get(f"{url}?granularity=monthly&days=30")
            monthly_data = monthly.context["chart_data"]

            # If we have labels, verify formats are different
            if weekly_data["labels"] and monthly_data["labels"]:
                weekly_label = weekly_data["labels"][0]
                monthly_label = monthly_data["labels"][0]

                # Weekly format: "2024-W01", Monthly format: "2024-01"
                self.assertIn(
                    "-W",
                    weekly_label,
                    f"{url_name}: Weekly label '{weekly_label}' should contain '-W' (week format)",
                )
                self.assertNotIn(
                    "-W",
                    monthly_label,
                    f"{url_name}: Monthly label '{monthly_label}' should NOT contain '-W'",
                )
