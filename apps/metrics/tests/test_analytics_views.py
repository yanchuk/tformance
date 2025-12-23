"""Tests for analytics views - Overview and tabbed analytics pages."""

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class TestAnalyticsOverviewView(TestCase):
    """Tests for the analytics overview page."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()

    def test_overview_requires_login(self):
        """Test that analytics overview requires authentication."""
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_overview_requires_admin(self):
        """Test that analytics overview requires admin role."""
        self.client.force_login(self.member_user)
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        # Returns 404 for non-admin team members (consistent with cto_overview behavior)
        self.assertEqual(response.status_code, 404)

    def test_overview_accessible_to_admin(self):
        """Test that admin can access analytics overview."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/analytics/overview.html")

    def test_overview_has_active_page_context(self):
        """Test that overview has correct active_page for nav highlighting."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        self.assertEqual(response.context["active_page"], "overview")

    def test_overview_has_days_context(self):
        """Test that overview receives days parameter."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url, {"days": "7"})

        self.assertEqual(response.context["days"], 7)

    def test_overview_default_days_is_30(self):
        """Test that default days value is 30."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        self.assertEqual(response.context["days"], 30)

    def test_overview_htmx_returns_partial(self):
        """Test that HTMX request returns partial template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        # Partial should not have full HTML structure
        self.assertNotContains(response, "<html")

    def test_overview_has_insights_context(self):
        """Test that overview includes insights for the team."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        self.assertIn("insights", response.context)

    def test_overview_has_analytics_tabs(self):
        """Test that overview page shows analytics tab navigation."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        # Should have tab links to other analytics pages
        self.assertContains(response, "Overview")
        self.assertContains(response, "Pull Requests")


