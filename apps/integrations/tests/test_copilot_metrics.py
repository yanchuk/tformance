"""Tests for Copilot metrics service."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.services.copilot_metrics import (
    CopilotMetricsError,
    check_copilot_availability,
    fetch_copilot_metrics,
    map_copilot_to_ai_usage,
    parse_metrics_response,
)
from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.metrics.models import AIUsageDaily


class TestCopilotMetricsError(TestCase):
    """Tests for CopilotMetricsError exception."""

    def test_copilot_metrics_error_can_be_raised(self):
        """Test that CopilotMetricsError can be raised and caught."""
        with self.assertRaises(CopilotMetricsError):
            raise CopilotMetricsError("Test error")


class TestCheckCopilotAvailability(TestCase):
    """Tests for checking if organization has Copilot metrics available."""

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_check_copilot_availability_returns_true_when_available(self, mock_get):
        """Test that check_copilot_availability returns True when org has Copilot metrics."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2025-12-17",
                "total_active_users": 12,
                "copilot_ide_code_completions": {
                    "total_engaged_users": 8,
                },
            }
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token_123"
        org_slug = "test-org"

        # Act
        result = check_copilot_availability(access_token, org_slug)

        # Assert
        self.assertTrue(result)
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        self.assertIn("headers", call_kwargs)
        self.assertEqual(call_kwargs["headers"]["Authorization"], f"Bearer {access_token}")
        self.assertEqual(call_kwargs["headers"]["Accept"], "application/vnd.github+json")

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_check_copilot_availability_returns_false_when_forbidden(self, mock_get):
        """Test that check_copilot_availability returns False when org lacks Copilot access (403)."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "This organization does not have a Copilot Business or Enterprise subscription.",
            "documentation_url": "https://docs.github.com/rest/copilot/copilot-usage",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token_456"
        org_slug = "org-without-copilot"

        # Act
        result = check_copilot_availability(access_token, org_slug)

        # Assert
        self.assertFalse(result)

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_check_copilot_availability_uses_correct_endpoint(self, mock_get):
        """Test that check_copilot_availability calls the correct GitHub API endpoint."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_token"
        org_slug = "my-org"

        # Act
        check_copilot_availability(access_token, org_slug)

        # Assert
        expected_url = "https://api.github.com/orgs/my-org/copilot/metrics"
        mock_get.assert_called_once()
        actual_url = mock_get.call_args[0][0]
        self.assertEqual(actual_url, expected_url)


