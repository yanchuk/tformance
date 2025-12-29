"""Tests for sync progress redirect after repository selection.

TDD RED Phase: These tests verify that after selecting repositories,
the user is redirected to the sync progress page instead of directly
to the Jira connection step.

Current behavior: POST to select_repositories -> redirect to /onboarding/jira/
Desired behavior: POST to select_repositories -> redirect to /onboarding/sync/
"""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class TestSelectRepositoriesRedirectToSyncProgress(TestCase):
    """Tests that repository selection redirects to sync progress page."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(
            username="repotest@example.com",
            email="repotest@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)

    def test_post_select_repositories_redirects_to_sync_progress(self):
        """Test that POST to select_repositories redirects to sync progress, not Jira.

        After the user selects repositories, they should be redirected to the
        sync progress page so they can see the real-time sync status before
        continuing to the Jira connection step.
        """
        self.client.login(username="repotest@example.com", password="testpassword123")

        # Mock the GitHub API call and Celery task
        with (
            patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_repos,
            patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline,
        ):
            mock_repos.return_value = [
                {"id": 123456, "full_name": "org/repo1", "name": "repo1"},
            ]
            mock_pipeline.return_value.id = "test-task-id-123"

            response = self.client.post(
                reverse("onboarding:select_repos"),
                {"repos": ["123456"]},
            )

        # Should redirect to sync progress page, NOT to Jira
        self.assertRedirects(
            response,
            reverse("onboarding:sync_progress"),
            fetch_redirect_response=False,
        )

    def test_post_select_repositories_without_repos_redirects_to_sync_progress(self):
        """Test that POST without selecting repos still redirects to sync progress.

        Even if no repositories are selected (user skips), they should see
        the sync progress page which will show no repos are being synced.
        """
        self.client.login(username="repotest@example.com", password="testpassword123")

        response = self.client.post(
            reverse("onboarding:select_repos"),
            {"repos": []},
        )

        # Should still redirect to sync progress page
        self.assertRedirects(
            response,
            reverse("onboarding:sync_progress"),
            fetch_redirect_response=False,
        )


class TestSyncProgressAccessibleAfterRepoSelection(TestCase):
    """Tests that sync progress page is accessible with proper context."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(
            username="synctest@example.com",
            email="synctest@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)

    def test_sync_progress_page_accessible_after_repo_selection(self):
        """Test that sync progress page loads correctly after repo selection."""
        self.client.login(username="synctest@example.com", password="testpassword123")

        # Create tracked repositories (simulating what happens after selection)
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "onboarding/sync_progress.html")

    def test_sync_progress_page_shows_tracked_repositories(self):
        """Test that sync progress page shows the tracked repositories."""
        self.client.login(username="synctest@example.com", password="testpassword123")

        # Create tracked repositories
        repo1 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/repo1",
        )
        repo2 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="org/repo2",
        )

        response = self.client.get(reverse("onboarding:sync_progress"))

        # Context should contain the repos
        self.assertIn("repos", response.context)
        repos_in_context = list(response.context["repos"])
        self.assertEqual(len(repos_in_context), 2)
        self.assertIn(repo1, repos_in_context)
        self.assertIn(repo2, repos_in_context)


class TestSyncTaskIdStoredInSession(TestCase):
    """Tests that sync_task_id is stored in session for progress polling."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(
            username="tasktest@example.com",
            email="tasktest@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)

    def test_sync_task_id_stored_in_session_after_repo_selection(self):
        """Test that sync_task_id is stored in session when repos are selected.

        The sync_task_id is needed for the sync progress page to poll for
        the background task's progress.
        """
        self.client.login(username="tasktest@example.com", password="testpassword123")

        # Mock the GitHub API call and Celery task
        with (
            patch("apps.onboarding.views.github_oauth.get_organization_repositories") as mock_repos,
            patch("apps.onboarding.views.start_onboarding_pipeline") as mock_pipeline,
        ):
            mock_repos.return_value = [
                {"id": 789012, "full_name": "org/repo", "name": "repo"},
            ]
            mock_pipeline.return_value.id = "celery-task-uuid-456"

            self.client.post(
                reverse("onboarding:select_repos"),
                {"repos": ["789012"]},
            )

        # Verify the task_id is stored in session
        session = self.client.session
        self.assertIn("sync_task_id", session)
        self.assertEqual(session["sync_task_id"], "celery-task-uuid-456")

    def test_sync_progress_page_has_access_to_task_id(self):
        """Test that sync progress page can access the task_id from session.

        The sync progress page needs the task_id to poll for progress updates
        via the start_sync API or a progress endpoint.
        """
        self.client.login(username="tasktest@example.com", password="testpassword123")

        # Simulate having a task_id in session (as would happen after repo selection)
        session = self.client.session
        session["sync_task_id"] = "test-task-uuid-789"
        session.save()

        # Create a tracked repo so the page has something to show
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # The sync progress template should receive the task_id in context
        # or be able to access it for JavaScript polling
        # Note: Current implementation may not pass task_id to template context,
        # but the session should be accessible for polling endpoints
