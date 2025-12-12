"""Tests for Slack user matching service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import IntegrationCredentialFactory
from apps.integrations.services.slack_user_matching import (
    get_slack_users,
    match_slack_user_to_team_member,
    sync_slack_users,
)
from apps.metrics.factories import TeamFactory, TeamMemberFactory


class TestGetSlackUsers(TestCase):
    """Tests for get_slack_users function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.services.encryption import encrypt

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="slack",
            access_token=encrypt("xoxb-test-slack-token"),
        )

    @patch("apps.integrations.services.slack_user_matching.get_workspace_users")
    @patch("apps.integrations.services.slack_user_matching.get_slack_client")
    def test_returns_list_of_user_dicts_with_required_fields(self, mock_get_client, mock_get_workspace_users):
        """Test that get_slack_users returns list of user dicts with id, email, real_name."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create mock Slack users
        mock_slack_users = [
            {
                "id": "U123456",
                "profile": {
                    "email": "john.doe@example.com",
                    "real_name": "John Doe",
                },
                "is_bot": False,
                "deleted": False,
            },
            {
                "id": "U789012",
                "profile": {
                    "email": "jane.smith@example.com",
                    "real_name": "Jane Smith",
                },
                "is_bot": False,
                "deleted": False,
            },
        ]

        mock_get_workspace_users.return_value = mock_slack_users

        # Act
        result = get_slack_users(self.credential)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # Check first user
        self.assertEqual(result[0]["id"], "U123456")
        self.assertEqual(result[0]["email"], "john.doe@example.com")
        self.assertEqual(result[0]["real_name"], "John Doe")

        # Check second user
        self.assertEqual(result[1]["id"], "U789012")
        self.assertEqual(result[1]["email"], "jane.smith@example.com")
        self.assertEqual(result[1]["real_name"], "Jane Smith")

        # Verify get_workspace_users was called with the client
        mock_get_workspace_users.assert_called_once_with(mock_client)

    @patch("apps.integrations.services.slack_user_matching.get_workspace_users")
    @patch("apps.integrations.services.slack_user_matching.get_slack_client")
    def test_filters_out_users_without_email(self, mock_get_client, mock_get_workspace_users):
        """Test that get_slack_users filters out users without email addresses."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # User with email and user without email
        mock_slack_users = [
            {
                "id": "U123456",
                "profile": {
                    "email": "john.doe@example.com",
                    "real_name": "John Doe",
                },
                "is_bot": False,
                "deleted": False,
            },
            {
                "id": "U789012",
                "profile": {
                    "real_name": "Bot User",
                    # No email field
                },
                "is_bot": True,
                "deleted": False,
            },
        ]

        mock_get_workspace_users.return_value = mock_slack_users

        # Act
        result = get_slack_users(self.credential)

        # Assert - should only return the user with email
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["email"], "john.doe@example.com")


