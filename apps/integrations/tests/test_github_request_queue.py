"""Tests for GitHub request queue service with serial execution enforcement."""

import threading
import time
from unittest.mock import MagicMock

from django.test import TestCase
from github import GithubException

from apps.integrations.services.github_request_queue import GitHubRequestQueue


class TestGitHubRequestQueueSerialExecution(TestCase):
    """Tests that GitHubRequestQueue enforces serial execution of requests."""

    def test_request_queue_enforces_serial_execution(self):
        """Test that multiple requests execute one at a time, not concurrently."""
        # Arrange
        queue = GitHubRequestQueue()
        execution_times = []
        lock = threading.Lock()

        def slow_request():
            """Simulates a slow API request that takes 100ms."""
            start = time.time()
            time.sleep(0.1)  # Simulate API latency
            end = time.time()
            with lock:
                execution_times.append((start, end))
            return {"status": "success"}

        # Act - fire off 3 requests in parallel threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=lambda: queue.request(slow_request))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert - verify requests executed serially (no overlap)
        # Sort by start time
        execution_times.sort(key=lambda x: x[0])

        # Check that each request started after the previous one ended
        for i in range(len(execution_times) - 1):
            previous_end = execution_times[i][1]
            next_start = execution_times[i + 1][0]
            self.assertGreaterEqual(
                next_start,
                previous_end,
                "Requests overlapped - serial execution not enforced",
            )

    def test_request_returns_callable_result(self):
        """Test that request() returns the result from the callable."""
        # Arrange
        queue = GitHubRequestQueue()
        expected_result = {"data": "test_value", "count": 42}

        def mock_request():
            return expected_result

        # Act
        result = queue.request(mock_request)

        # Assert
        self.assertEqual(result, expected_result)

    def test_request_allows_arguments_to_callable(self):
        """Test that request() can pass arguments to the callable."""
        # Arrange
        queue = GitHubRequestQueue()

        def request_with_args(arg1, arg2, kwarg1=None):
            return {"arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

        # Act
        result = queue.request(
            request_with_args,
            "value1",
            "value2",
            kwarg1="keyword_value",
        )

        # Assert
        self.assertEqual(result["arg1"], "value1")
        self.assertEqual(result["arg2"], "value2")
        self.assertEqual(result["kwarg1"], "keyword_value")


class TestGitHubRequestQueueRateLimitTracking(TestCase):
    """Tests for tracking GitHub API rate limit headers."""

    def test_request_tracks_rate_limit_headers(self):
        """Test that rate limit info from response headers is stored."""
        # Arrange
        queue = GitHubRequestQueue()

        # Create a mock response object with rate limit headers
        mock_response = MagicMock()
        mock_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Reset": "1735000000",
        }

        def mock_github_request():
            return mock_response

        # Act
        queue.request(mock_github_request)

        # Assert - check that rate limit info was stored
        rate_limit_info = queue.get_rate_limit_info()
        self.assertIsNotNone(rate_limit_info)
        self.assertEqual(rate_limit_info["remaining"], 4999)
        self.assertEqual(rate_limit_info["limit"], 5000)
        self.assertEqual(rate_limit_info["reset"], 1735000000)

    def test_request_handles_missing_rate_limit_headers(self):
        """Test that request() handles responses without rate limit headers."""
        # Arrange
        queue = GitHubRequestQueue()

        # Create a mock response without rate limit headers
        mock_response = MagicMock()
        mock_response.headers = {}

        def mock_github_request():
            return mock_response

        # Act
        queue.request(mock_github_request)

        # Assert - should not crash, rate limit info should be None or default
        rate_limit_info = queue.get_rate_limit_info()
        # Should either be None or have None/default values
        if rate_limit_info is not None:
            self.assertIsNone(rate_limit_info.get("remaining"))

    def test_get_rate_limit_info_returns_none_before_first_request(self):
        """Test that get_rate_limit_info() returns None before any requests."""
        # Arrange
        queue = GitHubRequestQueue()

        # Act
        rate_limit_info = queue.get_rate_limit_info()

        # Assert
        self.assertIsNone(rate_limit_info)


