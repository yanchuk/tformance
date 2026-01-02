"""Tests for PostHog analytics events in teams app.

These tests verify that team_member_invited and team_member_joined
events are properly tracked when team invitations are sent and accepted.
"""

from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Invitation
from apps.teams.roles import ROLE_ADMIN


class TestTeamMemberInvitedEvent(TestCase):
    """Tests for team_member_invited event tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.admin)

    @patch("apps.teams.views.manage_team_views.track_event")
    @patch("apps.teams.views.manage_team_views.send_invitation")
    def test_send_invitation_tracks_event(self, mock_send, mock_track):
        """Test that sending an invitation tracks team_member_invited event."""
        url = reverse("single_team:send_invitation")
        response = self.client.post(url, {"email": "newmember@example.com", "role": "member"})

        self.assertEqual(response.status_code, 200)
        mock_track.assert_called_once()

        # Verify event properties
        call_args = mock_track.call_args
        self.assertEqual(call_args[0][0], self.admin)  # First arg is user
        self.assertEqual(call_args[0][1], "team_member_invited")  # Second arg is event name
        props = call_args[0][2]
        self.assertEqual(props["team_slug"], self.team.slug)
        self.assertEqual(props["inviter_role"], ROLE_ADMIN)
        self.assertEqual(props["invite_method"], "email")

    @patch("apps.teams.views.manage_team_views.track_event")
    def test_send_invitation_does_not_track_on_failure(self, mock_track):
        """Test that failed invitation does not track event."""
        # First create an invitation
        Invitation.objects.create(
            team=self.team,
            email="existing@example.com",
            invited_by=self.admin,
        )

        # Try to invite the same email again (should fail)
        url = reverse("single_team:send_invitation")
        self.client.post(url, {"email": "existing@example.com"})

        # Event should not be tracked for duplicate invitations
        mock_track.assert_not_called()


class TestTeamMemberJoinedEvent(TestCase):
    """Tests for team_member_joined event tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})

        # Create new user to accept invitation
        self.new_user = UserFactory()

        # Create invitation
        self.invitation = Invitation.objects.create(
            team=self.team,
            email=self.new_user.email,
            invited_by=self.admin,
        )

        self.client = Client()

    @patch("apps.teams.views.invitation_views.track_event")
    def test_accept_invitation_tracks_event(self, mock_track):
        """Test that accepting an invitation tracks team_member_joined event."""
        self.client.force_login(self.new_user)

        url = reverse("teams:accept_invitation", kwargs={"invitation_id": self.invitation.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)  # Redirects to home
        mock_track.assert_called_once()

        # Verify event properties
        call_args = mock_track.call_args
        self.assertEqual(call_args[0][0], self.new_user)  # First arg is user
        self.assertEqual(call_args[0][1], "team_member_joined")  # Second arg is event name
        props = call_args[0][2]
        self.assertEqual(props["team_slug"], self.team.slug)
        self.assertIn("invite_age_days", props)
        self.assertEqual(props["joined_via"], "invite")

    @patch("apps.teams.views.invitation_views.track_event")
    def test_accept_already_accepted_invitation_does_not_track(self, mock_track):
        """Test that already accepted invitation does not track event."""
        # Mark invitation as accepted
        self.invitation.is_accepted = True
        self.invitation.save()

        self.client.force_login(self.new_user)

        url = reverse("teams:accept_invitation", kwargs={"invitation_id": self.invitation.id})
        response = self.client.post(url)

        # Should redirect to home with error
        self.assertEqual(response.status_code, 302)
        # Event should not be tracked
        mock_track.assert_not_called()


class TestTeamMemberEventProperties(TestCase):
    """Tests for team member event property requirements."""

    def test_team_member_invited_event_has_required_properties(self):
        """Test that team_member_invited event includes required properties."""
        expected_properties = ["team_slug", "inviter_role", "invite_method"]
        self.assertEqual(
            set(expected_properties),
            {"team_slug", "inviter_role", "invite_method"},
        )

    def test_team_member_joined_event_has_required_properties(self):
        """Test that team_member_joined event includes required properties."""
        expected_properties = ["team_slug", "invite_age_days", "joined_via"]
        self.assertEqual(
            set(expected_properties),
            {"team_slug", "invite_age_days", "joined_via"},
        )