class TestAnalyticsBaseTemplate(TestCase):
    """Tests for base analytics template features."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_overview_extends_base_analytics(self):
        """Test that overview extends base analytics template."""
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        self.assertTemplateUsed(response, "metrics/analytics/base_analytics.html")

    def test_analytics_nav_highlights_active_tab(self):
        """Test that the active tab is highlighted in navigation."""
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        # Active tab should have 'tab-active' class
        content = response.content.decode()
        self.assertIn("tab-active", content)

    def test_date_filter_present_in_analytics(self):
        """Test that date filter controls are shown."""
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)

        # Should have time range filter buttons
        self.assertContains(response, "7d")
        self.assertContains(response, "30d")
        self.assertContains(response, "90d")


class TestAnalyticsUrlPatterns(TestCase):
    """Tests for analytics URL routing."""

    def test_analytics_overview_url_resolves(self):
        """Test that analytics overview URL resolves correctly."""
        url = reverse("metrics:analytics_overview")

        self.assertIn("/analytics/", url)

    def test_pr_list_accessible_from_analytics(self):
        """Test that PR list page is still accessible."""
        url = reverse("metrics:pr_list")

        self.assertIn("/pull-requests/", url)


class TestAnalyticsAIAdoptionView(TestCase):
    """Tests for the AI adoption analytics page."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_ai_adoption_requires_login(self):
        """Test that AI adoption page requires authentication."""
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_ai_adoption_requires_admin(self):
        """Test that AI adoption page requires admin role."""
        self.client.force_login(self.member_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_ai_adoption_accessible_to_admin(self):
        """Test that admin can access AI adoption page."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/analytics/ai_adoption.html")

    def test_ai_adoption_has_active_page_context(self):
        """Test that AI adoption has correct active_page for nav highlighting."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        self.assertEqual(response.context["active_page"], "ai_adoption")

    def test_ai_adoption_has_days_context(self):
        """Test that AI adoption receives days parameter."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url, {"days": "7"})

        self.assertEqual(response.context["days"], 7)

    def test_ai_adoption_htmx_returns_partial(self):
        """Test that HTMX request returns partial template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<html")

    def test_ai_adoption_extends_base_analytics(self):
        """Test that AI adoption extends base analytics template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        self.assertTemplateUsed(response, "metrics/analytics/base_analytics.html")

    def test_ai_adoption_has_tabs_with_ai_active(self):
        """Test that AI adoption tab is shown as active."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        content = response.content.decode()
        # AI Adoption tab should be present and active
        self.assertIn("AI Adoption", content)
        self.assertIn("tab-active", content)

    def test_ai_adoption_url_resolves(self):
        """Test that AI adoption URL resolves correctly."""
        url = reverse("metrics:analytics_ai_adoption")

        self.assertIn("/analytics/ai-adoption/", url)

    def test_ai_adoption_has_comparison_data(self):
        """Test that AI adoption page includes AI vs non-AI comparison."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        self.assertIn("comparison", response.context)

    def test_ai_adoption_shows_ai_prs_link(self):
        """Test that AI adoption has link to view AI-assisted PRs."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        # Should have link to PR list with AI filter
        self.assertContains(response, "pull-requests")
        self.assertContains(response, "ai=yes")


class TestAnalyticsDeliveryView(TestCase):
    """Tests for the delivery analytics page."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_delivery_requires_login(self):
        """Test that delivery page requires authentication."""
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_delivery_requires_admin(self):
        """Test that delivery page requires admin role."""
        self.client.force_login(self.member_user)
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_delivery_accessible_to_admin(self):
        """Test that admin can access delivery page."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/analytics/delivery.html")

    def test_delivery_has_active_page_context(self):
        """Test that delivery has correct active_page for nav highlighting."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url)

        self.assertEqual(response.context["active_page"], "delivery")

    def test_delivery_has_days_context(self):
        """Test that delivery receives days parameter."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url, {"days": "7"})

        self.assertEqual(response.context["days"], 7)

    def test_delivery_htmx_returns_partial(self):
        """Test that HTMX request returns partial template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<html")

    def test_delivery_extends_base_analytics(self):
        """Test that delivery extends base analytics template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url)

        self.assertTemplateUsed(response, "metrics/analytics/base_analytics.html")

    def test_delivery_has_tabs_with_delivery_active(self):
        """Test that delivery tab is shown as active."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url)

        content = response.content.decode()
        self.assertIn("Delivery", content)
        self.assertIn("tab-active", content)

    def test_delivery_url_resolves(self):
        """Test that delivery URL resolves correctly."""
        url = reverse("metrics:analytics_delivery")

        self.assertIn("/analytics/delivery/", url)


class TestAnalyticsQualityView(TestCase):
    """Tests for the quality analytics page."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_quality_requires_login(self):
        """Test that quality page requires authentication."""
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_quality_requires_admin(self):
        """Test that quality page requires admin role."""
        self.client.force_login(self.member_user)
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_quality_accessible_to_admin(self):
        """Test that admin can access quality page."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/analytics/quality.html")

    def test_quality_has_active_page_context(self):
        """Test that quality has correct active_page for nav highlighting."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url)

        self.assertEqual(response.context["active_page"], "quality")

    def test_quality_has_days_context(self):
        """Test that quality receives days parameter."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url, {"days": "7"})

        self.assertEqual(response.context["days"], 7)

    def test_quality_htmx_returns_partial(self):
        """Test that HTMX request returns partial template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<html")

    def test_quality_extends_base_analytics(self):
        """Test that quality extends base analytics template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url)

        self.assertTemplateUsed(response, "metrics/analytics/base_analytics.html")

    def test_quality_has_tabs_with_quality_active(self):
        """Test that quality tab is shown as active."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url)

        content = response.content.decode()
        self.assertIn("Quality", content)
        self.assertIn("tab-active", content)

    def test_quality_url_resolves(self):
        """Test that quality URL resolves correctly."""
        url = reverse("metrics:analytics_quality")

        self.assertIn("/analytics/quality/", url)


class TestAnalyticsTeamView(TestCase):
    """Tests for the team performance analytics page."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_team_requires_login(self):
        """Test that team page requires authentication."""
        url = reverse("metrics:analytics_team")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_team_requires_admin(self):
        """Test that team page requires admin role."""
        self.client.force_login(self.member_user)
        url = reverse("metrics:analytics_team")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_team_accessible_to_admin(self):
        """Test that admin can access team page."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_team")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/analytics/team.html")

    def test_team_has_active_page_context(self):
        """Test that team has correct active_page for nav highlighting."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_team")

        response = self.client.get(url)

        self.assertEqual(response.context["active_page"], "team")

    def test_team_has_days_context(self):
        """Test that team receives days parameter."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_team")

        response = self.client.get(url, {"days": "7"})

        self.assertEqual(response.context["days"], 7)

    def test_team_htmx_returns_partial(self):
        """Test that HTMX request returns partial template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_team")

        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<html")

    def test_team_extends_base_analytics(self):
        """Test that team extends base analytics template."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_team")

        response = self.client.get(url)

        self.assertTemplateUsed(response, "metrics/analytics/base_analytics.html")

    def test_team_has_tabs_with_team_active(self):
        """Test that team tab is shown as active."""
        self.client.force_login(self.admin_user)
        url = reverse("metrics:analytics_team")

        response = self.client.get(url)

        content = response.content.decode()
        self.assertIn("Team", content)
        self.assertIn("tab-active", content)

    def test_team_url_resolves(self):
        """Test that team URL resolves correctly."""
        url = reverse("metrics:analytics_team")

        self.assertIn("/analytics/team/", url)
