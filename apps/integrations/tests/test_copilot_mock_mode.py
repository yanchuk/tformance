"""
Tests for Copilot mock mode settings toggle.

These tests verify that when COPILOT_USE_MOCK_DATA is enabled,
the fetch_copilot_metrics function returns mock data instead of
making real API calls.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.integrations.services.copilot_metrics import fetch_copilot_metrics


class TestCopilotMockMode(TestCase):
    """Tests for Copilot mock mode toggle."""

    def test_mock_mode_disabled_by_default(self):
        """Test that mock mode is disabled by default (makes real API call)."""
        # This test just verifies the default behavior - without mocking the request,
        # it would try to make a real API call (which would fail without a real token)
        # So we patch the actual API call to verify it gets called
        with patch("apps.integrations.services.copilot_metrics._make_github_api_request") as mock_request:
            mock_request.return_value = []

            fetch_copilot_metrics("fake-token", "test-org")

            # Real API should be called when mock mode is disabled
            mock_request.assert_called_once()

    @override_settings(COPILOT_USE_MOCK_DATA=True, COPILOT_MOCK_SEED=42)
    def test_mock_mode_enabled_returns_mock_data(self):
        """Test that enabling mock mode returns mock data without API call."""
        with patch("apps.integrations.services.copilot_metrics._make_github_api_request") as mock_request:
            # Arrange
            since = (date.today() - timedelta(days=7)).isoformat()
            until = date.today().isoformat()

            # Act
            result = fetch_copilot_metrics("fake-token", "test-org", since=since, until=until)

            # Assert - Should NOT call real API
            mock_request.assert_not_called()

            # Should return mock data with expected structure
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)

            # Verify data structure matches GitHub API format
            first_day = result[0]
            self.assertIn("date", first_day)
            self.assertIn("total_active_users", first_day)
            self.assertIn("copilot_ide_code_completions", first_day)

    @override_settings(COPILOT_USE_MOCK_DATA=True, COPILOT_MOCK_SEED=42)
    def test_mock_seed_produces_deterministic_output(self):
        """Test that same seed produces identical mock data."""
        since = (date.today() - timedelta(days=7)).isoformat()
        until = date.today().isoformat()

        # Run twice with same settings
        result1 = fetch_copilot_metrics("fake-token", "test-org", since=since, until=until)
        result2 = fetch_copilot_metrics("fake-token", "test-org", since=since, until=until)

        # Should produce identical data
        self.assertEqual(len(result1), len(result2))
        for day1, day2 in zip(result1, result2, strict=False):
            self.assertEqual(day1["date"], day2["date"])
            self.assertEqual(
                day1["copilot_ide_code_completions"]["total_completions"],
                day2["copilot_ide_code_completions"]["total_completions"],
            )

    @override_settings(COPILOT_USE_MOCK_DATA=True, COPILOT_MOCK_SEED=42, COPILOT_MOCK_SCENARIO="high_adoption")
    def test_mock_scenario_parameter_used(self):
        """Test that COPILOT_MOCK_SCENARIO setting affects generated data."""
        since = (date.today() - timedelta(days=7)).isoformat()
        until = date.today().isoformat()

        result = fetch_copilot_metrics("fake-token", "test-org", since=since, until=until)

        # High adoption scenario should have higher acceptance rates
        self.assertGreater(len(result), 0)

        # Calculate average acceptance rate
        total_completions = sum(day["copilot_ide_code_completions"]["total_completions"] for day in result)
        total_acceptances = sum(day["copilot_ide_code_completions"]["total_acceptances"] for day in result)

        if total_completions > 0:
            avg_rate = total_acceptances / total_completions
            # High adoption should have acceptance rate >= 0.40
            self.assertGreaterEqual(avg_rate, 0.40)

    @override_settings(COPILOT_USE_MOCK_DATA=True, COPILOT_MOCK_SEED=999)
    def test_different_seed_produces_different_output(self):
        """Test that different seeds produce different data."""
        since = (date.today() - timedelta(days=7)).isoformat()
        until = date.today().isoformat()

        # Get data with seed 999 (from settings)
        result_999 = fetch_copilot_metrics("fake-token", "test-org", since=since, until=until)

        # Override with different seed
        with override_settings(COPILOT_USE_MOCK_DATA=True, COPILOT_MOCK_SEED=123):
            result_123 = fetch_copilot_metrics("fake-token", "test-org", since=since, until=until)

        # Total completions should differ
        total_999 = sum(day["copilot_ide_code_completions"]["total_completions"] for day in result_999)
        total_123 = sum(day["copilot_ide_code_completions"]["total_completions"] for day in result_123)

        self.assertNotEqual(total_999, total_123)
