"""Security tests for GitHub App callback slug collision vulnerability (Bug 13).

Verifies that the github_app_callback view never reuses an existing team
when creating a new one during onboarding. Previously, get_or_create on
the slug would give an attacker admin access to another team.
"""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.integrations.models import GitHubAppInstallation
from apps.metrics.factories import TeamFactory
from apps.teams.models import Membership
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser


def _make_installation_response(login, account_id=12345678, installation_id=None):
    """Build a mock GitHub API response for get_installation."""
    return {
        "id": installation_id or account_id,
        "account": {
            "login": login,
            "id": account_id,
            "type": "Organization",
        },
        "permissions": {"contents": "read"},
        "events": ["pull_request"],
        "repository_selection": "selected",
    }


class GitHubAppCallbackSlugCollisionTests(TestCase):
    """Regression tests for Bug 13: onboarding slug collision vulnerability."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="attacker@example.com",
            email="attacker@example.com",
            password="testpassword123",
        )
        self.callback_url = reverse("onboarding:github_app_callback")

    def _create_state(self, user_id: int) -> str:
        from apps.auth.oauth_state import create_oauth_state

        return create_oauth_state("github_app_install", user_id=user_id)

    def _do_callback(self, installation_id, state):
        return self.client.get(
            self.callback_url,
            {
                "installation_id": str(installation_id),
                "setup_action": "install",
                "state": state,
            },
        )

    @patch("apps.integrations.services.github_app.get_installation")
    def test_callback_creates_new_team_when_slug_exists(self, mock_get_installation):
        """Pre-existing team 'acme' must not be hijacked when org 'Acme' onboards."""
        # Existing team owned by someone else
        victim_team = TeamFactory(name="Acme Corp", slug="acme")
        victim_user = CustomUser.objects.create_user(
            username="victim@example.com",
            email="victim@example.com",
            password="testpassword123",
        )
        Membership.objects.create(team=victim_team, user=victim_user, role=ROLE_ADMIN)

        mock_get_installation.return_value = _make_installation_response(
            login="Acme", account_id=99990001, installation_id=88880001
        )

        self.client.login(username="attacker@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        response = self._do_callback(88880001, state)

        # Should redirect to select_repos (successful onboarding)
        self.assertRedirects(response, reverse("onboarding:select_repos"))

        # A NEW team must have been created
        installation = GitHubAppInstallation.objects.get(installation_id=88880001)
        new_team = installation.team

        # The new team must NOT be the victim's team
        self.assertNotEqual(new_team.id, victim_team.id)

        # The new team slug should be unique (e.g. "acme-2")
        self.assertNotEqual(new_team.slug, "acme")
        self.assertTrue(new_team.slug.startswith("acme"))

        # Attacker must NOT be a member of the victim's team
        self.assertFalse(victim_team.members.filter(id=self.user.id).exists())

        # Attacker IS admin of their own new team
        self.assertTrue(Membership.objects.filter(team=new_team, user=self.user, role=ROLE_ADMIN).exists())

        # Victim's team is untouched
        victim_team.refresh_from_db()
        self.assertEqual(victim_team.members.count(), 1)
        self.assertEqual(victim_team.members.first().id, victim_user.id)

    @patch("apps.integrations.services.github_app.get_installation")
    def test_callback_creates_team_normally(self, mock_get_installation):
        """When no slug collision exists, team is created with the plain slug."""
        mock_get_installation.return_value = _make_installation_response(
            login="NewOrg", account_id=99990002, installation_id=88880002
        )

        self.client.login(username="attacker@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        response = self._do_callback(88880002, state)

        self.assertRedirects(response, reverse("onboarding:select_repos"))

        # Team created with expected name and slug
        installation = GitHubAppInstallation.objects.get(installation_id=88880002)
        team = installation.team
        self.assertEqual(team.name, "NewOrg")
        self.assertEqual(team.slug, "neworg")

        # User is admin
        self.assertTrue(Membership.objects.filter(team=team, user=self.user, role=ROLE_ADMIN).exists())
