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
from apps.teams.models import Team


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

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.map_copilot_to_ai_usage")
    @patch("apps.integrations._task_modules.copilot.parse_metrics_response")
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_fetches_and_stores_metrics(
        self, mock_fetch, mock_parse, mock_map, mock_flag_check
    ):
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

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_handles_unavailable_copilot(self, mock_fetch, mock_flag_check):
        """Test that task gracefully handles 403 error when Copilot is not available."""
        from apps.integrations._task_modules.copilot import sync_copilot_metrics_task
        from apps.integrations.services.copilot_metrics import CopilotMetricsError

        # Set team to connected first
        self.team.copilot_status = "connected"
        self.team.save(update_fields=["copilot_status"])

        # Arrange - Mock fetch to raise 403 error
        mock_fetch.side_effect = CopilotMetricsError(
            "HTTP 403: Organization does not have Copilot Business subscription"
        )

        # Act
        result = sync_copilot_metrics_task(self.team.id)

        # Assert - Task should not raise exception, return error status
        self.assertIsInstance(result, dict)
        # Key behavior: copilot_available flag should be False for 403 errors
        self.assertIn("copilot_available", result)
        self.assertFalse(result["copilot_available"])

        # Verify copilot_status was updated to insufficient_licenses
        self.team.refresh_from_db()
        self.assertEqual(self.team.copilot_status, "insufficient_licenses")
        self.assertEqual(self.team.copilot_consecutive_failures, 1)

        # Verify no AIUsageDaily records were created
        self.assertEqual(AIUsageDaily.objects.filter(team=self.team, source="copilot").count(), 0)

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_handles_token_revoked(self, mock_fetch, mock_flag_check):
        """Test that task handles 401 error by marking token as revoked."""
        from apps.integrations._task_modules.copilot import sync_copilot_metrics_task
        from apps.integrations.services.copilot_metrics import CopilotMetricsError

        # Set team to connected first
        self.team.copilot_status = "connected"
        self.team.save(update_fields=["copilot_status"])

        # Arrange - Mock fetch to raise 401 error
        mock_fetch.side_effect = CopilotMetricsError("HTTP 401: Unauthorized - Token invalid or expired")

        # Act
        result = sync_copilot_metrics_task(self.team.id)

        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "token_revoked")

        # Verify copilot_status was updated
        self.team.refresh_from_db()
        self.assertEqual(self.team.copilot_status, "token_revoked")

        # Verify credential was marked as revoked
        self.credential.refresh_from_db()
        self.assertTrue(self.credential.is_revoked)

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.map_copilot_to_ai_usage")
    @patch("apps.integrations._task_modules.copilot.parse_metrics_response")
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_resets_failures_on_success(
        self, mock_fetch, mock_parse, mock_map, mock_flag_check
    ):
        """Test that successful sync resets consecutive_failures and updates last_sync_at."""
        from django.utils import timezone

        from apps.integrations._task_modules.copilot import sync_copilot_metrics_task

        # Arrange - Team with previous failures
        self.team.copilot_status = "connected"
        self.team.copilot_consecutive_failures = 3
        self.team.copilot_last_sync_at = None
        self.team.save(update_fields=["copilot_status", "copilot_consecutive_failures", "copilot_last_sync_at"])

        # Mock successful sync
        mock_fetch.return_value = [{"date": "2025-12-17", "total_active_users": 1}]
        mock_parse.return_value = [{"date": "2025-12-17", "code_completions_total": 100}]
        mock_map.return_value = {
            "date": "2025-12-17",
            "source": "copilot",
            "suggestions_shown": 100,
            "suggestions_accepted": 60,
            "acceptance_rate": 60.0,
        }

        before_sync = timezone.now()

        # Act
        result = sync_copilot_metrics_task(self.team.id)

        # Assert
        self.assertIn("metrics_synced", result)

        # Verify failures were reset
        self.team.refresh_from_db()
        self.assertEqual(self.team.copilot_consecutive_failures, 0)

        # Verify last_sync_at was updated
        self.assertIsNotNone(self.team.copilot_last_sync_at)
        self.assertGreaterEqual(self.team.copilot_last_sync_at, before_sync)

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.map_copilot_to_ai_usage")
    @patch("apps.integrations._task_modules.copilot.parse_metrics_response")
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_matches_users_by_github_username(
        self, mock_fetch, mock_parse, mock_map, mock_flag_check
    ):
        """Test that task correctly matches Copilot users to TeamMembers by GitHub username."""
        from apps.integrations._task_modules.copilot import sync_copilot_metrics_task

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

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    def test_sync_copilot_metrics_task_skips_team_without_github_integration(self, mock_flag_check):
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

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_retries_on_error(self, mock_fetch, mock_flag_check):
        """Test that task retries up to 3 times on transient errors."""
        from apps.integrations._task_modules.copilot import sync_copilot_metrics_task

        # Arrange - Mock fetch to raise network error
        mock_fetch.side_effect = Exception("Network timeout")

        # Mock the task's retry method on the actual task from _task_modules
        with patch.object(sync_copilot_metrics_task, "retry") as mock_retry:
            mock_retry.side_effect = Retry()

            # Act & Assert - Should raise Retry
            with self.assertRaises(Retry):
                sync_copilot_metrics_task(self.team.id)

            # Verify retry was called
            mock_retry.assert_called_once()

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("sentry_sdk.capture_exception")
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_metrics_task_logs_to_sentry_on_final_failure(self, mock_fetch, mock_sentry, mock_flag_check):
        """Test that task logs errors to Sentry after max retries exhausted."""
        from apps.integrations._task_modules.copilot import sync_copilot_metrics_task

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

        # Create multiple teams with GitHub integrations
        self.team1 = TeamFactory()
        # Set copilot_status="connected" so teams are eligible for sync
        self.team1.copilot_status = "connected"
        self.team1.save(update_fields=["copilot_status"])
        self.credential1 = IntegrationCredentialFactory(team=self.team1, provider="github")
        self.integration1 = GitHubIntegrationFactory(team=self.team1, credential=self.credential1)

        self.team2 = TeamFactory(copilot_status="connected")
        self.credential2 = IntegrationCredentialFactory(team=self.team2, provider="github")
        self.integration2 = GitHubIntegrationFactory(team=self.team2, credential=self.credential2)

        # Create team without GitHub integration (but with copilot connected - will be skipped)
        self.team_no_integration = TeamFactory(copilot_status="connected")

        # Store team IDs for test isolation
        self.connected_team_ids = [self.team1.id, self.team2.id, self.team_no_integration.id]

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_globally_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.sync_copilot_metrics_task")
    def test_sync_all_copilot_metrics_dispatches_tasks_for_each_team(self, mock_task, mock_global_flag):
        """Test that sync_all_copilot_metrics dispatches individual tasks for connected teams."""
        from apps.integrations.tasks import sync_all_copilot_metrics

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Act
        result = sync_all_copilot_metrics()

        # Get team IDs that were dispatched
        called_team_ids = {call[0][0] for call in mock_delay.call_args_list}

        # Assert - at minimum, our two test teams with integrations should be dispatched
        # (other teams from parallel tests may also be included, so we check containment)
        self.assertIn(self.team1.id, called_team_ids)
        self.assertIn(self.team2.id, called_team_ids)

        # team_no_integration has copilot_status="connected" but no GitHubIntegration
        # so it should NOT be in dispatched (should be skipped)
        self.assertNotIn(self.team_no_integration.id, called_team_ids)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        self.assertGreaterEqual(result["teams_dispatched"], 2)
        self.assertIn("teams_skipped", result)
        self.assertIn("duration_seconds", result)

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_globally_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.sync_copilot_metrics_task")
    def test_sync_all_copilot_metrics_handles_empty_team_list(self, mock_task, mock_global_flag):
        """Test that task handles case where no teams have copilot_status='connected'."""
        from apps.integrations.tasks import sync_all_copilot_metrics

        # First, set all our test teams to disabled (so they won't be synced)
        Team.objects.filter(id__in=self.connected_team_ids).update(copilot_status="disabled")

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Act
        result = sync_all_copilot_metrics()

        # Get team IDs that were dispatched
        called_team_ids = {call[0][0] for call in mock_delay.call_args_list}

        # Our test teams should NOT be called (they're now disabled)
        self.assertNotIn(self.team1.id, called_team_ids)
        self.assertNotIn(self.team2.id, called_team_ids)
        self.assertNotIn(self.team_no_integration.id, called_team_ids)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        self.assertIn("teams_skipped", result)

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_globally_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.sync_copilot_metrics_task")
    def test_sync_all_copilot_metrics_continues_on_individual_dispatch_error(self, mock_task, mock_global_flag):
        """Test that task continues dispatching even if one dispatch fails."""
        from apps.integrations.tasks import sync_all_copilot_metrics

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

        # Get team IDs that were attempted
        called_team_ids = {call[0][0] for call in mock_delay.call_args_list}

        # At minimum, our test teams should have been attempted
        self.assertIn(self.team1.id, called_team_ids)
        self.assertIn(self.team2.id, called_team_ids)

        # Result should show at least one successful dispatch
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        self.assertGreaterEqual(result["teams_dispatched"], 1)  # At least team2 succeeded
        self.assertIn("teams_skipped", result)
        self.assertGreaterEqual(result["teams_skipped"], 1)  # At least team1 failed + team_no_integration skipped

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_globally_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.sync_copilot_metrics_task")
    def test_sync_all_copilot_metrics_returns_correct_counts(self, mock_task, mock_global_flag):
        """Test that task returns dict with teams_dispatched, teams_skipped, and duration."""
        from apps.integrations.tasks import sync_all_copilot_metrics

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Act
        result = sync_all_copilot_metrics()

        # Assert - verify all return fields are present
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        self.assertGreaterEqual(result["teams_dispatched"], 2)  # At least our 2 test teams
        self.assertIn("teams_skipped", result)
        # At least 1 skipped (team_no_integration has no GitHubIntegration)
        self.assertGreaterEqual(result["teams_skipped"], 1)
        self.assertIn("duration_seconds", result)
        self.assertIsInstance(result["duration_seconds"], float)


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

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.map_copilot_to_ai_usage")
    @patch("apps.integrations._task_modules.copilot.parse_metrics_response")
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_metrics_query_count_is_constant(self, mock_fetch, mock_parse, mock_map, mock_flag_check):
        """Test that TeamMember lookups use batch query (no N+1)."""
        from apps.integrations._task_modules.copilot import sync_copilot_metrics_task

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
        # - Team update for copilot_consecutive_failures and copilot_last_sync_at (1)
        # Total: ~65 queries
        # Without fix: would be ~74 queries (10 extra member lookups)
        # With fix: ~65 queries (member lookups batched into 1 query)
        with self.assertNumQueries(65):
            result = sync_copilot_metrics_task(self.team.id)

        self.assertEqual(result["metrics_synced"], 10)


