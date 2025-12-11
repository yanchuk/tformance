"""Tests for Jira sync service."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import JiraIntegrationFactory, TrackedJiraProjectFactory
from apps.integrations.services.jira_sync import (
    JiraSyncError,
    _calculate_cycle_time,
    _convert_jira_issue_to_dict,
    sync_project_issues,
)
from apps.metrics.factories import JiraIssueFactory, TeamMemberFactory
from apps.metrics.models import JiraIssue


class TestConvertJiraIssueToDictFunction(TestCase):
    """Tests for _convert_jira_issue_to_dict helper function."""

    def test_converts_all_fields_correctly(self):
        """Test that all Jira API fields are correctly mapped to model fields."""
        # Arrange - Mock Jira API response data
        issue_data = {
            "key": "PROJ-123",
            "id": "10001",
            "fields": {
                "summary": "Implement user authentication",
                "issuetype": {"name": "Story"},
                "status": {"name": "Done"},
                "assignee": {"accountId": "jira-user-001"},
                "customfield_10016": 5.0,  # Story points
                "created": "2025-01-01T10:00:00.000+0000",
                "resolutiondate": "2025-01-05T15:30:00.000+0000",
            },
        }

        # Act
        result = _convert_jira_issue_to_dict(issue_data)

        # Assert
        self.assertEqual(result["jira_key"], "PROJ-123")
        self.assertEqual(result["jira_id"], "10001")
        self.assertEqual(result["summary"], "Implement user authentication")
        self.assertEqual(result["issue_type"], "Story")
        self.assertEqual(result["status"], "Done")
        self.assertEqual(result["assignee_account_id"], "jira-user-001")
        self.assertEqual(result["story_points"], Decimal("5.0"))
        self.assertEqual(result["issue_created_at"], datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC))
        self.assertEqual(result["resolved_at"], datetime(2025, 1, 5, 15, 30, 0, tzinfo=UTC))

    def test_handles_missing_optional_fields(self):
        """Test that missing optional fields are handled gracefully."""
        # Arrange - Mock data without assignee, story_points, and resolution_date
        issue_data = {
            "key": "PROJ-456",
            "id": "10002",
            "fields": {
                "summary": "Fix login bug",
                "issuetype": {"name": "Bug"},
                "status": {"name": "In Progress"},
                "assignee": None,
                "customfield_10016": None,
                "created": "2025-01-10T09:00:00.000+0000",
                "resolutiondate": None,
            },
        }

        # Act
        result = _convert_jira_issue_to_dict(issue_data)

        # Assert
        self.assertIsNone(result["assignee_account_id"])
        self.assertIsNone(result["story_points"])
        self.assertIsNone(result["resolved_at"])
        self.assertEqual(result["jira_key"], "PROJ-456")
        self.assertEqual(result["status"], "In Progress")

    def test_handles_null_values_gracefully(self):
        """Test that null values in fields don't cause errors."""
        # Arrange - Mock data with null values
        issue_data = {
            "key": "PROJ-789",
            "id": "10003",
            "fields": {
                "summary": "Update documentation",
                "issuetype": {"name": "Task"},
                "status": {"name": "To Do"},
                "assignee": None,
                "customfield_10016": None,
                "created": "2025-01-15T14:00:00.000+0000",
                "resolutiondate": None,
            },
        }

        # Act
        result = _convert_jira_issue_to_dict(issue_data)

        # Assert
        self.assertIsNone(result["assignee_account_id"])
        self.assertIsNone(result["story_points"])
        self.assertIsNone(result["resolved_at"])
        self.assertEqual(result["summary"], "Update documentation")


class TestCalculateCycleTimeFunction(TestCase):
    """Tests for _calculate_cycle_time helper function."""

    def test_returns_hours_between_created_and_resolved(self):
        """Test that cycle time is calculated correctly in hours."""
        # Arrange
        created = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        resolved = datetime(2025, 1, 2, 14, 0, 0, tzinfo=UTC)  # 28 hours later

        # Act
        result = _calculate_cycle_time(created, resolved)

        # Assert
        self.assertEqual(result, Decimal("28.00"))

    def test_returns_none_if_resolved_is_none(self):
        """Test that None is returned if issue is not resolved."""
        # Arrange
        created = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        resolved = None

        # Act
        result = _calculate_cycle_time(created, resolved)

        # Assert
        self.assertIsNone(result)

    def test_returns_none_if_created_is_none(self):
        """Test that None is returned if created timestamp is missing."""
        # Arrange
        created = None
        resolved = datetime(2025, 1, 5, 10, 0, 0, tzinfo=UTC)

        # Act
        result = _calculate_cycle_time(created, resolved)

        # Assert
        self.assertIsNone(result)


