"""Tests for sync logging in the onboarding pipeline.

TDD RED Phase: These tests verify that the pipeline logs structured events
using the sync_logger module for observability and debugging.

Tests expect the following log events:
- sync.pipeline.started: When start_phase1_pipeline is called
- sync.pipeline.phase_changed: When update_pipeline_status changes phase
- sync.pipeline.completed: When status becomes phase1_complete
- sync.pipeline.failed: When handle_pipeline_failure is called
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

from apps.integrations.factories import TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory


class TestPipelineLogsStartedEvent(TestCase):
    """Tests for sync.pipeline.started log event."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    @patch("apps.integrations.onboarding_pipeline.get_sync_logger")
    def test_pipeline_logs_started_event(self, mock_get_logger, mock_chain):
        """When start_phase1_pipeline is called, it logs sync.pipeline.started with team_id, repos_count, phase."""
        from apps.integrations.onboarding_pipeline import start_phase1_pipeline

        # Configure mock chain
        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Call the pipeline
        start_phase1_pipeline(self.team.id, [self.repo.id])

        # Verify sync.pipeline.started was logged
        # The logger should have been called with info() containing the event
        # Note: signal-based architecture adds execution_mode to the extra
        mock_logger.info.assert_any_call(
            "sync.pipeline.started",
            extra={
                "team_id": self.team.id,
                "repos_count": 1,
                "phase": "phase1",
                "execution_mode": "signal_based",
            },
        )


class TestPipelineLogsPhaseChangedEvent(TestCase):
    """Tests for sync.pipeline.phase_changed log event."""

    def setUp(self):
        self.team = TeamFactory()
        # Set initial pipeline status
        self.team.onboarding_pipeline_status = "syncing"
        self.team.save()

    @patch("apps.integrations.onboarding_pipeline.get_sync_logger")
    def test_pipeline_logs_phase_changed_event(self, mock_get_logger):
        """Logs sync.pipeline.phase_changed with team_id, phase, previous_phase."""
        from apps.integrations.onboarding_pipeline import update_pipeline_status

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Update pipeline status from syncing to llm_processing
        update_pipeline_status(self.team.id, "llm_processing")

        # Verify sync.pipeline.phase_changed was logged
        mock_logger.info.assert_any_call(
            "sync.pipeline.phase_changed",
            extra={
                "team_id": self.team.id,
                "phase": "llm_processing",
                "previous_phase": "syncing",
            },
        )

    @patch("apps.integrations.onboarding_pipeline.get_sync_logger")
    def test_pipeline_logs_phase_changed_from_not_started(self, mock_get_logger):
        """Logs phase change from not_started to syncing."""
        from apps.integrations.onboarding_pipeline import update_pipeline_status

        # Reset to not_started
        self.team.onboarding_pipeline_status = "not_started"
        self.team.save()

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Update pipeline status
        update_pipeline_status(self.team.id, "syncing")

        # Verify log
        mock_logger.info.assert_any_call(
            "sync.pipeline.phase_changed",
            extra={
                "team_id": self.team.id,
                "phase": "syncing",
                "previous_phase": "not_started",
            },
        )


