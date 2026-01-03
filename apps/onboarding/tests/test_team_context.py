"""Tests for team context handling in onboarding views.

ISS-005: Onboarding sync page shows wrong team when navigating from team dashboard.
"""

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class SyncProgressTeamContextTests(TestCase):
    """Tests for team context in sync_progress view.

    Verifies that sync_progress respects the session team context
    rather than always showing the user's first team.
    """

    def setUp(self):
        """Set up test fixtures with user having multiple teams."""
        self.user = CustomUser.objects.create_user(
            username="multi_team@example.com",
            email="multi_team@example.com",
            password="testpassword123",
        )
        # Create two teams - user's first team will be team_a
        self.team_a = TeamFactory(name="Team Alpha")
        self.team_b = TeamFactory(name="Team Beta")

        # Add user to both teams (team_a first, so it's the "first" team)
        self.team_a.members.add(self.user)
        self.team_b.members.add(self.user)

        # Set up integrations for both teams
        self.integration_a = GitHubIntegrationFactory(team=self.team_a)
        self.integration_b = GitHubIntegrationFactory(team=self.team_b)
        TrackedRepositoryFactory(team=self.team_a, integration=self.integration_a)
        TrackedRepositoryFactory(team=self.team_b, integration=self.integration_b)

    def test_sync_progress_uses_session_team_when_set(self):
        """sync_progress should show the team from session, not user's first team.

        When user navigates from a team dashboard (e.g., ?team=84), the session
        stores that team ID. sync_progress should respect this.
        """
        self.client.login(username="multi_team@example.com", password="testpassword123")

        # Set team_b in session (simulating navigation from team_b dashboard)
        session = self.client.session
        session["team"] = self.team_b.id
        session.save()

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Should show team_b (from session), NOT team_a (user's first team)
        self.assertEqual(response.context["team"], self.team_b)
        self.assertNotEqual(response.context["team"], self.team_a)

    def test_sync_progress_falls_back_to_first_team_when_no_session(self):
        """sync_progress should fall back to first team when no session team set.

        This maintains backward compatibility for users without session team.
        """
        self.client.login(username="multi_team@example.com", password="testpassword123")

        # Don't set any team in session
        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Should fall back to first team (team_a)
        self.assertEqual(response.context["team"], self.team_a)

    def test_sync_progress_shows_correct_repos_for_session_team(self):
        """sync_progress should show repositories for the session team."""
        self.client.login(username="multi_team@example.com", password="testpassword123")

        # Set team_b in session
        session = self.client.session
        session["team"] = self.team_b.id
        session.save()

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Repos should be from team_b, not team_a
        repos = list(response.context["repos"])
        for repo in repos:
            self.assertEqual(repo.team, self.team_b)


class StartSyncTeamContextTests(TestCase):
    """Tests for team context in start_sync API view.

    Verifies that start_sync respects the session team context.
    """

    def setUp(self):
        """Set up test fixtures with user having multiple teams."""
        self.user = CustomUser.objects.create_user(
            username="api_multi_team@example.com",
            email="api_multi_team@example.com",
            password="testpassword123",
        )
        self.team_a = TeamFactory(name="API Team Alpha")
        self.team_b = TeamFactory(name="API Team Beta")

        self.team_a.members.add(self.user)
        self.team_b.members.add(self.user)

        self.integration_a = GitHubIntegrationFactory(team=self.team_a)
        self.integration_b = GitHubIntegrationFactory(team=self.team_b)
        self.repo_a = TrackedRepositoryFactory(team=self.team_a, integration=self.integration_a)
        self.repo_b = TrackedRepositoryFactory(team=self.team_b, integration=self.integration_b)

    def test_start_sync_uses_session_team_when_set(self):
        """start_sync should sync the team from session, not user's first team."""
        self.client.login(username="api_multi_team@example.com", password="testpassword123")

        # Set team_b in session
        session = self.client.session
        session["team"] = self.team_b.id
        session.save()

        # Mock the Celery task to avoid actual sync
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            from unittest.mock import patch

            with patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline:
                mock_pipeline.return_value.id = "test-task-id"

                response = self.client.post(reverse("onboarding:start_sync"))

                self.assertEqual(response.status_code, 200)
                # Should call pipeline with team_b.id, not team_a.id
                mock_pipeline.assert_called_once()
                call_args = mock_pipeline.call_args
                self.assertEqual(call_args[0][0], self.team_b.id)

    def test_start_sync_falls_back_to_first_team_when_no_session(self):
        """start_sync should fall back to first team when no session team set."""
        self.client.login(username="api_multi_team@example.com", password="testpassword123")

        # Don't set any team in session
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            from unittest.mock import patch

            with patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline:
                mock_pipeline.return_value.id = "test-task-id"

                response = self.client.post(reverse("onboarding:start_sync"))

                self.assertEqual(response.status_code, 200)
                # Should call pipeline with team_a.id (first team)
                mock_pipeline.assert_called_once()
                call_args = mock_pipeline.call_args
                self.assertEqual(call_args[0][0], self.team_a.id)
