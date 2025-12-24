"""Tests for PR list views - Pull Requests data explorer page."""

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.integrations.factories import UserFactory
from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.teams.roles import ROLE_ADMIN


class TestPrListView(TestCase):
    """Tests for the main PR list view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team, display_name="Alice")
        self.client = Client()
        self.client.force_login(self.user)

    def test_pr_list_requires_login(self):
        """Test that PR list page requires authentication."""
        self.client.logout()
        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_pr_list_renders_successfully(self):
        """Test that PR list page renders with 200 status and analytics tabs."""
        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/analytics/pull_requests.html")
        self.assertTemplateUsed(response, "metrics/analytics/base_analytics.html")

    def test_pr_list_shows_prs(self):
        """Test that PR list page shows PRs for the team."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team,
            author=self.member,
            title="Test PR",
            github_repo="org/repo",
            state="merged",
            merged_at=now - timedelta(days=5),
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        self.assertContains(response, "Test PR")
        self.assertContains(response, "org/repo")

    def test_pr_list_filter_options_in_context(self):
        """Test that filter options are passed to template context."""
        now = timezone.now()
        PullRequestFactory(team=self.team, github_repo="org/repo-a", state="merged", merged_at=now - timedelta(days=5))
        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        self.assertIn("filter_options", response.context)
        self.assertIn("repos", response.context["filter_options"])

    def test_pr_list_applies_repo_filter(self):
        """Test that repo filter is applied from GET params."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, github_repo="org/repo-a", title="PR A", state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, github_repo="org/repo-b", title="PR B", state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"repo": "org/repo-a"})

        self.assertContains(response, "PR A")
        self.assertNotContains(response, "PR B")

    def test_pr_list_applies_ai_filter_yes(self):
        """Test that AI filter is applied from GET params."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, is_ai_assisted=True, title="AI PR", state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, is_ai_assisted=False, title="Normal PR", state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"ai": "yes"})

        self.assertContains(response, "AI PR")
        self.assertNotContains(response, "Normal PR")

    def test_pr_list_applies_state_filter(self):
        """Test that state filter is applied from GET params."""
        now = timezone.now()
        # Both need merged_at to show up in default 30-day filter
        PullRequestFactory(team=self.team, state="merged", title="Merged PR", merged_at=now - timedelta(days=5))
        # Open PRs don't have merged_at, so won't show with default filter
        # Use explicit date_from/date_to to include open PRs for this test
        PullRequestFactory(team=self.team, state="open", title="Open PR", pr_created_at=now - timedelta(days=5))
        url = reverse("metrics:pr_list")

        # Pass explicit dates to include both merged and open PRs
        date_from = (now - timedelta(days=30)).date().isoformat()
        date_to = now.date().isoformat()
        response = self.client.get(url, {"state": "merged", "date_from": date_from, "date_to": date_to})

        self.assertContains(response, "Merged PR")
        self.assertNotContains(response, "Open PR")

    def test_pr_list_applies_date_range_filter(self):
        """Test that date range filters are applied."""
        today = timezone.now()
        PullRequestFactory(
            team=self.team,
            merged_at=today - timedelta(days=3),
            state="merged",
            title="Recent PR",
        )
        PullRequestFactory(
            team=self.team,
            merged_at=today - timedelta(days=30),
            state="merged",
            title="Old PR",
        )
        url = reverse("metrics:pr_list")
        week_ago = (today - timedelta(days=7)).date().isoformat()
        today_str = today.date().isoformat()

        response = self.client.get(url, {"date_from": week_ago, "date_to": today_str})

        self.assertContains(response, "Recent PR")
        self.assertNotContains(response, "Old PR")

    def test_pr_list_shows_stats(self):
        """Test that aggregate stats are shown."""
        now = timezone.now()
        PullRequestFactory(team=self.team, cycle_time_hours=10, state="merged", merged_at=now - timedelta(days=5))
        PullRequestFactory(team=self.team, cycle_time_hours=20, state="merged", merged_at=now - timedelta(days=5))
        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        self.assertIn("stats", response.context)
        self.assertEqual(response.context["stats"]["total_count"], 2)

    def test_pr_list_htmx_returns_partial(self):
        """Test that HTMX request returns partial template."""
        now = timezone.now()
        PullRequestFactory(team=self.team, title="Test PR", state="merged", merged_at=now - timedelta(days=5))
        url = reverse("metrics:pr_list")

        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        # Should return partial, not full page (no <html> tag)
        self.assertNotContains(response, "<html")

    def test_pr_list_pagination(self):
        """Test that PR list is paginated."""
        # Create more PRs than fit on one page (all merged within last 30 days)
        now = timezone.now()
        for i in range(60):
            PullRequestFactory(
                team=self.team,
                title=f"PR {i}",
                state="merged",
                merged_at=now - timedelta(days=i % 25 + 1),  # Within last 25 days
            )
        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        self.assertIn("page_obj", response.context)
        # Default page size should be 50
        self.assertEqual(len(response.context["page_obj"]), 50)

    def test_pr_list_page_param(self):
        """Test that page parameter works."""
        now = timezone.now()
        for i in range(60):
            PullRequestFactory(
                team=self.team,
                title=f"PR {i}",
                state="merged",
                merged_at=now - timedelta(days=i % 25 + 1),
            )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"page": "2"})

        self.assertEqual(response.status_code, 200)
        # Second page should have remaining PRs
        self.assertEqual(len(response.context["page_obj"]), 10)


