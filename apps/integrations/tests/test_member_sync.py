"""Tests for GitHub member sync service."""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations.services.member_sync import sync_github_members
from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.metrics.models import TeamMember


class TestSyncGitHubMembers(TestCase):
    """Tests for sync_github_members service function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.access_token = "gho_test_token_12345"
        self.org_slug = "acme-corp"

    @patch("apps.integrations.services.member_sync.get_user_details")
    @patch("apps.integrations.services.member_sync.get_organization_members")
    def test_sync_creates_new_team_member_for_new_github_user(self, mock_get_org_members, mock_get_user_details):
        """Test that sync creates a new TeamMember for a GitHub user not in the database."""
        # Mock GitHub API responses
        mock_get_org_members.return_value = [
            {
                "login": "johndoe",
                "id": 12345,
                "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                "type": "User",
            }
        ]
        mock_get_user_details.return_value = {
            "login": "johndoe",
            "id": 12345,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }

        # Run sync
        result = sync_github_members(self.team, self.access_token, self.org_slug)

        # Assert: TeamMember was created
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 1)
        member = TeamMember.objects.get(team=self.team, github_id="12345")
        self.assertEqual(member.github_username, "johndoe")
        self.assertEqual(member.display_name, "John Doe")
        self.assertEqual(member.email, "john.doe@example.com")
        self.assertTrue(member.is_active)

        # Assert: Result shows 1 created
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["unchanged"], 0)
        self.assertEqual(result["failed"], 0)

        # Assert: get_user_details was called for new member
        mock_get_user_details.assert_called_once_with(self.access_token, "johndoe")

    @patch("apps.integrations.services.member_sync.get_user_details")
    @patch("apps.integrations.services.member_sync.get_organization_members")
    def test_sync_updates_existing_team_member_if_username_changed(self, mock_get_org_members, mock_get_user_details):
        """Test that sync updates an existing TeamMember if their GitHub username has changed."""
        # Create existing member with old username
        existing_member = TeamMemberFactory(
            team=self.team,
            github_id="12345",
            github_username="john_old",
            display_name="Old Name",
            email="old@example.com",
        )

        # Mock GitHub API responses with updated username
        mock_get_org_members.return_value = [
            {
                "login": "johndoe",
                "id": 12345,
                "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                "type": "User",
            }
        ]

        # Run sync
        result = sync_github_members(self.team, self.access_token, self.org_slug)

        # Assert: Member was updated, not created
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 1)
        existing_member.refresh_from_db()
        self.assertEqual(existing_member.github_username, "johndoe")

        # Assert: Result shows 1 updated
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["unchanged"], 0)
        self.assertEqual(result["failed"], 0)

        # Assert: get_user_details was NOT called for existing member
        mock_get_user_details.assert_not_called()

    @patch("apps.integrations.services.member_sync.get_user_details")
    @patch("apps.integrations.services.member_sync.get_organization_members")
    def test_sync_fetches_user_details_for_new_members_only(self, mock_get_org_members, mock_get_user_details):
        """Test that sync calls get_user_details only for new members to get name and email."""
        # Create one existing member
        TeamMemberFactory(
            team=self.team,
            github_id="11111",
            github_username="existing_user",
        )

        # Mock GitHub API responses: 1 existing + 1 new
        mock_get_org_members.return_value = [
            {
                "login": "existing_user",
                "id": 11111,
                "avatar_url": "https://avatars.githubusercontent.com/u/11111",
                "type": "User",
            },
            {
                "login": "newuser",
                "id": 22222,
                "avatar_url": "https://avatars.githubusercontent.com/u/22222",
                "type": "User",
            },
        ]
        mock_get_user_details.return_value = {
            "login": "newuser",
            "id": 22222,
            "name": "New User",
            "email": "new@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/22222",
        }

        # Run sync
        result = sync_github_members(self.team, self.access_token, self.org_slug)

        # Assert: 2 members total (1 existing + 1 new)
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 2)

        # Assert: get_user_details called only once for new member
        mock_get_user_details.assert_called_once_with(self.access_token, "newuser")

        # Assert: Result shows 1 created, 0 updated, 1 unchanged
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["failed"], 0)

    @patch("apps.integrations.services.member_sync.get_user_details")
    @patch("apps.integrations.services.member_sync.get_organization_members")
    def test_sync_handles_private_email_gracefully(self, mock_get_org_members, mock_get_user_details):
        """Test that sync handles users with private email (None) without errors."""
        # Mock GitHub API responses with null email
        mock_get_org_members.return_value = [
            {
                "login": "privateuser",
                "id": 99999,
                "avatar_url": "https://avatars.githubusercontent.com/u/99999",
                "type": "User",
            }
        ]
        mock_get_user_details.return_value = {
            "login": "privateuser",
            "id": 99999,
            "name": "Private User",
            "email": None,  # Private email
            "avatar_url": "https://avatars.githubusercontent.com/u/99999",
        }

        # Run sync
        result = sync_github_members(self.team, self.access_token, self.org_slug)

        # Assert: TeamMember created with empty email
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 1)
        member = TeamMember.objects.get(team=self.team, github_id="99999")
        self.assertEqual(member.github_username, "privateuser")
        self.assertEqual(member.display_name, "Private User")
        self.assertEqual(member.email, "")  # Should be empty string, not None

        # Assert: Result shows 1 created
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["failed"], 0)

    @patch("apps.integrations.services.member_sync.get_user_details")
    @patch("apps.integrations.services.member_sync.get_organization_members")
    def test_sync_returns_accurate_counts(self, mock_get_org_members, mock_get_user_details):
        """Test that sync returns accurate counts of created, updated, and unchanged members."""
        # Create 2 existing members: 1 unchanged, 1 to be updated
        TeamMemberFactory(
            team=self.team,
            github_id="11111",
            github_username="unchanged_user",
        )
        TeamMemberFactory(
            team=self.team,
            github_id="22222",
            github_username="old_username",  # Will be updated
        )

        # Mock GitHub API: 2 existing (1 unchanged, 1 updated) + 2 new
        mock_get_org_members.return_value = [
            {
                "login": "unchanged_user",
                "id": 11111,
                "avatar_url": "https://avatars.githubusercontent.com/u/11111",
                "type": "User",
            },
            {
                "login": "updated_username",
                "id": 22222,
                "avatar_url": "https://avatars.githubusercontent.com/u/22222",
                "type": "User",
            },
            {
                "login": "newuser1",
                "id": 33333,
                "avatar_url": "https://avatars.githubusercontent.com/u/33333",
                "type": "User",
            },
            {
                "login": "newuser2",
                "id": 44444,
                "avatar_url": "https://avatars.githubusercontent.com/u/44444",
                "type": "User",
            },
        ]

        # Mock get_user_details to return data for new users
        def user_details_side_effect(token, username):
            user_data = {
                "newuser1": {
                    "login": "newuser1",
                    "id": 33333,
                    "name": "New User 1",
                    "email": "new1@example.com",
                    "avatar_url": "https://avatars.githubusercontent.com/u/33333",
                },
                "newuser2": {
                    "login": "newuser2",
                    "id": 44444,
                    "name": "New User 2",
                    "email": "new2@example.com",
                    "avatar_url": "https://avatars.githubusercontent.com/u/44444",
                },
            }
            return user_data[username]

        mock_get_user_details.side_effect = user_details_side_effect

        # Run sync
        result = sync_github_members(self.team, self.access_token, self.org_slug)

        # Assert: Counts are accurate
        self.assertEqual(result["created"], 2, "Should create 2 new members")
        self.assertEqual(result["updated"], 1, "Should update 1 member")
        self.assertEqual(result["unchanged"], 1, "Should leave 1 member unchanged")
        self.assertEqual(result["failed"], 0, "Should have no failures")

        # Assert: Total members is 4
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 4)

    @patch("apps.integrations.services.member_sync.get_user_details")
    @patch("apps.integrations.services.member_sync.get_organization_members")
    def test_sync_is_idempotent(self, mock_get_org_members, mock_get_user_details):
        """Test that running sync twice with same data doesn't duplicate members."""
        # Mock GitHub API responses
        mock_get_org_members.return_value = [
            {
                "login": "johndoe",
                "id": 12345,
                "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                "type": "User",
            }
        ]
        mock_get_user_details.return_value = {
            "login": "johndoe",
            "id": 12345,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }

        # Run sync first time
        result1 = sync_github_members(self.team, self.access_token, self.org_slug)

        # Assert first run: 1 created
        self.assertEqual(result1["created"], 1)
        self.assertEqual(result1["failed"], 0)
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 1)

        # Run sync second time with same data
        result2 = sync_github_members(self.team, self.access_token, self.org_slug)

        # Assert second run: 0 created, 0 updated, 1 unchanged
        self.assertEqual(result2["created"], 0)
        self.assertEqual(result2["updated"], 0)
        self.assertEqual(result2["unchanged"], 1)
        self.assertEqual(result2["failed"], 0)

        # Assert: Still only 1 member (no duplicates)
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 1)

        # Assert: get_user_details was only called on first run
        self.assertEqual(mock_get_user_details.call_count, 1)

    @patch("apps.integrations.services.member_sync.get_user_details")
    @patch("apps.integrations.services.member_sync.get_organization_members")
    def test_sync_continues_on_user_details_failure(self, mock_get_org_members, mock_get_user_details):
        """Test that sync continues when get_user_details fails for one member."""
        # Mock GitHub API responses with 3 new members
        mock_get_org_members.return_value = [
            {
                "login": "user1",
                "id": 11111,
                "avatar_url": "https://avatars.githubusercontent.com/u/11111",
                "type": "User",
            },
            {
                "login": "user2",
                "id": 22222,
                "avatar_url": "https://avatars.githubusercontent.com/u/22222",
                "type": "User",
            },
            {
                "login": "user3",
                "id": 33333,
                "avatar_url": "https://avatars.githubusercontent.com/u/33333",
                "type": "User",
            },
        ]

        # Mock get_user_details to fail for user2, succeed for others
        def user_details_side_effect(token, username):
            if username == "user2":
                raise Exception("API rate limit exceeded")
            user_data = {
                "user1": {
                    "login": "user1",
                    "id": 11111,
                    "name": "User One",
                    "email": "user1@example.com",
                    "avatar_url": "https://avatars.githubusercontent.com/u/11111",
                },
                "user3": {
                    "login": "user3",
                    "id": 33333,
                    "name": "User Three",
                    "email": "user3@example.com",
                    "avatar_url": "https://avatars.githubusercontent.com/u/33333",
                },
            }
            return user_data[username]

        mock_get_user_details.side_effect = user_details_side_effect

        # Run sync
        result = sync_github_members(self.team, self.access_token, self.org_slug)

        # Assert: 2 created (user1, user3), 1 failed (user2)
        self.assertEqual(result["created"], 2, "Should create 2 members")
        self.assertEqual(result["failed"], 1, "Should have 1 failure")
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["unchanged"], 0)

        # Assert: Only 2 members created (user2 was skipped)
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 2)
        self.assertTrue(TeamMember.objects.filter(team=self.team, github_username="user1").exists())
        self.assertFalse(TeamMember.objects.filter(team=self.team, github_username="user2").exists())
        self.assertTrue(TeamMember.objects.filter(team=self.team, github_username="user3").exists())
