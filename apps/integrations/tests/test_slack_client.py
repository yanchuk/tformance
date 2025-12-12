"""Tests for Slack client service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import IntegrationCredentialFactory
from apps.integrations.services.slack_client import (
    SlackClientError,
    get_slack_client,
    get_user_info,
    get_workspace_users,
    send_channel_message,
    send_dm,
)
from apps.metrics.factories import TeamFactory


class TestSlackClientError(TestCase):
    """Tests for SlackClientError exception."""

    def test_slack_client_error_can_be_raised(self):
        """Test that SlackClientError can be raised and caught."""
        with self.assertRaises(SlackClientError):
            raise SlackClientError("Test error")

    def test_slack_client_error_message(self):
        """Test that SlackClientError preserves error message."""
        error_message = "Connection to Slack API failed"
        try:
            raise SlackClientError(error_message)
        except SlackClientError as e:
            self.assertEqual(str(e), error_message)


class TestGetSlackClient(TestCase):
    """Tests for get_slack_client function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.services.encryption import encrypt

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="slack",
            access_token=encrypt("xoxb-test-slack-bot-token"),
        )

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_get_slack_client_returns_webclient_instance(self, mock_webclient_class):
        """Test that get_slack_client returns a WebClient instance."""
        # Arrange
        mock_webclient_instance = MagicMock()
        mock_webclient_class.return_value = mock_webclient_instance

        # Act
        result = get_slack_client(self.credential)

        # Assert
        self.assertEqual(result, mock_webclient_instance)
        mock_webclient_class.assert_called_once()

    @patch("apps.integrations.services.slack_client.decrypt")
    @patch("apps.integrations.services.slack_client.WebClient")
    def test_get_slack_client_uses_decrypted_token_from_credential(self, mock_webclient_class, mock_decrypt):
        """Test that get_slack_client uses decrypted token from credential."""
        # Arrange
        mock_decrypt.return_value = "xoxb-decrypted-slack-token"
        mock_webclient_instance = MagicMock()
        mock_webclient_class.return_value = mock_webclient_instance

        # Act
        get_slack_client(self.credential)

        # Assert - decrypt should be called with the encrypted token
        mock_decrypt.assert_called_once_with(self.credential.access_token)

        # Assert - WebClient should be instantiated with the decrypted token
        mock_webclient_class.assert_called_once_with(token="xoxb-decrypted-slack-token")


class TestSendDM(TestCase):
    """Tests for send_dm function."""

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_send_dm_opens_conversation_first(self, mock_webclient_class):
        """Test that send_dm opens a direct message conversation first."""
        # Arrange
        mock_client = MagicMock()
        mock_client.conversations_open.return_value = {"channel": {"id": "D123456"}}
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}

        user_id = "U123456"
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Hello!"}}]

        # Act
        send_dm(mock_client, user_id, blocks)

        # Assert - conversations_open should be called with the user_id
        mock_client.conversations_open.assert_called_once_with(users=user_id)

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_send_dm_sends_message_with_blocks(self, mock_webclient_class):
        """Test that send_dm sends message with blocks to the opened channel."""
        # Arrange
        mock_client = MagicMock()
        dm_channel_id = "D987654"
        mock_client.conversations_open.return_value = {"channel": {"id": dm_channel_id}}
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}

        user_id = "U789012"
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Hello user!"}},
            {"type": "divider"},
        ]
        text_fallback = "Hello user!"

        # Act
        send_dm(mock_client, user_id, blocks, text=text_fallback)

        # Assert - chat_postMessage should be called with channel, blocks, and text
        mock_client.chat_postMessage.assert_called_once_with(channel=dm_channel_id, blocks=blocks, text=text_fallback)

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_send_dm_returns_response_with_message_ts(self, mock_webclient_class):
        """Test that send_dm returns response dict with message_ts."""
        # Arrange
        mock_client = MagicMock()
        mock_client.conversations_open.return_value = {"channel": {"id": "D111222"}}
        expected_response = {
            "ok": True,
            "ts": "1701234567.123456",
            "channel": "D111222",
            "message": {"text": "Test message"},
        }
        mock_client.chat_postMessage.return_value = expected_response

        user_id = "U111222"
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]

        # Act
        result = send_dm(mock_client, user_id, blocks)

        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(result["ok"], True)
        self.assertEqual(result["ts"], "1701234567.123456")


