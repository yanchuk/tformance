"""Tests for syncing per-user Copilot activity from Seats API to TeamMember."""

from django.test import TestCase

from apps.metrics.factories import TeamFactory, TeamMemberFactory


class TestSyncCopilotMemberActivity(TestCase):
    """Tests for sync_copilot_member_activity function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(
            team=self.team,
            github_username="octocat",
            display_name="Octocat Developer",
        )

    def test_sync_updates_member_copilot_fields(self):
        """Test that sync updates copilot_last_activity_at and copilot_last_editor for matching member."""
        from apps.integrations.services.copilot_metrics import sync_copilot_member_activity

        # Arrange
        seats_data = {
            "total_seats": 25,
            "seats": [
                {
                    "assignee": {"login": "octocat", "id": 12345},
                    "last_activity_at": "2024-01-15T10:30:00Z",
                    "last_activity_editor": "vscode/1.85.1",
                }
            ],
        }

        # Act
        sync_copilot_member_activity(self.team, seats_data)

        # Assert
        self.member.refresh_from_db()
        self.assertIsNotNone(self.member.copilot_last_activity_at)
        self.assertEqual(self.member.copilot_last_activity_at.year, 2024)
        self.assertEqual(self.member.copilot_last_activity_at.month, 1)
        self.assertEqual(self.member.copilot_last_activity_at.day, 15)
        self.assertEqual(self.member.copilot_last_editor, "vscode/1.85.1")

    def test_sync_matches_by_github_username(self):
        """Test that sync matches TeamMember by github_username to assignee.login."""
        from apps.integrations.services.copilot_metrics import sync_copilot_member_activity

        # Arrange - Create another member with different username
        other_member = TeamMemberFactory(
            team=self.team,
            github_username="other_user",
            display_name="Other Developer",
        )

        seats_data = {
            "total_seats": 25,
            "seats": [
                {
                    "assignee": {"login": "octocat", "id": 12345},
                    "last_activity_at": "2024-01-15T10:30:00Z",
                    "last_activity_editor": "vscode/1.85.1",
                }
            ],
        }

        # Act
        sync_copilot_member_activity(self.team, seats_data)

        # Assert - Only octocat member should be updated
        self.member.refresh_from_db()
        other_member.refresh_from_db()

        self.assertIsNotNone(self.member.copilot_last_activity_at)
        self.assertEqual(self.member.copilot_last_editor, "vscode/1.85.1")
        self.assertIsNone(other_member.copilot_last_activity_at)
        self.assertIsNone(other_member.copilot_last_editor)

    def test_sync_handles_no_matching_members(self):
        """Test that sync returns 0 when no members match (no error)."""
        from apps.integrations.services.copilot_metrics import sync_copilot_member_activity

        # Arrange - seats_data has user not in team
        seats_data = {
            "total_seats": 25,
            "seats": [
                {
                    "assignee": {"login": "unknown_user", "id": 99999},
                    "last_activity_at": "2024-01-15T10:30:00Z",
                    "last_activity_editor": "vscode/1.85.1",
                }
            ],
        }

        # Act
        result = sync_copilot_member_activity(self.team, seats_data)

        # Assert
        self.assertEqual(result, 0)
        # Original member should not be updated
        self.member.refresh_from_db()
        self.assertIsNone(self.member.copilot_last_activity_at)

    def test_sync_handles_multiple_members(self):
        """Test that sync updates multiple members from seats array."""
        from apps.integrations.services.copilot_metrics import sync_copilot_member_activity

        # Arrange - Create additional members
        member2 = TeamMemberFactory(
            team=self.team,
            github_username="alice",
            display_name="Alice Developer",
        )
        member3 = TeamMemberFactory(
            team=self.team,
            github_username="bob",
            display_name="Bob Engineer",
        )

        seats_data = {
            "total_seats": 25,
            "seats": [
                {
                    "assignee": {"login": "octocat", "id": 12345},
                    "last_activity_at": "2024-01-15T10:30:00Z",
                    "last_activity_editor": "vscode/1.85.1",
                },
                {
                    "assignee": {"login": "alice", "id": 12346},
                    "last_activity_at": "2024-01-14T09:00:00Z",
                    "last_activity_editor": "jetbrains/2023.3",
                },
                {
                    "assignee": {"login": "bob", "id": 12347},
                    "last_activity_at": "2024-01-13T08:00:00Z",
                    "last_activity_editor": "neovim/0.9.4",
                },
            ],
        }

        # Act
        sync_copilot_member_activity(self.team, seats_data)

        # Assert - All three members should be updated
        self.member.refresh_from_db()
        member2.refresh_from_db()
        member3.refresh_from_db()

        self.assertEqual(self.member.copilot_last_editor, "vscode/1.85.1")
        self.assertEqual(member2.copilot_last_editor, "jetbrains/2023.3")
        self.assertEqual(member3.copilot_last_editor, "neovim/0.9.4")

    def test_sync_returns_count_of_updated_members(self):
        """Test that sync returns count of members updated."""
        from apps.integrations.services.copilot_metrics import sync_copilot_member_activity

        # Arrange - Create additional member
        _member2 = TeamMemberFactory(  # noqa: F841 - member needs to exist for seats sync
            team=self.team,
            github_username="alice",
            display_name="Alice Developer",
        )

        seats_data = {
            "total_seats": 25,
            "seats": [
                {
                    "assignee": {"login": "octocat", "id": 12345},
                    "last_activity_at": "2024-01-15T10:30:00Z",
                    "last_activity_editor": "vscode/1.85.1",
                },
                {
                    "assignee": {"login": "alice", "id": 12346},
                    "last_activity_at": "2024-01-14T09:00:00Z",
                    "last_activity_editor": "jetbrains/2023.3",
                },
                {
                    "assignee": {"login": "unknown_user", "id": 99999},
                    "last_activity_at": "2024-01-13T08:00:00Z",
                    "last_activity_editor": "vscode/1.85.1",
                },
            ],
        }

        # Act
        result = sync_copilot_member_activity(self.team, seats_data)

        # Assert - Should return 2 (octocat and alice, not unknown_user)
        self.assertEqual(result, 2)

    def test_sync_skips_members_without_last_activity(self):
        """Test that sync skips seats where last_activity_at is null."""
        from apps.integrations.services.copilot_metrics import sync_copilot_member_activity

        # Arrange - Create member for inactive seat
        inactive_member = TeamMemberFactory(
            team=self.team,
            github_username="inactive_user",
            display_name="Inactive Developer",
        )

        seats_data = {
            "total_seats": 25,
            "seats": [
                {
                    "assignee": {"login": "octocat", "id": 12345},
                    "last_activity_at": "2024-01-15T10:30:00Z",
                    "last_activity_editor": "vscode/1.85.1",
                },
                {
                    "assignee": {"login": "inactive_user", "id": 12348},
                    "last_activity_at": None,
                    "last_activity_editor": None,
                },
            ],
        }

        # Act
        result = sync_copilot_member_activity(self.team, seats_data)

        # Assert - Only octocat should be updated
        self.assertEqual(result, 1)
        self.member.refresh_from_db()
        inactive_member.refresh_from_db()

        self.assertIsNotNone(self.member.copilot_last_activity_at)
        self.assertIsNone(inactive_member.copilot_last_activity_at)

    def test_sync_is_team_scoped(self):
        """Test that sync only updates members of the specified team."""
        from apps.integrations.services.copilot_metrics import sync_copilot_member_activity

        # Arrange - Create another team with member that has same github_username
        other_team = TeamFactory()
        other_team_member = TeamMemberFactory(
            team=other_team,
            github_username="octocat",  # Same username as self.member
            display_name="Other Team Octocat",
        )

        seats_data = {
            "total_seats": 25,
            "seats": [
                {
                    "assignee": {"login": "octocat", "id": 12345},
                    "last_activity_at": "2024-01-15T10:30:00Z",
                    "last_activity_editor": "vscode/1.85.1",
                }
            ],
        }

        # Act - Sync only for self.team
        result = sync_copilot_member_activity(self.team, seats_data)

        # Assert - Only self.team's member should be updated
        self.assertEqual(result, 1)
        self.member.refresh_from_db()
        other_team_member.refresh_from_db()

        self.assertIsNotNone(self.member.copilot_last_activity_at)
        self.assertEqual(self.member.copilot_last_editor, "vscode/1.85.1")
        # Other team's member should NOT be updated
        self.assertIsNone(other_team_member.copilot_last_activity_at)
        self.assertIsNone(other_team_member.copilot_last_editor)
