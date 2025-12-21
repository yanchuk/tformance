"""Tests for support app views."""

from django.test import Client, TestCase
from django.urls import reverse

from apps.users.models import CustomUser


class TestHijackUserView(TestCase):
    """Tests for hijack_user view."""

    def setUp(self):
        """Create test users."""
        self.client = Client()
        self.superuser = CustomUser.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )
        self.staff_user = CustomUser.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staffpass123",
            is_staff=True,
        )
        self.regular_user = CustomUser.objects.create_user(
            username="user",
            email="user@example.com",
            password="userpass123",
        )
        self.url = reverse("support:hijack_user")

    def test_superuser_can_access_hijack_view(self):
        """Test that superuser can access the hijack user view."""
        self.client.login(email="admin@example.com", password="adminpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_hijack_view_contains_form(self):
        """Test that hijack view contains the form."""
        self.client.login(email="admin@example.com", password="adminpass123")
        response = self.client.get(self.url)
        self.assertIn("form", response.context)

    def test_hijack_view_contains_redirect_url(self):
        """Test that hijack view contains redirect_url in context."""
        self.client.login(email="admin@example.com", password="adminpass123")
        response = self.client.get(self.url)
        self.assertIn("redirect_url", response.context)

    def test_staff_non_superuser_cannot_access(self):
        """Test that staff user who is not superuser cannot access."""
        self.client.login(email="staff@example.com", password="staffpass123")
        response = self.client.get(self.url)
        # Should redirect to 404 (as per login_url="/404")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/404", response.url)

    def test_regular_user_cannot_access(self):
        """Test that regular user cannot access hijack view."""
        self.client.login(email="user@example.com", password="userpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_anonymous_user_cannot_access(self):
        """Test that anonymous user cannot access hijack view."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_hijack_view_uses_correct_template(self):
        """Test that hijack view uses the correct template."""
        self.client.login(email="admin@example.com", password="adminpass123")
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "support/hijack_user.html")
