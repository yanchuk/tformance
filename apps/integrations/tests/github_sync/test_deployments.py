"""Tests for GitHub sync service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    sync_repository_deployments,
)


class TestSyncRepositoryDeployments(TestCase):
    """Tests for syncing deployments from a GitHub repository."""

    def _create_mock_deployment(
        self,
        deployment_id: int,
        environment: str,
        creator_id: int | None = None,
        created_at: str = "2025-01-15T10:00:00Z",
        sha: str = "a" * 40,
    ) -> MagicMock:
        """Create a mock PyGithub Deployment object with all required attributes."""
        mock_deployment = MagicMock()
        mock_deployment.id = deployment_id
        mock_deployment.environment = environment
        mock_deployment.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        mock_deployment.sha = sha

        # Mock creator
        if creator_id:
            mock_creator = MagicMock()
            mock_creator.id = creator_id
            mock_deployment.creator = mock_creator
        else:
            mock_deployment.creator = None

        return mock_deployment

    def _create_mock_deployment_status(
        self,
        state: str,
        created_at: str = "2025-01-15T10:05:00Z",
    ) -> MagicMock:
        """Create a mock PyGithub DeploymentStatus object."""
        mock_status = MagicMock()
        mock_status.state = state
        mock_status.created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return mock_status

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_repository_deployments_creates_records(self, mock_github_class):
        """Test that sync_repository_deployments creates Deployment records from GitHub deployments."""
        from apps.metrics.factories import TeamFactory, TeamMemberFactory
        from apps.metrics.models import Deployment

        # Set up test data
        team = TeamFactory()
        member = TeamMemberFactory(team=team, github_id="12345", display_name="Deploy Bot")

        # Mock deployments
        mock_deployment1 = self._create_mock_deployment(
            deployment_id=1001,
            environment="production",
            creator_id=12345,
            created_at="2025-01-15T10:00:00Z",
        )
        mock_deployment2 = self._create_mock_deployment(
            deployment_id=1002,
            environment="staging",
            creator_id=12345,
            created_at="2025-01-15T11:00:00Z",
        )

        # Mock deployment statuses (first status is latest)
        mock_status1 = self._create_mock_deployment_status(state="success", created_at="2025-01-15T10:05:00Z")
        mock_status2 = self._create_mock_deployment_status(state="pending", created_at="2025-01-15T11:02:00Z")

        mock_deployment1.get_statuses.return_value = [mock_status1]
        mock_deployment2.get_statuses.return_value = [mock_status2]

        # Mock PyGithub repository and API chain
        mock_repo = MagicMock()
        mock_repo.get_deployments.return_value = [mock_deployment1, mock_deployment2]

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        deployments_synced = sync_repository_deployments(
            repo_full_name="acme/repo",
            access_token="fake-token",
            team=team,
            errors=errors,
        )

        # Verify deployments were created
        self.assertEqual(deployments_synced, 2)
        self.assertEqual(len(errors), 0)

        # Verify database records
        deployment1 = Deployment.objects.get(team=team, github_deployment_id=1001)
        self.assertEqual(deployment1.github_repo, "acme/repo")
        self.assertEqual(deployment1.environment, "production")
        self.assertEqual(deployment1.status, "success")
        self.assertEqual(deployment1.creator, member)
        self.assertEqual(deployment1.deployed_at, datetime.fromisoformat("2025-01-15T10:00:00+00:00"))
        self.assertEqual(deployment1.sha, "a" * 40)  # Default SHA from mock

        deployment2 = Deployment.objects.get(team=team, github_deployment_id=1002)
        self.assertEqual(deployment2.environment, "staging")
        self.assertEqual(deployment2.status, "pending")
        self.assertEqual(deployment2.sha, "a" * 40)  # Default SHA from mock

        # Verify API calls
        mock_github_class.assert_called_once_with("fake-token")
        mock_github_instance.get_repo.assert_called_once_with("acme/repo")
        mock_repo.get_deployments.assert_called_once()
        mock_deployment1.get_statuses.assert_called_once()
        mock_deployment2.get_statuses.assert_called_once()

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_repository_deployments_gets_latest_status(self, mock_github_class):
        """Test that sync_repository_deployments uses the first status from get_statuses()."""
        from apps.metrics.factories import TeamFactory
        from apps.metrics.models import Deployment

        # Set up test data
        team = TeamFactory()

        # Mock deployment with multiple statuses (first is latest)
        mock_deployment = self._create_mock_deployment(
            deployment_id=2001,
            environment="production",
            created_at="2025-01-16T14:00:00Z",
        )

        # Multiple statuses - first one should be used
        mock_status_latest = self._create_mock_deployment_status(state="success", created_at="2025-01-16T14:10:00Z")
        mock_status_older = self._create_mock_deployment_status(state="pending", created_at="2025-01-16T14:05:00Z")
        mock_deployment.get_statuses.return_value = [mock_status_latest, mock_status_older]

        # Mock PyGithub repository
        mock_repo = MagicMock()
        mock_repo.get_deployments.return_value = [mock_deployment]

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        sync_repository_deployments(
            repo_full_name="acme/repo",
            access_token="fake-token",
            team=team,
            errors=errors,
        )

        # Verify the latest status (first in list) was used
        deployment = Deployment.objects.get(team=team, github_deployment_id=2001)
        self.assertEqual(deployment.status, "success")  # Not "pending"

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_repository_deployments_maps_creator(self, mock_github_class):
        """Test that sync_repository_deployments links deployment creator to TeamMember."""
        from apps.metrics.factories import TeamFactory, TeamMemberFactory
        from apps.metrics.models import Deployment

        # Set up test data with a team member
        team = TeamFactory()
        creator = TeamMemberFactory(team=team, github_id="99999", display_name="Jane Deployer")

        # Mock deployment with creator
        mock_deployment = self._create_mock_deployment(
            deployment_id=3001,
            environment="production",
            creator_id=99999,
            created_at="2025-01-17T09:00:00Z",
        )

        # Mock status
        mock_status = self._create_mock_deployment_status(state="success")
        mock_deployment.get_statuses.return_value = [mock_status]

        # Mock PyGithub repository
        mock_repo = MagicMock()
        mock_repo.get_deployments.return_value = [mock_deployment]

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        sync_repository_deployments(
            repo_full_name="acme/repo",
            access_token="fake-token",
            team=team,
            errors=errors,
        )

        # Verify creator was linked
        deployment = Deployment.objects.get(team=team, github_deployment_id=3001)
        self.assertEqual(deployment.creator, creator)
        self.assertEqual(deployment.creator.display_name, "Jane Deployer")

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_repository_deployments_maps_creator_handles_missing_member(self, mock_github_class):
        """Test that sync_repository_deployments handles deployments when creator is not a TeamMember."""
        from apps.metrics.factories import TeamFactory
        from apps.metrics.models import Deployment

        # Set up test data (no team member with github_id=88888)
        team = TeamFactory()

        # Mock deployment with creator that's not in our team
        mock_deployment = self._create_mock_deployment(
            deployment_id=4001,
            environment="production",
            creator_id=88888,  # Not a team member
            created_at="2025-01-18T12:00:00Z",
        )

        # Mock status
        mock_status = self._create_mock_deployment_status(state="success")
        mock_deployment.get_statuses.return_value = [mock_status]

        # Mock PyGithub repository
        mock_repo = MagicMock()
        mock_repo.get_deployments.return_value = [mock_deployment]

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        sync_repository_deployments(
            repo_full_name="acme/repo",
            access_token="fake-token",
            team=team,
            errors=errors,
        )

        # Verify deployment was created with no creator
        deployment = Deployment.objects.get(team=team, github_deployment_id=4001)
        self.assertIsNone(deployment.creator)

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_repository_deployments_updates_existing(self, mock_github_class):
        """Test that sync_repository_deployments updates existing records on re-sync."""
        from apps.metrics.factories import TeamFactory
        from apps.metrics.models import Deployment

        # Set up test data
        team = TeamFactory()

        # Create an existing deployment record with "pending" status
        Deployment.objects.create(
            team=team,
            github_deployment_id=5001,
            github_repo="acme/repo",
            environment="production",
            status="pending",
            deployed_at=datetime.fromisoformat("2025-01-19T08:00:00+00:00"),
        )

        # Mock deployment with updated status
        mock_deployment = self._create_mock_deployment(
            deployment_id=5001,
            environment="production",
            created_at="2025-01-19T08:00:00Z",
        )

        # Mock status showing success now
        mock_status = self._create_mock_deployment_status(state="success", created_at="2025-01-19T08:10:00Z")
        mock_deployment.get_statuses.return_value = [mock_status]

        # Mock PyGithub repository
        mock_repo = MagicMock()
        mock_repo.get_deployments.return_value = [mock_deployment]

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Verify initial state
        self.assertEqual(Deployment.objects.filter(team=team, github_deployment_id=5001).count(), 1)
        initial_deployment = Deployment.objects.get(team=team, github_deployment_id=5001)
        self.assertEqual(initial_deployment.status, "pending")

        # Call sync function
        errors = []
        deployments_synced = sync_repository_deployments(
            repo_full_name="acme/repo",
            access_token="fake-token",
            team=team,
            errors=errors,
        )

        # Verify deployment was updated (not duplicated)
        self.assertEqual(deployments_synced, 1)
        self.assertEqual(Deployment.objects.filter(team=team, github_deployment_id=5001).count(), 1)

        updated_deployment = Deployment.objects.get(team=team, github_deployment_id=5001)
        self.assertEqual(updated_deployment.status, "success")  # Updated from "pending"

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_repository_deployments_handles_api_error(self, mock_github_class):
        """Test that sync_repository_deployments accumulates errors on API failure."""
        from github import GithubException

        from apps.metrics.factories import TeamFactory
        from apps.metrics.models import Deployment

        # Set up test data
        team = TeamFactory()

        # Mock PyGithub to raise exception when getting deployments
        mock_repo = MagicMock()
        mock_repo.get_deployments.side_effect = GithubException(403, {"message": "Forbidden"})

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        deployments_synced = sync_repository_deployments(
            repo_full_name="acme/repo",
            access_token="fake-token",
            team=team,
            errors=errors,
        )

        # Verify error was accumulated (not raised)
        self.assertEqual(deployments_synced, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("acme/repo", errors[0])

        # Verify no deployments were created
        self.assertEqual(Deployment.objects.filter(team=team).count(), 0)
