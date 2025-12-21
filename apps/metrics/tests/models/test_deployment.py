from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    Deployment,
    PullRequest,
    TeamMember,
)
from apps.teams.context import unset_current_team
from apps.teams.models import Team


class TestDeploymentModel(TestCase):
    """Tests for Deployment model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.creator = TeamMember.objects.create(
            team=self.team,
            display_name="John Doe",
            github_username="johndoe",
            github_id="123",
        )
        self.author = TeamMember.objects.create(
            team=self.team,
            display_name="Jane Smith",
            github_username="janesmith",
            github_id="456",
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team,
            github_pr_id=1,
            github_repo="org/repo",
            title="Test PR",
            author=self.author,
            state="merged",
            pr_created_at=django_timezone.now(),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_deployment_creation(self):
        """Test that Deployment can be created with all fields."""
        deployment = Deployment.objects.create(
            team=self.team,
            github_deployment_id=123456789,
            github_repo="org/repo",
            environment="production",
            status="success",
            creator=self.creator,
            deployed_at=django_timezone.now(),
            pull_request=self.pull_request,
            sha="a" * 40,
        )
        self.assertEqual(deployment.github_deployment_id, 123456789)
        self.assertEqual(deployment.github_repo, "org/repo")
        self.assertEqual(deployment.environment, "production")
        self.assertEqual(deployment.status, "success")
        self.assertEqual(deployment.creator, self.creator)
        self.assertEqual(deployment.pull_request, self.pull_request)
        self.assertEqual(deployment.sha, "a" * 40)
        self.assertIsNotNone(deployment.deployed_at)
        self.assertIsNotNone(deployment.pk)

    def test_deployment_team_relationship(self):
        """Test that deployment belongs to team."""
        deployment = Deployment.objects.create(
            team=self.team,
            github_deployment_id=987654321,
            github_repo="org/repo",
            environment="staging",
            status="success",
            deployed_at=django_timezone.now(),
            sha="b" * 40,
        )
        self.assertEqual(deployment.team, self.team)

        # Test team filtering
        team2 = Team.objects.create(name="Team Two", slug="team-two")
        deployment2 = Deployment.objects.create(
            team=team2,
            github_deployment_id=111111111,
            github_repo="org/other-repo",
            environment="production",
            status="success",
            deployed_at=django_timezone.now(),
            sha="c" * 40,
        )

        team1_deployments = Deployment.objects.filter(team=self.team)
        self.assertEqual(team1_deployments.count(), 1)
        self.assertIn(deployment, team1_deployments)
        self.assertNotIn(deployment2, team1_deployments)

    def test_deployment_unique_constraint(self):
        """Test that unique constraint on (team, github_deployment_id) is enforced."""
        Deployment.objects.create(
            team=self.team,
            github_deployment_id=999,
            github_repo="org/repo",
            environment="production",
            status="success",
            deployed_at=django_timezone.now(),
            sha="d" * 40,
        )
        # Attempt to create another deployment with same github_deployment_id in same team
        with self.assertRaises(IntegrityError):
            Deployment.objects.create(
                team=self.team,
                github_deployment_id=999,
                github_repo="org/other-repo",
                environment="staging",
                status="failure",
                deployed_at=django_timezone.now(),
                sha="e" * 40,
            )

    def test_deployment_str_representation(self):
        """Test that __str__ returns meaningful string."""
        deployment = Deployment.objects.create(
            team=self.team,
            github_deployment_id=555,
            github_repo="org/frontend",
            environment="production",
            status="success",
            deployed_at=django_timezone.now(),
            sha="f" * 40,
        )
        str_repr = str(deployment)
        # Should contain repo and environment at minimum
        self.assertIn("org/frontend", str_repr)
        self.assertIn("production", str_repr)

    def test_deployment_creator_relationship(self):
        """Test optional FK to TeamMember for creator."""
        # Test with creator
        deployment_with_creator = Deployment.objects.create(
            team=self.team,
            github_deployment_id=777,
            github_repo="org/repo",
            environment="staging",
            status="success",
            creator=self.creator,
            deployed_at=django_timezone.now(),
            sha="g" * 40,
        )
        self.assertEqual(deployment_with_creator.creator, self.creator)

        # Test without creator (null=True)
        deployment_no_creator = Deployment.objects.create(
            team=self.team,
            github_deployment_id=888,
            github_repo="org/repo",
            environment="production",
            status="success",
            deployed_at=django_timezone.now(),
            sha="h" * 40,
        )
        self.assertIsNone(deployment_no_creator.creator)

    def test_deployment_pull_request_relationship(self):
        """Test optional FK to PullRequest."""
        # Test with pull_request
        deployment_with_pr = Deployment.objects.create(
            team=self.team,
            github_deployment_id=333,
            github_repo="org/repo",
            environment="production",
            status="success",
            pull_request=self.pull_request,
            deployed_at=django_timezone.now(),
            sha="i" * 40,
        )
        self.assertEqual(deployment_with_pr.pull_request, self.pull_request)

        # Test without pull_request (null=True)
        deployment_no_pr = Deployment.objects.create(
            team=self.team,
            github_deployment_id=444,
            github_repo="org/repo",
            environment="staging",
            status="success",
            deployed_at=django_timezone.now(),
            sha="j" * 40,
        )
        self.assertIsNone(deployment_no_pr.pull_request)
