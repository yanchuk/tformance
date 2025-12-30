"""Tests for team role checking functions."""

from django.test import TestCase

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER, is_admin, is_member


class TestRoles(TestCase):
    """Tests for is_admin and is_member role checking functions."""

    def setUp(self):
        """Set up test fixtures for each test."""
        self.team1 = TeamFactory()
        self.team2 = TeamFactory()

    def test_is_admin_returns_true_for_admin_role(self):
        """is_admin returns True when user has admin role on team."""
        user = UserFactory()
        self.team1.members.add(user, through_defaults={"role": ROLE_ADMIN})

        self.assertTrue(is_admin(user, self.team1))

    def test_is_admin_returns_false_for_member_role(self):
        """is_admin returns False when user has member role (not admin)."""
        user = UserFactory()
        self.team1.members.add(user, through_defaults={"role": ROLE_MEMBER})

        self.assertFalse(is_admin(user, self.team1))

    def test_is_admin_returns_false_for_other_team(self):
        """is_admin returns False when user is admin on different team."""
        user = UserFactory()
        self.team1.members.add(user, through_defaults={"role": ROLE_ADMIN})

        self.assertFalse(is_admin(user, self.team2))

    def test_is_member_returns_true_for_admin_role(self):
        """is_member returns True when user has admin role (admin is also member)."""
        user = UserFactory()
        self.team1.members.add(user, through_defaults={"role": ROLE_ADMIN})

        self.assertTrue(is_member(user, self.team1))

    def test_is_member_returns_true_for_member_role(self):
        """is_member returns True when user has member role."""
        user = UserFactory()
        self.team1.members.add(user, through_defaults={"role": ROLE_MEMBER})

        self.assertTrue(is_member(user, self.team1))

    def test_is_member_returns_false_for_other_team(self):
        """is_member returns False when user is member of different team."""
        user = UserFactory()
        self.team1.members.add(user, through_defaults={"role": ROLE_MEMBER})

        self.assertFalse(is_member(user, self.team2))

    def test_is_member_returns_false_for_non_member(self):
        """is_member returns False when user is not a member of any team."""
        user = UserFactory()

        self.assertFalse(is_member(user, self.team1))
        self.assertFalse(is_member(user, self.team2))