class TestFetchCopilotMetrics(TestCase):
    """Tests for fetching Copilot metrics from GitHub API."""

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_metrics_success(self, mock_get):
        """Test that fetch_copilot_metrics returns metrics data on success."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2025-12-17",
                "total_active_users": 15,
                "total_engaged_users": 12,
                "copilot_ide_code_completions": {
                    "total_engaged_users": 10,
                    "total_completions": 5432,
                    "total_acceptances": 3210,
                    "total_lines_suggested": 8765,
                    "total_lines_accepted": 4321,
                },
                "copilot_ide_chat": {
                    "total_engaged_users": 8,
                    "total_chats": 234,
                },
                "copilot_dotcom_chat": {
                    "total_engaged_users": 5,
                    "total_chats": 123,
                },
                "copilot_dotcom_pull_requests": {
                    "total_engaged_users": 3,
                    "total_prs": 45,
                },
            },
            {
                "date": "2025-12-16",
                "total_active_users": 14,
                "total_engaged_users": 11,
                "copilot_ide_code_completions": {
                    "total_engaged_users": 9,
                    "total_completions": 4567,
                    "total_acceptances": 2890,
                    "total_lines_suggested": 7654,
                    "total_lines_accepted": 3890,
                },
                "copilot_ide_chat": {
                    "total_engaged_users": 7,
                    "total_chats": 198,
                },
                "copilot_dotcom_chat": {
                    "total_engaged_users": 4,
                    "total_chats": 98,
                },
                "copilot_dotcom_pull_requests": {
                    "total_engaged_users": 2,
                    "total_prs": 32,
                },
            },
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token_789"
        org_slug = "test-org"

        # Act
        result = fetch_copilot_metrics(access_token, org_slug)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["date"], "2025-12-17")
        self.assertEqual(result[0]["total_active_users"], 15)
        self.assertEqual(result[0]["copilot_ide_code_completions"]["total_completions"], 5432)

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_metrics_handles_403_error(self, mock_get):
        """Test that fetch_copilot_metrics raises CopilotMetricsError on 403 response."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "This organization does not have a Copilot Business subscription.",
        }
        mock_get.return_value = mock_response

        access_token = "gho_token"
        org_slug = "no-copilot-org"

        # Act & Assert
        with self.assertRaises(CopilotMetricsError) as context:
            fetch_copilot_metrics(access_token, org_slug)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_metrics_with_date_range(self, mock_get):
        """Test that fetch_copilot_metrics passes since and until parameters correctly."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_token"
        org_slug = "test-org"
        since = "2025-12-01"
        until = "2025-12-15"

        # Act
        fetch_copilot_metrics(access_token, org_slug, since=since, until=until)

        # Assert
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        self.assertIn("params", call_kwargs)
        self.assertEqual(call_kwargs["params"]["since"], since)
        self.assertEqual(call_kwargs["params"]["until"], until)

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_metrics_with_partial_date_range(self, mock_get):
        """Test that fetch_copilot_metrics handles only 'since' parameter."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_token"
        org_slug = "test-org"
        since = "2025-12-10"

        # Act
        fetch_copilot_metrics(access_token, org_slug, since=since)

        # Assert
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        self.assertIn("params", call_kwargs)
        self.assertEqual(call_kwargs["params"]["since"], since)
        self.assertNotIn("until", call_kwargs["params"])

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_metrics_handles_network_error(self, mock_get):
        """Test that fetch_copilot_metrics raises CopilotMetricsError on network error."""
        # Arrange
        mock_get.side_effect = Exception("Network timeout")

        access_token = "gho_token"
        org_slug = "test-org"

        # Act & Assert
        with self.assertRaises(CopilotMetricsError):
            fetch_copilot_metrics(access_token, org_slug)

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_metrics_sends_correct_headers(self, mock_get):
        """Test that fetch_copilot_metrics sends correct authorization and accept headers."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_test_token_special"
        org_slug = "test-org"

        # Act
        fetch_copilot_metrics(access_token, org_slug)

        # Assert
        call_kwargs = mock_get.call_args[1]
        self.assertIn("headers", call_kwargs)
        self.assertEqual(call_kwargs["headers"]["Authorization"], f"Bearer {access_token}")
        self.assertEqual(call_kwargs["headers"]["Accept"], "application/vnd.github+json")


class TestParseMetricsResponse(TestCase):
    """Tests for parsing and normalizing Copilot metrics API response."""

    def test_parse_metrics_response_extracts_correct_fields(self):
        """Test that parse_metrics_response extracts and normalizes all required fields."""
        # Arrange
        raw_data = [
            {
                "date": "2025-12-17",
                "total_active_users": 15,
                "total_engaged_users": 12,
                "copilot_ide_code_completions": {
                    "total_engaged_users": 10,
                    "total_completions": 5432,
                    "total_acceptances": 3210,
                    "total_lines_suggested": 8765,
                    "total_lines_accepted": 4321,
                },
                "copilot_ide_chat": {
                    "total_engaged_users": 8,
                    "total_chats": 234,
                },
                "copilot_dotcom_chat": {
                    "total_engaged_users": 5,
                    "total_chats": 123,
                },
                "copilot_dotcom_pull_requests": {
                    "total_engaged_users": 3,
                    "total_prs": 45,
                },
            }
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        metric = result[0]
        self.assertEqual(metric["date"], "2025-12-17")
        self.assertEqual(metric["total_active_users"], 15)
        self.assertEqual(metric["total_engaged_users"], 12)
        self.assertEqual(metric["code_completions_total"], 5432)
        self.assertEqual(metric["code_completions_accepted"], 3210)
        self.assertEqual(metric["lines_suggested"], 8765)
        self.assertEqual(metric["lines_accepted"], 4321)
        self.assertEqual(metric["chat_total"], 234)
        self.assertEqual(metric["dotcom_chat_total"], 123)
        self.assertEqual(metric["dotcom_prs_total"], 45)

    def test_parse_metrics_response_handles_multiple_days(self):
        """Test that parse_metrics_response correctly processes multiple daily entries."""
        # Arrange
        raw_data = [
            {
                "date": "2025-12-17",
                "total_active_users": 15,
                "total_engaged_users": 12,
                "copilot_ide_code_completions": {
                    "total_engaged_users": 10,
                    "total_completions": 5432,
                    "total_acceptances": 3210,
                    "total_lines_suggested": 8765,
                    "total_lines_accepted": 4321,
                },
                "copilot_ide_chat": {
                    "total_engaged_users": 8,
                    "total_chats": 234,
                },
                "copilot_dotcom_chat": {
                    "total_engaged_users": 5,
                    "total_chats": 123,
                },
                "copilot_dotcom_pull_requests": {
                    "total_engaged_users": 3,
                    "total_prs": 45,
                },
            },
            {
                "date": "2025-12-16",
                "total_active_users": 14,
                "total_engaged_users": 11,
                "copilot_ide_code_completions": {
                    "total_engaged_users": 9,
                    "total_completions": 4567,
                    "total_acceptances": 2890,
                    "total_lines_suggested": 7654,
                    "total_lines_accepted": 3890,
                },
                "copilot_ide_chat": {
                    "total_engaged_users": 7,
                    "total_chats": 198,
                },
                "copilot_dotcom_chat": {
                    "total_engaged_users": 4,
                    "total_chats": 98,
                },
                "copilot_dotcom_pull_requests": {
                    "total_engaged_users": 2,
                    "total_prs": 32,
                },
            },
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["date"], "2025-12-17")
        self.assertEqual(result[1]["date"], "2025-12-16")
        self.assertEqual(result[0]["code_completions_total"], 5432)
        self.assertEqual(result[1]["code_completions_total"], 4567)

    def test_parse_metrics_response_handles_missing_optional_fields(self):
        """Test that parse_metrics_response handles missing optional fields gracefully."""
        # Arrange - Some fields might be missing in real API responses
        raw_data = [
            {
                "date": "2025-12-17",
                "total_active_users": 15,
                "total_engaged_users": 12,
                "copilot_ide_code_completions": {
                    "total_engaged_users": 10,
                    "total_completions": 5432,
                    "total_acceptances": 3210,
                    "total_lines_suggested": 8765,
                    "total_lines_accepted": 4321,
                },
            }
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        metric = result[0]
        self.assertEqual(metric["date"], "2025-12-17")
        self.assertEqual(metric["code_completions_total"], 5432)
        # Optional fields should default to 0 or None
        self.assertIn("chat_total", metric)
        self.assertIn("dotcom_chat_total", metric)

    def test_parse_metrics_response_handles_empty_list(self):
        """Test that parse_metrics_response handles empty data gracefully."""
        # Arrange
        raw_data = []

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)


class TestCopilotDataStorage(TestCase):
    """Tests for storing Copilot metrics in AIUsageDaily model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_copilot_metrics_can_be_stored_in_ai_usage_daily(self):
        """Test that AIUsageDaily record can be created with source='copilot' and parsed metrics data."""
        # Arrange
        test_date = timezone.now().date()
        suggestions_shown = 5432
        suggestions_accepted = 3210
        expected_acceptance_rate = Decimal("59.09")  # (3210 / 5432) * 100

        # Act
        ai_usage = AIUsageDaily.objects.create(
            team=self.team,
            member=self.member,
            date=test_date,
            source="copilot",
            suggestions_shown=suggestions_shown,
            suggestions_accepted=suggestions_accepted,
            acceptance_rate=expected_acceptance_rate,
        )

        # Assert
        self.assertIsNotNone(ai_usage.id)
        self.assertEqual(ai_usage.source, "copilot")
        self.assertEqual(ai_usage.member, self.member)
        self.assertEqual(ai_usage.date, test_date)
        self.assertEqual(ai_usage.suggestions_shown, suggestions_shown)
        self.assertEqual(ai_usage.suggestions_accepted, suggestions_accepted)
        self.assertEqual(ai_usage.acceptance_rate, expected_acceptance_rate)

        # Verify it can be retrieved
        retrieved = AIUsageDaily.objects.get(
            team=self.team,
            member=self.member,
            date=test_date,
            source="copilot",
        )
        self.assertEqual(retrieved.suggestions_shown, suggestions_shown)
        self.assertEqual(retrieved.suggestions_accepted, suggestions_accepted)

    def test_copilot_metrics_mapping_from_parsed_response(self):
        """Test that map_copilot_to_ai_usage transforms parsed API response to AIUsageDaily-compatible dict."""
        # Arrange - Parsed data from parse_metrics_response
        parsed_day_data = {
            "date": "2025-12-17",
            "total_active_users": 15,
            "total_engaged_users": 12,
            "code_completions_total": 5432,
            "code_completions_accepted": 3210,
            "lines_suggested": 8765,
            "lines_accepted": 4321,
            "chat_total": 234,
            "dotcom_chat_total": 123,
            "dotcom_prs_total": 45,
        }

        # Act
        result = map_copilot_to_ai_usage(parsed_day_data)

        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(result["date"], "2025-12-17")
        self.assertEqual(result["source"], "copilot")

        # Test field mapping: code_completions_total -> suggestions_shown
        self.assertEqual(result["suggestions_shown"], 5432)

        # Test field mapping: code_completions_accepted -> suggestions_accepted
        self.assertEqual(result["suggestions_accepted"], 3210)

        # Test calculated acceptance_rate
        self.assertIn("acceptance_rate", result)
        expected_rate = Decimal("59.09")  # (3210 / 5432) * 100, rounded to 2 decimals
        self.assertEqual(result["acceptance_rate"], expected_rate)

    def test_map_copilot_to_ai_usage_handles_zero_completions(self):
        """Test that map_copilot_to_ai_usage handles zero completions gracefully."""
        # Arrange
        parsed_day_data = {
            "date": "2025-12-17",
            "total_active_users": 5,
            "total_engaged_users": 0,
            "code_completions_total": 0,
            "code_completions_accepted": 0,
            "lines_suggested": 0,
            "lines_accepted": 0,
            "chat_total": 0,
            "dotcom_chat_total": 0,
            "dotcom_prs_total": 0,
        }

        # Act
        result = map_copilot_to_ai_usage(parsed_day_data)

        # Assert
        self.assertEqual(result["suggestions_shown"], 0)
        self.assertEqual(result["suggestions_accepted"], 0)
        # Acceptance rate should be None or 0 when there are no completions
        self.assertIn("acceptance_rate", result)
        # Acceptable to be None or 0 when no suggestions shown
        self.assertIn(result["acceptance_rate"], [None, Decimal("0"), Decimal("0.00")])

    def test_map_copilot_to_ai_usage_calculates_acceptance_rate_correctly(self):
        """Test that map_copilot_to_ai_usage calculates acceptance rate with correct precision."""
        # Arrange
        parsed_day_data = {
            "date": "2025-12-18",
            "total_active_users": 10,
            "total_engaged_users": 8,
            "code_completions_total": 1000,
            "code_completions_accepted": 333,
            "lines_suggested": 5000,
            "lines_accepted": 1665,
            "chat_total": 50,
            "dotcom_chat_total": 20,
            "dotcom_prs_total": 10,
        }

        # Act
        result = map_copilot_to_ai_usage(parsed_day_data)

        # Assert
        # (333 / 1000) * 100 = 33.30%
        expected_rate = Decimal("33.30")
        self.assertEqual(result["acceptance_rate"], expected_rate)
