"""
Tests for the AI Feedback views.
"""

from django.test import TestCase

from apps.feedback.factories import AIFeedbackFactory
from apps.feedback.models import AIFeedback
from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.users.models import CustomUser


class FeedbackViewTestCase(TestCase):
    """Base test case for feedback views."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="testpass123",
        )
        # Add user to team as admin
        from apps.teams.models import Membership
        from apps.teams.roles import ROLE_ADMIN

        Membership.objects.create(
            team=self.team,
            user=self.user,
            role=ROLE_ADMIN,
        )
        self.member = TeamMemberFactory(team=self.team, email=self.user.email)
        self.client.login(email="test@example.com", password="testpass123")
        # Set team in session
        session = self.client.session
        session["team"] = self.team.id
        session.save()

    def get_dashboard_url(self):
        """Get the feedback dashboard URL."""
        return "/app/feedback/"

    def get_create_url(self):
        """Get the create feedback URL."""
        return "/app/feedback/create/"

    def get_detail_url(self, pk):
        """Get the feedback detail URL."""
        return f"/app/feedback/{pk}/"

    def get_resolve_url(self, pk):
        """Get the resolve feedback URL."""
        return f"/app/feedback/{pk}/resolve/"


class TestFeedbackDashboard(FeedbackViewTestCase):
    """Tests for the feedback dashboard view."""

    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        self.client.logout()
        response = self.client.get(self.get_dashboard_url())
        self.assertEqual(response.status_code, 302)

    def test_dashboard_returns_200(self):
        """Test that dashboard returns 200 for authenticated users."""
        response = self.client.get(self.get_dashboard_url())
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_team_feedback_only(self):
        """Test that dashboard only shows feedback for the current team."""
        # Create feedback for our team
        our_feedback = AIFeedbackFactory(team=self.team)

        # Create feedback for another team
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        other_feedback = AIFeedbackFactory(team=other_team, reported_by=other_member)

        response = self.client.get(self.get_dashboard_url())

        self.assertContains(response, our_feedback.get_category_display())
        self.assertNotContains(response, other_feedback.description[:20])

    def test_dashboard_shows_feedback_list(self):
        """Test that dashboard displays feedback items."""
        AIFeedbackFactory(team=self.team, category="wrong_code")
        AIFeedbackFactory(team=self.team, category="security")

        response = self.client.get(self.get_dashboard_url())

        self.assertContains(response, "Generated wrong code")
        self.assertContains(response, "Security concern")


class TestCreateFeedback(FeedbackViewTestCase):
    """Tests for creating feedback."""

    def test_create_requires_login(self):
        """Test that create requires authentication."""
        self.client.logout()
        response = self.client.post(self.get_create_url(), {})
        self.assertEqual(response.status_code, 302)

    def test_create_feedback_via_post(self):
        """Test creating feedback via POST."""
        pr = PullRequestFactory(team=self.team)
        data = {
            "category": "wrong_code",
            "description": "AI generated incorrect ORM query",
            "pull_request": pr.id,
        }
        response = self.client.post(self.get_create_url(), data)

        # Should redirect after success
        self.assertEqual(response.status_code, 302)

        # Verify feedback was created
        feedback = AIFeedback.objects.filter(team=self.team).first()
        self.assertIsNotNone(feedback)
        self.assertEqual(feedback.category, "wrong_code")
        self.assertEqual(feedback.description, "AI generated incorrect ORM query")
        self.assertEqual(feedback.pull_request, pr)

    def test_create_feedback_with_minimal_data(self):
        """Test creating feedback with only required fields."""
        data = {
            "category": "other",
            "description": "",
        }
        response = self.client.post(self.get_create_url(), data)

        self.assertEqual(response.status_code, 302)
        feedback = AIFeedback.objects.filter(team=self.team).first()
        self.assertIsNotNone(feedback)
        self.assertEqual(feedback.category, "other")

    def test_create_feedback_invalid_category(self):
        """Test that invalid category is rejected."""
        data = {
            "category": "invalid_category",
            "description": "Test",
        }
        self.client.post(self.get_create_url(), data)

        # No feedback should be created for invalid category
        self.assertEqual(AIFeedback.objects.filter(team=self.team).count(), 0)

    def test_create_feedback_htmx_returns_partial(self):
        """Test that HTMX request returns a partial template."""
        data = {
            "category": "style_issue",
            "description": "Wrong formatting",
        }
        response = self.client.post(
            self.get_create_url(),
            data,
            HTTP_HX_REQUEST="true",
        )

        # HTMX should return 200 with partial content
        self.assertEqual(response.status_code, 200)


class TestFeedbackDetail(FeedbackViewTestCase):
    """Tests for feedback detail view."""

    def test_detail_requires_login(self):
        """Test that detail requires authentication."""
        feedback = AIFeedbackFactory(team=self.team)
        self.client.logout()
        response = self.client.get(self.get_detail_url(feedback.id))
        self.assertEqual(response.status_code, 302)

    def test_detail_returns_200(self):
        """Test that detail returns 200 for authenticated users."""
        feedback = AIFeedbackFactory(team=self.team)
        response = self.client.get(self.get_detail_url(feedback.id))
        self.assertEqual(response.status_code, 200)

    def test_detail_shows_feedback_info(self):
        """Test that detail shows feedback information."""
        feedback = AIFeedbackFactory(
            team=self.team,
            category="security",
            description="SQL injection risk in query",
        )
        response = self.client.get(self.get_detail_url(feedback.id))

        self.assertContains(response, "Security concern")
        self.assertContains(response, "SQL injection risk in query")

    def test_detail_other_team_returns_404(self):
        """Test that viewing other team's feedback returns 404."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        other_feedback = AIFeedbackFactory(team=other_team, reported_by=other_member)

        response = self.client.get(self.get_detail_url(other_feedback.id))
        self.assertEqual(response.status_code, 404)


