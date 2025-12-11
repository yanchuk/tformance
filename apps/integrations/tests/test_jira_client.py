"""Tests for Jira client service."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase

from apps.integrations.factories import IntegrationCredentialFactory
from apps.integrations.services.jira_client import (
    JiraClientError,
    get_accessible_projects,
    get_jira_client,
    get_project_issues,
)
from apps.metrics.factories import TeamFactory


class TestJiraClientError(TestCase):
    """Tests for JiraClientError exception."""

    def test_jira_client_error_can_be_raised(self):
        """Test that JiraClientError can be raised and caught."""
        with self.assertRaises(JiraClientError):
            raise JiraClientError("Test error")

    def test_jira_client_error_message(self):
        """Test that JiraClientError preserves error message."""
        error_message = "Connection to Jira API failed"
        try:
            raise JiraClientError(error_message)
        except JiraClientError as e:
            self.assertEqual(str(e), error_message)


class TestGetJiraClient(TestCase):
    """Tests for get_jira_client function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.services.encryption import encrypt

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token=encrypt("test_access_token_123"),
        )

    @patch("apps.integrations.services.jira_client.ensure_valid_jira_token")
    @patch("apps.integrations.services.jira_client.JIRA")
    def test_creates_jira_instance_with_correct_server_url(self, mock_jira_class, mock_ensure_token):
        """Test that get_jira_client creates JIRA instance with correct server URL."""
        # Arrange
        mock_ensure_token.return_value = "valid_access_token"
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        # Assume the credential has a related JiraIntegration
        from apps.integrations.factories import JiraIntegrationFactory

        jira_integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            cloud_id="test-cloud-id-12345",
        )

        # Act
        client = get_jira_client(self.credential)

        # Assert
        mock_jira_class.assert_called_once()
        call_kwargs = mock_jira_class.call_args[1]
        expected_server = f"https://api.atlassian.com/ex/jira/{jira_integration.cloud_id}"
        self.assertEqual(call_kwargs["server"], expected_server)
        self.assertIsNotNone(client)

    @patch("apps.integrations.services.jira_client.ensure_valid_jira_token")
    @patch("apps.integrations.services.jira_client.JIRA")
    def test_uses_bearer_token_from_ensure_valid_jira_token(self, mock_jira_class, mock_ensure_token):
        """Test that get_jira_client uses bearer token from ensure_valid_jira_token."""
        # Arrange
        mock_ensure_token.return_value = "refreshed_valid_token_xyz"
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        from apps.integrations.factories import JiraIntegrationFactory

        JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            cloud_id="test-cloud-id",
        )

        # Act
        get_jira_client(self.credential)

        # Assert - ensure_valid_jira_token should be called to get/refresh token
        mock_ensure_token.assert_called_once_with(self.credential)

        # Assert - JIRA should be instantiated with bearer token in options
        call_kwargs = mock_jira_class.call_args[1]
        self.assertIn("options", call_kwargs)
        self.assertIn("headers", call_kwargs["options"])
        self.assertEqual(
            call_kwargs["options"]["headers"]["Authorization"],
            "Bearer refreshed_valid_token_xyz",
        )

    @patch("apps.integrations.services.jira_client.ensure_valid_jira_token")
    @patch("apps.integrations.services.jira_client.JIRA")
    def test_raises_jira_client_error_on_authentication_failure(self, mock_jira_class, mock_ensure_token):
        """Test that get_jira_client raises JiraClientError on authentication failure."""
        # Arrange
        mock_ensure_token.return_value = "valid_token"
        mock_jira_class.side_effect = Exception("401 Unauthorized")

        from apps.integrations.factories import JiraIntegrationFactory

        JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            cloud_id="test-cloud-id",
        )

        # Act & Assert
        with self.assertRaises(JiraClientError) as context:
            get_jira_client(self.credential)

        self.assertIn("Failed to create Jira client", str(context.exception))


