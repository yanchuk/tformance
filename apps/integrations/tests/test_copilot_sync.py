"""Tests for Copilot metrics sync Celery tasks."""

from unittest.mock import MagicMock, patch

from celery.exceptions import Retry
from django.test import TestCase

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
)
from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.metrics.models import AIUsageDaily


class TestSyncCopilotMetricsTask(TestCase):
    """Tests for sync_copilot_metrics_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="gho_test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="test-org",
        )
        # Create team members with GitHub usernames
        self.member1 = TeamMemberFactory(
            team=self.team,
            github_username="alice",
            display_name="Alice Developer",
        )
        self.member2 = TeamMemberFactory(
            team=self.team,
            github_username="bob",
            display_name="Bob Engineer",
        )

    @patch("apps.integrations.tasks.map_copilot_to_ai_usage")
    @patch("apps.integrations.tasks.parse_metrics_response")
    @patch("apps.integrations.tasks.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_fetches_and_stores_metrics(self, mock_fetch, mock_parse, mock_map):
        """Test that sync_copilot_metrics_task fetches metrics and stores them in AIUsageDaily."""
        from apps.integrations.tasks import sync_copilot_metrics_task

        # Arrange - Mock the service layer calls
        mock_fetch.return_value = [
            {
                "date": "2025-12-17",
                "total_active_users": 10,
                "copilot_ide_code_completions": {
                    "total_completions": 5000,
                    "total_acceptances": 3000,
                },
            }
        ]

        mock_parse.return_value = [
            {
                "date": "2025-12-17",
                "code_completions_total": 5000,
                "code_completions_accepted": 3000,
            }
        ]

        mock_map.return_value = {
            "date": "2025-12-17",
            "source": "copilot",
            "suggestions_shown": 5000,
            "suggestions_accepted": 3000,
            "acceptance_rate": 60.0,
        }

        # Act
        result = sync_copilot_metrics_task(self.team.id)

        # Assert - Verify service methods were called
        mock_fetch.assert_called_once_with("gho_test_token_12345", "test-org", since=None, until=None)
        mock_parse.assert_called_once()
        mock_map.assert_called_once()

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("metrics_synced", result)
        self.assertEqual(result["metrics_synced"], 1)

        # Verify AIUsageDaily records were created
        ai_usage_records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        self.assertEqual(ai_usage_records.count(), 1)
        record = ai_usage_records.first()
        self.assertEqual(record.suggestions_shown, 5000)
        self.assertEqual(record.suggestions_accepted, 3000)

    @patch("apps.integrations.tasks.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_handles_unavailable_copilot(self, mock_fetch):
        """Test that task gracefully handles 403 error when Copilot is not available."""
        from apps.integrations.services.copilot_metrics import CopilotMetricsError
        from apps.integrations.tasks import sync_copilot_metrics_task

        # Arrange - Mock fetch to raise 403 error
        mock_fetch.side_effect = CopilotMetricsError(
            "HTTP 403: Organization does not have Copilot Business subscription"
        )

        # Act
        result = sync_copilot_metrics_task(self.team.id)

        # Assert - Task should not raise exception, return error status
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("403", result["error"])
        self.assertIn("copilot_available", result)
        self.assertFalse(result["copilot_available"])

        # Verify no AIUsageDaily records were created
        self.assertEqual(AIUsageDaily.objects.filter(team=self.team, source="copilot").count(), 0)

    @patch("apps.integrations.tasks.map_copilot_to_ai_usage")
    @patch("apps.integrations.tasks.parse_metrics_response")
    @patch("apps.integrations.tasks.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_matches_users_by_github_username(self, mock_fetch, mock_parse, mock_map):
        """Test that task correctly matches Copilot users to TeamMembers by GitHub username."""
        from apps.integrations.tasks import sync_copilot_metrics_task

        # Arrange - Mock API response with per_user_data
        mock_fetch.return_value = [
            {
                "date": "2025-12-17",
                "total_active_users": 2,
                "per_user_data": [
                    {
                        "github_username": "alice",
                        "total_completions": 2500,
                        "total_acceptances": 1500,
                    },
                    {
                        "github_username": "bob",
                        "total_completions": 2500,
                        "total_acceptances": 1500,
                    },
                ],
            }
        ]

        mock_parse.return_value = [
            {
                "date": "2025-12-17",
                "per_user_data": [
                    {
                        "github_username": "alice",
                        "code_completions_total": 2500,
                        "code_completions_accepted": 1500,
                    },
                    {
                        "github_username": "bob",
                        "code_completions_total": 2500,
                        "code_completions_accepted": 1500,
                    },
                ],
            }
        ]

        def map_side_effect(parsed_data, github_username=None):
            return {
                "date": "2025-12-17",
                "source": "copilot",
                "suggestions_shown": 2500,
                "suggestions_accepted": 1500,
                "acceptance_rate": 60.0,
            }

        mock_map.side_effect = map_side_effect

        # Act
        result = sync_copilot_metrics_task(self.team.id)

        # Assert - Verify AIUsageDaily records were created for both members
        alice_usage = AIUsageDaily.objects.filter(team=self.team, member=self.member1, source="copilot")
        bob_usage = AIUsageDaily.objects.filter(team=self.team, member=self.member2, source="copilot")

        self.assertEqual(alice_usage.count(), 1)
        self.assertEqual(bob_usage.count(), 1)

        # Verify result shows correct count
        self.assertIn("metrics_synced", result)
        self.assertEqual(result["metrics_synced"], 2)

    def test_sync_copilot_metrics_task_skips_team_without_github_integration(self):
        """Test that task skips teams without GitHub integration setup."""
        from apps.integrations.tasks import sync_copilot_metrics_task

        # Create team without GitHub integration
        team_no_integration = TeamFactory()

        # Act
        result = sync_copilot_metrics_task(team_no_integration.id)

        # Assert
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])
        self.assertIn("reason", result)
        self.assertIn("no github integration", result["reason"].lower())

    @patch("apps.integrations.tasks.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_retries_on_error(self, mock_fetch):
        """Test that task retries up to 3 times on transient errors."""
        from apps.integrations.tasks import sync_copilot_metrics_task

        # Arrange - Mock fetch to raise network error
        mock_fetch.side_effect = Exception("Network timeout")

        # Mock the task's retry method
        with patch.object(sync_copilot_metrics_task, "retry") as mock_retry:
            mock_retry.side_effect = Retry()

            # Act & Assert - Should raise Retry
            with self.assertRaises(Retry):
                sync_copilot_metrics_task(self.team.id)

            # Verify retry was called
            mock_retry.assert_called_once()

    @patch("sentry_sdk.capture_exception")
    @patch("apps.integrations.tasks.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_logs_to_sentry_on_final_failure(self, mock_fetch, mock_sentry):
        """Test that task logs errors to Sentry after max retries exhausted."""
        from apps.integrations.tasks import sync_copilot_metrics_task

        # Arrange
        test_exception = Exception("Permanent API failure")
        mock_fetch.side_effect = test_exception

        # Mock retry to simulate max retries exhausted
        with patch.object(sync_copilot_metrics_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            # Act
            result = sync_copilot_metrics_task(self.team.id)

            # Assert - Sentry should be called
            mock_sentry.assert_called_once()

            # Result should contain error
            self.assertIsInstance(result, dict)
            self.assertIn("error", result)


class TestSyncAllCopilotMetrics(TestCase):
    """Tests for sync_all_copilot_metrics Celery task.

    Note: These tests mock GitHubIntegration.objects to return only the test's
    integrations. This prevents flaky failures when running in parallel with
    other tests that create GitHubIntegration objects.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.models import GitHubIntegration

        # Create multiple teams with GitHub integrations
        self.team1 = TeamFactory()
        self.credential1 = IntegrationCredentialFactory(team=self.team1, provider="github")
        self.integration1 = GitHubIntegrationFactory(team=self.team1, credential=self.credential1)

        self.team2 = TeamFactory()
        self.credential2 = IntegrationCredentialFactory(team=self.team2, provider="github")
        self.integration2 = GitHubIntegrationFactory(team=self.team2, credential=self.credential2)

        # Create team without GitHub integration
        self.team_no_integration = TeamFactory()

        # Store integration IDs for isolated queryset
        self.integration_ids = [self.integration1.id, self.integration2.id]

        # Create isolated queryset that only includes this test's integrations
        self.isolated_qs = GitHubIntegration.objects.filter(id__in=self.integration_ids)

    def _get_isolated_queryset_mock(self):
        """Return a mock manager that returns only this test's integrations."""

        mock_manager = MagicMock()
        # Chain .exclude().exclude() to return the isolated queryset
        mock_manager.exclude.return_value.exclude.return_value = self.isolated_qs
        return mock_manager

    @patch("apps.integrations.tasks.sync_copilot_metrics_task")
    @patch("apps.integrations.tasks.GitHubIntegration.objects")
    def test_sync_all_copilot_metrics_dispatches_tasks_for_each_team(self, mock_objects, mock_task):
        """Test that sync_all_copilot_metrics dispatches individual tasks for all teams with GitHub."""
        from apps.integrations.tasks import sync_all_copilot_metrics

        # Mock to return only this test's integrations
        mock_objects.exclude.return_value.exclude.return_value = self.isolated_qs

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Act
        result = sync_all_copilot_metrics()

        # Assert - Verify sync_copilot_metrics_task.delay was called for teams with GitHub integration
        self.assertEqual(mock_delay.call_count, 2)

        # Verify correct team IDs were passed
        called_team_ids = {call[0][0] for call in mock_delay.call_args_list}
        expected_team_ids = {self.team1.id, self.team2.id}
        self.assertEqual(called_team_ids, expected_team_ids)

        # Verify team without integration was NOT called
        self.assertNotIn(self.team_no_integration.id, called_team_ids)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        self.assertEqual(result["teams_dispatched"], 2)

    @patch("apps.integrations.tasks.sync_copilot_metrics_task")
    @patch("apps.integrations.tasks.GitHubIntegration.objects")
    def test_sync_all_copilot_metrics_handles_empty_team_list(self, mock_objects, mock_task):
        """Test that task handles case where no teams have GitHub integration."""
        from apps.integrations.models import GitHubIntegration
        from apps.integrations.tasks import sync_all_copilot_metrics

        # Mock to return empty queryset (no integrations)
        mock_objects.exclude.return_value.exclude.return_value = GitHubIntegration.objects.none()

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Act
        result = sync_all_copilot_metrics()

        # Assert - No tasks should be dispatched
        mock_delay.assert_not_called()

        # Verify result shows zero teams
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        self.assertEqual(result["teams_dispatched"], 0)

    @patch("apps.integrations.tasks.sync_copilot_metrics_task")
    @patch("apps.integrations.tasks.GitHubIntegration.objects")
    def test_sync_all_copilot_metrics_continues_on_individual_dispatch_error(self, mock_objects, mock_task):
        """Test that task continues dispatching even if one dispatch fails."""
        from apps.integrations.tasks import sync_all_copilot_metrics

        # Mock to return only this test's integrations
        mock_objects.exclude.return_value.exclude.return_value = self.isolated_qs

        # Mock delay to raise exception for first team only
        mock_delay = MagicMock()

        def delay_side_effect(team_id):
            if team_id == self.team1.id:
                raise Exception("Celery connection error")
            return MagicMock()

        mock_delay.side_effect = delay_side_effect
        mock_task.delay = mock_delay

        # Act - Should not raise exception
        result = sync_all_copilot_metrics()

        # Assert - All teams were attempted
        self.assertEqual(mock_delay.call_count, 2)

        # Result should show successful dispatches
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        # Should count only successful dispatch (team2)
        self.assertEqual(result["teams_dispatched"], 1)

    @patch("apps.integrations.tasks.sync_copilot_metrics_task")
    @patch("apps.integrations.tasks.GitHubIntegration.objects")
    def test_sync_all_copilot_metrics_returns_correct_counts(self, mock_objects, mock_task):
        """Test that task returns dict with teams_dispatched count."""
        from apps.integrations.tasks import sync_all_copilot_metrics

        # Mock to return only this test's integrations
        mock_objects.exclude.return_value.exclude.return_value = self.isolated_qs

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Act
        result = sync_all_copilot_metrics()

        # Assert
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        self.assertEqual(result["teams_dispatched"], 2)


