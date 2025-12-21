from django.db import IntegrityError
from django.test import TestCase

from apps.metrics.models import (
    PRCheckRun,
    PullRequest,
    TeamMember,
)
from apps.teams.context import unset_current_team
from apps.teams.models import Team


class TestPRCheckRunModel(TestCase):
    """Tests for PRCheckRun model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(team=self.team, display_name="Author", github_username="author")
        self.pull_request = PullRequest.objects.create(
            team=self.team, github_pr_id=1, github_repo="org/repo", state="open", author=self.author
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_check_run_creation(self):
        """Test that PRCheckRun can be created with required fields."""
        check_run = PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=123456789,
            pull_request=self.pull_request,
            name="pytest",
            status="completed",
            conclusion="success",
        )
        self.assertEqual(check_run.github_check_run_id, 123456789)
        self.assertEqual(check_run.pull_request, self.pull_request)
        self.assertEqual(check_run.name, "pytest")
        self.assertEqual(check_run.status, "completed")
        self.assertEqual(check_run.conclusion, "success")
        self.assertIsNotNone(check_run.pk)

    def test_pr_check_run_pull_request_relationship(self):
        """Test that PRCheckRun has correct foreign key relationship with PullRequest."""
        check_run1 = PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=111,
            pull_request=self.pull_request,
            name="eslint",
            status="completed",
        )
        check_run2 = PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=222,
            pull_request=self.pull_request,
            name="build",
            status="in_progress",
        )

        # Test forward relationship
        self.assertEqual(check_run1.pull_request, self.pull_request)
        self.assertEqual(check_run2.pull_request, self.pull_request)

        # Test reverse relationship via related_name='check_runs'
        check_runs = self.pull_request.check_runs.all()
        self.assertEqual(check_runs.count(), 2)
        self.assertIn(check_run1, check_runs)
        self.assertIn(check_run2, check_runs)

    def test_pr_check_run_unique_constraint(self):
        """Test that unique constraint on (team, github_check_run_id) is enforced."""
        PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=999,
            pull_request=self.pull_request,
            name="test-check",
            status="queued",
        )
        # Attempt to create another check run with same github_check_run_id in same team
        with self.assertRaises(IntegrityError):
            PRCheckRun.objects.create(
                team=self.team,
                github_check_run_id=999,
                pull_request=self.pull_request,
                name="different-check",
                status="completed",
            )

    def test_pr_check_run_str_representation(self):
        """Test that PRCheckRun.__str__ returns sensible format."""
        check_run = PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=555,
            pull_request=self.pull_request,
            name="pytest",
            status="completed",
            conclusion="failure",
        )
        str_repr = str(check_run)
        # Should contain key identifying information
        self.assertIn("pytest", str_repr)
        # Should indicate it's a check run
        self.assertTrue(len(str_repr) > 0)
