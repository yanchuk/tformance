"""Jira user matching service for syncing Jira users to TeamMembers."""

from apps.integrations.services.jira_client import get_jira_client
from apps.metrics.models import TeamMember

__all__ = [
    "get_jira_users",
    "match_jira_user_to_team_member",
    "sync_jira_users",
]


def get_jira_users(credential) -> list[dict]:
    """Fetch all Jira users from the connected site.

    Args:
        credential: IntegrationCredential instance

    Returns:
        List of user dicts with keys: accountId, emailAddress, displayName
    """
    jira = get_jira_client(credential)

    # Search for all users (assignable users in the site)
    # jira.search_assignable_users_for_projects requires a project key
    # We use search_users which searches across the site
    users = jira.search_users(query="", maxResults=1000)

    return [
        {
            "accountId": user.accountId,
            "emailAddress": getattr(user, "emailAddress", None),
            "displayName": user.displayName,
        }
        for user in users
    ]


def match_jira_user_to_team_member(jira_user: dict, team) -> TeamMember | None:
    """Match a Jira user to a TeamMember by email.

    Args:
        jira_user: Dict with accountId, emailAddress, displayName
        team: Team instance

    Returns:
        TeamMember if matched, None otherwise
    """
    email = jira_user.get("emailAddress")
    if not email:
        return None

    # Case-insensitive email match
    try:
        return TeamMember.objects.get(team=team, email__iexact=email)
    except TeamMember.DoesNotExist:
        return None


def sync_jira_users(team, credential) -> dict:
    """Sync Jira users to TeamMembers by email matching.

    Args:
        team: Team instance
        credential: IntegrationCredential instance

    Returns:
        Dict with matched_count, unmatched_count, unmatched_users list
    """
    jira_users = get_jira_users(credential)

    matched_count = 0
    unmatched_count = 0
    unmatched_users = []

    for jira_user in jira_users:
        # Skip users without email
        email = jira_user.get("emailAddress")
        if not email:
            continue

        team_member = match_jira_user_to_team_member(jira_user, team)

        if team_member:
            # Only update if not already set to same value
            account_id = jira_user["accountId"]
            if team_member.jira_account_id != account_id:
                team_member.jira_account_id = account_id
                team_member.save(update_fields=["jira_account_id"])
            matched_count += 1
        else:
            unmatched_count += 1
            unmatched_users.append(
                {
                    "accountId": jira_user["accountId"],
                    "displayName": jira_user["displayName"],
                    "emailAddress": email,
                }
            )

    return {
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "unmatched_users": unmatched_users,
    }
