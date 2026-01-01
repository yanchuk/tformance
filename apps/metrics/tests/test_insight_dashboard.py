"""Tests for displaying insights on the CTO dashboard.

This test module covers:
- get_recent_insights service function
- cto_overview view including insights
- dismiss_insight view for dismissing insights via HTMX
"""

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.integrations.factories import UserFactory
from apps.metrics.factories import DailyInsightFactory, TeamFactory
from apps.metrics.services import insight_service
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class TestGetRecentInsightsService(TestCase):
    """Tests for get_recent_insights service function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_get_recent_insights_returns_insights(self):
        """Test that get_recent_insights returns insights for the team."""
        # Arrange - create some insights
        insight1 = DailyInsightFactory(
            team=self.team,
            date=timezone.now().date(),
            category="trend",
            priority="high",
        )
        insight2 = DailyInsightFactory(
            team=self.team,
            date=timezone.now().date() - timedelta(days=1),
            category="anomaly",
            priority="medium",
        )

        # Act
        insights = insight_service.get_recent_insights(self.team, limit=5)

        # Assert
        self.assertEqual(len(insights), 2)
        self.assertIn(insight1, insights)
        self.assertIn(insight2, insights)

    def test_get_recent_insights_excludes_dismissed(self):
        """Test that get_recent_insights excludes dismissed insights."""
        # Arrange - create dismissed and non-dismissed insights
        active_insight = DailyInsightFactory(
            team=self.team,
            date=timezone.now().date(),
            is_dismissed=False,
        )
        dismissed_insight = DailyInsightFactory(
            team=self.team,
            date=timezone.now().date(),
            is_dismissed=True,
            dismissed_at=timezone.now(),
        )

        # Act
        insights = insight_service.get_recent_insights(self.team, limit=5)

        # Assert
        self.assertEqual(len(insights), 1)
        self.assertIn(active_insight, insights)
        self.assertNotIn(dismissed_insight, insights)

    def test_get_recent_insights_respects_limit(self):
        """Test that get_recent_insights respects the limit parameter."""
        # Arrange - create more insights than the limit
        for i in range(10):
            DailyInsightFactory(
                team=self.team,
                date=timezone.now().date() - timedelta(days=i),
            )

        # Act
        insights = insight_service.get_recent_insights(self.team, limit=3)

        # Assert
        self.assertEqual(len(insights), 3)

    def test_get_recent_insights_orders_correctly(self):
        """Test that get_recent_insights orders by date desc, priority, category."""
        # Arrange - create insights with different dates, priorities, categories
        old_insight = DailyInsightFactory(
            team=self.team,
            date=timezone.now().date() - timedelta(days=5),
            category="trend",
            priority="low",
        )
        new_high_insight = DailyInsightFactory(
            team=self.team,
            date=timezone.now().date(),
            category="action",
            priority="high",
        )
        new_medium_insight = DailyInsightFactory(
            team=self.team,
            date=timezone.now().date(),
            category="anomaly",
            priority="medium",
        )

        # Act
        insights = insight_service.get_recent_insights(self.team, limit=5)

        # Assert
        insights_list = list(insights)
        # Most recent date should be first
        self.assertEqual(insights_list[0], new_high_insight)
        self.assertEqual(insights_list[1], new_medium_insight)
        self.assertEqual(insights_list[2], old_insight)


class TestCTOOverviewWithInsights(TestCase):
    """Tests for cto_overview view including insights in context."""

    def setUp(self):
        """Set up test fixtures using factories."""
        # Use status="complete" to ensure dashboard is accessible
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_dashboard_includes_insights_in_context(self):
        """Test that cto_overview includes insights in context."""
        # Arrange
        DailyInsightFactory(team=self.team, date=timezone.now().date())
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:cto_overview"))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn("insights", response.context)

    def test_dashboard_shows_insights_panel(self):
        """Test that cto_overview renders insights in the template."""
        # Arrange
        DailyInsightFactory(
            team=self.team,
            date=timezone.now().date(),
            title="Test Insight Title",
            description="Test insight description",
            category="trend",
            priority="high",
        )
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:cto_overview"))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Insight Title")
        self.assertContains(response, "Test insight description")


class TestDismissInsightView(TestCase):
    """Tests for dismiss_insight view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_dismiss_insight_sets_dismissed_flag(self):
        """Test that dismiss_insight sets is_dismissed to True."""
        # Arrange
        insight = DailyInsightFactory(team=self.team, is_dismissed=False)
        self.client.force_login(self.admin_user)

        # Act
        self.client.post(reverse("metrics:dismiss_insight", args=[insight.id]))

        # Assert
        insight.refresh_from_db()
        self.assertTrue(insight.is_dismissed)

    def test_dismiss_insight_sets_dismissed_at(self):
        """Test that dismiss_insight sets dismissed_at timestamp."""
        # Arrange
        insight = DailyInsightFactory(team=self.team, is_dismissed=False, dismissed_at=None)
        self.client.force_login(self.admin_user)
        before_dismiss = timezone.now()

        # Act
        self.client.post(reverse("metrics:dismiss_insight", args=[insight.id]))

        # Assert
        insight.refresh_from_db()
        self.assertIsNotNone(insight.dismissed_at)
        self.assertGreaterEqual(insight.dismissed_at, before_dismiss)

    def test_dismiss_insight_returns_success(self):
        """Test that dismiss_insight returns success response for HTMX."""
        # Arrange
        insight = DailyInsightFactory(team=self.team)
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.post(reverse("metrics:dismiss_insight", args=[insight.id]))

        # Assert
        self.assertEqual(response.status_code, 200)

    def test_dismiss_insight_requires_post(self):
        """Test that dismiss_insight only accepts POST requests."""
        # Arrange
        insight = DailyInsightFactory(team=self.team)
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:dismiss_insight", args=[insight.id]))

        # Assert
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_dismiss_insight_404_for_other_team(self):
        """Test that dismiss_insight returns 404 for insights from another team."""
        # Arrange
        other_team = TeamFactory()
        insight = DailyInsightFactory(team=other_team)
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.post(reverse("metrics:dismiss_insight", args=[insight.id]))

        # Assert
        self.assertEqual(response.status_code, 404)