class TestGitHubRequestQueueResponseData(TestCase):
    """Tests for returning response data from GitHub API requests."""

    def test_request_returns_response_data(self):
        """Test that request() returns the API response data."""
        # Arrange
        queue = GitHubRequestQueue()
        expected_data = {
            "id": 12345,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "private": False,
        }

        def mock_api_call():
            return expected_data

        # Act
        result = queue.request(mock_api_call)

        # Assert
        self.assertEqual(result, expected_data)

    def test_request_preserves_response_structure(self):
        """Test that request() preserves the exact structure of API responses."""
        # Arrange
        queue = GitHubRequestQueue()
        complex_response = {
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": [
                            {"number": 1, "title": "PR 1"},
                            {"number": 2, "title": "PR 2"},
                        ],
                        "pageInfo": {
                            "hasNextPage": True,
                            "endCursor": "cursor123",
                        },
                    }
                }
            }
        }

        def mock_graphql_request():
            return complex_response

        # Act
        result = queue.request(mock_graphql_request)

        # Assert
        self.assertEqual(result, complex_response)
        self.assertEqual(result["data"]["repository"]["pullRequests"]["nodes"][0]["number"], 1)

    def test_request_handles_none_response(self):
        """Test that request() can handle callables that return None."""
        # Arrange
        queue = GitHubRequestQueue()

        def request_returning_none():
            return None

        # Act
        result = queue.request(request_returning_none)

        # Assert
        self.assertIsNone(result)


class TestGitHubRequestQueueRetryAfter(TestCase):
    """Tests for retry-after header handling in GitHub request queue."""

    def test_request_parses_retry_after_seconds(self):
        """Test that retry-after header is parsed and stored in rate limit info."""
        # Arrange
        queue = GitHubRequestQueue()

        # Create a mock response with retry-after header
        mock_response = MagicMock()
        mock_response.headers = {
            "retry-after": "60",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Reset": "1735000000",
        }

        def mock_github_request():
            return mock_response

        # Act
        queue.request(mock_github_request)

        # Assert - retry_after should be stored in rate limit info
        rate_limit_info = queue.get_rate_limit_info()
        self.assertIsNotNone(rate_limit_info)
        self.assertEqual(rate_limit_info["retry_after"], 60)

    def test_request_handles_retry_after_with_github_exception(self):
        """Test that retry-after is captured when GithubException is raised with 403."""
        # Arrange
        queue = GitHubRequestQueue()

        # Create a GithubException with retry-after header
        headers = {
            "retry-after": "120",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Reset": "1735000000",
        }

        def mock_github_request():
            raise GithubException(
                status=403,
                data={"message": "API rate limit exceeded"},
                headers=headers,
            )

        # Act & Assert - exception should be raised
        with self.assertRaises(GithubException):
            queue.request(mock_github_request)

        # Assert - retry_after should still be captured before re-raising
        rate_limit_info = queue.get_rate_limit_info()
        self.assertIsNotNone(rate_limit_info)
        self.assertEqual(rate_limit_info["retry_after"], 120)

    def test_request_handles_retry_after_with_429_status(self):
        """Test that retry-after is captured when GithubException is raised with 429."""
        # Arrange
        queue = GitHubRequestQueue()

        # Create a GithubException with retry-after header
        headers = {
            "retry-after": "90",
        }

        def mock_github_request():
            raise GithubException(
                status=429,
                data={"message": "Too many requests"},
                headers=headers,
            )

        # Act & Assert - exception should be raised
        with self.assertRaises(GithubException):
            queue.request(mock_github_request)

        # Assert - retry_after should still be captured
        rate_limit_info = queue.get_rate_limit_info()
        self.assertIsNotNone(rate_limit_info)
        self.assertEqual(rate_limit_info["retry_after"], 90)

    def test_get_retry_after_returns_seconds_to_wait(self):
        """Test that get_retry_after() method returns seconds to wait or 0."""
        # Arrange
        queue = GitHubRequestQueue()

        # Assert - before any requests, should return 0
        self.assertEqual(queue.get_retry_after(), 0)

        # Act - make a request with retry-after
        mock_response = MagicMock()
        mock_response.headers = {
            "retry-after": "30",
            "X-RateLimit-Remaining": "0",
        }

        def mock_github_request():
            return mock_response

        queue.request(mock_github_request)

        # Assert - should return the retry-after value
        self.assertEqual(queue.get_retry_after(), 30)

    def test_get_retry_after_returns_zero_when_no_retry_after(self):
        """Test that get_retry_after() returns 0 when no retry-after header present."""
        # Arrange
        queue = GitHubRequestQueue()

        # Create a mock response without retry-after
        mock_response = MagicMock()
        mock_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Limit": "5000",
        }

        def mock_github_request():
            return mock_response

        # Act
        queue.request(mock_github_request)

        # Assert - should return 0
        self.assertEqual(queue.get_retry_after(), 0)
