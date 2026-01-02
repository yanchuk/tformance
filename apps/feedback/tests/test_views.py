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


# =============================================================================
# LLM Feedback View Tests
# =============================================================================


class LLMFeedbackViewTestCase(TestCase):
    """Base test case for LLM feedback views."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="llmtest@example.com",
            email="llmtest@example.com",
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
        self.client.login(email="llmtest@example.com", password="testpass123")
        # Set team in session
        session = self.client.session
        session["team"] = self.team.id
        session.save()

    def get_submit_url(self):
        """Get the LLM feedback submit URL."""
        return "/app/feedback/llm/submit/"

    def get_feedback_url(self, content_type, content_id):
        """Get the LLM feedback retrieval URL."""
        return f"/app/feedback/llm/{content_type}/{content_id}/"

    def get_comment_url(self, pk):
        """Get the LLM feedback comment URL."""
        return f"/app/feedback/llm/{pk}/comment/"


class TestSubmitLLMFeedback(LLMFeedbackViewTestCase):
    """Tests for submitting LLM feedback."""

    def test_submit_llm_feedback_creates_record(self):
        """Test that submitting LLM feedback creates a new LLMFeedback record."""
        from apps.feedback.models import LLMFeedback

        data = {
            "content_type": "pr_summary",
            "content_id": "pr-123",
            "rating": True,
            "content_snapshot": {"summary": "Test PR summary content"},
        }
        response = self.client.post(
            self.get_submit_url(),
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Verify feedback was created
        feedback = LLMFeedback.objects.filter(
            team=self.team,
            content_type="pr_summary",
            content_id="pr-123",
        ).first()
        self.assertIsNotNone(feedback)
        self.assertTrue(feedback.rating)
        self.assertEqual(feedback.user, self.user)

    def test_submit_llm_feedback_requires_auth(self):
        """Test that submitting LLM feedback requires authentication."""
        self.client.logout()
        data = {
            "content_type": "pr_summary",
            "content_id": "pr-123",
            "rating": True,
            "content_snapshot": {"summary": "Test content"},
        }
        response = self.client.post(
            self.get_submit_url(),
            data=data,
            content_type="application/json",
        )

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_submit_llm_feedback_requires_team_membership(self):
        """Test that submitting LLM feedback requires team membership."""
        # Create a user not in the team
        CustomUser.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpass123",
        )
        self.client.logout()
        self.client.login(email="other@example.com", password="testpass123")
        # Don't set team in session or membership

        data = {
            "content_type": "pr_summary",
            "content_id": "pr-123",
            "rating": True,
            "content_snapshot": {"summary": "Test content"},
        }
        response = self.client.post(
            self.get_submit_url(),
            data=data,
            content_type="application/json",
        )

        # Should redirect, return forbidden, or 404 (to avoid leaking team info)
        self.assertIn(response.status_code, [302, 403, 404])

    def test_submit_llm_feedback_validates_content_type(self):
        """Test that submitting LLM feedback validates content_type choices."""
        data = {
            "content_type": "invalid_type",
            "content_id": "pr-123",
            "rating": True,
            "content_snapshot": {"summary": "Test content"},
        }
        response = self.client.post(
            self.get_submit_url(),
            data=data,
            content_type="application/json",
        )

        # Should return 400 for invalid content_type
        self.assertEqual(response.status_code, 400)

    def test_submit_llm_feedback_updates_existing(self):
        """Test that submitting feedback for same content updates existing record."""
        from apps.feedback.factories import LLMFeedbackFactory
        from apps.feedback.models import LLMFeedback

        # Create existing feedback
        existing = LLMFeedbackFactory(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            content_id="pr-123",
            rating=False,
        )

        data = {
            "content_type": "pr_summary",
            "content_id": "pr-123",
            "rating": True,  # Change rating
            "content_snapshot": {"summary": "Updated content"},
        }
        response = self.client.post(
            self.get_submit_url(),
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Verify only one record exists and it's updated
        feedback_count = LLMFeedback.objects.filter(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            content_id="pr-123",
        ).count()
        self.assertEqual(feedback_count, 1)

        existing.refresh_from_db()
        self.assertTrue(existing.rating)

    def test_submit_llm_feedback_returns_json_response(self):
        """Test that submitting feedback returns JSON with feedback ID."""
        import json

        data = {
            "content_type": "engineering_insight",
            "content_id": "insight-456",
            "rating": False,
            "content_snapshot": {"insight": "Test insight content"},
        }
        response = self.client.post(
            self.get_submit_url(),
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        response_data = json.loads(response.content)
        self.assertIn("id", response_data)
        self.assertIsNotNone(response_data["id"])

    def test_submit_llm_feedback_with_optional_fields(self):
        """Test that submitting feedback accepts optional input_context and prompt_version."""
        from apps.feedback.models import LLMFeedback

        data = {
            "content_type": "ai_detection",
            "content_id": "pr-789",
            "rating": True,
            "content_snapshot": {"detection": "AI-assisted"},
            "input_context": {"pr_title": "Test PR", "diff_size": 100},
            "prompt_version": "1.2.0",
        }
        response = self.client.post(
            self.get_submit_url(),
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        feedback = LLMFeedback.objects.filter(
            team=self.team,
            content_id="pr-789",
        ).first()
        self.assertIsNotNone(feedback)
        self.assertEqual(feedback.input_context, {"pr_title": "Test PR", "diff_size": 100})
        self.assertEqual(feedback.prompt_version, "1.2.0")


class TestGetLLMFeedback(LLMFeedbackViewTestCase):
    """Tests for retrieving LLM feedback."""

    def test_get_llm_feedback_returns_existing(self):
        """Test that GET returns existing feedback for content."""
        import json

        from apps.feedback.factories import LLMFeedbackFactory

        feedback = LLMFeedbackFactory(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            content_id="pr-123",
            rating=True,
        )

        response = self.client.get(self.get_feedback_url("pr_summary", "pr-123"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        response_data = json.loads(response.content)
        self.assertEqual(response_data["rating"], True)
        self.assertEqual(response_data["id"], feedback.id)

    def test_get_llm_feedback_returns_null_if_none(self):
        """Test that GET returns null rating if no feedback exists."""
        import json

        response = self.client.get(self.get_feedback_url("pr_summary", "nonexistent-123"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        response_data = json.loads(response.content)
        self.assertIsNone(response_data.get("rating"))

    def test_get_llm_feedback_requires_auth(self):
        """Test that GET feedback requires authentication."""
        self.client.logout()
        response = self.client.get(self.get_feedback_url("pr_summary", "pr-123"))

        self.assertEqual(response.status_code, 302)

    def test_get_llm_feedback_team_scoped(self):
        """Test that GET only returns feedback for current team."""
        import json

        from apps.feedback.factories import LLMFeedbackFactory

        # Create feedback for another team
        other_team = TeamFactory()
        other_user = CustomUser.objects.create_user(
            username="otherteam@example.com",
            email="otherteam@example.com",
            password="testpass123",
        )
        LLMFeedbackFactory(
            team=other_team,
            user=other_user,
            content_type="pr_summary",
            content_id="pr-123",
            rating=True,
        )

        # Request from our team context should return null
        response = self.client.get(self.get_feedback_url("pr_summary", "pr-123"))

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIsNone(response_data.get("rating"))

    def test_get_llm_feedback_user_specific(self):
        """Test that GET returns feedback specific to current user."""
        import json

        from apps.feedback.factories import LLMFeedbackFactory
        from apps.teams.models import Membership
        from apps.teams.roles import ROLE_ADMIN

        # Create feedback from another user in same team
        other_user = CustomUser.objects.create_user(
            username="teammate@example.com",
            email="teammate@example.com",
            password="testpass123",
        )
        Membership.objects.create(
            team=self.team,
            user=other_user,
            role=ROLE_ADMIN,
        )
        LLMFeedbackFactory(
            team=self.team,
            user=other_user,
            content_type="pr_summary",
            content_id="pr-123",
            rating=True,
        )

        # Our user should see null (no feedback from them)
        response = self.client.get(self.get_feedback_url("pr_summary", "pr-123"))

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIsNone(response_data.get("rating"))


class TestAddCommentToLLMFeedback(LLMFeedbackViewTestCase):
    """Tests for adding comments to LLM feedback."""

    def test_add_comment_to_feedback(self):
        """Test that a comment can be added to existing feedback."""
        from apps.feedback.factories import LLMFeedbackFactory

        feedback = LLMFeedbackFactory(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            content_id="pr-123",
            rating=False,
            comment="",
        )

        data = {"comment": "The summary missed important context about security changes."}
        response = self.client.post(
            self.get_comment_url(feedback.id),
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        feedback.refresh_from_db()
        self.assertEqual(feedback.comment, "The summary missed important context about security changes.")

    def test_add_comment_requires_auth(self):
        """Test that adding comment requires authentication."""
        from apps.feedback.factories import LLMFeedbackFactory

        feedback = LLMFeedbackFactory(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            content_id="pr-123",
        )

        self.client.logout()
        data = {"comment": "Test comment"}
        response = self.client.post(
            self.get_comment_url(feedback.id),
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)

    def test_add_comment_requires_ownership(self):
        """Test that user can only add comment to their own feedback."""
        from apps.feedback.factories import LLMFeedbackFactory
        from apps.teams.models import Membership
        from apps.teams.roles import ROLE_ADMIN

        # Create feedback from another user
        other_user = CustomUser.objects.create_user(
            username="feedbackowner@example.com",
            email="feedbackowner@example.com",
            password="testpass123",
        )
        Membership.objects.create(
            team=self.team,
            user=other_user,
            role=ROLE_ADMIN,
        )
        feedback = LLMFeedbackFactory(
            team=self.team,
            user=other_user,
            content_type="pr_summary",
            content_id="pr-123",
        )

        # Our user tries to add comment
        data = {"comment": "Trying to comment on someone else's feedback"}
        response = self.client.post(
            self.get_comment_url(feedback.id),
            data=data,
            content_type="application/json",
        )

        # Should return 404 or 403
        self.assertIn(response.status_code, [403, 404])

    def test_add_comment_team_scoped(self):
        """Test that user cannot add comment to feedback from another team."""
        from apps.feedback.factories import LLMFeedbackFactory

        other_team = TeamFactory()
        other_user = CustomUser.objects.create_user(
            username="otherteamuser@example.com",
            email="otherteamuser@example.com",
            password="testpass123",
        )
        feedback = LLMFeedbackFactory(
            team=other_team,
            user=other_user,
            content_type="pr_summary",
            content_id="pr-123",
        )

        data = {"comment": "Cross-team comment attempt"}
        response = self.client.post(
            self.get_comment_url(feedback.id),
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_add_comment_returns_json_response(self):
        """Test that adding comment returns JSON response."""
        import json

        from apps.feedback.factories import LLMFeedbackFactory

        feedback = LLMFeedbackFactory(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            content_id="pr-123",
        )

        data = {"comment": "This is helpful feedback"}
        response = self.client.post(
            self.get_comment_url(feedback.id),
            data=data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        response_data = json.loads(response.content)
        self.assertIn("success", response_data)
        self.assertTrue(response_data["success"])


class TestLLMFeedbackAnalyticsEvents(LLMFeedbackViewTestCase):
    """Tests for analytics events fired by LLM feedback views."""

    def test_submit_feedback_fires_analytics_event(self):
        """Test that submitting feedback fires llm_feedback_submitted event."""
        from unittest.mock import patch

        with patch("apps.feedback.views.track_event") as mock_track:
            data = {
                "content_type": "pr_summary",
                "content_id": "pr-123",
                "rating": True,
                "content_snapshot": {"summary": "Test summary"},
                "prompt_version": "1.0.0",
            }
            self.client.post(
                self.get_submit_url(),
                data=data,
                content_type="application/json",
            )

            mock_track.assert_called_once()
            call_args = mock_track.call_args
            self.assertEqual(call_args[0][0], self.user)
            self.assertEqual(call_args[0][1], "llm_feedback_submitted")

    def test_submit_feedback_event_has_correct_properties(self):
        """Test that llm_feedback_submitted event has expected properties."""
        from unittest.mock import patch

        with patch("apps.feedback.views.track_event") as mock_track:
            data = {
                "content_type": "engineering_insight",
                "content_id": "insight-456",
                "rating": False,
                "content_snapshot": {},
                "prompt_version": "2.0.0",
            }
            self.client.post(
                self.get_submit_url(),
                data=data,
                content_type="application/json",
            )

            properties = mock_track.call_args[0][2]
            self.assertEqual(properties["content_type"], "engineering_insight")
            self.assertEqual(properties["rating"], "negative")
            self.assertTrue(properties["is_new"])
            self.assertEqual(properties["prompt_version"], "2.0.0")

    def test_submit_feedback_positive_rating_tracked(self):
        """Test that positive rating is tracked as 'positive'."""
        from unittest.mock import patch

        with patch("apps.feedback.views.track_event") as mock_track:
            data = {
                "content_type": "pr_summary",
                "content_id": "pr-789",
                "rating": True,
            }
            self.client.post(
                self.get_submit_url(),
                data=data,
                content_type="application/json",
            )

            properties = mock_track.call_args[0][2]
            self.assertEqual(properties["rating"], "positive")

    def test_submit_feedback_update_tracks_is_new_false(self):
        """Test that updating existing feedback tracks is_new as False."""
        from unittest.mock import patch

        from apps.feedback.factories import LLMFeedbackFactory

        # Create existing feedback
        LLMFeedbackFactory(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            content_id="pr-existing",
            rating=True,
        )

        with patch("apps.feedback.views.track_event") as mock_track:
            data = {
                "content_type": "pr_summary",
                "content_id": "pr-existing",
                "rating": False,
            }
            self.client.post(
                self.get_submit_url(),
                data=data,
                content_type="application/json",
            )

            properties = mock_track.call_args[0][2]
            self.assertFalse(properties["is_new"])

    def test_add_comment_fires_analytics_event(self):
        """Test that adding comment fires llm_feedback_comment_added event."""
        from unittest.mock import patch

        from apps.feedback.factories import LLMFeedbackFactory

        feedback = LLMFeedbackFactory(
            team=self.team,
            user=self.user,
            content_type="qa_answer",
            content_id="qa-123",
            rating=True,
        )

        with patch("apps.feedback.views.track_event") as mock_track:
            data = {"comment": "This was very helpful!"}
            self.client.post(
                self.get_comment_url(feedback.id),
                data=data,
                content_type="application/json",
            )

            mock_track.assert_called_once()
            call_args = mock_track.call_args
            self.assertEqual(call_args[0][0], self.user)
            self.assertEqual(call_args[0][1], "llm_feedback_comment_added")

    def test_add_comment_event_has_correct_properties(self):
        """Test that llm_feedback_comment_added event has expected properties."""
        from unittest.mock import patch

        from apps.feedback.factories import LLMFeedbackFactory

        feedback = LLMFeedbackFactory(
            team=self.team,
            user=self.user,
            content_type="engineering_insight",
            content_id="insight-789",
            rating=False,
        )

        comment_text = "The insight was not accurate for our use case."
        with patch("apps.feedback.views.track_event") as mock_track:
            data = {"comment": comment_text}
            self.client.post(
                self.get_comment_url(feedback.id),
                data=data,
                content_type="application/json",
            )

            properties = mock_track.call_args[0][2]
            self.assertEqual(properties["content_type"], "engineering_insight")
            self.assertEqual(properties["rating"], "negative")
            self.assertEqual(properties["comment_length"], len(comment_text))
