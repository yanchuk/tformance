"""Slack client service for API interactions."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from apps.integrations.services.encryption import decrypt


class SlackClientError(Exception):
    """Exception raised for Slack client errors."""

    pass


def get_slack_client(credential) -> WebClient:
    """Create authenticated Slack WebClient from credential.

    Args:
        credential: IntegrationCredential instance with encrypted access_token

    Returns:
        WebClient: Authenticated Slack WebClient instance
    """
    token = decrypt(credential.access_token)
    return WebClient(token=token)


def send_dm(client: WebClient, user_id: str, blocks: list, text: str = "") -> dict:
    """Send a direct message to a user.

    Args:
        client: Authenticated Slack WebClient instance
        user_id: Slack user ID to send message to
        blocks: List of Block Kit blocks for the message
        text: Fallback text for notifications (optional)

    Returns:
        dict: Response containing 'ok', 'ts', and 'channel'

    Raises:
        SlackClientError: If the Slack API call fails
    """
    try:
        # First open a DM conversation
        conv_response = client.conversations_open(users=user_id)
        channel_id = conv_response["channel"]["id"]

        # Send the message
        response = client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=text or "New message",
        )
        return {"ok": True, "ts": response["ts"], "channel": channel_id}
    except SlackApiError as e:
        raise SlackClientError(f"Failed to send DM: {e.response['error']}") from e


def send_channel_message(client: WebClient, channel_id: str, blocks: list, text: str = "") -> dict:
    """Send a message to a channel.

    Args:
        client: Authenticated Slack WebClient instance
        channel_id: Slack channel ID to send message to
        blocks: List of Block Kit blocks for the message
        text: Fallback text for notifications (optional)

    Returns:
        dict: Response from chat_postMessage API call

    Raises:
        SlackClientError: If the Slack API call fails
    """
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=text or "New message",
        )
        return response
    except SlackApiError as e:
        raise SlackClientError(f"Failed to send channel message: {e.response['error']}") from e


def get_workspace_users(client: WebClient) -> list[dict]:
    """Fetch all users in workspace with pagination.

    Args:
        client: Authenticated Slack WebClient instance

    Returns:
        list[dict]: List of user dicts with full Slack API structure

    Raises:
        SlackClientError: If the Slack API call fails
    """
    users = []
    cursor = None

    try:
        while True:
            response = client.users_list(cursor=cursor, limit=200)
            users.extend(response["members"])

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return users
    except SlackApiError as e:
        raise SlackClientError(f"Failed to get workspace users: {e.response['error']}") from e


def get_user_info(client: WebClient, user_id: str) -> dict:
    """Get user info by Slack user ID.

    Args:
        client: Authenticated Slack WebClient instance
        user_id: Slack user ID to fetch

    Returns:
        dict: User data dict with full Slack API structure

    Raises:
        SlackClientError: If the Slack API call fails
    """
    try:
        response = client.users_info(user=user_id)
        return response["user"]
    except SlackApiError as e:
        raise SlackClientError(f"Failed to get user info: {e.response['error']}") from e
