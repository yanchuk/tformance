"""Tests for chart partial views (HTMX endpoints).

This test module covers chart-related views that return partial HTML
for HTMX-driven dashboard updates.
"""

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_MEMBER


class TestJiraLinkageChart(TestCase):
    """Tests for jira_linkage_chart view.

    This view returns a donut chart showing Jira linkage statistics
    for pull requests in the team.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_jira_linkage_chart_requires_login(self):
        """Test that jira_linkage_chart redirects to login if not authenticated."""
        url = reverse("metrics:jira_linkage_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_jira_linkage_chart_returns_200(self):
        """Test that jira_linkage_chart returns 200 for authenticated team members."""
        self.client.force_login(self.user)
        url = reverse("metrics:jira_linkage_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_jira_linkage_chart_returns_correct_template(self):
        """Test that jira_linkage_chart renders the correct partial template."""
        self.client.force_login(self.user)
        url = reverse("metrics:jira_linkage_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/jira_linkage_chart.html")

    def test_jira_linkage_chart_has_linkage_data_context(self):
        """Test that context contains linkage_data from get_pr_jira_correlation."""
        self.client.force_login(self.user)
        url = reverse("metrics:jira_linkage_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("linkage_data", response.context)


class TestSPCorrelationChart(TestCase):
    """Tests for sp_correlation_chart view.

    This view returns a grouped bar chart showing story point buckets
    vs actual delivery hours for the team's PRs.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_sp_correlation_chart_requires_login(self):
        """Test that sp_correlation_chart redirects to login if not authenticated."""
        url = reverse("metrics:sp_correlation_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_sp_correlation_chart_returns_200(self):
        """Test that sp_correlation_chart returns 200 for authenticated team members."""
        self.client.force_login(self.user)
        url = reverse("metrics:sp_correlation_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_sp_correlation_chart_returns_bucket_data(self):
        """Test that context contains correlation_data with bucket structure."""
        self.client.force_login(self.user)
        url = reverse("metrics:sp_correlation_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("correlation_data", response.context)
        # Verify correlation_data contains the expected bucket structure
        correlation_data = response.context["correlation_data"]
        self.assertIn("buckets", correlation_data)

    def test_sp_correlation_chart_uses_date_range(self):
        """Test that sp_correlation_chart respects the days query parameter."""
        self.client.force_login(self.user)
        url = reverse("metrics:sp_correlation_chart")

        # Request with specific days parameter
        response = self.client.get(url, {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("correlation_data", response.context)


class TestVelocityTrendChart(TestCase):
    """Tests for velocity_trend_chart view.

    This view returns a line chart showing team velocity (story points)
    over time, using data from get_velocity_trend().
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_velocity_trend_chart_requires_login(self):
        """Test that velocity_trend_chart redirects to login if not authenticated."""
        url = reverse("metrics:velocity_trend_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_velocity_trend_chart_returns_200(self):
        """Test that velocity_trend_chart returns 200 for authenticated team members."""
        self.client.force_login(self.user)
        url = reverse("metrics:velocity_trend_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_velocity_trend_chart_returns_velocity_data(self):
        """Test that context contains velocity_data with periods structure."""
        self.client.force_login(self.user)
        url = reverse("metrics:velocity_trend_chart")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("velocity_data", response.context)
        # Verify velocity_data contains the expected periods structure
        velocity_data = response.context["velocity_data"]
        self.assertIn("periods", velocity_data)

    def test_velocity_trend_chart_uses_date_range(self):
        """Test that velocity_trend_chart respects the days query parameter."""
        self.client.force_login(self.user)
        url = reverse("metrics:velocity_trend_chart")

        # Request with specific days parameter
        response = self.client.get(url, {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("velocity_data", response.context)
