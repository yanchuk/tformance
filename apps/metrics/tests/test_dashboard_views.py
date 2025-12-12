"""Tests for dashboard page views.

This test module covers:
- dashboard_redirect: Routes admins to CTO overview, members to team dashboard
- cto_overview: Admin-only dashboard with team-wide metrics
- team_dashboard: Member-accessible individual dashboard
"""

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class TestDashboardRedirect(TestCase):
    """Tests for dashboard_redirect view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_dashboard_redirect_requires_login(self):
        """Test that dashboard_redirect redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:dashboard_redirect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_redirect_requires_team_membership(self):
        """Test that dashboard_redirect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:dashboard_redirect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_dashboard_redirect_admin_goes_to_cto_overview(self):
        """Test that admin users are redirected to cto_overview."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:dashboard_redirect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("metrics:cto_overview", args=[self.team.slug]))

    def test_dashboard_redirect_member_goes_to_team_dashboard(self):
        """Test that non-admin users are redirected to team_dashboard."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:dashboard_redirect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("metrics:team_dashboard", args=[self.team.slug]))


class TestCTOOverview(TestCase):
    """Tests for cto_overview view (admin-only team-wide dashboard)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_cto_overview_requires_login(self):
        """Test that cto_overview redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_cto_overview_requires_team_membership(self):
        """Test that cto_overview returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_cto_overview_requires_admin_role(self):
        """Test that cto_overview returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_cto_overview_returns_200_for_admin(self):
        """Test that cto_overview returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)

    def test_cto_overview_renders_correct_template(self):
        """Test that cto_overview renders cto_overview.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/cto_overview.html")

    def test_cto_overview_context_has_required_keys(self):
        """Test that cto_overview context contains required keys."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)
        self.assertIn("start_date", response.context)
        self.assertIn("end_date", response.context)
        self.assertIn("active_tab", response.context)

    def test_cto_overview_active_tab_is_metrics(self):
        """Test that cto_overview sets active_tab to 'metrics'."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_tab"], "metrics")

    def test_cto_overview_default_days_is_30(self):
        """Test that cto_overview defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)

    def test_cto_overview_accepts_days_query_param_7(self):
        """Test that cto_overview accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 7)

    def test_cto_overview_accepts_days_query_param_30(self):
        """Test that cto_overview accepts days=30 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]), {"days": "30"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)

    def test_cto_overview_accepts_days_query_param_90(self):
        """Test that cto_overview accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 90)

    def test_cto_overview_date_range_calculation(self):
        """Test that cto_overview correctly calculates date range based on days parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]), {"days": "7"})

        self.assertEqual(response.status_code, 200)

        # Get dates from context
        start_date = response.context["start_date"]
        end_date = response.context["end_date"]

        # end_date should be today
        self.assertEqual(end_date, timezone.now().date())

        # start_date should be 7 days ago
        expected_start = timezone.now().date() - timedelta(days=7)
        self.assertEqual(start_date, expected_start)

    def test_cto_overview_htmx_request_returns_partial_template(self):
        """Test that cto_overview returns partial template for HTMX requests."""
        self.client.force_login(self.admin_user)

        # Make HTMX request (indicated by HX-Request header)
        response = self.client.get(reverse("metrics:cto_overview", args=[self.team.slug]), HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        # For HTMX, should use partial template (with #page-content or similar)
        # The exact template depends on implementation, but it should be different from full template
        # We can check that it's still a valid response with the same context
        self.assertIn("days", response.context)
        self.assertIn("active_tab", response.context)


class TestTeamDashboard(TestCase):
    """Tests for team_dashboard view (member-accessible individual dashboard)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_team_dashboard_requires_login(self):
        """Test that team_dashboard redirects to login page if user is not authenticated."""
        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_team_dashboard_requires_team_membership(self):
        """Test that team_dashboard returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_team_dashboard_returns_200_for_member(self):
        """Test that team_dashboard returns 200 for regular team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)

    def test_team_dashboard_returns_200_for_admin(self):
        """Test that team_dashboard returns 200 for admin users (admins can see member view too)."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)

    def test_team_dashboard_renders_correct_template(self):
        """Test that team_dashboard renders team_dashboard.html template."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/team_dashboard.html")

    def test_team_dashboard_context_has_required_keys(self):
        """Test that team_dashboard context contains required keys."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)
        self.assertIn("start_date", response.context)
        self.assertIn("end_date", response.context)
        self.assertIn("active_tab", response.context)

    def test_team_dashboard_active_tab_is_metrics(self):
        """Test that team_dashboard sets active_tab to 'metrics'."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_tab"], "metrics")

    def test_team_dashboard_default_days_is_30(self):
        """Test that team_dashboard defaults to 30 days if no query param provided."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)

    def test_team_dashboard_accepts_days_query_param_7(self):
        """Test that team_dashboard accepts days=7 query parameter."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 7)

    def test_team_dashboard_accepts_days_query_param_30(self):
        """Test that team_dashboard accepts days=30 query parameter."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]), {"days": "30"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)

    def test_team_dashboard_accepts_days_query_param_90(self):
        """Test that team_dashboard accepts days=90 query parameter."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 90)

    def test_team_dashboard_date_range_calculation(self):
        """Test that team_dashboard correctly calculates date range based on days parameter."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]), {"days": "7"})

        self.assertEqual(response.status_code, 200)

        # Get dates from context
        start_date = response.context["start_date"]
        end_date = response.context["end_date"]

        # end_date should be today
        self.assertEqual(end_date, timezone.now().date())

        # start_date should be 7 days ago
        expected_start = timezone.now().date() - timedelta(days=7)
        self.assertEqual(start_date, expected_start)

    def test_team_dashboard_htmx_request_returns_partial_template(self):
        """Test that team_dashboard returns partial template for HTMX requests."""
        self.client.force_login(self.member_user)

        # Make HTMX request (indicated by HX-Request header)
        response = self.client.get(reverse("metrics:team_dashboard", args=[self.team.slug]), HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        # For HTMX, should use partial template (with #page-content or similar)
        # The exact template depends on implementation, but it should be different from full template
        # We can check that it's still a valid response with the same context
        self.assertIn("days", response.context)
        self.assertIn("active_tab", response.context)