class TestSyncProjectIssuesFullSync(TestCase):
    """Tests for sync_project_issues function with full_sync=True."""

    def setUp(self):
        """Set up test fixtures."""
        self.integration = JiraIntegrationFactory()
        self.tracked_project = TrackedJiraProjectFactory(integration=self.integration)

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_creates_new_jira_issue_records(self, mock_get_issues):
        """Test that new JiraIssue records are created from API data."""
        # Arrange
        mock_get_issues.return_value = [
            {
                "key": "PROJ-100",
                "id": "10100",
                "fields": {
                    "summary": "New feature",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "Done"},
                    "assignee": None,
                    "customfield_10016": 8.0,
                    "created": "2025-01-01T10:00:00.000+0000",
                    "resolutiondate": "2025-01-03T12:00:00.000+0000",
                },
            }
        ]

        # Act
        result = sync_project_issues(self.tracked_project, full_sync=True)

        # Assert
        self.assertEqual(result["issues_created"], 1)
        self.assertEqual(result["issues_updated"], 0)
        self.assertEqual(result["errors"], 0)

        # Verify issue was created in database
        issue = JiraIssue.objects.get(jira_key="PROJ-100")
        self.assertEqual(issue.jira_id, "10100")
        self.assertEqual(issue.summary, "New feature")
        self.assertEqual(issue.issue_type, "Story")
        self.assertEqual(issue.status, "Done")
        self.assertEqual(issue.story_points, Decimal("8.0"))

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_updates_existing_jira_issue_records(self, mock_get_issues):
        """Test that existing JiraIssue records are updated with changed data."""
        # Arrange - Create an existing issue
        existing_issue = JiraIssueFactory(
            team=self.tracked_project.team,
            jira_key="PROJ-200",
            jira_id="10200",
            summary="Old summary",
            status="In Progress",
            story_points=Decimal("3.0"),
        )

        # Mock API returns updated data
        mock_get_issues.return_value = [
            {
                "key": "PROJ-200",
                "id": "10200",
                "fields": {
                    "summary": "Updated summary",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "Done"},
                    "assignee": None,
                    "customfield_10016": 5.0,
                    "created": "2025-01-01T10:00:00.000+0000",
                    "resolutiondate": "2025-01-04T16:00:00.000+0000",
                },
            }
        ]

        # Act
        result = sync_project_issues(self.tracked_project, full_sync=True)

        # Assert
        self.assertEqual(result["issues_created"], 0)
        self.assertEqual(result["issues_updated"], 1)
        self.assertEqual(result["errors"], 0)

        # Verify issue was updated
        existing_issue.refresh_from_db()
        self.assertEqual(existing_issue.summary, "Updated summary")
        self.assertEqual(existing_issue.status, "Done")
        self.assertEqual(existing_issue.story_points, Decimal("5.0"))

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_links_assignee_to_team_member_by_jira_account_id(self, mock_get_issues):
        """Test that assignee is linked to TeamMember via jira_account_id."""
        # Arrange - Create a team member with Jira account ID
        team_member = TeamMemberFactory(
            team=self.tracked_project.team, jira_account_id="jira-user-123", display_name="Jane Developer"
        )

        mock_get_issues.return_value = [
            {
                "key": "PROJ-300",
                "id": "10300",
                "fields": {
                    "summary": "Task with assignee",
                    "issuetype": {"name": "Task"},
                    "status": {"name": "In Progress"},
                    "assignee": {"accountId": "jira-user-123"},
                    "customfield_10016": 2.0,
                    "created": "2025-01-05T09:00:00.000+0000",
                    "resolutiondate": None,
                },
            }
        ]

        # Act
        result = sync_project_issues(self.tracked_project, full_sync=True)

        # Assert
        self.assertEqual(result["issues_created"], 1)

        # Verify assignee is linked correctly
        issue = JiraIssue.objects.get(jira_key="PROJ-300")
        self.assertEqual(issue.assignee, team_member)

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_sets_assignee_to_none_when_no_match_found(self, mock_get_issues):
        """Test that assignee is set to None when no matching TeamMember found."""
        # Arrange - No team member with matching Jira account ID
        mock_get_issues.return_value = [
            {
                "key": "PROJ-400",
                "id": "10400",
                "fields": {
                    "summary": "Task with unknown assignee",
                    "issuetype": {"name": "Task"},
                    "status": {"name": "To Do"},
                    "assignee": {"accountId": "jira-unknown-999"},
                    "customfield_10016": 1.0,
                    "created": "2025-01-06T11:00:00.000+0000",
                    "resolutiondate": None,
                },
            }
        ]

        # Act
        result = sync_project_issues(self.tracked_project, full_sync=True)

        # Assert
        self.assertEqual(result["issues_created"], 1)

        # Verify assignee is None
        issue = JiraIssue.objects.get(jira_key="PROJ-400")
        self.assertIsNone(issue.assignee)

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_updates_tracked_project_last_sync_at_and_sync_status(self, mock_get_issues):
        """Test that TrackedJiraProject.last_sync_at and sync_status are updated."""
        # Arrange
        mock_get_issues.return_value = []
        original_sync_at = self.tracked_project.last_sync_at

        # Act
        sync_project_issues(self.tracked_project, full_sync=True)

        # Assert
        self.tracked_project.refresh_from_db()
        self.assertIsNotNone(self.tracked_project.last_sync_at)
        self.assertNotEqual(self.tracked_project.last_sync_at, original_sync_at)
        self.assertEqual(self.tracked_project.sync_status, "complete")


