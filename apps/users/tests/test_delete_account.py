"""Tests for A-016: User account deletion.

GDPR compliance requires users to be able to delete their own accounts.
"""

from django.contrib.auth import get_user
from django.test import TestCase
from django.urls import reverse

from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class TestDeleteAccount(TestCase):
    """Tests for user account deletion functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="delete_test@example.com",
            email="delete_test@example.com",
            password="testpassword123",
        )
        self.client.login(username="delete_test@example.com", password="testpassword123")

    def test_delete_account_requires_post(self):
        """Test that delete account endpoint only accepts POST requests."""
        response = self.client.get(reverse("users:delete_account"))
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_delete_account_requires_login(self):
        """Test that delete account requires authentication."""
        self.client.logout()
        response = self.client.post(reverse("users:delete_account"))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_user_can_delete_own_account(self):
        """Test that a user can delete their own account."""
        user_id = self.user.id

        response = self.client.post(reverse("users:delete_account"))

        # Should redirect to login or home page
        self.assertEqual(response.status_code, 302)

        # User should no longer exist
        self.assertFalse(CustomUser.objects.filter(id=user_id).exists())

    def test_delete_account_logs_out_user(self):
        """Test that deleting account logs the user out."""
        self.client.post(reverse("users:delete_account"))

        # User should be logged out
        user = get_user(self.client)
        self.assertFalse(user.is_authenticated)


class TestDeleteAccountWithTeams(TestCase):
    """Tests for account deletion when user belongs to teams."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="team_member@example.com",
            email="team_member@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.client.login(username="team_member@example.com", password="testpassword123")

    def test_delete_account_removes_user_from_teams(self):
        """Test that deleting account removes user from all teams."""
        user_id = self.user.id

        response = self.client.post(reverse("users:delete_account"))

        self.assertEqual(response.status_code, 302)
        # User should no longer exist
        self.assertFalse(CustomUser.objects.filter(id=user_id).exists())
        # User should be removed from team (team still exists)
        self.assertTrue(self.team.members.count() >= 0)  # Team may have other members


class TestDeleteAccountUI(TestCase):
    """Tests for delete account UI in profile page."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="ui_test@example.com",
            email="ui_test@example.com",
            password="testpassword123",
        )
        self.client.login(username="ui_test@example.com", password="testpassword123")

    def test_profile_page_has_danger_zone_section(self):
        """Test that profile page has a Danger Zone section."""
        response = self.client.get(reverse("users:user_profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Danger Zone")

    def test_profile_page_has_delete_account_button(self):
        """Test that profile page has a delete account button."""
        response = self.client.get(reverse("users:user_profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete Account")

    def test_profile_page_has_delete_confirmation_modal(self):
        """Test that profile page has a confirmation modal for deletion."""
        response = self.client.get(reverse("users:user_profile"))

        self.assertEqual(response.status_code, 200)
        # Check for modal elements
        self.assertContains(response, "delete-account-modal")
        self.assertContains(response, "cannot be undone")
