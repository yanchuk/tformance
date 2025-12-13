"""Tests for Jira user matching service."""

from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase

from apps.integrations.factories import IntegrationCredentialFactory
from apps.integrations.services.jira_user_matching import (
    get_jira_users,
    match_jira_user_to_team_member,
    sync_jira_users,
)
from apps.metrics.factories import TeamFactory, TeamMemberFactory


class TestGetJiraUsers(TestCase):
    """Tests for get_jira_users function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        # EncryptedTextField auto-encrypts, so use plaintext values
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token="test_access_token_123",
        )

    @patch("apps.integrations.services.jira_user_matching.get_jira_client")
    def test_returns_list_of_user_dicts_with_required_fields(self, mock_get_client):
        """Test that get_jira_users returns list of user dicts with accountId, emailAddress, displayName."""
        # Arrange
        mock_client = MagicMock()

        # Create mock users
        mock_user1 = Mock()
        mock_user1.accountId = "user-account-id-1"
        mock_user1.emailAddress = "john.doe@example.com"
        mock_user1.displayName = "John Doe"

        mock_user2 = Mock()
        mock_user2.accountId = "user-account-id-2"
        mock_user2.emailAddress = "jane.smith@example.com"
        mock_user2.displayName = "Jane Smith"

        mock_client.search_users.return_value = [mock_user1, mock_user2]
        mock_get_client.return_value = mock_client

        # Act
        result = get_jira_users(self.credential)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # Check first user
        self.assertEqual(result[0]["accountId"], "user-account-id-1")
        self.assertEqual(result[0]["emailAddress"], "john.doe@example.com")
        self.assertEqual(result[0]["displayName"], "John Doe")

        # Check second user
        self.assertEqual(result[1]["accountId"], "user-account-id-2")
        self.assertEqual(result[1]["emailAddress"], "jane.smith@example.com")
        self.assertEqual(result[1]["displayName"], "Jane Smith")

    @patch("apps.integrations.services.jira_user_matching.get_jira_client")
    def test_handles_empty_user_list(self, mock_get_client):
        """Test that get_jira_users handles empty user list gracefully."""
        # Arrange
        mock_client = MagicMock()
        mock_client.search_users.return_value = []
        mock_get_client.return_value = mock_client

        # Act
        result = get_jira_users(self.credential)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.jira_user_matching.get_jira_client")
    def test_handles_users_with_no_email_address(self, mock_get_client):
        """Test that get_jira_users handles users without email addresses."""
        # Arrange
        mock_client = MagicMock()

        # User with email
        mock_user1 = Mock()
        mock_user1.accountId = "user-account-id-1"
        mock_user1.emailAddress = "john.doe@example.com"
        mock_user1.displayName = "John Doe"

        # User without email (email attribute is None)
        mock_user2 = Mock()
        mock_user2.accountId = "user-account-id-2"
        mock_user2.emailAddress = None
        mock_user2.displayName = "Private User"

        mock_client.search_users.return_value = [mock_user1, mock_user2]
        mock_get_client.return_value = mock_client

        # Act
        result = get_jira_users(self.credential)

        # Assert
        self.assertEqual(len(result), 2)

        # First user has email
        self.assertEqual(result[0]["emailAddress"], "john.doe@example.com")

        # Second user has None email
        self.assertIsNone(result[1]["emailAddress"])


class TestMatchJiraUserToTeamMember(TestCase):
    """Tests for match_jira_user_to_team_member function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_returns_team_member_when_email_matches(self):
        """Test that match_jira_user_to_team_member returns TeamMember when email matches."""
        # Arrange
        member = TeamMemberFactory(team=self.team, email="john.doe@example.com")
        jira_user = {
            "accountId": "jira-account-123",
            "emailAddress": "john.doe@example.com",
            "displayName": "John Doe",
        }

        # Act
        result = match_jira_user_to_team_member(jira_user, self.team)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.id, member.id)
        self.assertEqual(result.email, "john.doe@example.com")

    def test_returns_team_member_when_email_matches_case_insensitive(self):
        """Test that match_jira_user_to_team_member matches email case-insensitively."""
        # Arrange
        member = TeamMemberFactory(team=self.team, email="john.doe@example.com")
        jira_user = {
            "accountId": "jira-account-123",
            "emailAddress": "JOHN.DOE@EXAMPLE.COM",  # Uppercase
            "displayName": "John Doe",
        }

        # Act
        result = match_jira_user_to_team_member(jira_user, self.team)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.id, member.id)

    def test_returns_none_when_no_email_match(self):
        """Test that match_jira_user_to_team_member returns None when no email match found."""
        # Arrange
        TeamMemberFactory(team=self.team, email="john.doe@example.com")
        jira_user = {
            "accountId": "jira-account-123",
            "emailAddress": "different.user@example.com",
            "displayName": "Different User",
        }

        # Act
        result = match_jira_user_to_team_member(jira_user, self.team)

        # Assert
        self.assertIsNone(result)

    def test_returns_none_when_jira_user_has_no_email(self):
        """Test that match_jira_user_to_team_member returns None when jira_user has no email."""
        # Arrange
        TeamMemberFactory(team=self.team, email="john.doe@example.com")
        jira_user = {
            "accountId": "jira-account-123",
            "emailAddress": None,  # No email
            "displayName": "Private User",
        }

        # Act
        result = match_jira_user_to_team_member(jira_user, self.team)

        # Assert
        self.assertIsNone(result)


