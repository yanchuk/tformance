"""
Tests for web app views.

This module contains tests for view behavior including query parameters.
"""

from django.test import TestCase
from django.urls import reverse

from apps.metrics.factories import TeamFactory
from apps.teams.models import Membership
from apps.users.models import CustomUser


class TestTeamHomeDaysParam(TestCase):
    """Tests for the days parameter in team_home view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="testpass123",
        )
        # Add user to team as member
        Membership.objects.create(team=self.team, user=self.user, role="admin")

        self.client.login(username="testuser@example.com", password="testpass123")
        # Set team in session for middleware
        session = self.client.session
        session["team"] = self.team.id
        session.save()

        self.dashboard_url = reverse("web_team:home")

    def test_default_days_is_30(self):
        """Test that accessing team home without params sets context['days'] to 30."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)
        self.assertEqual(response.context["days"], 30)

    def test_accepts_days_query_param(self):
        """Test that accessing team home with ?days=7 sets context['days'] to 7."""
        response = self.client.get(f"{self.dashboard_url}?days=7")
        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)
        self.assertEqual(response.context["days"], 7)

    def test_invalid_days_defaults_to_30(self):
        """Test that invalid days param (non-numeric) defaults to 30."""
        response = self.client.get(f"{self.dashboard_url}?days=abc")
        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)
        self.assertEqual(response.context["days"], 30)
