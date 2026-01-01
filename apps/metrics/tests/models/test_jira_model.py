"""Tests for new JiraIssue model fields (TDD RED Phase).

These tests verify the existence and behavior of 4 new fields:
- description: TextField for full issue description
- labels: JSONField for issue labels list
- priority: CharField for priority level (High, Medium, Low)
- parent_issue_key: CharField for parent epic/story key
"""

from django.test import TestCase

from apps.metrics.factories import JiraIssueFactory, TeamFactory


class TestJiraIssueFields(TestCase):
    """Tests for new JiraIssue model fields."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_jiraissue_has_description_field(self):
        """Test that JiraIssue has a description field that accepts text."""
        issue = JiraIssueFactory(
            team=self.team,
            description="This is a detailed description of the issue.\n\nIt includes multiple paragraphs.",
        )
        self.assertEqual(
            issue.description, "This is a detailed description of the issue.\n\nIt includes multiple paragraphs."
        )

    def test_jiraissue_has_labels_field(self):
        """Test that JiraIssue has a labels field that accepts a list of strings."""
        labels = ["backend", "priority-high", "tech-debt"]
        issue = JiraIssueFactory(team=self.team, labels=labels)
        self.assertEqual(issue.labels, labels)
        self.assertIsInstance(issue.labels, list)
        self.assertEqual(len(issue.labels), 3)

    def test_jiraissue_has_priority_field(self):
        """Test that JiraIssue has a priority field that accepts priority levels."""
        issue_high = JiraIssueFactory(team=self.team, priority="High")
        self.assertEqual(issue_high.priority, "High")

        issue_medium = JiraIssueFactory(team=self.team, priority="Medium")
        self.assertEqual(issue_medium.priority, "Medium")

        issue_low = JiraIssueFactory(team=self.team, priority="Low")
        self.assertEqual(issue_low.priority, "Low")

    def test_jiraissue_has_parent_issue_key_field(self):
        """Test that JiraIssue has a parent_issue_key field for epic/story linkage."""
        issue = JiraIssueFactory(team=self.team, parent_issue_key="PROJ-100")
        self.assertEqual(issue.parent_issue_key, "PROJ-100")

    def test_jiraissue_description_can_be_empty(self):
        """Test that JiraIssue.description can be empty."""
        issue = JiraIssueFactory(team=self.team, description="")
        self.assertEqual(issue.description, "")

    def test_jiraissue_labels_can_be_empty_list(self):
        """Test that JiraIssue.labels can be an empty list."""
        issue = JiraIssueFactory(team=self.team, labels=[])
        self.assertEqual(issue.labels, [])

    def test_jiraissue_priority_can_be_blank(self):
        """Test that JiraIssue.priority can be blank (unset)."""
        issue = JiraIssueFactory(team=self.team, priority="")
        self.assertEqual(issue.priority, "")

    def test_jiraissue_parent_issue_key_can_be_blank(self):
        """Test that JiraIssue.parent_issue_key can be blank (no parent)."""
        issue = JiraIssueFactory(team=self.team, parent_issue_key="")
        self.assertEqual(issue.parent_issue_key, "")