class TestPrListTableView(TestCase):
    """Tests for the PR list table HTMX partial view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.user)

    def test_pr_table_returns_partial(self):
        """Test that table endpoint returns partial template."""
        now = timezone.now()
        PullRequestFactory(team=self.team, title="Test PR", state="merged", merged_at=now - timedelta(days=5))
        url = reverse("metrics:pr_list_table")

        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/pull_requests/partials/table.html")

    def test_pr_table_applies_filters(self):
        """Test that table partial applies filters from GET params."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, github_repo="org/repo-a", title="PR A", state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, github_repo="org/repo-b", title="PR B", state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list_table")

        response = self.client.get(url, {"repo": "org/repo-a"}, HTTP_HX_REQUEST="true")

        self.assertContains(response, "PR A")
        self.assertNotContains(response, "PR B")


class TestPrListExportView(TestCase):
    """Tests for the PR list CSV export view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team, display_name="Alice")
        self.client = Client()
        self.client.force_login(self.user)

    def test_export_returns_csv(self):
        """Test that export returns CSV file."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, author=self.member, title="Test PR", state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list_export")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_includes_pr_data(self):
        """Test that CSV includes PR data."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team,
            author=self.member,
            title="Test PR Title",
            github_repo="org/repo",
            state="merged",
            merged_at=now - timedelta(days=5),
        )
        url = reverse("metrics:pr_list_export")

        response = self.client.get(url)

        # StreamingHttpResponse uses streaming_content
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("Test PR Title", content)
        self.assertIn("org/repo", content)

    def test_export_applies_filters(self):
        """Test that export applies filters from GET params."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, github_repo="org/repo-a", title="PR A", state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, github_repo="org/repo-b", title="PR B", state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list_export")

        response = self.client.get(url, {"repo": "org/repo-a"})

        # StreamingHttpResponse uses streaming_content
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("PR A", content)
        self.assertNotIn("PR B", content)

    def test_export_has_headers(self):
        """Test that CSV has proper column headers."""
        now = timezone.now()
        PullRequestFactory(team=self.team, state="merged", merged_at=now - timedelta(days=5))
        url = reverse("metrics:pr_list_export")

        response = self.client.get(url)

        # StreamingHttpResponse uses streaming_content
        content = b"".join(response.streaming_content).decode("utf-8")
        # Check for expected headers
        self.assertIn("Title", content)
        self.assertIn("Repository", content)
        self.assertIn("Author", content)
        self.assertIn("Cycle Time", content)

    def test_export_requires_login(self):
        """Test that export requires authentication."""
        self.client.logout()
        url = reverse("metrics:pr_list_export")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

    def test_export_query_count_is_constant(self):
        """Test that export uses select_related to avoid N+1 on author access."""
        # Create 10 PRs with authors (all merged within last 30 days)
        now = timezone.now()
        for i in range(10):
            member = TeamMemberFactory(team=self.team, display_name=f"Author{i}")
            PullRequestFactory(
                team=self.team,
                author=member,
                title=f"PR {i}",
                state="merged",
                merged_at=now - timedelta(days=i % 25 + 1),
            )

        url = reverse("metrics:pr_list_export")

        # Get the response and consume streaming content to trigger queries
        # Expected: 8 queries (session, user, team, membership, session update, PR query)
        # The PR query uses select_related for author - so NO N+1 (would be 18 with N+1)
        with self.assertNumQueries(8):
            response = self.client.get(url)
            # Must consume streaming content to trigger actual DB queries
            _ = b"".join(response.streaming_content)

        self.assertEqual(response.status_code, 200)