class TestSyncJiraUsers(TestCase):
    """Tests for sync_jira_users function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        # EncryptedTextField auto-encrypts, so use plaintext values
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token="test_access_token_123",
        )

    @patch("apps.integrations.services.jira_user_matching.get_jira_users")
    def test_updates_team_member_jira_account_id_for_matched_users(self, mock_get_jira_users):
        """Test that sync_jira_users updates TeamMember.jira_account_id when user matches by email."""
        # Arrange
        member1 = TeamMemberFactory(team=self.team, email="john.doe@example.com", jira_account_id="")
        member2 = TeamMemberFactory(team=self.team, email="jane.smith@example.com", jira_account_id="")

        mock_get_jira_users.return_value = [
            {
                "accountId": "jira-account-1",
                "emailAddress": "john.doe@example.com",
                "displayName": "John Doe",
            },
            {
                "accountId": "jira-account-2",
                "emailAddress": "jane.smith@example.com",
                "displayName": "Jane Smith",
            },
        ]

        # Act
        sync_jira_users(self.team, self.credential)

        # Assert
        member1.refresh_from_db()
        member2.refresh_from_db()

        self.assertEqual(member1.jira_account_id, "jira-account-1")
        self.assertEqual(member2.jira_account_id, "jira-account-2")

    @patch("apps.integrations.services.jira_user_matching.get_jira_users")
    def test_returns_dict_with_matched_count_unmatched_count_and_unmatched_users_list(self, mock_get_jira_users):
        """Test that sync_jira_users returns dict with matched_count, unmatched_count, unmatched_users."""
        # Arrange
        TeamMemberFactory(team=self.team, email="john.doe@example.com")
        # jane.smith is not in team - will be unmatched

        mock_get_jira_users.return_value = [
            {
                "accountId": "jira-account-1",
                "emailAddress": "john.doe@example.com",
                "displayName": "John Doe",
            },
            {
                "accountId": "jira-account-2",
                "emailAddress": "jane.smith@example.com",  # No match in team
                "displayName": "Jane Smith",
            },
        ]

        # Act
        result = sync_jira_users(self.team, self.credential)

        # Assert
        self.assertIn("matched_count", result)
        self.assertIn("unmatched_count", result)
        self.assertIn("unmatched_users", result)

        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["unmatched_count"], 1)
        self.assertEqual(len(result["unmatched_users"]), 1)
        self.assertEqual(result["unmatched_users"][0]["emailAddress"], "jane.smith@example.com")

    @patch("apps.integrations.services.jira_user_matching.get_jira_users")
    def test_does_not_modify_already_matched_team_members_with_same_account_id(self, mock_get_jira_users):
        """Test that sync_jira_users doesn't re-update TeamMember if jira_account_id already set to same value."""
        # Arrange
        member = TeamMemberFactory(
            team=self.team,
            email="john.doe@example.com",
            jira_account_id="jira-account-1",  # Already set
        )

        mock_get_jira_users.return_value = [
            {
                "accountId": "jira-account-1",  # Same as existing
                "emailAddress": "john.doe@example.com",
                "displayName": "John Doe",
            },
        ]

        # Act
        result = sync_jira_users(self.team, self.credential)

        # Assert
        member.refresh_from_db()
        self.assertEqual(member.jira_account_id, "jira-account-1")

        # Result should still count as matched
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["unmatched_count"], 0)

    @patch("apps.integrations.services.jira_user_matching.get_jira_users")
    def test_handles_empty_user_list_gracefully(self, mock_get_jira_users):
        """Test that sync_jira_users handles empty Jira user list without errors."""
        # Arrange
        TeamMemberFactory(team=self.team, email="john.doe@example.com")

        mock_get_jira_users.return_value = []

        # Act
        result = sync_jira_users(self.team, self.credential)

        # Assert
        self.assertEqual(result["matched_count"], 0)
        self.assertEqual(result["unmatched_count"], 0)
        self.assertEqual(len(result["unmatched_users"]), 0)

    @patch("apps.integrations.services.jira_user_matching.get_jira_users")
    def test_skips_users_without_email_addresses(self, mock_get_jira_users):
        """Test that sync_jira_users skips Jira users without email addresses."""
        # Arrange
        member = TeamMemberFactory(team=self.team, email="john.doe@example.com")

        mock_get_jira_users.return_value = [
            {
                "accountId": "jira-account-1",
                "emailAddress": "john.doe@example.com",
                "displayName": "John Doe",
            },
            {
                "accountId": "jira-account-2",
                "emailAddress": None,  # No email - should be skipped
                "displayName": "Private User",
            },
        ]

        # Act
        result = sync_jira_users(self.team, self.credential)

        # Assert
        # Only 1 user matched (the one with email)
        self.assertEqual(result["matched_count"], 1)

        # The user without email should not be counted as unmatched
        # It should be skipped entirely
        self.assertEqual(result["unmatched_count"], 0)
        self.assertEqual(len(result["unmatched_users"]), 0)

        # Verify member was updated
        member.refresh_from_db()
        self.assertEqual(member.jira_account_id, "jira-account-1")