class TestGetAccessibleProjects(TestCase):
    """Tests for get_accessible_projects function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.services.encryption import encrypt

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token=encrypt("test_access_token_123"),
        )

    @patch("apps.integrations.services.jira_client.get_jira_client")
    def test_returns_list_of_project_dicts(self, mock_get_client):
        """Test that get_accessible_projects returns list of project dicts with id, key, name."""
        # Arrange
        mock_client = MagicMock()
        mock_project1 = Mock()
        mock_project1.id = "10001"
        mock_project1.key = "PROJ"
        mock_project1.name = "Project Alpha"

        mock_project2 = Mock()
        mock_project2.id = "10002"
        mock_project2.key = "TEST"
        mock_project2.name = "Test Project"

        mock_client.projects.return_value = [mock_project1, mock_project2]
        mock_get_client.return_value = mock_client

        # Act
        result = get_accessible_projects(self.credential)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # Check first project
        self.assertEqual(result[0]["id"], "10001")
        self.assertEqual(result[0]["key"], "PROJ")
        self.assertEqual(result[0]["name"], "Project Alpha")

        # Check second project
        self.assertEqual(result[1]["id"], "10002")
        self.assertEqual(result[1]["key"], "TEST")
        self.assertEqual(result[1]["name"], "Test Project")

    @patch("apps.integrations.services.jira_client.get_jira_client")
    def test_handles_empty_projects_list(self, mock_get_client):
        """Test that get_accessible_projects handles empty projects list."""
        # Arrange
        mock_client = MagicMock()
        mock_client.projects.return_value = []
        mock_get_client.return_value = mock_client

        # Act
        result = get_accessible_projects(self.credential)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.jira_client.get_jira_client")
    def test_raises_jira_client_error_on_api_error(self, mock_get_client):
        """Test that get_accessible_projects raises JiraClientError on API error."""
        # Arrange
        mock_client = MagicMock()
        mock_client.projects.side_effect = Exception("API error: rate limit exceeded")
        mock_get_client.return_value = mock_client

        # Act & Assert
        with self.assertRaises(JiraClientError) as context:
            get_accessible_projects(self.credential)

        self.assertIn("Failed to get accessible projects", str(context.exception))


class TestGetProjectIssuesFullSync(TestCase):
    """Tests for get_project_issues function (full sync without since parameter)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.services.encryption import encrypt

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token=encrypt("test_access_token_123"),
        )

    @patch("apps.integrations.services.jira_client.get_jira_client")
    def test_returns_list_of_issue_dicts_with_required_fields(self, mock_get_client):
        """Test that get_project_issues returns list of issue dicts with all required fields."""
        # Arrange
        mock_client = MagicMock()

        # Create mock issue with all required fields matching JiraIssue model
        mock_issue1 = Mock()
        mock_issue1.key = "PROJ-123"
        mock_issue1.id = "10050"
        mock_issue1.fields.summary = "Implement user authentication"
        mock_issue1.fields.issuetype.name = "Story"
        mock_issue1.fields.status.name = "In Progress"
        mock_issue1.fields.assignee = Mock(accountId="user-account-id-1")
        mock_issue1.fields.customfield_10016 = 5.0  # Story points
        mock_issue1.fields.created = "2023-11-01T10:00:00.000+0000"
        mock_issue1.fields.updated = "2023-11-05T14:30:00.000+0000"

        mock_issue2 = Mock()
        mock_issue2.key = "PROJ-124"
        mock_issue2.id = "10051"
        mock_issue2.fields.summary = "Fix login bug"
        mock_issue2.fields.issuetype.name = "Bug"
        mock_issue2.fields.status.name = "Done"
        mock_issue2.fields.assignee = None  # Unassigned
        mock_issue2.fields.customfield_10016 = 3.0
        mock_issue2.fields.created = "2023-11-02T09:00:00.000+0000"
        mock_issue2.fields.updated = "2023-11-06T16:00:00.000+0000"

        mock_client.search_issues.return_value = [mock_issue1, mock_issue2]
        mock_get_client.return_value = mock_client

        # Act
        result = get_project_issues(self.credential, "PROJ")

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # Check first issue
        self.assertEqual(result[0]["key"], "PROJ-123")
        self.assertEqual(result[0]["id"], "10050")
        self.assertEqual(result[0]["summary"], "Implement user authentication")
        self.assertEqual(result[0]["issue_type"], "Story")
        self.assertEqual(result[0]["status"], "In Progress")
        self.assertEqual(result[0]["assignee_account_id"], "user-account-id-1")
        self.assertEqual(result[0]["story_points"], 5.0)
        self.assertIn("created", result[0])
        self.assertIn("updated", result[0])

        # Check second issue (unassigned)
        self.assertEqual(result[1]["key"], "PROJ-124")
        self.assertIsNone(result[1]["assignee_account_id"])

    @patch("apps.integrations.services.jira_client.get_jira_client")
    def test_uses_correct_jql_for_full_sync(self, mock_get_client):
        """Test that get_project_issues uses correct JQL: 'project = {key} ORDER BY updated DESC'."""
        # Arrange
        mock_client = MagicMock()
        mock_client.search_issues.return_value = []
        mock_get_client.return_value = mock_client

        # Act
        get_project_issues(self.credential, "TESTPROJ")

        # Assert - verify JQL query
        mock_client.search_issues.assert_called_once()
        call_args = mock_client.search_issues.call_args
        jql = call_args[0][0]
        self.assertEqual(jql, "project = TESTPROJ ORDER BY updated DESC")

    @patch("apps.integrations.services.jira_client.get_jira_client")
    def test_handles_pagination_automatically(self, mock_get_client):
        """Test that get_project_issues handles pagination automatically."""
        # Arrange
        mock_client = MagicMock()

        # Simulate paginated results - JIRA library handles this internally
        # We're testing that we specify maxResults and startAt correctly
        mock_client.search_issues.return_value = []
        mock_get_client.return_value = mock_client

        # Act
        get_project_issues(self.credential, "PROJ")

        # Assert - verify pagination parameters are passed
        call_kwargs = mock_client.search_issues.call_args[1]
        # jira-python library uses maxResults=False to get all results
        self.assertIn("maxResults", call_kwargs)


