"""Tests for integration status service."""

from django.test import TestCase

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    JiraIntegrationFactory,
    SlackIntegrationFactory,
    TrackedJiraProjectFactory,
    TrackedRepositoryFactory,
)
from apps.metrics.factories import PRSurveyFactory, PullRequestFactory, TeamFactory


class TestGetTeamIntegrationStatus(TestCase):
    """Tests for get_team_integration_status service function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_returns_correct_structure_for_team_with_no_integrations(self):
        """Test that the function returns the correct structure when team has no integrations."""
        from apps.integrations.services.status import get_team_integration_status

        status = get_team_integration_status(self.team)

        # Verify structure
        self.assertIn("github", status)
        self.assertIn("jira", status)
        self.assertIn("slack", status)
        self.assertIn("has_data", status)
        self.assertIn("pr_count", status)
        self.assertIn("survey_count", status)

        # Verify GitHub status
        self.assertIn("connected", status["github"])
        self.assertIn("org_name", status["github"])
        self.assertIn("member_count", status["github"])
        self.assertIn("repo_count", status["github"])
        self.assertFalse(status["github"]["connected"])
        self.assertIsNone(status["github"]["org_name"])
        self.assertEqual(status["github"]["member_count"], 0)
        self.assertEqual(status["github"]["repo_count"], 0)

        # Verify Jira status
        self.assertIn("connected", status["jira"])
        self.assertIn("site_name", status["jira"])
        self.assertIn("project_count", status["jira"])
        self.assertFalse(status["jira"]["connected"])
        self.assertIsNone(status["jira"]["site_name"])
        self.assertEqual(status["jira"]["project_count"], 0)

        # Verify Slack status
        self.assertIn("connected", status["slack"])
        self.assertIn("workspace_name", status["slack"])
        self.assertFalse(status["slack"]["connected"])
        self.assertIsNone(status["slack"]["workspace_name"])

        # Verify data counts
        self.assertFalse(status["has_data"])
        self.assertEqual(status["pr_count"], 0)
        self.assertEqual(status["survey_count"], 0)

    def test_returns_correct_github_status_when_connected(self):
        """Test that the function returns correct GitHub status when connected."""
        from apps.integrations.services.status import get_team_integration_status

        # Create GitHub integration with repositories
        github_integration = GitHubIntegrationFactory(team=self.team, organization_slug="my-awesome-org")
        TrackedRepositoryFactory.create_batch(3, team=self.team, integration=github_integration)

        status = get_team_integration_status(self.team)

        # Verify GitHub status
        self.assertTrue(status["github"]["connected"])
        self.assertEqual(status["github"]["org_name"], "my-awesome-org")
        self.assertEqual(status["github"]["repo_count"], 3)
        # member_count should come from TeamMember.objects.filter(team=team, github_id__isnull=False)
        self.assertEqual(status["github"]["member_count"], 0)

    def test_returns_correct_github_member_count(self):
        """Test that the function returns correct GitHub member count."""
        from apps.integrations.services.status import get_team_integration_status
        from apps.metrics.factories import TeamMemberFactory

        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team)

        # Create team members, some with GitHub IDs (factory generates unique IDs)
        TeamMemberFactory.create_batch(3, team=self.team)  # These have github_ids from factory sequence
        TeamMemberFactory.create_batch(2, team=self.team, github_id="")  # Empty string, not None

        status = get_team_integration_status(self.team)

        # Should only count members with github_id
        self.assertEqual(status["github"]["member_count"], 3)

    def test_returns_correct_jira_status_when_connected(self):
        """Test that the function returns correct Jira status when connected."""
        from apps.integrations.services.status import get_team_integration_status

        # Create Jira integration with projects
        jira_integration = JiraIntegrationFactory(team=self.team, site_name="Acme Corp")
        TrackedJiraProjectFactory.create_batch(2, team=self.team, integration=jira_integration)

        status = get_team_integration_status(self.team)

        # Verify Jira status
        self.assertTrue(status["jira"]["connected"])
        self.assertEqual(status["jira"]["site_name"], "Acme Corp")
        self.assertEqual(status["jira"]["project_count"], 2)

    def test_returns_correct_slack_status_when_connected(self):
        """Test that the function returns correct Slack status when connected."""
        from apps.integrations.services.status import get_team_integration_status

        # Create Slack integration
        SlackIntegrationFactory(team=self.team, workspace_name="Engineering Team")

        status = get_team_integration_status(self.team)

        # Verify Slack status
        self.assertTrue(status["slack"]["connected"])
        self.assertEqual(status["slack"]["workspace_name"], "Engineering Team")

    def test_has_data_is_true_when_prs_exist(self):
        """Test that has_data is True when PRs exist for the team."""
        from apps.integrations.services.status import get_team_integration_status

        # Create some PRs
        PullRequestFactory.create_batch(5, team=self.team)

        status = get_team_integration_status(self.team)

        # has_data should be True
        self.assertTrue(status["has_data"])
        self.assertEqual(status["pr_count"], 5)

    def test_has_data_is_false_when_no_prs_exist(self):
        """Test that has_data is False when no PRs exist for the team."""
        from apps.integrations.services.status import get_team_integration_status

        status = get_team_integration_status(self.team)

        # has_data should be False
        self.assertFalse(status["has_data"])
        self.assertEqual(status["pr_count"], 0)

    def test_pr_count_and_survey_count_are_correct(self):
        """Test that pr_count and survey_count are correctly calculated."""
        from apps.integrations.services.status import get_team_integration_status

        # Create PRs
        pr1 = PullRequestFactory(team=self.team)
        pr2 = PullRequestFactory(team=self.team)
        PullRequestFactory(team=self.team)  # pr3 - needed for count

        # Create surveys for some PRs
        PRSurveyFactory(team=self.team, pull_request=pr1)
        PRSurveyFactory(team=self.team, pull_request=pr2)

        status = get_team_integration_status(self.team)

        # Verify counts
        self.assertEqual(status["pr_count"], 3)
        self.assertEqual(status["survey_count"], 2)

    def test_returns_correct_status_with_all_integrations_connected(self):
        """Test that the function returns correct status when all integrations are connected."""
        from apps.integrations.services.status import get_team_integration_status
        from apps.metrics.factories import TeamMemberFactory

        # Create all integrations
        github_integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-org")
        TrackedRepositoryFactory.create_batch(2, team=self.team, integration=github_integration)
        members = TeamMemberFactory.create_batch(4, team=self.team)  # Factory generates unique github_ids

        jira_integration = JiraIntegrationFactory(team=self.team, site_name="Acme Jira")
        TrackedJiraProjectFactory.create_batch(3, team=self.team, integration=jira_integration)

        SlackIntegrationFactory(team=self.team, workspace_name="Acme Workspace")

        # Create some data (using existing members as authors to avoid creating extra members)
        pr1 = PullRequestFactory(team=self.team, author=members[0])
        PullRequestFactory(team=self.team, author=members[1])  # pr2 - for count
        PRSurveyFactory(team=self.team, pull_request=pr1)

        status = get_team_integration_status(self.team)

        # Verify all integrations
        self.assertTrue(status["github"]["connected"])
        self.assertEqual(status["github"]["org_name"], "acme-org")
        self.assertEqual(status["github"]["member_count"], 4)
        self.assertEqual(status["github"]["repo_count"], 2)

        self.assertTrue(status["jira"]["connected"])
        self.assertEqual(status["jira"]["site_name"], "Acme Jira")
        self.assertEqual(status["jira"]["project_count"], 3)

        self.assertTrue(status["slack"]["connected"])
        self.assertEqual(status["slack"]["workspace_name"], "Acme Workspace")

        self.assertTrue(status["has_data"])
        self.assertEqual(status["pr_count"], 2)
        self.assertEqual(status["survey_count"], 1)
