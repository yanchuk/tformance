"""Jira issue sync service for syncing issues to local database."""

import contextlib
from datetime import datetime
from decimal import Decimal

from dateutil import parser
from django.utils import timezone

from apps.integrations.models import TrackedJiraProject
from apps.integrations.services.jira_client import get_project_issues
from apps.metrics.models import JiraIssue, TeamMember

__all__ = [
    "JiraSyncError",
    "sync_project_issues",
]


class JiraSyncError(Exception):
    """Exception raised for Jira sync errors."""

    pass


def _parse_jira_datetime(dt_string: str | None) -> datetime | None:
    """Parse Jira datetime string to Python datetime."""
    if not dt_string:
        return None
    # Jira returns ISO format like "2024-01-15T10:30:00.000+0000"
    try:
        return parser.isoparse(dt_string)
    except Exception:
        return None


def _calculate_cycle_time(created: datetime | None, resolved: datetime | None) -> Decimal | None:
    """Calculate cycle time in hours between created and resolved."""
    if not created or not resolved:
        return None
    delta = resolved - created
    hours = delta.total_seconds() / 3600
    return Decimal(str(round(hours, 2)))


def _convert_jira_issue_to_dict(issue_data: dict) -> dict:
    """Convert Jira API issue data to model-ready dictionary.

    Args:
        issue_data: Raw Jira API issue data with 'key', 'id', and 'fields' keys

    Returns:
        Dictionary with model-ready fields
    """
    fields = issue_data.get("fields", {})

    # Extract data from nested structure
    key = issue_data.get("key", "")
    jira_id = issue_data.get("id", "")
    summary = fields.get("summary", "")

    # Extract issue type
    issue_type_obj = fields.get("issuetype")
    issue_type = issue_type_obj.get("name", "") if issue_type_obj else ""

    # Extract status
    status_obj = fields.get("status")
    status = status_obj.get("name", "") if status_obj else ""

    # Extract assignee account ID
    assignee_obj = fields.get("assignee")
    assignee_account_id = assignee_obj.get("accountId") if assignee_obj else None

    # Extract story points (customfield_10016)
    story_points_raw = fields.get("customfield_10016")
    story_points = Decimal(str(story_points_raw)) if story_points_raw is not None else None

    # Parse timestamps
    created = _parse_jira_datetime(fields.get("created"))
    resolved = _parse_jira_datetime(fields.get("resolutiondate"))

    # Extract description
    description = fields.get("description") or ""

    # Extract labels (already a list)
    labels = fields.get("labels") or []

    # Extract priority from nested object
    priority_obj = fields.get("priority")
    priority = priority_obj.get("name", "") if priority_obj else ""

    # Extract parent issue key from nested object
    parent_obj = fields.get("parent")
    parent_issue_key = parent_obj.get("key", "") if parent_obj else ""

    return {
        "jira_key": key,
        "jira_id": jira_id,
        "summary": summary,
        "issue_type": issue_type,
        "status": status,
        "assignee_account_id": assignee_account_id,
        "story_points": story_points,
        "issue_created_at": created,
        "resolved_at": resolved,
        "cycle_time_hours": _calculate_cycle_time(created, resolved),
        "description": description,
        "labels": labels,
        "priority": priority,
        "parent_issue_key": parent_issue_key,
    }


def sync_project_issues(tracked_project: TrackedJiraProject, full_sync: bool = False) -> dict:
    """Sync issues from a tracked Jira project.

    Args:
        tracked_project: TrackedJiraProject instance
        full_sync: If True, sync all issues; if False, only since last_sync_at

    Returns:
        Dict with issues_created, issues_updated, errors counts
    """
    team = tracked_project.team
    credential = tracked_project.integration.credential
    project_key = tracked_project.jira_project_key

    # Determine since datetime for incremental sync
    since = None
    if not full_sync and tracked_project.last_sync_at:
        since = tracked_project.last_sync_at

    # Update status to syncing
    tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_SYNCING
    tracked_project.save(update_fields=["sync_status"])

    issues_created = 0
    issues_updated = 0
    errors = 0

    try:
        # Fetch issues from Jira
        issues_data = get_project_issues(credential, project_key, since=since)

        for issue_data in issues_data:
            try:
                converted = _convert_jira_issue_to_dict(issue_data)

                # Look up assignee by jira_account_id
                assignee = None
                if converted["assignee_account_id"]:
                    with contextlib.suppress(TeamMember.DoesNotExist):
                        assignee = TeamMember.objects.get(team=team, jira_account_id=converted["assignee_account_id"])

                # Create or update JiraIssue
                issue, created = JiraIssue.objects.update_or_create(
                    team=team,
                    jira_id=converted["jira_id"],
                    defaults={
                        "jira_key": converted["jira_key"],
                        "summary": converted["summary"],
                        "issue_type": converted["issue_type"],
                        "status": converted["status"],
                        "assignee": assignee,
                        "story_points": converted["story_points"],
                        "issue_created_at": converted["issue_created_at"],
                        "resolved_at": converted["resolved_at"],
                        "cycle_time_hours": converted["cycle_time_hours"],
                        "description": converted["description"],
                        "labels": converted["labels"],
                        "priority": converted["priority"],
                        "parent_issue_key": converted["parent_issue_key"],
                    },
                )

                if created:
                    issues_created += 1
                else:
                    issues_updated += 1

            except Exception:
                errors += 1

        # Update tracked project with success status
        tracked_project.last_sync_at = timezone.now()
        tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_COMPLETE
        tracked_project.last_sync_error = None
        tracked_project.save(update_fields=["last_sync_at", "sync_status", "last_sync_error"])

    except Exception as e:
        # Update tracked project with error status
        tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_ERROR
        tracked_project.last_sync_error = str(e)
        tracked_project.save(update_fields=["sync_status", "last_sync_error"])
        errors += 1

    return {
        "issues_created": issues_created,
        "issues_updated": issues_updated,
        "errors": errors,
    }
