"""Tests for GitHub rate limit helper service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_rate_limit import (
    check_rate_limit,
    should_pause_for_rate_limit,
    wait_for_rate_limit_reset,
)


class TestCheckRateLimit(TestCase):
    """Tests for checking GitHub API rate limit status."""

    def _setup_github_mock(self, mock_github_class, remaining=4500, limit=5000, reset_time=None):
        """Helper to set up GitHub API mock with rate limit data.

        Args:
            mock_github_class: The mocked Github class
            remaining: Number of remaining API calls (default: 4500)
            limit: Total API call limit (default: 5000)
            reset_time: DateTime when rate limit resets (default: 2025-12-21 15:30 UTC)

        Returns:
            The mocked Github instance
        """
        if reset_time is None:
            reset_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=UTC)

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_rate_limit = MagicMock()
        mock_core = MagicMock()
        mock_core.remaining = remaining
        mock_core.limit = limit
        mock_core.reset = reset_time
        mock_rate_limit.core = mock_core
        mock_github.get_rate_limit.return_value = mock_rate_limit

        return mock_github

    @patch("apps.integrations.services.github_rate_limit.Github")
    def test_check_rate_limit_returns_correct_structure(self, mock_github_class):
        """Test that check_rate_limit returns dict with required keys."""
        # Arrange
        access_token = "gho_test_token_123"
        self._setup_github_mock(mock_github_class)

        # Act
        result = check_rate_limit(access_token)

        # Assert
        self.assertIn("remaining", result)
        self.assertIn("limit", result)
        self.assertIn("reset_at", result)

    @patch("apps.integrations.services.github_rate_limit.Github")
    def test_check_rate_limit_extracts_remaining_from_github_api(self, mock_github_class):
        """Test that check_rate_limit correctly extracts remaining value."""
        # Arrange
        access_token = "gho_test_token_123"
        self._setup_github_mock(mock_github_class, remaining=3200)

        # Act
        result = check_rate_limit(access_token)

        # Assert
        self.assertEqual(result["remaining"], 3200)

    @patch("apps.integrations.services.github_rate_limit.Github")
    def test_check_rate_limit_extracts_limit_from_github_api(self, mock_github_class):
        """Test that check_rate_limit correctly extracts limit value."""
        # Arrange
        access_token = "gho_test_token_123"
        self._setup_github_mock(mock_github_class, limit=5000)

        # Act
        result = check_rate_limit(access_token)

        # Assert
        self.assertEqual(result["limit"], 5000)

    @patch("apps.integrations.services.github_rate_limit.Github")
    def test_check_rate_limit_extracts_reset_at_from_github_api(self, mock_github_class):
        """Test that check_rate_limit correctly extracts reset_at datetime."""
        # Arrange
        access_token = "gho_test_token_123"
        reset_time = datetime(2025, 12, 21, 16, 0, 0, tzinfo=UTC)
        self._setup_github_mock(mock_github_class, reset_time=reset_time)

        # Act
        result = check_rate_limit(access_token)

        # Assert
        self.assertEqual(result["reset_at"], reset_time)


class TestShouldPauseForRateLimit(TestCase):
    """Tests for determining if rate limit pause is needed."""

    def test_should_pause_returns_true_when_remaining_below_threshold(self):
        """Test that should_pause_for_rate_limit returns True when remaining < threshold."""
        # Arrange
        remaining = 50
        threshold = 100

        # Act
        result = should_pause_for_rate_limit(remaining, threshold)

        # Assert
        self.assertTrue(result)

    def test_should_pause_returns_false_when_remaining_at_threshold(self):
        """Test that should_pause_for_rate_limit returns False when remaining == threshold."""
        # Arrange
        remaining = 100
        threshold = 100

        # Act
        result = should_pause_for_rate_limit(remaining, threshold)

        # Assert
        self.assertFalse(result)

    def test_should_pause_returns_false_when_remaining_above_threshold(self):
        """Test that should_pause_for_rate_limit returns False when remaining > threshold."""
        # Arrange
        remaining = 150
        threshold = 100

        # Act
        result = should_pause_for_rate_limit(remaining, threshold)

        # Assert
        self.assertFalse(result)

    def test_should_pause_uses_default_threshold_of_100(self):
        """Test that should_pause_for_rate_limit uses default threshold of 100."""
        # Arrange - 99 is below the default threshold of 100
        remaining_below = 99

        # Act
        result_below = should_pause_for_rate_limit(remaining_below)

        # Assert
        self.assertTrue(result_below)

        # Arrange - 100 equals the default threshold
        remaining_at = 100

        # Act
        result_at = should_pause_for_rate_limit(remaining_at)

        # Assert
        self.assertFalse(result_at)


class TestWaitForRateLimitReset(TestCase):
    """Tests for waiting until rate limit resets."""

    @patch("apps.integrations.services.github_rate_limit.time")
    def test_wait_for_rate_limit_reset_waits_correct_duration(self, mock_time):
        """Test that wait_for_rate_limit_reset calculates and waits correct duration."""
        # Arrange
        current_time = datetime(2025, 12, 21, 15, 0, 0, tzinfo=UTC)
        reset_time = datetime(2025, 12, 21, 15, 5, 0, tzinfo=UTC)  # 5 minutes in future

        mock_time.time.return_value = current_time.timestamp()

        # Act
        wait_for_rate_limit_reset(reset_time)

        # Assert - should sleep for 301 seconds (5 minutes + 1 second)
        expected_sleep_duration = 301
        mock_time.sleep.assert_called_once_with(expected_sleep_duration)

    @patch("apps.integrations.services.github_rate_limit.time")
    def test_wait_for_rate_limit_reset_does_not_wait_if_reset_in_past(self, mock_time):
        """Test that wait_for_rate_limit_reset doesn't wait if reset_at is in the past."""
        # Arrange
        current_time = datetime(2025, 12, 21, 15, 10, 0, tzinfo=UTC)
        reset_time = datetime(2025, 12, 21, 15, 0, 0, tzinfo=UTC)  # 10 minutes in past

        mock_time.time.return_value = current_time.timestamp()

        # Act
        wait_for_rate_limit_reset(reset_time)

        # Assert - should not call sleep since reset is in the past
        mock_time.sleep.assert_not_called()

    @patch("apps.integrations.services.github_rate_limit.time")
    def test_wait_for_rate_limit_reset_adds_one_second_buffer(self, mock_time):
        """Test that wait_for_rate_limit_reset adds 1 second buffer to wait time."""
        # Arrange
        current_time = datetime(2025, 12, 21, 15, 0, 0, tzinfo=UTC)
        reset_time = datetime(2025, 12, 21, 15, 0, 10, tzinfo=UTC)  # 10 seconds in future

        mock_time.time.return_value = current_time.timestamp()

        # Act
        wait_for_rate_limit_reset(reset_time)

        # Assert - should sleep for 11 seconds (10 seconds + 1 second buffer)
        expected_sleep_duration = 11
        mock_time.sleep.assert_called_once_with(expected_sleep_duration)
