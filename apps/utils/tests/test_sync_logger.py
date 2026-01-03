"""Tests for sync logger module.

These tests verify the sync_logger module provides structured JSON logging with
automatic context injection for sync operations (team_id, repo_id, task_id) and
timing instrumentation for performance tracking.
"""

import json
import logging
from unittest.mock import patch

from django.test import TestCase


class TestSyncContext(TestCase):
    """Tests for SyncContext class and sync_context() context manager."""

    def test_sync_context_injects_team_id(self):
        """Test that context manager sets team_id available in logs."""
        from apps.utils.sync_logger import get_sync_logger, sync_context

        with patch("logging.Logger.info") as mock_info:
            logger = get_sync_logger("test")

            with sync_context(team_id="team-123"):
                logger.info("Test message")

            mock_info.assert_called_once()
            call_args = mock_info.call_args
            # The log output should include team_id in the extra fields or message
            # Check that team_id was passed to the logger
            self.assertIn("team_id", str(call_args))

    def test_sync_context_injects_repo_id(self):
        """Test that context manager sets repo_id available in logs."""
        from apps.utils.sync_logger import get_sync_logger, sync_context

        with patch("logging.Logger.info") as mock_info:
            logger = get_sync_logger("test")

            with sync_context(repo_id="repo-456"):
                logger.info("Test message")

            mock_info.assert_called_once()
            call_args = mock_info.call_args
            self.assertIn("repo_id", str(call_args))

    def test_sync_context_injects_task_id(self):
        """Test that context manager sets task_id available in logs."""
        from apps.utils.sync_logger import get_sync_logger, sync_context

        with patch("logging.Logger.info") as mock_info:
            logger = get_sync_logger("test")

            with sync_context(task_id="celery-task-789"):
                logger.info("Test message")

            mock_info.assert_called_once()
            call_args = mock_info.call_args
            self.assertIn("task_id", str(call_args))

    def test_sync_context_nested_overrides(self):
        """Test that nested contexts properly override values."""
        from apps.utils.sync_logger import SyncContext, sync_context

        with sync_context(team_id="team-outer", repo_id="repo-outer"):
            outer_team = SyncContext.get_team_id()
            outer_repo = SyncContext.get_repo_id()

            with sync_context(team_id="team-inner"):
                inner_team = SyncContext.get_team_id()
                inner_repo = SyncContext.get_repo_id()

            # After inner context exits, should restore outer values
            restored_team = SyncContext.get_team_id()
            restored_repo = SyncContext.get_repo_id()

        self.assertEqual(outer_team, "team-outer")
        self.assertEqual(outer_repo, "repo-outer")
        self.assertEqual(inner_team, "team-inner")
        # repo_id should be inherited from outer context
        self.assertEqual(inner_repo, "repo-outer")
        self.assertEqual(restored_team, "team-outer")
        self.assertEqual(restored_repo, "repo-outer")


class TestTimedOperation(TestCase):
    """Tests for timed_operation() context manager."""

    def test_timed_operation_logs_duration_ms(self):
        """Test that duration is logged in milliseconds when block exits."""
        from apps.utils.sync_logger import get_sync_logger, timed_operation

        with patch("logging.Logger.info") as mock_info:
            logger = get_sync_logger("test")

            with timed_operation(logger, "fetch_prs"):
                pass  # Simulate work

            mock_info.assert_called()
            # Find the call that includes duration_ms
            call_found = False
            for call in mock_info.call_args_list:
                call_str = str(call)
                if "duration_ms" in call_str:
                    call_found = True
                    break

            self.assertTrue(call_found, "Expected duration_ms in log output")

    def test_timed_operation_logs_extra_fields(self):
        """Test that extra kwargs are included in log output."""
        from apps.utils.sync_logger import get_sync_logger, timed_operation

        with patch("logging.Logger.info") as mock_info:
            logger = get_sync_logger("test")

            with timed_operation(logger, "sync_repos", repo_count=5, org_name="acme"):
                pass

            mock_info.assert_called()
            # Check that extra fields were passed
            call_str = str(mock_info.call_args_list)
            self.assertIn("repo_count", call_str)
            self.assertIn("org_name", call_str)

    def test_timed_operation_logs_on_exception(self):
        """Test that duration is logged even if exception is raised."""
        from apps.utils.sync_logger import get_sync_logger, timed_operation

        with patch("logging.Logger.info") as mock_info:
            logger = get_sync_logger("test")

            with self.assertRaises(ValueError), timed_operation(logger, "failing_operation"):
                raise ValueError("Test error")

            # Should still have logged the duration
            mock_info.assert_called()
            call_str = str(mock_info.call_args_list)
            self.assertIn("duration_ms", call_str)


class TestGetSyncLogger(TestCase):
    """Tests for get_sync_logger() function."""

    def test_get_sync_logger_returns_logger_with_context(self):
        """Test that logger includes context in output."""
        from apps.utils.sync_logger import get_sync_logger, sync_context

        # Capture actual log output
        log_output = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                log_output.append(self.format(record))

        logger = get_sync_logger("test.context")
        handler = CaptureHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            with sync_context(team_id="test-team", repo_id="test-repo", task_id="test-task"):
                logger.info("Test log message")

            # Should have captured at least one log entry
            self.assertTrue(len(log_output) > 0, "Expected at least one log entry")

            # The output should be JSON format with context fields
            log_entry = log_output[0]
            try:
                parsed = json.loads(log_entry)
                self.assertEqual(parsed.get("team_id"), "test-team")
                self.assertEqual(parsed.get("repo_id"), "test-repo")
                self.assertEqual(parsed.get("task_id"), "test-task")
            except json.JSONDecodeError:
                # If not JSON, check that context is in the string
                self.assertIn("test-team", log_entry)
                self.assertIn("test-repo", log_entry)
                self.assertIn("test-task", log_entry)
        finally:
            logger.removeHandler(handler)

    def test_get_sync_logger_returns_logger_instance(self):
        """Test that get_sync_logger returns a logging.Logger instance."""
        from apps.utils.sync_logger import get_sync_logger

        logger = get_sync_logger("test.module")

        self.assertIsInstance(logger, logging.Logger)

    def test_get_sync_logger_same_name_returns_same_logger(self):
        """Test that calling with same name returns the same logger."""
        from apps.utils.sync_logger import get_sync_logger

        logger1 = get_sync_logger("test.same")
        logger2 = get_sync_logger("test.same")

        self.assertIs(logger1, logger2)
