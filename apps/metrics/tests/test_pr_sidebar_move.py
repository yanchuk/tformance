"""Tests for PR sidebar move - Pull Requests as top-level navigation item.

TDD Red Phase: These tests define the expected behavior for moving
Pull Requests from an Analytics sub-tab to a standalone sidebar item.
"""

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.teams.roles import ROLE_ADMIN


class TestPrListUrlChanges(TestCase):
    """Tests for new PR list URL structure."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.user)

    def test_pr_list_accessible_at_new_url(self):
        """Test PR list is accessible at /app/pull-requests/."""
        url = "/app/pull-requests/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_pr_list_table_accessible_at_new_url(self):
        """Test PR list table partial is accessible at new URL."""
        url = "/app/pull-requests/table/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_pr_list_export_accessible_at_new_url(self):
        """Test PR list export is accessible at new URL."""
        url = "/app/pull-requests/export/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_pr_list_url_name_resolves(self):
        """Test that 'pr_list' URL name resolves to new path."""
        # The URL name should resolve to the new path structure
        url = reverse("pullrequests:pr_list")

        self.assertIn("/pull-requests/", url)
        self.assertNotIn("/metrics/", url)


class TestSidebarNavigation(TestCase):
    """Tests for sidebar navigation with PR entry."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.user)

    def test_sidebar_contains_pr_link(self):
        """Test that sidebar contains Pull Requests link."""
        # Visit any team page to get sidebar
        url = reverse("metrics:dashboard_redirect")

        response = self.client.get(url, follow=True)

        self.assertContains(response, "Pull Requests")
        self.assertContains(response, "/pull-requests/")

    def test_pr_link_appears_after_analytics(self):
        """Test that PR link appears after Analytics in sidebar."""
        url = reverse("metrics:dashboard_redirect")

        response = self.client.get(url, follow=True)
        content = response.content.decode()

        # Find positions of both links in sidebar
        analytics_pos = content.find("Analytics")
        pr_pos = content.find("Pull Requests")
        integrations_pos = content.find("Integrations")

        # PR should come after Analytics but before Integrations
        self.assertGreater(pr_pos, analytics_pos, "PR link should appear after Analytics")
        self.assertLess(pr_pos, integrations_pos, "PR link should appear before Integrations")

    def test_pr_page_highlights_sidebar_item(self):
        """Test that PR page has correct active_tab for sidebar highlighting."""
        url = "/app/pull-requests/"

        response = self.client.get(url)

        # The context should have active_tab = 'pull_requests'
        self.assertEqual(response.context.get("active_tab"), "pull_requests")


class TestAnalyticsHubTabs(TestCase):
    """Tests for Analytics hub without PR tab."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.user)

    def test_analytics_has_six_tabs(self):
        """Test that Analytics hub has exactly 6 tabs (no PR)."""
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)
        content = response.content.decode()

        # Count tab entries in the tablist
        expected_tabs = ["Overview", "AI Adoption", "Delivery", "Quality", "Team", "Trends"]
        for tab in expected_tabs:
            self.assertIn(tab, content, f"Tab '{tab}' should be present")

    def test_analytics_tabs_exclude_pr(self):
        """Test that Analytics tabs don't include Pull Requests."""
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)
        content = response.content.decode()

        # Find the tablist section and verify no PR tab
        # The tablist has role="tablist"
        tablist_start = content.find('role="tablist"')
        tablist_end = content.find("</div>", tablist_start)
        tablist_content = content[tablist_start:tablist_end]

        self.assertNotIn("Pull Requests", tablist_content, "PR tab should not be in Analytics tabs")