class TestSyncCopilotMetricsQueryCount(TestCase):
    """Tests for query count optimization in sync_copilot_metrics_task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="gho_test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="test-org",
        )
        # Create 10 team members with GitHub usernames
        self.members = []
        for i in range(10):
            member = TeamMemberFactory(
                team=self.team,
                github_username=f"user{i}",
                display_name=f"User {i}",
            )
            self.members.append(member)

    @patch("apps.integrations.tasks.map_copilot_to_ai_usage")
    @patch("apps.integrations.tasks.parse_metrics_response")
    @patch("apps.integrations.tasks.fetch_copilot_metrics")
    def test_sync_copilot_metrics_query_count_is_constant(self, mock_fetch, mock_parse, mock_map):
        """Test that TeamMember lookups use batch query (no N+1)."""
        from apps.integrations.tasks import sync_copilot_metrics_task

        # Arrange - Mock API response with 10 users
        per_user_data = [
            {
                "github_username": f"user{i}",
                "code_completions_total": 1000,
                "code_completions_accepted": 600,
            }
            for i in range(10)
        ]

        mock_fetch.return_value = [{"date": "2025-12-17", "per_user_data": per_user_data}]
        mock_parse.return_value = [{"date": "2025-12-17", "per_user_data": per_user_data}]

        def map_side_effect(parsed_data, github_username=None):
            return {
                "date": "2025-12-17",
                "source": "copilot",
                "suggestions_shown": 1000,
                "suggestions_accepted": 600,
                "acceptance_rate": 60.0,
            }

        mock_map.side_effect = map_side_effect

        # Act & Assert - Should use constant queries (not N+1)
        # Expected breakdown:
        # - Team lookup (1)
        # - GitHub Integration lookup (1) + credential access (1)
        # - Batch TeamMember lookup (1) - KEY: was N queries, now 1
        # - 10 update_or_create operations (6 queries each due to savepoints)
        # Total: ~64 queries
        # Without fix: would be ~73 queries (10 extra member lookups)
        # With fix: ~64 queries (member lookups batched into 1 query)
        with self.assertNumQueries(64):
            result = sync_copilot_metrics_task(self.team.id)

        self.assertEqual(result["metrics_synced"], 10)