class TestSyncProjectIssuesIncrementalSync(TestCase):
    """Tests for sync_project_issues function with full_sync=False."""

    def setUp(self):
        """Set up test fixtures."""
        self.integration = JiraIntegrationFactory()
        self.tracked_project = TrackedJiraProjectFactory(
            integration=self.integration, last_sync_at=timezone.now() - timezone.timedelta(hours=1)
        )

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_only_fetches_issues_updated_since_last_sync(self, mock_get_issues):
        """Test that incremental sync only fetches issues updated since last_sync_at."""
        # Arrange
        mock_get_issues.return_value = []

        # Act
        sync_project_issues(self.tracked_project, full_sync=False)

        # Assert
        mock_get_issues.assert_called_once()
        call_kwargs = mock_get_issues.call_args[1]
        self.assertIn("since", call_kwargs)
        self.assertIsNotNone(call_kwargs["since"])

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_passes_since_parameter_to_get_project_issues(self, mock_get_issues):
        """Test that the since parameter is correctly passed to get_project_issues."""
        # Arrange
        last_sync_time = timezone.now() - timezone.timedelta(hours=2)
        self.tracked_project.last_sync_at = last_sync_time
        self.tracked_project.save()

        mock_get_issues.return_value = []

        # Act
        sync_project_issues(self.tracked_project, full_sync=False)

        # Assert
        call_kwargs = mock_get_issues.call_args[1]
        self.assertEqual(call_kwargs["since"], last_sync_time)


class TestSyncProjectIssuesErrorHandling(TestCase):
    """Tests for error handling in sync_project_issues function."""

    def setUp(self):
        """Set up test fixtures."""
        self.integration = JiraIntegrationFactory()
        self.tracked_project = TrackedJiraProjectFactory(integration=self.integration)

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_sets_sync_status_to_error_on_failure(self, mock_get_issues):
        """Test that sync_status is set to 'error' when sync fails."""
        # Arrange
        mock_get_issues.side_effect = Exception("API connection failed")

        # Act
        result = sync_project_issues(self.tracked_project, full_sync=True)

        # Assert
        self.tracked_project.refresh_from_db()
        self.assertEqual(self.tracked_project.sync_status, "error")
        self.assertGreater(result["errors"], 0)

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_stores_error_message_in_last_sync_error(self, mock_get_issues):
        """Test that error message is stored in last_sync_error field."""
        # Arrange
        mock_get_issues.side_effect = JiraSyncError("Authentication failed")

        # Act
        sync_project_issues(self.tracked_project, full_sync=True)

        # Assert
        self.tracked_project.refresh_from_db()
        self.assertIsNotNone(self.tracked_project.last_sync_error)
        self.assertIn("Authentication failed", self.tracked_project.last_sync_error)


class TestSyncProjectIssuesReturnValue(TestCase):
    """Tests for the return value of sync_project_issues function."""

    def setUp(self):
        """Set up test fixtures."""
        self.integration = JiraIntegrationFactory()
        self.tracked_project = TrackedJiraProjectFactory(integration=self.integration)

    @patch("apps.integrations.services.jira_sync.get_project_issues")
    def test_returns_dict_with_issues_created_updated_errors_counts(self, mock_get_issues):
        """Test that function returns a dict with issues_created, issues_updated, and errors counts."""
        # Arrange - Create one existing issue and mock API to return 2 issues
        JiraIssueFactory(team=self.tracked_project.team, jira_key="PROJ-1", jira_id="1001")

        mock_get_issues.return_value = [
            {
                "key": "PROJ-1",
                "id": "1001",
                "fields": {
                    "summary": "Updated issue",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "Done"},
                    "assignee": None,
                    "customfield_10016": 3.0,
                    "created": "2025-01-01T10:00:00.000+0000",
                    "resolutiondate": "2025-01-02T10:00:00.000+0000",
                },
            },
            {
                "key": "PROJ-2",
                "id": "1002",
                "fields": {
                    "summary": "New issue",
                    "issuetype": {"name": "Bug"},
                    "status": {"name": "To Do"},
                    "assignee": None,
                    "customfield_10016": 2.0,
                    "created": "2025-01-03T10:00:00.000+0000",
                    "resolutiondate": None,
                },
            },
        ]

        # Act
        result = sync_project_issues(self.tracked_project, full_sync=True)

        # Assert
        self.assertIn("issues_created", result)
        self.assertIn("issues_updated", result)
        self.assertIn("errors", result)
        self.assertEqual(result["issues_created"], 1)
        self.assertEqual(result["issues_updated"], 1)
        self.assertEqual(result["errors"], 0)
