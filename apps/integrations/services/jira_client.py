"""Jira API client service using jira-python library."""

from datetime import datetime

from jira import JIRA

from apps.integrations.services.jira_oauth import ensure_valid_jira_token

__all__ = [
    "JiraClientError",
    "get_jira_client",
    "get_accessible_projects",
    "get_project_issues",
]


class JiraClientError(Exception):
    """Exception raised for Jira client errors."""

    pass


def get_jira_client(credential) -> JIRA:
    """Create authenticated JIRA instance for Atlassian Cloud.

    Args:
        credential: IntegrationCredential instance with Jira tokens

    Returns:
        JIRA instance authenticated with bearer token

    Raises:
        JiraClientError: If authentication fails
    """
    try:
        # Get valid access token (refreshes if needed)
        access_token = ensure_valid_jira_token(credential)

        # Get cloud_id from JiraIntegration
        jira_integration = credential.jira_integration
        cloud_id = jira_integration.cloud_id

        # Build server URL for Atlassian Cloud
        server_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"

        # Create JIRA client with bearer token in headers
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        return JIRA(server=server_url, options={"headers": headers})
    except Exception as e:
        raise JiraClientError(f"Failed to create Jira client: {e}") from e


def get_accessible_projects(credential) -> list[dict]:
    """Get all accessible Jira projects.

    Args:
        credential: IntegrationCredential instance

    Returns:
        List of project dicts with keys: id, key, name

    Raises:
        JiraClientError: If API call fails
    """
    try:
        jira = get_jira_client(credential)
        projects = jira.projects()

        return [
            {
                "id": str(project.id),
                "key": project.key,
                "name": project.name,
            }
            for project in projects
        ]
    except Exception as e:
        raise JiraClientError(f"Failed to get accessible projects: {e}") from e


def get_project_issues(credential, project_key: str, since: datetime | None = None) -> list[dict]:
    """Get issues from a Jira project.

    Args:
        credential: IntegrationCredential instance
        project_key: Jira project key (e.g., "PROJ")
        since: Optional datetime for incremental sync

    Returns:
        List of issue dicts with keys: key, id, summary, issue_type, status,
        assignee_account_id, story_points, created, updated, resolution_date

    Raises:
        JiraClientError: If API call fails
    """
    try:
        jira = get_jira_client(credential)

        # Build JQL query
        if since:
            # Format: "2024-01-01 00:00"
            since_str = since.strftime("%Y-%m-%d %H:%M")
            jql = f'project = {project_key} AND updated >= "{since_str}" ORDER BY updated DESC'
        else:
            jql = f"project = {project_key} ORDER BY updated DESC"

        # Fetch issues with required fields
        # jira.search_issues handles pagination automatically
        issues = jira.search_issues(
            jql,
            maxResults=False,  # Get all results
            fields="summary,status,issuetype,assignee,created,updated,resolutiondate,customfield_10016",
        )

        return [_convert_issue_to_dict(issue) for issue in issues]

    except Exception as e:
        raise JiraClientError(f"Failed to get project issues: {e}") from e


def _convert_issue_to_dict(issue) -> dict:
    """Convert JIRA Issue object to dictionary with all required attributes.

    Args:
        issue: JIRA Issue object

    Returns:
        Dictionary with issue data in standardized format with keys:
        key, id, summary, issue_type, status, assignee_account_id,
        story_points, created, updated, resolution_date
    """
    fields = issue.fields

    return {
        "key": issue.key,
        "id": issue.id,
        "summary": fields.summary or "",
        "issue_type": fields.issuetype.name if fields.issuetype else "",
        "status": fields.status.name if fields.status else "",
        "assignee_account_id": fields.assignee.accountId if fields.assignee else None,
        "story_points": getattr(fields, "customfield_10016", None),
        "created": fields.created,
        "updated": fields.updated,
        "resolution_date": fields.resolutiondate,
    }
