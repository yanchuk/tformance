"""Tests for invitation views."""

from django.test import TestCase

from apps.teams.models import Invitation, Team
from apps.users.models import CustomUser


class AcceptInvitationViewTests(TestCase):
    """Tests for accept_invitation view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.admin = CustomUser.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="testpassword123",
        )
        self.team.members.add(self.admin)
        self.invitation = Invitation.objects.create(
            team=self.team,
            email="invitee@example.com",
            invited_by=self.admin,
        )

    def test_invalid_uuid_format_returns_404(self):
        """Test that invalid UUID format returns 404 instead of 500.

        Regression test: Previously invalid UUIDs caused ValidationError (500).
        """
        response = self.client.get("/teams/invitation/invalid-uuid/")
        self.assertEqual(response.status_code, 404)

    def test_invalid_uuid_with_special_chars_returns_404(self):
        """Test that UUIDs with special characters return 404."""
        response = self.client.get("/teams/invitation/not-a-uuid-at-all!/")
        self.assertEqual(response.status_code, 404)

    def test_valid_uuid_format_non_existent_returns_404(self):
        """Test that valid UUID format but non-existent invitation returns 404."""
        response = self.client.get("/teams/invitation/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, 404)

    def test_valid_invitation_loads(self):
        """Test that valid invitation loads the accept page."""
        response = self.client.get(f"/teams/invitation/{self.invitation.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "teams/accept_invite.html")


class SignupAfterInviteViewTests(TestCase):
    """Tests for SignupAfterInvite view."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.admin = CustomUser.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="testpassword123",
        )
        self.team.members.add(self.admin)
        self.invitation = Invitation.objects.create(
            team=self.team,
            email="invitee@example.com",
            invited_by=self.admin,
        )

    def test_invalid_uuid_format_returns_404(self):
        """Test that invalid UUID format returns 404 instead of 500.

        Regression test: Previously invalid UUIDs caused ValidationError (500).
        """
        response = self.client.get("/teams/invitation/invalid-uuid/signup/")
        self.assertEqual(response.status_code, 404)

    def test_valid_uuid_format_non_existent_returns_404(self):
        """Test that valid UUID format but non-existent invitation returns 404."""
        response = self.client.get("/teams/invitation/00000000-0000-0000-0000-000000000000/signup/")
        self.assertEqual(response.status_code, 404)

    def test_valid_invitation_loads_signup(self):
        """Test that valid invitation loads the signup page."""
        response = self.client.get(f"/teams/invitation/{self.invitation.id}/signup/")
        self.assertEqual(response.status_code, 200)
        # Should show signup form with pre-filled email
        self.assertContains(response, "invitee@example.com")
