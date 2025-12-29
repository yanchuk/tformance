"""Tests for GitHub UX messaging improvements on onboarding start page.

Users who signed up via GitHub OAuth should see different messaging than
users who signed up via email, since they already have a GitHub connection
and just need to grant repository access.
"""

from allauth.socialaccount.models import SocialAccount
from django.test import TestCase
from django.urls import reverse

from apps.users.models import CustomUser


class TestGitHubUXMessagingEmailSignup(TestCase):
    """Tests for users who signed up via email (no GitHub social account)."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="email_user@example.com",
            email="email_user@example.com",
            password="testpassword123",
        )

    def test_email_user_sees_connect_github_heading(self):
        """Test that email signup user sees 'Connect Your GitHub Organization' heading."""
        self.client.login(username="email_user@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect Your GitHub Organization")

    def test_email_user_sees_connect_github_button(self):
        """Test that email signup user sees 'Connect GitHub' button text."""
        self.client.login(username="email_user@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect GitHub")

    def test_email_user_context_has_github_social_false(self):
        """Test that email signup user gets has_github_social=False in context."""
        self.client.login(username="email_user@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("has_github_social", response.context)
        self.assertFalse(response.context["has_github_social"])


class TestGitHubUXMessagingGitHubSignup(TestCase):
    """Tests for users who signed up via GitHub OAuth (has SocialAccount)."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="github_user@example.com",
            email="github_user@example.com",
            password="testpassword123",
        )
        # Create GitHub social account to simulate GitHub OAuth signup
        SocialAccount.objects.create(
            user=self.user,
            provider="github",
            uid="12345678",
        )

    def test_github_user_sees_grant_access_heading(self):
        """Test that GitHub signup user sees 'Grant Repository Access' heading."""
        self.client.login(username="github_user@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Grant Repository Access")
        # Should NOT see the email user heading
        self.assertNotContains(response, "Connect Your GitHub Organization")

    def test_github_user_sees_grant_access_button(self):
        """Test that GitHub signup user sees 'Grant Access' button text."""
        self.client.login(username="github_user@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Grant Access")

    def test_github_user_context_has_github_social_true(self):
        """Test that GitHub signup user gets has_github_social=True in context."""
        self.client.login(username="github_user@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("has_github_social", response.context)
        self.assertTrue(response.context["has_github_social"])


class TestGitHubUXMessagingOtherProviders(TestCase):
    """Tests to ensure only GitHub social accounts affect the messaging."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="google_user@example.com",
            email="google_user@example.com",
            password="testpassword123",
        )
        # Create non-GitHub social account (e.g., Google)
        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="google-12345",
        )

    def test_non_github_social_user_sees_connect_github_heading(self):
        """Test that user with non-GitHub social account sees 'Connect' heading."""
        self.client.login(username="google_user@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect Your GitHub Organization")

    def test_non_github_social_user_context_has_github_social_false(self):
        """Test that user with non-GitHub social account gets has_github_social=False."""
        self.client.login(username="google_user@example.com", password="testpassword123")

        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("has_github_social", response.context)
        self.assertFalse(response.context["has_github_social"])