class TestMatchSlackUserToTeamMember(TestCase):
    """Tests for match_slack_user_to_team_member function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_returns_team_member_when_email_matches(self):
        """Test that match_slack_user_to_team_member returns TeamMember when email matches."""
        # Arrange
        member = TeamMemberFactory(team=self.team, email="john.doe@example.com")
        slack_user = {
            "id": "U123456",
            "email": "john.doe@example.com",
            "real_name": "John Doe",
        }

        # Act
        result = match_slack_user_to_team_member(slack_user, self.team)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.id, member.id)
        self.assertEqual(result.email, "john.doe@example.com")

    def test_returns_team_member_when_email_matches_case_insensitive(self):
        """Test that match_slack_user_to_team_member matches email case-insensitively."""
        # Arrange
        member = TeamMemberFactory(team=self.team, email="john.doe@example.com")
        slack_user = {
            "id": "U123456",
            "email": "JOHN.DOE@EXAMPLE.COM",  # Uppercase
            "real_name": "John Doe",
        }

        # Act
        result = match_slack_user_to_team_member(slack_user, self.team)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.id, member.id)

    def test_returns_none_when_no_email_match(self):
        """Test that match_slack_user_to_team_member returns None when no email match found."""
        # Arrange
        TeamMemberFactory(team=self.team, email="john.doe@example.com")
        slack_user = {
            "id": "U123456",
            "email": "different.user@example.com",
            "real_name": "Different User",
        }

        # Act
        result = match_slack_user_to_team_member(slack_user, self.team)

        # Assert
        self.assertIsNone(result)


class TestSyncSlackUsers(TestCase):
    """Tests for sync_slack_users function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.services.encryption import encrypt

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="slack",
            access_token=encrypt("xoxb-test-slack-token"),
        )

    @patch("apps.integrations.services.slack_user_matching.get_slack_users")
    def test_updates_team_member_slack_user_id_for_matched_users(self, mock_get_slack_users):
        """Test that sync_slack_users updates TeamMember.slack_user_id when user matches by email."""
        # Arrange
        member1 = TeamMemberFactory(team=self.team, email="john.doe@example.com", slack_user_id="")
        member2 = TeamMemberFactory(team=self.team, email="jane.smith@example.com", slack_user_id="")

        mock_get_slack_users.return_value = [
            {
                "id": "U123456",
                "email": "john.doe@example.com",
                "real_name": "John Doe",
            },
            {
                "id": "U789012",
                "email": "jane.smith@example.com",
                "real_name": "Jane Smith",
            },
        ]

        # Act
        sync_slack_users(self.team, self.credential)

        # Assert
        member1.refresh_from_db()
        member2.refresh_from_db()

        self.assertEqual(member1.slack_user_id, "U123456")
        self.assertEqual(member2.slack_user_id, "U789012")

    @patch("apps.integrations.services.slack_user_matching.get_slack_users")
    def test_returns_dict_with_matched_count_unmatched_count_and_unmatched_users_list(self, mock_get_slack_users):
        """Test that sync_slack_users returns dict with matched_count, unmatched_count, unmatched_users."""
        # Arrange
        TeamMemberFactory(team=self.team, email="john.doe@example.com")
        # jane.smith is not in team - will be unmatched

        mock_get_slack_users.return_value = [
            {
                "id": "U123456",
                "email": "john.doe@example.com",
                "real_name": "John Doe",
            },
            {
                "id": "U789012",
                "email": "jane.smith@example.com",  # No match in team
                "real_name": "Jane Smith",
            },
        ]

        # Act
        result = sync_slack_users(self.team, self.credential)

        # Assert
        self.assertIn("matched_count", result)
        self.assertIn("unmatched_count", result)
        self.assertIn("unmatched_users", result)

        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["unmatched_count"], 1)
        self.assertEqual(len(result["unmatched_users"]), 1)
        self.assertEqual(result["unmatched_users"][0]["email"], "jane.smith@example.com")

    @patch("apps.integrations.services.slack_user_matching.get_slack_users")
    def test_skips_users_without_email_addresses(self, mock_get_slack_users):
        """Test that sync_slack_users skips Slack users without email addresses."""
        # Arrange
        member = TeamMemberFactory(team=self.team, email="john.doe@example.com")

        mock_get_slack_users.return_value = [
            {
                "id": "U123456",
                "email": "john.doe@example.com",
                "real_name": "John Doe",
            },
            {
                "id": "U789012",
                "email": None,  # No email - should be skipped
                "real_name": "Bot User",
            },
        ]

        # Act
        result = sync_slack_users(self.team, self.credential)

        # Assert
        # Only 1 user matched (the one with email)
        self.assertEqual(result["matched_count"], 1)

        # The user without email should not be counted as unmatched
        # It should be skipped entirely
        self.assertEqual(result["unmatched_count"], 0)
        self.assertEqual(len(result["unmatched_users"]), 0)

        # Verify member was updated
        member.refresh_from_db()
        self.assertEqual(member.slack_user_id, "U123456")
