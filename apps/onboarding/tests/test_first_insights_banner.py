"""Tests for First Insights Ready banner on sync progress page.

Phase 3.4 - Banner appears when quick sync completes to let users view
initial dashboard insights while full sync continues in background.
"""

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.users.models import CustomUser


class FirstInsightsBannerContextTests(TestCase):
    """Tests for first_insights_ready context variable in sync_progress view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="insights_test@example.com",
            email="insights_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        self.client.login(username="insights_test@example.com", password="testpassword123")

    def test_context_includes_first_insights_ready(self):
        """Test that sync_progress view includes first_insights_ready in context."""
        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("first_insights_ready", response.context)

    def test_first_insights_ready_true_when_team_has_pr_data(self):
        """Test that first_insights_ready is True when team has PR data from quick sync."""
        # Create a team member and PR for this team
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(team=self.team, author=member)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["first_insights_ready"])

    def test_first_insights_ready_false_when_no_pr_data(self):
        """Test that first_insights_ready is False when team has no PR data."""
        # No PRs created - team has no data yet

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["first_insights_ready"])

    def test_first_insights_ready_true_with_multiple_prs(self):
        """Test that first_insights_ready is True when team has multiple PRs."""
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory.create_batch(5, team=self.team, author=member)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["first_insights_ready"])


class FirstInsightsBannerTemplateTests(TestCase):
    """Tests for first insights banner HTML element rendering."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="banner_test@example.com",
            email="banner_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        self.client.login(username="banner_test@example.com", password="testpassword123")

    def test_banner_element_exists_when_first_insights_ready(self):
        """Test that banner with id='first-insights-banner' exists when first_insights_ready=True."""
        # Create PR data so first_insights_ready is True
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(team=self.team, author=member)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="first-insights-banner"')

    def test_banner_contains_view_dashboard_link(self):
        """Test that banner contains a 'View Dashboard' link."""
        # Create PR data so banner appears
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(team=self.team, author=member)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Check for View Dashboard text
        self.assertContains(response, "View Dashboard")
        # Check it links to the team dashboard (web_team:home doesn't require team_slug arg)
        dashboard_url = reverse("web_team:home")
        self.assertContains(response, dashboard_url)

    def test_banner_not_visible_when_no_pr_data(self):
        """Test that banner is not visible when first_insights_ready=False."""
        # No PRs created - banner should not appear

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Banner element should not be in the response
        self.assertNotContains(response, 'id="first-insights-banner"')

    def test_banner_shows_ready_message(self):
        """Test that banner shows appropriate message when insights are ready."""
        import re

        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(team=self.team, author=member)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Find the banner element and check it contains a "ready" or "available" message
        # The banner should have id="first-insights-banner" and contain status text
        banner_match = re.search(
            r'id="first-insights-banner"[^>]*>.*?</div>',
            content,
            re.DOTALL | re.IGNORECASE,
        )
        self.assertIsNotNone(banner_match, "Banner element should exist")

        banner_content = banner_match.group(0).lower()
        self.assertTrue(
            "ready" in banner_content or "available" in banner_content or "insights" in banner_content,
            f"Banner should indicate insights are ready/available. Got: {banner_content[:200]}",
        )


class FirstInsightsBannerDuringSyncTests(TestCase):
    """Tests for banner visibility during ongoing sync."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="sync_banner_test@example.com",
            email="sync_banner_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        self.client.login(username="sync_banner_test@example.com", password="testpassword123")

    def test_banner_visible_while_sync_in_progress(self):
        """Test that banner is visible even while full sync continues in background.

        The banner should appear as soon as quick sync produces results,
        even if the full historical sync is still running.
        """
        # Create PR data (simulating quick sync results)
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(team=self.team, author=member)

        # Store a task_id in session to simulate sync in progress
        session = self.client.session
        session["sync_task_id"] = "test-task-id-in-progress"
        session.save()

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Banner should still be visible during sync
        self.assertContains(response, 'id="first-insights-banner"')

    def test_banner_and_progress_both_visible(self):
        """Test that both the progress indicator and insights banner can be visible.

        Users should see sync progress AND have option to view initial insights.
        """
        # Create PR data
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(team=self.team, author=member)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Both progress bar and banner should exist
        self.assertContains(response, 'id="progress-bar"')
        self.assertContains(response, 'id="first-insights-banner"')


class FirstInsightsBannerIsolationTests(TestCase):
    """Tests to ensure banner only shows data from user's team."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="isolation_test@example.com",
            email="isolation_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        self.client.login(username="isolation_test@example.com", password="testpassword123")

    def test_banner_not_shown_for_other_teams_pr_data(self):
        """Test that banner is not shown based on other team's PR data.

        first_insights_ready should only be True if the user's team has PR data.
        """
        # Create PR data for a DIFFERENT team
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        PullRequestFactory(team=other_team, author=other_member)

        # User's team has no PR data
        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Banner should NOT appear since user's team has no data
        self.assertFalse(response.context["first_insights_ready"])
        self.assertNotContains(response, 'id="first-insights-banner"')
