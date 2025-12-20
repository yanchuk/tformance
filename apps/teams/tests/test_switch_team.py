from django.test import TestCase
from django.urls import reverse

from apps.teams.models import Membership, Team
from apps.users.models import CustomUser


class TestSwitchTeam(TestCase):
    """Tests for the switch_team view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="testpass123",
        )
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        Membership.objects.create(team=self.team1, user=self.user, role="admin")
        Membership.objects.create(team=self.team2, user=self.user, role="member")

    def test_switch_team_success(self):
        """User can switch to a team they belong to."""
        self.client.login(email="test@example.com", password="testpass123")
        url = reverse("teams:switch_team", kwargs={"team_slug": self.team2.slug})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("web_team:home"))

    def test_switch_team_updates_session(self):
        """Switching teams updates the session with the new team ID."""
        self.client.login(email="test@example.com", password="testpass123")
        # Start with team1 in session
        session = self.client.session
        session["team"] = self.team1.id
        session.save()

        url = reverse("teams:switch_team", kwargs={"team_slug": self.team2.slug})
        self.client.get(url)

        # Session should now have team2
        self.assertEqual(self.client.session["team"], self.team2.id)

    def test_switch_team_not_member(self):
        """Returns 404 if user is not a member of the team."""
        CustomUser.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpass123",
        )
        self.client.login(email="other@example.com", password="testpass123")
        url = reverse("teams:switch_team", kwargs={"team_slug": self.team1.slug})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_switch_team_unauthenticated(self):
        """Unauthenticated users are redirected to login."""
        url = reverse("teams:switch_team", kwargs={"team_slug": self.team1.slug})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_switch_team_nonexistent_team(self):
        """Returns 404 for non-existent team slug."""
        self.client.login(email="test@example.com", password="testpass123")
        url = reverse("teams:switch_team", kwargs={"team_slug": "nonexistent"})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_dashboard_url_returns_switch_url(self):
        """Team.dashboard_url returns the switch_team URL with the team slug."""
        url = self.team1.dashboard_url

        expected_url = reverse("teams:switch_team", kwargs={"team_slug": self.team1.slug})
        self.assertEqual(url, expected_url)
