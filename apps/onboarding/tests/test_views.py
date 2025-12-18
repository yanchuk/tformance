"""Tests for onboarding views."""

from django.test import TestCase
from django.urls import reverse

from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class OnboardingStartViewTests(TestCase):
    """Tests for onboarding_start view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="testpassword123",
        )

    def test_redirect_to_login_when_not_authenticated(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("onboarding:start"))
        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={reverse('onboarding:start')}",
        )

    def test_redirect_to_app_when_user_has_team(self):
        """Test that users with teams are redirected to /app/ (web:home).

        Regression test: Previously this used web_team:home with team_slug
        which caused NoReverseMatch error.
        """
        self.client.login(username="test@example.com", password="testpassword123")

        # Create a team and add user as member
        team = TeamFactory()
        team.members.add(self.user)

        response = self.client.get(reverse("onboarding:start"))

        # Should redirect to web:home (which is /)
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)

    def test_shows_start_page_when_user_has_no_team(self):
        """Test that users without teams see the onboarding start page."""
        self.client.login(username="test@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "onboarding/start.html")


class GithubConnectViewTests(TestCase):
    """Tests for github_connect view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="test2@example.com",
            email="test2@example.com",
            password="testpassword123",
        )

    def test_redirect_to_app_when_user_has_team(self):
        """Test that users with teams are redirected to /app/ (web:home).

        Regression test: Previously this used web_team:home with team_slug
        which caused NoReverseMatch error.
        """
        self.client.login(username="test2@example.com", password="testpassword123")

        # Create a team and add user as member
        team = TeamFactory()
        team.members.add(self.user)

        response = self.client.get(reverse("onboarding:github_connect"))

        # Should redirect to web:home (which is /)
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)


class SelectOrganizationViewTests(TestCase):
    """Tests for select_organization view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="test3@example.com",
            email="test3@example.com",
            password="testpassword123",
        )

    def test_redirect_to_app_when_user_has_team(self):
        """Test that users with teams are redirected to /app/ (web:home).

        Regression test: Previously this used web_team:home with team_slug
        which caused NoReverseMatch error.
        """
        self.client.login(username="test3@example.com", password="testpassword123")

        # Create a team and add user as member
        team = TeamFactory()
        team.members.add(self.user)

        response = self.client.get(reverse("onboarding:select_org"))

        # Should redirect to web:home (which is /)
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)