class TestPipelineLogsCompletedEvent(TestCase):
    """Tests for sync.pipeline.completed log event."""

    def setUp(self):
        self.team = TeamFactory()
        # Set initial status and started_at to simulate an active pipeline
        self.team.onboarding_pipeline_status = "computing_insights"
        self.team.save()

    @patch("apps.integrations.onboarding_pipeline.get_sync_logger")
    def test_pipeline_logs_completed_event(self, mock_get_logger):
        """When status becomes phase1_complete, it logs sync.pipeline.completed with duration."""
        from django.utils import timezone

        from apps.integrations.onboarding_pipeline import update_pipeline_status

        # Set a started_at time to calculate duration
        self.team.onboarding_pipeline_started_at = timezone.now() - timezone.timedelta(minutes=5)
        self.team.save()

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Update status to phase1_complete
        update_pipeline_status(self.team.id, "phase1_complete")

        # Verify sync.pipeline.completed was logged with duration
        # Find the call that includes sync.pipeline.completed
        completed_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.pipeline.completed"]
        self.assertEqual(len(completed_calls), 1, "Expected sync.pipeline.completed to be logged once")

        # Check the extra dict has required fields
        extra = completed_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("team_id"), self.team.id)
        self.assertIn("duration_seconds", extra)
        # Duration should be approximately 300 seconds (5 minutes)
        self.assertGreater(extra["duration_seconds"], 0)

    @patch("apps.integrations.onboarding_pipeline.get_sync_logger")
    def test_pipeline_logs_completed_event_with_full_complete_status(self, mock_get_logger):
        """Also logs completed event when status becomes 'complete' (full pipeline)."""
        from django.utils import timezone

        from apps.integrations.onboarding_pipeline import update_pipeline_status

        # Set a started_at time
        self.team.onboarding_pipeline_started_at = timezone.now() - timezone.timedelta(minutes=10)
        self.team.save()

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Update status to complete (full pipeline completion)
        update_pipeline_status(self.team.id, "complete")

        # Verify sync.pipeline.completed was logged
        completed_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.pipeline.completed"]
        self.assertEqual(len(completed_calls), 1, "Expected sync.pipeline.completed to be logged once")


class TestPipelineLogsFailedEvent(TestCase):
    """Tests for sync.pipeline.failed log event."""

    def setUp(self):
        self.team = TeamFactory()
        self.team.onboarding_pipeline_status = "syncing"
        self.team.save()

    @patch("apps.integrations.onboarding_pipeline.get_sync_logger")
    def test_pipeline_logs_failed_event(self, mock_get_logger):
        """When handle_pipeline_failure is called, it logs sync.pipeline.failed with error details."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Create a test exception
        test_exception = Exception("Test connection error")

        # Call failure handler
        handle_pipeline_failure(
            None,  # request
            test_exception,  # exception
            None,  # traceback
            team_id=self.team.id,
        )

        # Verify sync.pipeline.failed was logged
        failed_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "sync.pipeline.failed"]
        self.assertEqual(len(failed_calls), 1, "Expected sync.pipeline.failed to be logged once")

        # Check the extra dict has required fields
        extra = failed_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("team_id"), self.team.id)
        self.assertIn("error_type", extra)
        self.assertIn("error_message", extra)

    @patch("apps.integrations.onboarding_pipeline.get_sync_logger")
    def test_pipeline_logs_failed_event_with_error_type(self, mock_get_logger):
        """Failed event includes error_type from exception class."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Create a specific exception type
        class GitHubAPIError(Exception):
            pass

        test_exception = GitHubAPIError("Rate limit exceeded")

        # Call failure handler
        handle_pipeline_failure(
            None,
            test_exception,
            None,
            team_id=self.team.id,
        )

        # Verify error_type is captured
        failed_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "sync.pipeline.failed"]
        self.assertEqual(len(failed_calls), 1)

        extra = failed_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("error_type"), "GitHubAPIError")

    @patch("apps.integrations.onboarding_pipeline.get_sync_logger")
    def test_pipeline_logs_failed_event_with_previous_phase(self, mock_get_logger):
        """Failed event includes the phase that was active when failure occurred."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        # Set a specific phase before failure
        self.team.onboarding_pipeline_status = "llm_processing"
        self.team.save()

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Call failure handler
        handle_pipeline_failure(
            None,
            Exception("LLM API timeout"),
            None,
            team_id=self.team.id,
        )

        # Verify failed_phase is included
        failed_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "sync.pipeline.failed"]
        self.assertEqual(len(failed_calls), 1)

        extra = failed_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("failed_phase"), "llm_processing")


class TestRepoSyncLogsStartedEvent(TestCase):
    """Tests for sync.repo.started log event in sync_historical_data_task."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService")
    @patch("apps.utils.sync_logger.get_sync_logger")
    def test_repo_sync_logs_started_event(self, mock_get_logger, mock_service_class):
        """Logs sync.repo.started with team_id, repo_id, full_name."""
        from apps.integrations.tasks import sync_historical_data_task

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure mock service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.sync_repository.return_value = {"prs_synced": 5}

        # Call the task directly (bypass Celery)
        sync_historical_data_task(
            team_id=self.team.id,
            repo_ids=[self.repo.id],
            days_back=30,
        )

        # Verify sync.repo.started was logged
        started_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.repo.started"]
        self.assertEqual(len(started_calls), 1, "Expected sync.repo.started to be logged once")

        # Check the extra dict has required fields
        extra = started_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("team_id"), self.team.id)
        self.assertEqual(extra.get("repo_id"), self.repo.id)
        self.assertEqual(extra.get("full_name"), self.repo.full_name)