class TestSendChannelMessage(TestCase):
    """Tests for send_channel_message function."""

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_send_channel_message_sends_to_channel(self, mock_webclient_class):
        """Test that send_channel_message sends message to specified channel."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {"ok": True, "ts": "1234567890.123456", "channel": "C123456"}
        mock_client.chat_postMessage.return_value = expected_response

        channel_id = "C123456"
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Leaderboard for this week!"},
            }
        ]
        text_fallback = "Leaderboard for this week!"

        # Act
        result = send_channel_message(mock_client, channel_id, blocks, text=text_fallback)

        # Assert - chat_postMessage should be called with channel, blocks, and text
        mock_client.chat_postMessage.assert_called_once_with(channel=channel_id, blocks=blocks, text=text_fallback)
        self.assertEqual(result, expected_response)


class TestGetWorkspaceUsers(TestCase):
    """Tests for get_workspace_users function."""

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_get_workspace_users_returns_user_list(self, mock_webclient_class):
        """Test that get_workspace_users returns list of user dicts."""
        # Arrange
        mock_client = MagicMock()
        mock_users = [
            {
                "id": "U123456",
                "profile": {
                    "email": "user1@example.com",
                    "real_name": "Alice Smith",
                },
                "is_bot": False,
                "deleted": False,
            },
            {
                "id": "U789012",
                "profile": {
                    "email": "user2@example.com",
                    "real_name": "Bob Jones",
                },
                "is_bot": False,
                "deleted": False,
            },
        ]
        mock_client.users_list.return_value = {"ok": True, "members": mock_users}

        # Act
        result = get_workspace_users(mock_client)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "U123456")
        self.assertEqual(result[0]["profile"]["email"], "user1@example.com")
        self.assertEqual(result[1]["id"], "U789012")

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_get_workspace_users_handles_pagination(self, mock_webclient_class):
        """Test that get_workspace_users handles pagination (multiple pages)."""
        # Arrange
        mock_client = MagicMock()

        # Simulate two pages of results
        page1_users = [
            {
                "id": "U000001",
                "profile": {"email": "user1@example.com", "real_name": "User 1"},
                "is_bot": False,
                "deleted": False,
            },
            {
                "id": "U000002",
                "profile": {"email": "user2@example.com", "real_name": "User 2"},
                "is_bot": False,
                "deleted": False,
            },
        ]

        page2_users = [
            {
                "id": "U000003",
                "profile": {"email": "user3@example.com", "real_name": "User 3"},
                "is_bot": False,
                "deleted": False,
            }
        ]

        # First call returns page 1 with cursor
        # Second call returns page 2 without cursor (end of pagination)
        mock_client.users_list.side_effect = [
            {
                "ok": True,
                "members": page1_users,
                "response_metadata": {"next_cursor": "cursor-page-2"},
            },
            {"ok": True, "members": page2_users, "response_metadata": {"next_cursor": ""}},
        ]

        # Act
        result = get_workspace_users(mock_client)

        # Assert - should have collected users from both pages
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["id"], "U000001")
        self.assertEqual(result[1]["id"], "U000002")
        self.assertEqual(result[2]["id"], "U000003")

        # Assert - users_list should have been called twice with correct cursor
        self.assertEqual(mock_client.users_list.call_count, 2)
        first_call = mock_client.users_list.call_args_list[0]
        second_call = mock_client.users_list.call_args_list[1]

        # First call should not have cursor or have empty cursor
        self.assertIn("cursor", first_call[1])

        # Second call should have the cursor from first response
        self.assertEqual(second_call[1]["cursor"], "cursor-page-2")


class TestGetUserInfo(TestCase):
    """Tests for get_user_info function."""

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_get_user_info_returns_user_data(self, mock_webclient_class):
        """Test that get_user_info returns user data dict."""
        # Arrange
        mock_client = MagicMock()
        user_id = "U123456"
        expected_user_data = {
            "id": user_id,
            "profile": {
                "email": "alice@example.com",
                "real_name": "Alice Smith",
                "display_name": "alice",
            },
            "is_bot": False,
            "deleted": False,
        }
        mock_client.users_info.return_value = {"ok": True, "user": expected_user_data}

        # Act
        result = get_user_info(mock_client, user_id)

        # Assert
        mock_client.users_info.assert_called_once_with(user=user_id)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], user_id)
        self.assertEqual(result["profile"]["email"], "alice@example.com")
        self.assertEqual(result["profile"]["real_name"], "Alice Smith")


class TestSlackClientErrorHandling(TestCase):
    """Tests for Slack client error handling."""

    @patch("apps.integrations.services.slack_client.WebClient")
    def test_slack_client_error_raised_on_api_failure(self, mock_webclient_class):
        """Test that SlackClientError is raised when Slack API fails."""
        # Arrange
        mock_client = MagicMock()

        # Simulate SlackApiError from slack_sdk
        from slack_sdk.errors import SlackApiError

        mock_client.users_list.side_effect = SlackApiError(message="rate_limited", response={"error": "rate_limited"})

        # Act & Assert
        with self.assertRaises(SlackClientError) as context:
            get_workspace_users(mock_client)

        self.assertIn("Failed to get workspace users", str(context.exception))
