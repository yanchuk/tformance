from unittest import skip

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.teams.models import Invitation, Membership, Team
from apps.users.models import CustomUser


@override_settings(ACCOUNT_ADAPTER="apps.teams.adapter.AcceptInvitationAdapter", TURNSTILE_SECRET=None)
class TestSignupView(TestCase):
    """Tests for the signup flow.

    NOTE: Email/password signup has been removed in favor of OAuth-only auth
    (GitHub/Google). The tests below are skipped as they test the old email/password
    flow. OAuth signup is tested via E2E tests.

    Invitation handling for OAuth users is done in apps.teams.adapter.AcceptInvitationAdapter.
    """

    @skip("Email/password signup removed - using OAuth only (GitHub/Google)")
    def test_signup_creates_user_without_team(self):
        """New users should be created without a team."""
        password = "Super Secret Pa$$word!"
        data = {
            "email": "alice@example.com",
            "password1": password,
            "terms_agreement": True,
        }
        if "password2*" in settings.ACCOUNT_SIGNUP_FIELDS:
            data["password2"] = password

        response = self.client.post(
            reverse("account_signup"),
            data=data,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        # User should be created
        self.assertEqual(1, CustomUser.objects.count())
        user = CustomUser.objects.get()
        self.assertEqual("alice@example.com", user.email)

        # No team should be created
        self.assertEqual(0, Team.objects.count())
        self.assertEqual(0, user.teams.count())

    @skip("Email/password signup removed - using OAuth only (GitHub/Google)")
    def test_signup_with_invitation_joins_existing_team(self):
        """Users signing up with an invitation should join the existing team."""
        # Create admin user who sent the invitation
        admin_user = CustomUser.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="adminpass",
        )

        # Create existing team and add admin
        team = Team.objects.create(name="Acme Corp", slug="acme-corp")
        Membership.objects.create(team=team, user=admin_user, role="admin")

        invitation = Invitation.objects.create(
            team=team,
            email="bob@example.com",
            invited_by=admin_user,
        )

        password = "Super Secret Pa$$word!"
        data = {
            "email": "bob@example.com",
            "password1": password,
            "terms_agreement": True,
            "invitation_id": str(invitation.id),
        }
        if "password2*" in settings.ACCOUNT_SIGNUP_FIELDS:
            data["password2"] = password

        # Note: invitation_id must also be in URL for the signal to pick it up
        signup_url = f"{reverse('account_signup')}?invitation_id={invitation.id}"
        response = self.client.post(
            signup_url,
            data=data,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        # User should be created (2 total: admin + new user)
        self.assertEqual(2, CustomUser.objects.count())
        user = CustomUser.objects.get(email="bob@example.com")
        self.assertEqual("bob@example.com", user.email)

        # User should be member of the invited team
        self.assertEqual(1, user.teams.count())
        self.assertEqual(team, user.teams.first())

        # Invitation should be marked as accepted
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_accepted)

    @skip("Email/password signup removed - using OAuth only (GitHub/Google)")
    def test_signup_with_invalid_invitation_shows_error(self):
        """Signing up with invalid invitation ID should show error."""
        password = "Super Secret Pa$$word!"
        data = {
            "email": "charlie@example.com",
            "password1": password,
            "terms_agreement": True,
            "invitation_id": "00000000-0000-0000-0000-000000000000",
        }
        if "password2*" in settings.ACCOUNT_SIGNUP_FIELDS:
            data["password2"] = password

        response = self.client.post(
            reverse("account_signup"),
            data=data,
            follow=True,
        )

        # Should show error, no user created
        self.assertContains(response, "could not be found")
        self.assertEqual(0, CustomUser.objects.count())

    @skip("Email/password signup removed - using OAuth only (GitHub/Google)")
    def test_signup_with_wrong_email_for_invitation_shows_error(self):
        """Signing up with different email than invitation should show error."""
        # Create admin user who sent the invitation
        admin_user = CustomUser.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="adminpass",
        )

        team = Team.objects.create(name="Acme Corp", slug="acme-corp")
        Membership.objects.create(team=team, user=admin_user, role="admin")

        invitation = Invitation.objects.create(
            team=team,
            email="invited@example.com",
            invited_by=admin_user,
        )

        password = "Super Secret Pa$$word!"
        data = {
            "email": "different@example.com",
            "password1": password,
            "terms_agreement": True,
            "invitation_id": str(invitation.id),
        }
        if "password2*" in settings.ACCOUNT_SIGNUP_FIELDS:
            data["password2"] = password

        response = self.client.post(
            reverse("account_signup"),
            data=data,
            follow=True,
        )

        # Should show error, only admin user exists (no new user created)
        self.assertContains(response, "must sign up with the email address")
        self.assertEqual(1, CustomUser.objects.count())  # Only the admin user