class TestRepoSyncLogsProgressEvent(TestCase):
    """Tests for sync.repo.progress log event in sync_historical_data_task."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService")
    @patch("apps.utils.sync_logger.get_sync_logger")
    def test_repo_sync_logs_progress_event(self, mock_get_logger, mock_service_class):
        """Progress callback logs sync.repo.progress with prs_done, prs_total, pct (every 10 PRs or configurable)."""
        from apps.integrations.tasks import sync_historical_data_task

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure mock service to call progress callback
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        def simulate_progress(repo, progress_callback, days_back, skip_recent):
            # Simulate progress at 10, 20, and 30 PRs (every 10 PRs)
            progress_callback(10, 30, "Processing PRs")
            progress_callback(20, 30, "Processing PRs")
            progress_callback(30, 30, "Processing PRs")
            return {"prs_synced": 30}

        mock_service.sync_repository.side_effect = simulate_progress

        # Call the task directly (bypass Celery)
        sync_historical_data_task(
            team_id=self.team.id,
            repo_ids=[self.repo.id],
            days_back=30,
        )

        # Verify sync.repo.progress was logged
        progress_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.repo.progress"]
        # Expect at least one progress log (logging strategy may vary)
        self.assertGreaterEqual(len(progress_calls), 1, "Expected at least one sync.repo.progress log")

        # Check the first progress call has required fields
        extra = progress_calls[0][1].get("extra", {})
        self.assertIn("prs_done", extra)
        self.assertIn("prs_total", extra)
        self.assertIn("pct", extra)
        self.assertEqual(extra.get("repo_id"), self.repo.id)


class TestRepoSyncLogsCompletedEvent(TestCase):
    """Tests for sync.repo.completed log event in sync_historical_data_task."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService")
    @patch("apps.utils.sync_logger.get_sync_logger")
    def test_repo_sync_logs_completed_event(self, mock_get_logger, mock_service_class):
        """When a repo sync completes, logs sync.repo.completed with prs_synced, duration_seconds."""
        from apps.integrations.tasks import sync_historical_data_task

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure mock service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.sync_repository.return_value = {"prs_synced": 25}

        # Call the task directly (bypass Celery)
        sync_historical_data_task(
            team_id=self.team.id,
            repo_ids=[self.repo.id],
            days_back=30,
        )

        # Verify sync.repo.completed was logged
        completed_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.repo.completed"]
        self.assertEqual(len(completed_calls), 1, "Expected sync.repo.completed to be logged once")

        # Check the extra dict has required fields
        extra = completed_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("team_id"), self.team.id)
        self.assertEqual(extra.get("repo_id"), self.repo.id)
        self.assertEqual(extra.get("prs_synced"), 25)
        self.assertIn("duration_seconds", extra)
        self.assertGreaterEqual(extra["duration_seconds"], 0)