class TestGetProjectIssuesIncrementalSync(TestCase):
    """Tests for get_project_issues function (incremental sync with since parameter)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.services.encryption import encrypt

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token=encrypt("test_access_token_123"),
        )

    @patch("apps.integrations.services.jira_client.get_jira_client")
    def test_uses_correct_jql_for_incremental_sync(self, mock_get_client):
        """Test that get_project_issues uses JQL with updated filter when since is provided."""
        # Arrange
        mock_client = MagicMock()
        mock_client.search_issues.return_value = []
        mock_get_client.return_value = mock_client

        since_date = datetime(2023, 11, 1, 12, 0, 0)

        # Act
        get_project_issues(self.credential, "PROJ", since=since_date)

        # Assert - verify JQL query includes updated date filter
        call_args = mock_client.search_issues.call_args
        jql = call_args[0][0]

        # JQL should filter by updated date and order by updated DESC
        self.assertIn("project = PROJ", jql)
        self.assertIn("updated >=", jql)
        self.assertIn("ORDER BY updated DESC", jql)

        # Check that date is formatted correctly for Jira (YYYY-MM-DD HH:MM or YYYY/MM/DD HH:MM)
        # Jira accepts: '2023-11-01 12:00' or '2023/11/01 12:00'
        self.assertTrue("2023-11-01" in jql or "2023/11/01" in jql)

    @patch("apps.integrations.services.jira_client.get_jira_client")
    def test_returns_only_issues_updated_since_given_datetime(self, mock_get_client):
        """Test that get_project_issues returns only issues updated since given datetime."""
        # Arrange
        mock_client = MagicMock()

        # Only return issues updated after the since date
        mock_issue = Mock()
        mock_issue.key = "PROJ-125"
        mock_issue.id = "10052"
        mock_issue.fields.summary = "Recently updated issue"
        mock_issue.fields.issuetype.name = "Story"
        mock_issue.fields.status.name = "In Progress"
        mock_issue.fields.assignee = None
        mock_issue.fields.customfield_10016 = 2.0
        mock_issue.fields.created = "2023-10-01T10:00:00.000+0000"
        mock_issue.fields.updated = "2023-11-05T10:00:00.000+0000"  # After since date

        mock_client.search_issues.return_value = [mock_issue]
        mock_get_client.return_value = mock_client

        since_date = datetime(2023, 11, 1, 0, 0, 0)

        # Act
        result = get_project_issues(self.credential, "PROJ", since=since_date)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["key"], "PROJ-125")
        self.assertEqual(result[0]["summary"], "Recently updated issue")
