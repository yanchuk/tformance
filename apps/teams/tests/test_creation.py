from django.test import TestCase
from django.urls import reverse

from apps.teams.helpers import create_default_team_for_user
from apps.teams.models import Team
from apps.teams.roles import is_admin
from apps.users.models import CustomUser


class TeamCreationTest(TestCase):
    def test_create_for_user(self):
        email = "alice@example.com"
        user = CustomUser.objects.create(
            username=email,
            email=email,
        )
        team = create_default_team_for_user(user)
        self.assertEqual("Alice", team.name)
        self.assertEqual("alice", team.slug)
        self.assertTrue(is_admin(user, team))


class CreateTeamViewTest(TestCase):
    """Tests for the create_team view."""

    def setUp(self):
        """Set up test user."""
        self.user = CustomUser.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="testpass123",
        )

    def test_create_team_via_view_generates_slug(self):
        """Test that creating a team via POST to create_team view generates a valid slug."""
        self.client.force_login(self.user)

        # Act - create team via POST
        response = self.client.post(
            reverse("teams:create_team"),
            {"name": "My Awesome Team"},
        )

        # Assert - team should be created with a slug
        self.assertEqual(response.status_code, 302)  # Redirect on success
        team = Team.objects.get(name="My Awesome Team")
        self.assertIsNotNone(team.slug)
        self.assertNotEqual(team.slug, "")
        self.assertEqual(team.slug, "my-awesome-team")

    def test_create_team_via_view_slug_is_unique(self):
        """Test that creating teams with same name generates unique slugs."""
        self.client.force_login(self.user)

        # Create first team
        self.client.post(
            reverse("teams:create_team"),
            {"name": "Dev Team"},
        )

        # Create second team with same name
        self.client.post(
            reverse("teams:create_team"),
            {"name": "Dev Team"},
        )

        # Assert - both teams should have unique slugs
        teams = Team.objects.filter(name="Dev Team").order_by("created_at")
        self.assertEqual(teams.count(), 2)
        self.assertEqual(teams[0].slug, "dev-team")
        self.assertEqual(teams[1].slug, "dev-team-2")

    def test_create_team_via_view_handles_special_characters(self):
        """Test that special characters in team name are handled properly in slug."""
        self.client.force_login(self.user)

        # Act - create team with special characters
        response = self.client.post(
            reverse("teams:create_team"),
            {"name": "Team #1 (Engineering & Design)"},
        )

        # Assert - slug should be sanitized
        self.assertEqual(response.status_code, 302)
        team = Team.objects.get(name="Team #1 (Engineering & Design)")
        self.assertIsNotNone(team.slug)
        self.assertNotEqual(team.slug, "")
        # Should contain only alphanumeric and hyphens
        self.assertRegex(team.slug, r"^[a-z0-9-]+$")

    def test_created_team_dashboard_url_works(self):
        """Test that the dashboard_url property works after creating team via view."""
        self.client.force_login(self.user)

        # Act - create team via POST
        self.client.post(
            reverse("teams:create_team"),
            {"name": "Test Team"},
        )

        # Assert - dashboard_url should not raise NoReverseMatch
        team = Team.objects.get(name="Test Team")
        try:
            url = team.dashboard_url
            self.assertIsNotNone(url)
            self.assertIn("test-team", url)
        except Exception as e:
            self.fail(f"team.dashboard_url raised exception: {e}")