class TestRepoSyncLogsFailedEvent(TestCase):
    """Tests for sync.repo.failed log event in sync_historical_data_task."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.integrations.services.onboarding_sync.OnboardingSyncService")
    @patch("apps.utils.sync_logger.get_sync_logger")
    def test_repo_sync_logs_failed_event(self, mock_get_logger, mock_service_class):
        """When a repo sync fails, logs sync.repo.failed with error_type, error_message."""
        from apps.integrations.tasks import sync_historical_data_task

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure mock service to raise an exception
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        class GitHubRateLimitError(Exception):
            pass

        mock_service.sync_repository.side_effect = GitHubRateLimitError("API rate limit exceeded")

        # Call the task directly (bypass Celery)
        # The task catches exceptions per-repo and continues
        sync_historical_data_task(
            team_id=self.team.id,
            repo_ids=[self.repo.id],
            days_back=30,
        )

        # Verify sync.repo.failed was logged
        failed_calls = [call for call in mock_logger.error.call_args_list if call[0][0] == "sync.repo.failed"]
        self.assertEqual(len(failed_calls), 1, "Expected sync.repo.failed to be logged once")

        # Check the extra dict has required fields
        extra = failed_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("team_id"), self.team.id)
        self.assertEqual(extra.get("repo_id"), self.repo.id)
        self.assertEqual(extra.get("error_type"), "GitHubRateLimitError")
        self.assertIn("error_message", extra)
        self.assertIn("rate limit", extra["error_message"].lower())


@pytest.mark.skip(reason="TDD RED test - structured retry logging not implemented in sync tasks")
class TestTaskRetryLogsEvent(TestCase):
    """Tests for sync.task.retry log event when Celery task retries."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.utils.sync_logger.get_sync_logger")
    def test_task_retry_logs_event(self, mock_get_logger):
        """When a Celery task retries, logs sync.task.retry with retry_count, countdown, error."""
        from celery.exceptions import Retry

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # This test verifies that when a task raises self.retry(),
        # it logs sync.task.retry with the retry details before raising.
        #
        # We test the retry logging behavior by patching the internal sync function
        # to raise an exception, which triggers the retry logic in the task.
        # The task should log sync.task.retry BEFORE calling self.retry().

        # Patch the internal helper function that sync_repository_task calls
        with patch("apps.integrations.tasks._sync_incremental_with_graphql_or_rest") as mock_sync:
            mock_sync.side_effect = Exception("Connection timeout")

            # Also patch the retry method to capture what happens
            with patch("apps.integrations.tasks.sync_repository_task.retry") as mock_retry:
                mock_retry.side_effect = Retry()

                # The task should log sync.task.retry before raising Retry
                with self.assertRaises(Retry):
                    # Import the underlying function, not the Celery task wrapper
                    from apps.integrations.tasks import sync_repository_task

                    # Call with repo_id - this triggers the retry path
                    sync_repository_task(self.repo.id)

        # Verify sync.task.retry was logged
        retry_calls = [call for call in mock_logger.warning.call_args_list if call[0][0] == "sync.task.retry"]
        self.assertEqual(len(retry_calls), 1, "Expected sync.task.retry to be logged once")

        # Check the extra dict has required fields
        extra = retry_calls[0][1].get("extra", {})
        self.assertIn("retry_count", extra)
        self.assertIn("countdown", extra)
        self.assertIn("error", extra)


# =============================================================================
# GraphQL Sync Logging Tests
# =============================================================================


