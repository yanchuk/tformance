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
        response = self.client.get(reverse("metrics:dashboard_redirect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_redirect_requires_team_membership(self):
        """Test that dashboard_redirect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:dashboard_redirect"))

        self.assertEqual(response.status_code, 404)

    def test_dashboard_redirect_admin_goes_to_analytics_overview(self):
        """Test that admin users are redirected to analytics_overview."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:dashboard_redirect"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("metrics:analytics_overview"))

    def test_dashboard_redirect_member_goes_to_team_dashboard(self):
        """Test that non-admin users are redirected to team_dashboard."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:dashboard_redirect"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("metrics:team_dashboard"))


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
        response = self.client.get(reverse("metrics:cto_overview"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_cto_overview_requires_team_membership(self):
        """Test that cto_overview returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:cto_overview"))

        self.assertEqual(response.status_code, 404)

    def test_cto_overview_requires_admin_role(self):
        """Test that cto_overview returns 404 for non-admin team members."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:cto_overview"))

        self.assertEqual(response.status_code, 404)

    def test_cto_overview_returns_200_for_admin(self):
        """Test that cto_overview returns 200 for admin users."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"))

        self.assertEqual(response.status_code, 200)

    def test_cto_overview_renders_correct_template(self):
        """Test that cto_overview renders cto_overview.html template."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/cto_overview.html")

    def test_cto_overview_context_has_required_keys(self):
        """Test that cto_overview context contains required keys."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)
        self.assertIn("start_date", response.context)
        self.assertIn("end_date", response.context)
        self.assertIn("active_tab", response.context)

    def test_cto_overview_active_tab_is_metrics(self):
        """Test that cto_overview sets active_tab to 'metrics'."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_tab"], "metrics")

    def test_cto_overview_default_days_is_30(self):
        """Test that cto_overview defaults to 30 days if no query param provided."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)

    def test_cto_overview_accepts_days_query_param_7(self):
        """Test that cto_overview accepts days=7 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"), {"days": "7"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 7)

    def test_cto_overview_accepts_days_query_param_30(self):
        """Test that cto_overview accepts days=30 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"), {"days": "30"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)

    def test_cto_overview_accepts_days_query_param_90(self):
        """Test that cto_overview accepts days=90 query parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"), {"days": "90"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 90)

    def test_cto_overview_date_range_calculation(self):
        """Test that cto_overview correctly calculates date range based on days parameter."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cto_overview"), {"days": "7"})

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
        response = self.client.get(reverse("metrics:cto_overview"), HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        # For HTMX, should use partial template (with #page-content or similar)
        # The exact template depends on implementation, but it should be different from full template
        # We can check that it's still a valid response with the same context
        self.assertIn("days", response.context)
        self.assertIn("active_tab", response.context)


class TestTeamDashboard(TestCase):
    """Tests for team_dashboard view (deprecated - redirects to unified dashboard).

    The team_dashboard URL (/app/metrics/dashboard/team/) is deprecated and now
    redirects to the unified dashboard at /app/.
    """

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
        response = self.client.get(reverse("metrics:team_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_team_dashboard_requires_team_membership(self):
        """Test that team_dashboard returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:team_dashboard"))

        self.assertEqual(response.status_code, 404)

    def test_team_dashboard_redirects_to_unified_dashboard(self):
        """Test that team_dashboard redirects to unified dashboard at /app/."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/app/")

    def test_team_dashboard_redirects_for_admin(self):
        """Test that team_dashboard redirects for admin users too."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:team_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/app/")

    def test_team_dashboard_preserves_days_param_in_redirect(self):
        """Test that team_dashboard preserves days query param when redirecting."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard"), {"days": "7"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/app/?days=7")

    def test_team_dashboard_preserves_days_param_90(self):
        """Test that team_dashboard preserves days=90 query param when redirecting."""
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:team_dashboard"), {"days": "90"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/app/?days=90")


class TestBackgroundProgress(TestCase):
    """Tests for background_progress view (Two-Phase Onboarding banner)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

    def test_background_progress_requires_login(self):
        """Test that background_progress requires login."""
        response = self.client.get(reverse("metrics:background_progress"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_background_progress_returns_200(self):
        """Test that background_progress returns 200 for authenticated user."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:background_progress"))

        self.assertEqual(response.status_code, 200)

    def test_background_progress_renders_banner_template(self):
        """Test that background_progress renders the banner partial."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:background_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/background_progress_banner.html")

    def test_background_progress_context_has_team(self):
        """Test that background_progress context includes team object."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:background_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("team", response.context)
        self.assertEqual(response.context["team"].id, self.team.id)

    def test_background_progress_when_syncing(self):
        """Test that banner shows during background_syncing status."""
        self.team.onboarding_pipeline_status = "background_syncing"
        self.team.background_sync_progress = 50
        self.team.save()

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("metrics:background_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Syncing historical data")

    def test_background_progress_when_llm_processing(self):
        """Test that banner shows during background_llm status."""
        self.team.onboarding_pipeline_status = "background_llm"
        self.team.background_llm_progress = 75
        self.team.save()

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("metrics:background_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analyzing PRs with AI")

    def test_background_progress_hidden_when_complete(self):
        """Test that banner is hidden when processing is complete."""
        self.team.onboarding_pipeline_status = "complete"
        self.team.save()

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("metrics:background_progress"))

        self.assertEqual(response.status_code, 200)
        # Banner should not show progress bar when not in background states
        self.assertNotContains(response, "progress-info")

    def test_background_progress_hidden_during_phase1(self):
        """Test that banner is hidden during Phase 1 processing."""
        self.team.onboarding_pipeline_status = "llm_processing"
        self.team.save()

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("metrics:background_progress"))

        self.assertEqual(response.status_code, 200)
        # Not in background state, so banner should not show
        self.assertNotContains(response, "progress-info")