class TestResolveFeedback(FeedbackViewTestCase):
    """Tests for resolving feedback."""

    def test_resolve_requires_login(self):
        """Test that resolve requires authentication."""
        feedback = AIFeedbackFactory(team=self.team)
        self.client.logout()
        response = self.client.post(self.get_resolve_url(feedback.id))
        self.assertEqual(response.status_code, 302)

    def test_resolve_feedback(self):
        """Test resolving feedback."""
        feedback = AIFeedbackFactory(team=self.team, status="open")
        response = self.client.post(self.get_resolve_url(feedback.id))

        # Should redirect after success
        self.assertEqual(response.status_code, 302)

        # Verify feedback was resolved
        feedback.refresh_from_db()
        self.assertEqual(feedback.status, "resolved")
        self.assertIsNotNone(feedback.resolved_at)

    def test_resolve_other_team_returns_404(self):
        """Test that resolving other team's feedback returns 404."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        other_feedback = AIFeedbackFactory(team=other_team, reported_by=other_member)

        response = self.client.post(self.get_resolve_url(other_feedback.id))
        self.assertEqual(response.status_code, 404)

    def test_resolve_htmx_returns_partial(self):
        """Test that HTMX request returns updated card."""
        feedback = AIFeedbackFactory(team=self.team, status="open")
        response = self.client.post(
            self.get_resolve_url(feedback.id),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        # Should contain resolved status
        self.assertContains(response, "Resolved")


class TestCTOSummary(FeedbackViewTestCase):
    """Tests for the CTO dashboard summary card."""

    def get_cto_summary_url(self):
        """Get the CTO summary URL."""
        return "/app/feedback/cto-summary/"

    def test_cto_summary_requires_login(self):
        """Test that CTO summary requires authentication."""
        self.client.logout()
        response = self.client.get(self.get_cto_summary_url())
        self.assertEqual(response.status_code, 302)

    def test_cto_summary_returns_200(self):
        """Test that CTO summary returns 200 for authenticated users."""
        response = self.client.get(self.get_cto_summary_url())
        self.assertEqual(response.status_code, 200)

    def test_cto_summary_shows_counts(self):
        """Test that CTO summary shows open and resolved counts."""
        AIFeedbackFactory(team=self.team, status="open")
        AIFeedbackFactory(team=self.team, status="open")
        AIFeedbackFactory(team=self.team, status="resolved")

        response = self.client.get(self.get_cto_summary_url())

        # Check for open count and resolved count displayed
        self.assertContains(response, "Open Issues")
        self.assertContains(response, "Resolved")

    def test_cto_summary_shows_recent_feedback(self):
        """Test that CTO summary shows recent feedback items."""
        feedback = AIFeedbackFactory(team=self.team, category="security")

        response = self.client.get(self.get_cto_summary_url())

        self.assertContains(response, feedback.get_category_display()[:10])

    def test_cto_summary_team_isolated(self):
        """Test that CTO summary only counts team's feedback."""
        # Create feedback for our team
        AIFeedbackFactory(team=self.team, status="open")

        # Create feedback for another team
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        AIFeedbackFactory(team=other_team, reported_by=other_member, status="open")

        response = self.client.get(self.get_cto_summary_url())
        self.assertEqual(response.status_code, 200)