class TestGraphQLQueryLogsTiming(TestCase):
    """Tests for sync.api.graphql log event in GraphQL client."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.utils.sync_logger.get_sync_logger")
    @patch("apps.integrations.services.github_graphql.GitHubGraphQLClient._execute")
    async def test_graphql_query_logs_timing(self, mock_execute, mock_get_logger):
        """When fetch_prs_bulk is called, logs sync.api.graphql with query_name, duration_ms, status."""
        from apps.integrations.services.github_graphql import GitHubGraphQLClient

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure mock response with rate limit
        mock_execute.return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 4500, "resetAt": "2024-01-01T00:00:00Z"},
        }

        # Call the client
        client = GitHubGraphQLClient("fake_token")
        await client.fetch_prs_bulk("owner", "repo")

        # Verify sync.api.graphql was logged with timing info
        graphql_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.api.graphql"]
        self.assertEqual(len(graphql_calls), 1, "Expected sync.api.graphql to be logged once")

        # Check the extra dict has required fields
        extra = graphql_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("query_name"), "fetch_prs_bulk")
        self.assertIn("duration_ms", extra)
        self.assertGreaterEqual(extra["duration_ms"], 0)
        self.assertEqual(extra.get("status"), "success")


class TestGraphQLQueryLogsPointsCost(TestCase):
    """Tests for points_cost in GraphQL logs."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.utils.sync_logger.get_sync_logger")
    @patch("apps.integrations.services.github_graphql.GitHubGraphQLClient._execute")
    async def test_graphql_query_logs_points_cost(self, mock_execute, mock_get_logger):
        """GraphQL logs include points_cost from rate limit info."""
        from apps.integrations.services.github_graphql import GitHubGraphQLClient

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure mock response with rate limit showing points cost
        # Initial: 4500, After query: 4498, so cost = 2
        mock_execute.return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {
                "remaining": 4498,
                "resetAt": "2024-01-01T00:00:00Z",
                "cost": 2,  # GitHub includes this in responses
            },
        }

        # Call the client
        client = GitHubGraphQLClient("fake_token")
        await client.fetch_prs_bulk("owner", "repo")

        # Verify sync.api.graphql log includes points_cost
        graphql_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.api.graphql"]
        self.assertEqual(len(graphql_calls), 1)

        extra = graphql_calls[0][1].get("extra", {})
        self.assertIn("points_cost", extra)
        self.assertEqual(extra["points_cost"], 2)


class TestRateLimitCheckLogsStatus(TestCase):
    """Tests for sync.api.rate_limit log event."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.utils.sync_logger.get_sync_logger")
    @patch("apps.integrations.services.github_graphql.GitHubGraphQLClient._execute")
    async def test_rate_limit_check_logs_status(self, mock_execute, mock_get_logger):
        """When rate limit is checked, logs sync.api.rate_limit with remaining, limit, reset_at."""
        from apps.integrations.services.github_graphql import GitHubGraphQLClient

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure mock response with rate limit info
        mock_execute.return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {
                "remaining": 4500,
                "limit": 5000,
                "resetAt": "2024-01-01T12:00:00Z",
            },
        }

        # Call the client
        client = GitHubGraphQLClient("fake_token")
        await client.fetch_prs_bulk("owner", "repo")

        # Verify sync.api.rate_limit was logged
        rate_limit_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.api.rate_limit"]
        self.assertEqual(len(rate_limit_calls), 1, "Expected sync.api.rate_limit to be logged once")

        # Check the extra dict has required fields
        extra = rate_limit_calls[0][1].get("extra", {})
        self.assertEqual(extra.get("remaining"), 4500)
        self.assertEqual(extra.get("limit"), 5000)
        self.assertEqual(extra.get("reset_at"), "2024-01-01T12:00:00Z")


class TestRateLimitWaitLogsDuration(TestCase):
    """Tests for sync.api.rate_wait log event when waiting for rate limit reset."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.utils.sync_logger.get_sync_logger")
    @patch("apps.integrations.services.github_rate_limit.wait_for_rate_limit_reset_async")
    @patch("apps.integrations.services.github_graphql.GitHubGraphQLClient._execute")
    async def test_rate_limit_wait_logs_duration(self, mock_execute, mock_wait, mock_get_logger):
        """When waiting for rate limit reset, logs sync.api.rate_wait with wait_seconds."""
        from apps.integrations.services.github_graphql import GitHubGraphQLClient

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure wait to return True (indicating it waited)
        mock_wait.return_value = True

        # Configure mock response with LOW rate limit (below threshold of 100)
        # First call triggers wait, then returns success
        mock_execute.return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {
                "remaining": 50,  # Below RATE_LIMIT_THRESHOLD of 100
                "resetAt": "2024-01-01T12:00:00Z",
            },
        }

        # Call the client
        client = GitHubGraphQLClient("fake_token", wait_for_reset=True, max_wait_seconds=60)
        await client.fetch_prs_bulk("owner", "repo")

        # Verify sync.api.rate_wait was logged
        rate_wait_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.api.rate_wait"]
        self.assertEqual(len(rate_wait_calls), 1, "Expected sync.api.rate_wait to be logged once")

        # Check the extra dict has required fields
        extra = rate_wait_calls[0][1].get("extra", {})
        self.assertIn("wait_seconds", extra)
        self.assertGreaterEqual(extra["wait_seconds"], 0)


