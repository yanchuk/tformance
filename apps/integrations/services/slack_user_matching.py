"""Slack user matching service for syncing Slack users to TeamMembers."""

from apps.integrations.services.slack_client import get_slack_client, get_workspace_users
from apps.metrics.models import TeamMember

__all__ = [
    "get_slack_users",
    "match_slack_user_to_team_member",
    "sync_slack_users",
]


def get_slack_users(credential) -> list[dict]:
    """Fetch all Slack users from the connected workspace.

    Args:
        credential: IntegrationCredential instance

    Returns:
        List of user dicts with keys: id, email, real_name
    """
    client = get_slack_client(credential)

    # Get all workspace users
    users = get_workspace_users(client)

    # Transform to simplified structure and filter users without email
    return [
        {
            "id": user["id"],
            "email": user.get("profile", {}).get("email"),
            "real_name": user.get("profile", {}).get("real_name", ""),
        }
        for user in users
        if user.get("profile", {}).get("email")  # Only include users with email
    ]


def match_slack_user_to_team_member(slack_user: dict, team) -> TeamMember | None:
    """Match a Slack user to a TeamMember by email.

    Args:
        slack_user: Dict with id, email, real_name
        team: Team instance

    Returns:
        TeamMember if matched, None otherwise
    """
    email = slack_user.get("email")
    if not email:
        return None

    # Case-insensitive email match
    try:
        return TeamMember.objects.get(team=team, email__iexact=email)
    except TeamMember.DoesNotExist:
        return None


def sync_slack_users(team, credential) -> dict:
    """Sync Slack users to TeamMembers by email matching.

    Args:
        team: Team instance
        credential: IntegrationCredential instance

    Returns:
        Dict with matched_count, unmatched_count, unmatched_users list
    """
    slack_users = get_slack_users(credential)

    matched_count = 0
    unmatched_count = 0
    unmatched_users = []

    for slack_user in slack_users:
        # Skip users without email
        email = slack_user.get("email")
        if not email:
            continue

        team_member = match_slack_user_to_team_member(slack_user, team)

        if team_member:
            # Only update if not already set to same value
            slack_id = slack_user["id"]
            if team_member.slack_user_id != slack_id:
                team_member.slack_user_id = slack_id
                team_member.save(update_fields=["slack_user_id"])
            matched_count += 1
        else:
            unmatched_count += 1
            unmatched_users.append(
                {
                    "id": slack_user["id"],
                    "real_name": slack_user["real_name"],
                    "email": email,
                }
            )

    return {
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "unmatched_users": unmatched_users,
    }
