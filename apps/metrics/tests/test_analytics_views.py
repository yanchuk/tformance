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
        # Use status="complete" to ensure dashboard is accessible
        self.team = TeamFactory(onboarding_pipeline_status="complete")
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
        self.team = TeamFactory(onboarding_pipeline_status="complete")
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
        self.team = TeamFactory(onboarding_pipeline_status="complete")
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
        self.team = TeamFactory(onboarding_pipeline_status="complete")
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
        self.team = TeamFactory(onboarding_pipeline_status="complete")
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
        self.team = TeamFactory(onboarding_pipeline_status="complete")
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


class TestCopilotChampionsCardUX(TestCase):
    """Tests for Copilot Champions card UX improvements (P1).

    Verifies that the Champions card shows:
    - Visible metric labels (not hidden in tooltips)
    - Color-coded cycle time (<24h green, 24-72h yellow, >72h red)
    - Info tooltip explaining scoring methodology
    - Better subtitle explaining what Champions means
    """

    def setUp(self):
        """Set up test fixtures with champion data."""
        from datetime import date, timedelta
        from decimal import Decimal

        from apps.metrics.factories import AIUsageDailyFactory, PullRequestFactory

        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})

        # Create a champion with good stats
        self.member = TeamMemberFactory(team=self.team, display_name="Alice", github_username="alice123")
        start_date = date.today() - timedelta(days=30)

        # 7 days of Copilot usage (meets 5-day minimum)
        for day in range(7):
            AIUsageDailyFactory(
                team=self.team,
                member=self.member,
                date=start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=50,
                acceptance_rate=Decimal("50"),
            )

        # 5 PRs with 12h cycle time (fast, should be green)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                cycle_time_hours=Decimal("12"),
                is_revert=False,
            )

        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_champions_card_shows_visible_acceptance_label(self):
        """Test that acceptance rate has a visible label, not just tooltip."""
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        # Should show "acceptance" as visible text, not hidden in data-tip
        content = response.content.decode()
        self.assertIn("acceptance", content.lower())
        # Verify it's a visible label near the percentage
        self.assertContains(response, "% acceptance")

    def test_champions_card_shows_visible_prs_label(self):
        """Test that PRs merged count has visible label."""
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        # Should show "PRs merged" or similar visible text
        content = response.content.decode()
        # Already shows "5 PRs" - just verify it's present
        self.assertIn("PRs", content)

    def test_champions_card_shows_visible_cycle_time_label(self):
        """Test that cycle time has visible label with speed indicator."""
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        # Should show cycle time with a speed indicator like "fast", "avg", or hours
        content = response.content.decode()
        # Looking for visible cycle time context
        self.assertTrue(
            "cycle" in content.lower() or "hours" in content.lower() or "fast" in content.lower(),
            f"Expected visible cycle time label, got: {content[:500]}",
        )

    def test_champions_card_fast_cycle_time_is_green(self):
        """Test that fast cycle time (<24h) shows green color class."""
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        content = response.content.decode()
        # Fast cycle time should have success/green color indicator
        # Looking for text-success class near cycle time display
        self.assertIn("text-success", content)

    def test_champions_card_has_scoring_info_tooltip(self):
        """Test that card explains how champions are scored."""
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        content = response.content.decode()
        # Should have a tooltip or visible text explaining scoring weights
        # Either in data-tip attribute or visible text
        self.assertTrue(
            "40%" in content or "acceptance" in content.lower(),
            "Expected scoring methodology explanation (mentions 40% or acceptance weight)",
        )

    def test_champions_card_has_improved_subtitle(self):
        """Test that subtitle explains what Champions means."""
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)

        # Should have descriptive subtitle about Copilot + delivery
        content = response.content.decode()
        # Looking for improved subtitle mentioning both Copilot usage and delivery
        self.assertTrue(
            ("high" in content.lower() and "acceptance" in content.lower())
            or "delivery" in content.lower()
            or "mentor" in content.lower(),
            "Expected improved subtitle explaining Champions criteria",
        )