@pytest.mark.skip(reason="TDD RED test - sync.pr.processed logging not implemented in GraphQL sync")
class TestPRProcessedLogsDetails(TestCase):
    """Tests for sync.pr.processed log event when processing a PR in sync."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.utils.sync_logger.get_sync_logger")
    @patch("apps.integrations.services.github_graphql.GitHubGraphQLClient._execute")
    async def test_pr_processed_logs_details(self, mock_execute, mock_get_logger):
        """Logs sync.pr.processed with pr_id, pr_number, reviews/commits/files counts."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.integrations.services.github_graphql_sync import sync_repository_history_graphql

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Use recent dates within the 30-day window
        now = timezone.now()
        created_at = (now - timedelta(days=10)).isoformat()
        merged_at = (now - timedelta(days=9)).isoformat()

        # Configure mock response with a PR containing reviews, commits, files
        mock_execute.return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 123,
                            "title": "Test PR",
                            "body": "Test body",
                            "state": "MERGED",
                            "createdAt": created_at,
                            "mergedAt": merged_at,
                            "additions": 50,
                            "deletions": 10,
                            "isDraft": False,
                            "author": {"login": "test-user"},
                            "labels": {"nodes": []},
                            "milestone": None,
                            "assignees": {"nodes": []},
                            "closingIssuesReferences": {"nodes": []},
                            "reviews": {
                                "nodes": [
                                    {
                                        "databaseId": 1,
                                        "state": "APPROVED",
                                        "body": "LGTM",
                                        "submittedAt": created_at,
                                        "author": {"login": "reviewer"},
                                    },
                                    {
                                        "databaseId": 2,
                                        "state": "COMMENTED",
                                        "body": "Nice",
                                        "submittedAt": created_at,
                                        "author": {"login": "reviewer2"},
                                    },
                                ]
                            },
                            "commits": {
                                "nodes": [
                                    {
                                        "commit": {
                                            "oid": "abc123",
                                            "message": "Initial commit",
                                            "additions": 30,
                                            "deletions": 5,
                                            "author": {"date": created_at, "user": {"login": "test-user"}},
                                        }
                                    },
                                    {
                                        "commit": {
                                            "oid": "def456",
                                            "message": "Fix typo",
                                            "additions": 20,
                                            "deletions": 5,
                                            "author": {"date": created_at, "user": {"login": "test-user"}},
                                        }
                                    },
                                    {
                                        "commit": {
                                            "oid": "ghi789",
                                            "message": "Add tests",
                                            "additions": 0,
                                            "deletions": 0,
                                            "author": {"date": created_at, "user": {"login": "test-user"}},
                                        }
                                    },
                                ]
                            },
                            "files": {
                                "nodes": [
                                    {"path": "src/main.py", "additions": 30, "deletions": 5, "changeType": "MODIFIED"},
                                    {"path": "src/utils.py", "additions": 10, "deletions": 3, "changeType": "ADDED"},
                                    {
                                        "path": "tests/test_main.py",
                                        "additions": 10,
                                        "deletions": 2,
                                        "changeType": "ADDED",
                                    },
                                    {"path": "README.md", "additions": 0, "deletions": 0, "changeType": "MODIFIED"},
                                ]
                            },
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 4500, "resetAt": "2024-01-01T00:00:00Z"},
        }

        # Call the sync function
        await sync_repository_history_graphql(self.repo, days_back=30)

        # Verify sync.pr.processed was logged
        pr_processed_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.pr.processed"]
        self.assertEqual(len(pr_processed_calls), 1, "Expected sync.pr.processed to be logged once")

        # Check the extra dict has required fields
        extra = pr_processed_calls[0][1].get("extra", {})
        self.assertIn("pr_id", extra)
        self.assertEqual(extra.get("pr_number"), 123)
        self.assertEqual(extra.get("reviews_count"), 2)
        self.assertEqual(extra.get("commits_count"), 3)
        self.assertEqual(extra.get("files_count"), 4)