class TestSyncCopilotPipelineTask(TestCase):
    """Tests for sync_copilot_pipeline_task Celery task.

    This task is used during onboarding pipeline to sync Copilot metrics
    before LLM processing. It skips if Copilot is not connected and always
    transitions to llm_processing status.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="syncing_copilot")
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
        self.member = TeamMemberFactory(
            team=self.team,
            github_username="alice",
        )

    def test_sync_copilot_pipeline_task_skips_when_not_connected(self):
        """Test that task skips sync when copilot_status != 'connected'."""
        from apps.integrations._task_modules.copilot import sync_copilot_pipeline_task

        # Arrange - Team with Copilot disabled (default)
        self.team.copilot_status = "disabled"
        self.team.save(update_fields=["copilot_status"])

        # Act
        result = sync_copilot_pipeline_task(self.team.id)

        # Assert
        self.assertEqual(result["status"], "skipped")
        self.assertIn("copilot_status=disabled", result["reason"])

        # Verify status transitioned to llm_processing
        self.team.refresh_from_db()
        self.assertEqual(self.team.onboarding_pipeline_status, "llm_processing")

    def test_sync_copilot_pipeline_task_skips_when_insufficient_licenses(self):
        """Test that task skips when copilot_status is 'insufficient_licenses'."""
        from apps.integrations._task_modules.copilot import sync_copilot_pipeline_task

        # Arrange
        self.team.copilot_status = "insufficient_licenses"
        self.team.save(update_fields=["copilot_status"])

        # Act
        result = sync_copilot_pipeline_task(self.team.id)

        # Assert
        self.assertEqual(result["status"], "skipped")
        self.assertIn("insufficient_licenses", result["reason"])

        # Verify status transitioned to llm_processing
        self.team.refresh_from_db()
        self.assertEqual(self.team.onboarding_pipeline_status, "llm_processing")

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled", return_value=True)
    @patch("apps.integrations._task_modules.copilot.map_copilot_to_ai_usage")
    @patch("apps.integrations._task_modules.copilot.parse_metrics_response")
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_sync_copilot_pipeline_task_syncs_when_connected(self, mock_fetch, mock_parse, mock_map, mock_flag_check):
        """Test that task syncs Copilot metrics when copilot_status == 'connected'."""
        from apps.integrations._task_modules.copilot import sync_copilot_pipeline_task

        # Arrange - Team with Copilot connected
        self.team.copilot_status = "connected"
        self.team.save(update_fields=["copilot_status"])

        # Mock the sync response
        mock_fetch.return_value = [{"date": "2025-12-17", "total_active_users": 1}]
        mock_parse.return_value = [{"date": "2025-12-17", "code_completions_total": 100}]
        mock_map.return_value = {
            "date": "2025-12-17",
            "source": "copilot",
            "suggestions_shown": 100,
            "suggestions_accepted": 60,
            "acceptance_rate": 60.0,
        }

        # Act
        result = sync_copilot_pipeline_task(self.team.id)

        # Assert - Sync was called
        mock_fetch.assert_called_once()
        self.assertIn("metrics_synced", result)

        # Verify status transitioned to llm_processing
        self.team.refresh_from_db()
        self.assertEqual(self.team.onboarding_pipeline_status, "llm_processing")

    @patch("apps.integrations._task_modules.copilot.sync_copilot_metrics_task")
    def test_sync_copilot_pipeline_task_continues_on_sync_error(self, mock_sync_task):
        """Test that pipeline continues even if Copilot sync fails."""
        from apps.integrations._task_modules.copilot import sync_copilot_pipeline_task

        # Arrange - Team with Copilot connected but sync will fail
        self.team.copilot_status = "connected"
        self.team.save(update_fields=["copilot_status"])

        # Mock sync to raise exception
        mock_sync_task.side_effect = Exception("GitHub API timeout")

        # Act
        result = sync_copilot_pipeline_task(self.team.id)

        # Assert - Error was caught and logged
        self.assertEqual(result["status"], "error")
        self.assertIn("GitHub API timeout", result["reason"])

        # Verify status transitioned to llm_processing (pipeline didn't break)
        self.team.refresh_from_db()
        self.assertEqual(self.team.onboarding_pipeline_status, "llm_processing")