class TestPrListSorting(TestCase):
    """Tests for PR list sorting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.member = TeamMemberFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.user)

    def test_default_sort_by_merged_desc(self):
        """Test that default sort is by merged_at descending."""
        now = timezone.now()
        PullRequestFactory(team=self.team, title="Old PR", merged_at=now - timedelta(days=10))
        PullRequestFactory(team=self.team, title="New PR", merged_at=now - timedelta(days=1))
        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        prs = list(response.context["prs"])
        self.assertEqual(prs[0].title, "New PR")
        self.assertEqual(prs[1].title, "Old PR")

    def test_sort_by_cycle_time_desc(self):
        """Test sorting by cycle time descending."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, title="Fast PR", cycle_time_hours=5, state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, title="Slow PR", cycle_time_hours=50, state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "cycle_time", "order": "desc"})

        prs = list(response.context["prs"])
        self.assertEqual(prs[0].title, "Slow PR")
        self.assertEqual(prs[1].title, "Fast PR")

    def test_sort_by_cycle_time_asc(self):
        """Test sorting by cycle time ascending."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, title="Fast PR", cycle_time_hours=5, state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, title="Slow PR", cycle_time_hours=50, state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "cycle_time", "order": "asc"})

        prs = list(response.context["prs"])
        self.assertEqual(prs[0].title, "Fast PR")
        self.assertEqual(prs[1].title, "Slow PR")

    def test_sort_by_review_time(self):
        """Test sorting by review time."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, title="Quick Review", review_time_hours=2, state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, title="Long Review", review_time_hours=48, state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "review_time", "order": "desc"})

        prs = list(response.context["prs"])
        self.assertEqual(prs[0].title, "Long Review")

    def test_sort_by_lines(self):
        """Test sorting by lines (additions)."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team,
            title="Small PR",
            additions=10,
            deletions=5,
            state="merged",
            merged_at=now - timedelta(days=5),
        )
        PullRequestFactory(
            team=self.team,
            title="Large PR",
            additions=500,
            deletions=100,
            state="merged",
            merged_at=now - timedelta(days=5),
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "lines", "order": "desc"})

        prs = list(response.context["prs"])
        self.assertEqual(prs[0].title, "Large PR")

    def test_sort_by_comments(self):
        """Test sorting by comments."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, title="No Comments", total_comments=0, state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, title="Many Comments", total_comments=25, state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "comments", "order": "desc"})

        prs = list(response.context["prs"])
        self.assertEqual(prs[0].title, "Many Comments")

    def test_invalid_sort_defaults_to_merged(self):
        """Test that invalid sort field defaults to merged_at."""
        now = timezone.now()
        PullRequestFactory(team=self.team, title="Old", merged_at=now - timedelta(days=5))
        PullRequestFactory(team=self.team, title="New", merged_at=now - timedelta(days=1))
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "invalid_field"})

        # Should fall back to default sort (merged desc)
        prs = list(response.context["prs"])
        self.assertEqual(prs[0].title, "New")

    def test_invalid_order_defaults_to_desc(self):
        """Test that invalid order defaults to desc."""
        now = timezone.now()
        PullRequestFactory(team=self.team, title="Old", merged_at=now - timedelta(days=5))
        PullRequestFactory(team=self.team, title="New", merged_at=now - timedelta(days=1))
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "merged", "order": "invalid"})

        # Should fall back to desc order
        prs = list(response.context["prs"])
        self.assertEqual(prs[0].title, "New")

    def test_sort_context_in_response(self):
        """Test that sort and order are passed to template context."""
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "cycle_time", "order": "asc"})

        self.assertEqual(response.context["sort"], "cycle_time")
        self.assertEqual(response.context["order"], "asc")

    def test_sort_with_filters(self):
        """Test that sorting works with filters applied."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, title="Fast Merged", state="merged", cycle_time_hours=5, merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, title="Slow Merged", state="merged", cycle_time_hours=50, merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, title="Open PR", state="open", cycle_time_hours=1, pr_created_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"state": "merged", "sort": "cycle_time", "order": "asc"})

        prs = list(response.context["prs"])
        self.assertEqual(len(prs), 2)
        self.assertEqual(prs[0].title, "Fast Merged")
        self.assertEqual(prs[1].title, "Slow Merged")

    def test_sort_handles_null_values(self):
        """Test that sorting handles null values (nulls last)."""
        now = timezone.now()
        PullRequestFactory(
            team=self.team, title="Has Time", cycle_time_hours=10, state="merged", merged_at=now - timedelta(days=5)
        )
        PullRequestFactory(
            team=self.team, title="No Time", cycle_time_hours=None, state="merged", merged_at=now - timedelta(days=5)
        )
        url = reverse("metrics:pr_list")

        response = self.client.get(url, {"sort": "cycle_time", "order": "desc"})

        prs = list(response.context["prs"])
        # NULL values should be last
        self.assertEqual(prs[0].title, "Has Time")
        self.assertEqual(prs[1].title, "No Time")

    def test_table_partial_includes_sort_params(self):
        """Test that table partial view also applies sorting."""
        PullRequestFactory(team=self.team, title="Fast PR", cycle_time_hours=5)
        PullRequestFactory(team=self.team, title="Slow PR", cycle_time_hours=50)
        url = reverse("metrics:pr_list_table")

        response = self.client.get(url, {"sort": "cycle_time", "order": "asc"}, HTTP_HX_REQUEST="true")

        self.assertEqual(response.context["sort"], "cycle_time")
        self.assertEqual(response.context["order"], "asc")


class TestPrListSelfReviewedBadge(TestCase):
    """Tests for self-reviewed badge display (filter removed, badge kept)."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.metrics.factories import PRReviewFactory

        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.alice = TeamMemberFactory(team=self.team, display_name="Alice")
        self.bob = TeamMemberFactory(team=self.team, display_name="Bob")
        self.client = Client()
        self.client.force_login(self.user)
        self.PRReviewFactory = PRReviewFactory

    def test_self_reviewed_badge_displays_for_self_reviewed_prs(self):
        """Test that self-reviewed PRs show the 'Self' badge."""
        self_reviewed_pr = PullRequestFactory(team=self.team, title="Self Reviewed PR", author=self.alice)
        self.PRReviewFactory(team=self.team, pull_request=self_reviewed_pr, reviewer=self.alice)

        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        # Should contain the "Self" badge
        self.assertContains(response, 'title="Self-reviewed: Author is the only reviewer"')

    def test_pr_with_multiple_reviewers_not_marked_self_reviewed(self):
        """Test that PR with multiple reviewers does not show Self badge."""
        pr = PullRequestFactory(team=self.team, title="Multi Review", author=self.alice)
        self.PRReviewFactory(team=self.team, pull_request=pr, reviewer=self.alice)
        self.PRReviewFactory(team=self.team, pull_request=pr, reviewer=self.bob)

        url = reverse("metrics:pr_list")

        response = self.client.get(url)

        # PR should appear
        self.assertContains(response, "Multi Review")
        # But should NOT have the Self badge (since there are multiple reviewers)
        self.assertNotContains(response, 'title="Self-reviewed: Author is the only reviewer"')
