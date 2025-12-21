from django.db import IntegrityError
from django.test import TestCase

from apps.metrics.models import (
    TeamMember,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


class TestTeamMemberModel(TestCase):
    """Tests for TeamMember model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_team_member_creation_minimal_fields(self):
        """Test that TeamMember can be created with just display_name and team."""
        member = TeamMember.objects.create(team=self.team1, display_name="John Doe")
        self.assertEqual(member.display_name, "John Doe")
        self.assertEqual(member.team, self.team1)
        self.assertIsNotNone(member.pk)

    def test_team_member_creation_with_all_integration_fields(self):
        """Test that TeamMember can be created with all integration fields."""
        member = TeamMember.objects.create(
            team=self.team1,
            display_name="Jane Smith",
            email="jane@example.com",
            github_username="janesmith",
            github_id="12345",
            jira_account_id="jira-123",
            slack_user_id="U12345",
        )
        self.assertEqual(member.display_name, "Jane Smith")
        self.assertEqual(member.email, "jane@example.com")
        self.assertEqual(member.github_username, "janesmith")
        self.assertEqual(member.github_id, "12345")
        self.assertEqual(member.jira_account_id, "jira-123")
        self.assertEqual(member.slack_user_id, "U12345")

    def test_team_member_role_choices_developer(self):
        """Test that TeamMember role 'developer' works correctly."""
        member = TeamMember.objects.create(team=self.team1, display_name="Dev User", role="developer")
        self.assertEqual(member.role, "developer")

    def test_team_member_role_choices_lead(self):
        """Test that TeamMember role 'lead' works correctly."""
        member = TeamMember.objects.create(team=self.team1, display_name="Lead User", role="lead")
        self.assertEqual(member.role, "lead")

    def test_team_member_role_choices_admin(self):
        """Test that TeamMember role 'admin' works correctly."""
        member = TeamMember.objects.create(team=self.team1, display_name="Admin User", role="admin")
        self.assertEqual(member.role, "admin")

    def test_team_member_role_default_is_developer(self):
        """Test that TeamMember role defaults to 'developer'."""
        member = TeamMember.objects.create(team=self.team1, display_name="Default Role User")
        self.assertEqual(member.role, "developer")

    def test_team_member_is_active_default_is_true(self):
        """Test that TeamMember.is_active defaults to True."""
        member = TeamMember.objects.create(team=self.team1, display_name="Active User")
        self.assertTrue(member.is_active)

    def test_unique_constraint_team_github_id_enforced(self):
        """Test that unique constraint on (team, github_id) is enforced when github_id is not blank."""
        TeamMember.objects.create(team=self.team1, display_name="First User", github_id="github-123")
        # Attempt to create another member with the same github_id in the same team
        with self.assertRaises(IntegrityError):
            TeamMember.objects.create(team=self.team1, display_name="Second User", github_id="github-123")

    def test_unique_constraint_team_email_enforced(self):
        """Test that unique constraint on (team, email) is enforced when email is not blank."""
        TeamMember.objects.create(team=self.team1, display_name="First User", email="user@example.com")
        # Attempt to create another member with the same email in the same team
        with self.assertRaises(IntegrityError):
            TeamMember.objects.create(team=self.team1, display_name="Second User", email="user@example.com")

    def test_same_github_id_allowed_for_different_teams(self):
        """Test that same github_id is allowed for different teams."""
        member1 = TeamMember.objects.create(team=self.team1, display_name="User in Team 1", github_id="github-123")
        member2 = TeamMember.objects.create(team=self.team2, display_name="User in Team 2", github_id="github-123")
        self.assertEqual(member1.github_id, member2.github_id)
        self.assertNotEqual(member1.team, member2.team)

    def test_same_email_allowed_for_different_teams(self):
        """Test that same email is allowed for different teams."""
        member1 = TeamMember.objects.create(team=self.team1, display_name="User in Team 1", email="shared@example.com")
        member2 = TeamMember.objects.create(team=self.team2, display_name="User in Team 2", email="shared@example.com")
        self.assertEqual(member1.email, member2.email)
        self.assertNotEqual(member1.team, member2.team)

    def test_blank_github_id_allowed_multiple_times_per_team(self):
        """Test that blank github_id is allowed multiple times per team (no unique constraint)."""
        member1 = TeamMember.objects.create(team=self.team1, display_name="User Without GitHub 1", github_id="")
        member2 = TeamMember.objects.create(team=self.team1, display_name="User Without GitHub 2", github_id="")
        # Both should be created successfully
        self.assertEqual(member1.github_id, "")
        self.assertEqual(member2.github_id, "")
        self.assertEqual(member1.team, member2.team)

    def test_blank_email_allowed_multiple_times_per_team(self):
        """Test that blank email is allowed multiple times per team (no unique constraint)."""
        member1 = TeamMember.objects.create(team=self.team1, display_name="User Without Email 1", email="")
        member2 = TeamMember.objects.create(team=self.team1, display_name="User Without Email 2", email="")
        # Both should be created successfully
        self.assertEqual(member1.email, "")
        self.assertEqual(member2.email, "")
        self.assertEqual(member1.team, member2.team)

    def test_for_team_manager_filters_by_current_team(self):
        """Test that TeamMember.for_team manager filters by current team context."""
        # Create members for both teams
        member1 = TeamMember.objects.create(team=self.team1, display_name="Team 1 Member")
        member2 = TeamMember.objects.create(team=self.team2, display_name="Team 2 Member")

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_members = list(TeamMember.for_team.all())
        self.assertEqual(len(team1_members), 1)
        self.assertEqual(team1_members[0].pk, member1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_members = list(TeamMember.for_team.all())
        self.assertEqual(len(team2_members), 1)
        self.assertEqual(team2_members[0].pk, member2.pk)

    def test_for_team_manager_with_context_manager(self):
        """Test that TeamMember.for_team works with context manager."""
        # Create members for both teams
        TeamMember.objects.create(team=self.team1, display_name="Team 1 Member")
        TeamMember.objects.create(team=self.team2, display_name="Team 2 Member")

        with current_team(self.team1):
            self.assertEqual(TeamMember.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(TeamMember.for_team.count(), 1)

    def test_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that TeamMember.for_team returns empty queryset when no team is set."""
        TeamMember.objects.create(team=self.team1, display_name="Team 1 Member")

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(TeamMember.for_team.count(), 0)

    def test_team_member_str_returns_display_name(self):
        """Test that TeamMember.__str__ returns display_name."""
        member = TeamMember.objects.create(team=self.team1, display_name="John Doe")
        self.assertEqual(str(member), "John Doe")

    def test_team_member_has_created_at_from_base_model(self):
        """Test that TeamMember inherits created_at from BaseModel."""
        member = TeamMember.objects.create(team=self.team1, display_name="Test User")
        self.assertIsNotNone(member.created_at)

    def test_team_member_has_updated_at_from_base_model(self):
        """Test that TeamMember inherits updated_at from BaseModel."""
        member = TeamMember.objects.create(team=self.team1, display_name="Test User")
        self.assertIsNotNone(member.updated_at)

    def test_team_member_has_team_foreign_key_from_base_team_model(self):
        """Test that TeamMember has team ForeignKey from BaseTeamModel."""
        member = TeamMember.objects.create(team=self.team1, display_name="Test User")
        self.assertEqual(member.team, self.team1)
        self.assertIsInstance(member.team, Team)

    def test_team_member_updated_at_changes_on_save(self):
        """Test that updated_at timestamp changes when model is saved."""
        member = TeamMember.objects.create(team=self.team1, display_name="Test User")
        original_updated_at = member.updated_at

        # Update and save
        member.display_name = "Updated Name"
        member.save()

        # Refresh from database
        member.refresh_from_db()
        self.assertGreater(member.updated_at, original_updated_at)