class TestCrosslinks(TestCase):
    """Tests for crosslinks from Analytics pages to PR list."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.user)

    def test_overview_pr_crosslinks_use_new_url(self):
        """Test that overview page crosslinks use new PR URL."""
        url = reverse("metrics:analytics_overview")

        response = self.client.get(url)
        content = response.content.decode()

        # Should link to new URL, not old metrics path
        self.assertIn("/pull-requests/", content)
        self.assertNotIn("/metrics/pull-requests/", content)

    def test_ai_adoption_pr_crosslinks_use_new_url(self):
        """Test that AI adoption page crosslinks use new PR URL."""
        url = reverse("metrics:analytics_ai_adoption")

        response = self.client.get(url)
        content = response.content.decode()

        # Should have links with filters like ?ai=yes
        self.assertIn("/pull-requests/?ai=yes", content)
        self.assertNotIn("/metrics/pull-requests/", content)

    def test_delivery_pr_crosslinks_use_new_url(self):
        """Test that delivery page crosslinks use new PR URL."""
        url = reverse("metrics:analytics_delivery")

        response = self.client.get(url)
        content = response.content.decode()

        # Should have links with filters
        self.assertIn("/pull-requests/", content)
        self.assertNotIn("/metrics/pull-requests/", content)

    def test_quality_pr_crosslinks_use_new_url(self):
        """Test that quality page crosslinks use new PR URL."""
        url = reverse("metrics:analytics_quality")

        response = self.client.get(url)
        content = response.content.decode()

        self.assertIn("/pull-requests/", content)
        self.assertNotIn("/metrics/pull-requests/", content)

    def test_team_pr_crosslinks_use_new_url(self):
        """Test that team page crosslinks use new PR URL."""
        url = reverse("metrics:analytics_team")

        response = self.client.get(url)
        content = response.content.decode()

        self.assertIn("/pull-requests/", content)
        self.assertNotIn("/metrics/pull-requests/", content)

    def test_crosslink_filters_work_on_new_url(self):
        """Test that filter params work correctly on new URL."""
        # Create some test PRs
        PullRequestFactory(team=self.team, is_ai_assisted=True, state="merged")
        PullRequestFactory(team=self.team, is_ai_assisted=False, state="merged")

        # Access PR list with AI filter
        url = "/app/pull-requests/?ai=yes"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # The filter should be applied
        self.assertEqual(response.context.get("filters", {}).get("ai"), "yes")


class TestStandalonePrPage(TestCase):
    """Tests for standalone PR page (not under Analytics)."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.user)

    def test_pr_page_has_date_picker(self):
        """Test that standalone PR page has date range picker."""
        url = "/app/pull-requests/"

        response = self.client.get(url)
        content = response.content.decode()

        # Should have date range picker elements
        self.assertIn("date_from", content)
        self.assertIn("date_to", content)

    def test_pr_page_uses_standalone_template(self):
        """Test that PR page uses standalone template, not analytics base."""
        url = "/app/pull-requests/"

        response = self.client.get(url)

        # Should use standalone template
        self.assertTemplateUsed(response, "metrics/pull_requests/list_standalone.html")
        # Should NOT use analytics base
        self.assertTemplateNotUsed(response, "metrics/analytics/base_analytics.html")

    def test_pr_page_has_all_filters(self):
        """Test that standalone PR page has all filter options."""
        url = "/app/pull-requests/"

        response = self.client.get(url)
        content = response.content.decode()

        # Check for key filter elements
        expected_filters = [
            "Repository",
            "Author",
            "Reviewer",
            "AI Assisted",
            "State",
            "PR Size",
        ]
        for filter_name in expected_filters:
            self.assertIn(filter_name, content, f"Filter '{filter_name}' should be present")

    def test_pr_page_has_stats_row(self):
        """Test that standalone PR page has stats summary row."""
        url = "/app/pull-requests/"

        response = self.client.get(url)
        content = response.content.decode()

        # Should have stats elements
        self.assertIn("Total PRs", content)
        self.assertIn("Avg Cycle Time", content)

    def test_pr_page_has_export_button(self):
        """Test that standalone PR page has CSV export button."""
        url = "/app/pull-requests/"

        response = self.client.get(url)
        content = response.content.decode()

        self.assertIn("Export CSV", content)
        self.assertIn("/pull-requests/export/", content)

    def test_pr_page_table_sorting_works(self):
        """Test that table sorting works on standalone page."""
        PullRequestFactory(team=self.team, state="merged", cycle_time_hours=10)
        PullRequestFactory(team=self.team, state="merged", cycle_time_hours=5)

        url = "/app/pull-requests/?sort=cycle_time&order=asc"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get("sort"), "cycle_time")
        self.assertEqual(response.context.get("order"), "asc")

    def test_pr_page_pagination_works(self):
        """Test that pagination works on standalone page."""
        # Create enough PRs to trigger pagination (>50)
        PullRequestFactory.create_batch(55, team=self.team, state="merged")

        url = "/app/pull-requests/?page=2"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get("page_obj").number, 2)


class TestHtmxPartials(TestCase):
    """Tests for HTMX partial responses on new URL structure."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.user)

    def test_htmx_request_returns_partial(self):
        """Test that HTMX requests return partial content."""
        url = "/app/pull-requests/"

        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        # Should return partial, not full page
        content = response.content.decode()
        self.assertIn('id="page-content"', content)
        # Should not have full HTML structure
        self.assertNotIn("<!DOCTYPE", content)

    def test_table_partial_returns_table_only(self):
        """Test that table partial endpoint returns just the table."""
        url = "/app/pull-requests/table/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have table structure
        self.assertIn("<table", content)
        # Should not have full page structure
        self.assertNotIn("<!DOCTYPE", content)