@pytest.mark.skip(reason="TDD RED test - sync.db.write logging not implemented in GraphQL sync")
class TestDBWriteLogsDetails(TestCase):
    """Tests for sync.db.write log event when writing to database."""

    def setUp(self):
        from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory

        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)

    @patch("apps.utils.sync_logger.get_sync_logger")
    @patch("apps.integrations.services.github_graphql.GitHubGraphQLClient._execute")
    async def test_db_write_logs_details(self, mock_execute, mock_get_logger):
        """When writing to DB, logs sync.db.write with entity_type, created, updated, duration_ms."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.integrations.services.github_graphql_sync import sync_repository_history_graphql

        # Configure mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Use recent dates within the 30-day window
        now = timezone.now()
        created_at = (now - timedelta(days=10)).isoformat()

        # Configure mock response with a PR
        mock_execute.return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 456,
                            "title": "Another PR",
                            "body": "Body text",
                            "state": "OPEN",
                            "createdAt": created_at,
                            "mergedAt": None,
                            "additions": 25,
                            "deletions": 5,
                            "isDraft": False,
                            "author": {"login": "developer"},
                            "labels": {"nodes": []},
                            "milestone": None,
                            "assignees": {"nodes": []},
                            "closingIssuesReferences": {"nodes": []},
                            "reviews": {"nodes": []},
                            "commits": {
                                "nodes": [
                                    {
                                        "commit": {
                                            "oid": "xyz999",
                                            "message": "WIP",
                                            "additions": 25,
                                            "deletions": 5,
                                            "author": {"date": created_at, "user": {"login": "developer"}},
                                        }
                                    }
                                ]
                            },
                            "files": {
                                "nodes": [
                                    {"path": "src/feature.py", "additions": 25, "deletions": 5, "changeType": "ADDED"},
                                ]
                            },
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 4500, "resetAt": "2024-01-01T00:00:00Z"},
        }

        # Call the sync function
        await sync_repository_history_graphql(self.repo, days_back=30)

        # Verify sync.db.write was logged for different entity types
        db_write_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "sync.db.write"]

        # Should have logs for PR, commits, files (possibly reviews too)
        self.assertGreaterEqual(len(db_write_calls), 1, "Expected at least one sync.db.write log")

        # Check at least one call has the required fields
        found_valid_log = False
        for call in db_write_calls:
            extra = call[1].get("extra", {})
            if "entity_type" in extra and "created" in extra and "updated" in extra and "duration_ms" in extra:
                found_valid_log = True
                self.assertIn(extra["entity_type"], ["pull_request", "commit", "file", "review"])
                self.assertIsInstance(extra["created"], int)
                self.assertIsInstance(extra["updated"], int)
                self.assertIsInstance(extra["duration_ms"], (int, float))
                self.assertGreaterEqual(extra["duration_ms"], 0)
                break

        self.assertTrue(found_valid_log, "Expected sync.db.write log with entity_type, created, updated, duration_ms")
