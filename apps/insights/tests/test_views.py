"""
Tests for the insights API views.
"""

import json
from unittest.mock import patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.teams.models import Membership
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser


class InsightsViewTestCase(TestCase):
    """Base test case with authenticated user and team."""

    def setUp(self):
        """Set up test user and team."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        Membership.objects.create(team=self.team, user=self.user, role=ROLE_ADMIN)
        self.client.login(username="testuser", password="testpass123")
        # Set team in session for middleware
        session = self.client.session
        session["team"] = self.team.id
        session.save()

    def get_summary_url(self):
        return "/app/insights/summary/"

    def get_ask_url(self):
        return "/app/insights/ask/"

    def get_suggested_url(self):
        return "/app/insights/suggested/"


class TestGetSummaryView(InsightsViewTestCase):
    """Tests for the get_summary view."""

    def test_requires_login(self):
        """Test that login is required."""
        self.client.logout()
        response = self.client.get(self.get_summary_url())
        self.assertEqual(response.status_code, 302)  # Redirect to login

    @patch("apps.insights.views.summarize_daily_insights")
    def test_returns_summary(self, mock_summarize):
        """Test returns summary JSON."""
        mock_summarize.return_value = "The team is doing well."

        response = self.client.get(self.get_summary_url())

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["summary"], "The team is doing well.")

    @patch("apps.insights.views.summarize_daily_insights")
    def test_refresh_param_skips_cache(self, mock_summarize):
        """Test refresh=true skips the cache."""
        mock_summarize.return_value = "Fresh summary"

        response = self.client.get(self.get_summary_url() + "?refresh=true")

        self.assertEqual(response.status_code, 200)
        mock_summarize.assert_called_with(team=self.team, skip_cache=True)

    @patch("apps.insights.views.summarize_daily_insights")
    def test_handles_errors(self, mock_summarize):
        """Test handles errors gracefully."""
        mock_summarize.side_effect = Exception("API Error")

        response = self.client.get(self.get_summary_url())

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)


class TestAskQuestionView(InsightsViewTestCase):
    """Tests for the ask_question view."""

    def test_requires_login(self):
        """Test that login is required."""
        self.client.logout()
        response = self.client.post(
            self.get_ask_url(),
            data=json.dumps({"question": "How is the team?"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_requires_post(self):
        """Test only POST is allowed."""
        response = self.client.get(self.get_ask_url())
        self.assertEqual(response.status_code, 405)

    @patch("apps.insights.views.answer_question")
    def test_returns_answer(self, mock_answer):
        """Test returns answer JSON."""
        mock_answer.return_value = "The team has 50 PRs this month."

        response = self.client.post(
            self.get_ask_url(),
            data=json.dumps({"question": "How many PRs this month?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "The team has 50 PRs this month.")

    def test_requires_question(self):
        """Test question is required."""
        response = self.client.post(
            self.get_ask_url(),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_rejects_empty_question(self):
        """Test empty question is rejected."""
        response = self.client.post(
            self.get_ask_url(),
            data=json.dumps({"question": "   "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_rejects_long_question(self):
        """Test long questions are rejected."""
        long_question = "a" * 501
        response = self.client.post(
            self.get_ask_url(),
            data=json.dumps({"question": long_question}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("too long", data["error"])

    def test_rejects_invalid_json(self):
        """Test invalid JSON is rejected."""
        response = self.client.post(
            self.get_ask_url(),
            data="not json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("apps.insights.views.answer_question")
    def test_handles_errors(self, mock_answer):
        """Test handles errors gracefully."""
        mock_answer.side_effect = Exception("API Error")

        response = self.client.post(
            self.get_ask_url(),
            data=json.dumps({"question": "How is the team?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)


class TestSuggestedQuestionsView(InsightsViewTestCase):
    """Tests for the suggested_questions view."""

    def test_requires_login(self):
        """Test that login is required."""
        self.client.logout()
        response = self.client.get(self.get_suggested_url())
        self.assertEqual(response.status_code, 302)

    def test_returns_questions_list(self):
        """Test returns list of questions."""
        response = self.client.get(self.get_suggested_url())

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("questions", data)
        self.assertIsInstance(data["questions"], list)
        self.assertGreater(len(data["questions"]), 0)


class TestHtmxResponses(InsightsViewTestCase):
    """Tests for HTMX HTML partial responses."""

    @patch("apps.insights.views.summarize_daily_insights")
    def test_summary_returns_html_for_htmx(self, mock_summarize):
        """Test summary returns HTML partial for HTMX requests."""
        mock_summarize.return_value = "The team is doing great!"

        response = self.client.get(
            self.get_summary_url(),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The team is doing great!")
        self.assertNotIn(b'"summary"', response.content)

    @patch("apps.insights.views.summarize_daily_insights")
    def test_summary_error_returns_html_for_htmx(self, mock_summarize):
        """Test summary error returns HTML for HTMX requests."""
        mock_summarize.side_effect = Exception("API Error")

        response = self.client.get(
            self.get_summary_url(),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Failed to generate summary")

    @patch("apps.insights.views.answer_question")
    def test_ask_returns_html_for_htmx(self, mock_answer):
        """Test ask returns HTML partial for HTMX requests."""
        mock_answer.return_value = "The team merged 50 PRs."

        response = self.client.post(
            self.get_ask_url(),
            data={"question": "How many PRs this month?"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The team merged 50 PRs.")
        self.assertNotIn(b'"answer"', response.content)

    @patch("apps.insights.views.answer_question")
    def test_ask_error_returns_html_for_htmx(self, mock_answer):
        """Test ask error returns HTML for HTMX requests."""
        mock_answer.side_effect = Exception("API Error")

        response = self.client.post(
            self.get_ask_url(),
            data={"question": "How is the team?"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Failed to answer question")

    def test_ask_validation_error_returns_html_for_htmx(self):
        """Test ask validation error returns HTML for HTMX requests."""
        response = self.client.post(
            self.get_ask_url(),
            data={"question": ""},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Question is required")

    def test_suggested_returns_html_for_htmx(self):
        """Test suggested questions returns HTML for HTMX requests."""
        response = self.client.get(
            self.get_suggested_url(),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How is the team doing")
        self.assertNotIn(b'"questions"', response.content)


class TestTeamIsolation(InsightsViewTestCase):
    """Tests for team data isolation."""

    @patch("apps.insights.views.summarize_daily_insights")
    def test_tampered_session_still_uses_users_team(self, mock_summarize):
        """Test that tampering with session team ID still uses user's own team.

        When a user sets another team's ID in session, the middleware
        falls back to the user's own team - ensuring data isolation.
        """
        mock_summarize.return_value = "Summary for user's team"

        # Create another team that user is not a member of
        other_team = TeamFactory()

        # Set other team in session (simulating someone trying to access another team)
        session = self.client.session
        session["team"] = other_team.id
        session.save()

        response = self.client.get(self.get_summary_url())

        # Should succeed because middleware falls back to user's actual team
        self.assertEqual(response.status_code, 200)
        # Verify the correct team was passed (user's team, not other_team)
        mock_summarize.assert_called_once()
        call_kwargs = mock_summarize.call_args[1]
        self.assertEqual(call_kwargs["team"], self.team)

    def test_user_with_no_teams_gets_404(self):
        """Test user with no team membership gets 404."""
        # Create a user with no team memberships
        from apps.teams.models import Membership

        Membership.objects.filter(user=self.user).delete()

        response = self.client.get(self.get_summary_url())

        # Should be 404 because user has no teams
        self.assertEqual(response.status_code, 404)
