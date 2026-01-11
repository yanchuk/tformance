"""Tests for Copilot metrics service."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.services.copilot_metrics import (
    CopilotMetricsError,
    check_copilot_availability,
    fetch_copilot_metrics,
    fetch_copilot_seats,
    get_seat_utilization,
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

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_metrics_handles_invalid_json_response(self, mock_get):
        """Test that fetch_copilot_metrics handles malformed JSON response gracefully."""
        import json

        # Arrange - Mock a response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://api.github.com/orgs/test-org/copilot/usage"
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "not json {{{", 0)
        mock_get.return_value = mock_response

        access_token = "gho_token"
        org_slug = "test-org"

        # Act & Assert - Should raise CopilotMetricsError, not JSONDecodeError
        with self.assertRaises(CopilotMetricsError) as context:
            fetch_copilot_metrics(access_token, org_slug)

        # The error message should be user-friendly
        self.assertIn("Invalid", str(context.exception))

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_metrics_handles_invalid_json_in_403_response(self, mock_get):
        """Test that fetch_copilot_metrics handles malformed JSON in 403 error response."""
        import json

        # Arrange - Mock a 403 response with invalid JSON body
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.url = "https://api.github.com/orgs/test-org/copilot/usage"
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        mock_get.return_value = mock_response

        access_token = "gho_token"
        org_slug = "test-org"

        # Act & Assert - Should raise CopilotMetricsError with generic 403 message
        with self.assertRaises(CopilotMetricsError) as context:
            fetch_copilot_metrics(access_token, org_slug)

        # Should contain 403 reference since that's the status code
        self.assertIn("403", str(context.exception))


class TestParseMetricsResponse(TestCase):
    """Tests for parsing and normalizing Copilot metrics API response."""

    def _make_official_fixture(
        self,
        *,
        date: str = "2025-12-17",
        total_active_users: int = 15,
        total_engaged_users: int = 12,
        suggestions: int = 5432,
        acceptances: int = 3210,
        lines_suggested: int = 8765,
        lines_accepted: int = 4321,
        chat_total: int = 234,
        dotcom_chat_total: int = 123,
        dotcom_prs_total: int = 45,
    ) -> dict:
        """Create test fixture in official GitHub Copilot Metrics API format.

        Official schema has editors > models > languages (nested metrics).
        """
        return {
            "date": date,
            "total_active_users": total_active_users,
            "total_engaged_users": total_engaged_users,
            "copilot_ide_code_completions": {
                "total_engaged_users": 10,
                "editors": [
                    {
                        "name": "vscode",
                        "total_engaged_users": 10,
                        "models": [
                            {
                                "name": "default",
                                "is_custom_model": False,
                                "custom_model_training_date": None,
                                "total_engaged_users": 10,
                                "languages": [
                                    {
                                        "name": "python",
                                        "total_engaged_users": 5,
                                        "total_code_suggestions": suggestions,
                                        "total_code_acceptances": acceptances,
                                        "total_code_lines_suggested": lines_suggested,
                                        "total_code_lines_accepted": lines_accepted,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            "copilot_ide_chat": {
                "total_engaged_users": 8,
                "total_chats": chat_total,
            },
            "copilot_dotcom_chat": {
                "total_engaged_users": 5,
                "total_chats": dotcom_chat_total,
            },
            "copilot_dotcom_pull_requests": {
                "total_engaged_users": 3,
                "total_prs": dotcom_prs_total,
            },
        }

    def test_parse_metrics_response_extracts_correct_fields(self):
        """Test that parse_metrics_response extracts and normalizes all required fields."""
        # Arrange - Official API format with nested editors > models > languages
        raw_data = [self._make_official_fixture()]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        metric = result[0]
        self.assertEqual(metric["date"], "2025-12-17")
        self.assertEqual(metric["total_active_users"], 15)
        self.assertEqual(metric["total_engaged_users"], 12)
        # Totals are aggregated from nested editors > models > languages
        self.assertEqual(metric["code_completions_total"], 5432)
        self.assertEqual(metric["code_completions_accepted"], 3210)
        self.assertEqual(metric["lines_suggested"], 8765)
        self.assertEqual(metric["lines_accepted"], 4321)
        self.assertEqual(metric["chat_total"], 234)
        self.assertEqual(metric["dotcom_chat_total"], 123)
        self.assertEqual(metric["dotcom_prs_total"], 45)

    def test_parse_metrics_response_handles_multiple_days(self):
        """Test that parse_metrics_response correctly processes multiple daily entries."""
        # Arrange - Using official schema with nested editors > models > languages
        raw_data = [
            self._make_official_fixture(
                date="2025-12-17",
                total_active_users=15,
                total_engaged_users=12,
                suggestions=5432,
                acceptances=3210,
            ),
            self._make_official_fixture(
                date="2025-12-16",
                total_active_users=14,
                total_engaged_users=11,
                suggestions=4567,
                acceptances=2890,
            ),
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
        # Arrange - Official schema but without chat/dotcom fields
        raw_data = [
            {
                "date": "2025-12-17",
                "total_active_users": 15,
                "total_engaged_users": 12,
                "copilot_ide_code_completions": {
                    "total_engaged_users": 10,
                    "editors": [
                        {
                            "name": "vscode",
                            "total_engaged_users": 10,
                            "models": [
                                {
                                    "name": "default",
                                    "is_custom_model": False,
                                    "custom_model_training_date": None,
                                    "total_engaged_users": 10,
                                    "languages": [
                                        {
                                            "name": "python",
                                            "total_engaged_users": 5,
                                            "total_code_suggestions": 5432,
                                            "total_code_acceptances": 3210,
                                            "total_code_lines_suggested": 8765,
                                            "total_code_lines_accepted": 4321,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
                # No chat fields - optional
            }
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        metric = result[0]
        self.assertEqual(metric["date"], "2025-12-17")
        # Totals aggregated from nested editors > models > languages
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


class TestFetchCopilotSeats(TestCase):
    """Tests for fetching Copilot seat utilization from GitHub API."""

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_seats_success(self, mock_get):
        """Test that fetch_copilot_seats returns seat data on success."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_seats": 10,
            "seats": [
                {
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-12-18T00:00:00Z",
                    "pending_cancellation_date": None,
                    "last_activity_at": "2025-12-17T00:00:00Z",
                    "last_activity_editor": "vscode",
                    "assignee": {
                        "login": "user1",
                        "id": 12345,
                        "type": "User",
                    },
                },
                {
                    "created_at": "2025-01-15T00:00:00Z",
                    "updated_at": "2025-12-18T00:00:00Z",
                    "pending_cancellation_date": None,
                    "last_activity_at": "2025-11-01T00:00:00Z",
                    "last_activity_editor": "vscode",
                    "assignee": {
                        "login": "user2",
                        "id": 67890,
                        "type": "User",
                    },
                },
            ],
            "seat_breakdown": {
                "total": 10,
                "active_this_cycle": 8,
                "inactive_this_cycle": 2,
            },
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token_seats"
        org_slug = "test-org"

        # Act
        result = fetch_copilot_seats(access_token, org_slug)

        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(result["total_seats"], 10)
        self.assertIn("seats", result)
        self.assertEqual(len(result["seats"]), 2)
        self.assertIn("seat_breakdown", result)
        self.assertEqual(result["seat_breakdown"]["active_this_cycle"], 8)
        self.assertEqual(result["seat_breakdown"]["inactive_this_cycle"], 2)

        # Verify correct API endpoint was called
        expected_url = "https://api.github.com/orgs/test-org/copilot/billing/seats"
        mock_get.assert_called_once()
        actual_url = mock_get.call_args[0][0]
        self.assertEqual(actual_url, expected_url)

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_seats_handles_403_error(self, mock_get):
        """Test that fetch_copilot_seats raises CopilotMetricsError on 403 (insufficient permissions)."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "Resource not accessible by integration",
            "documentation_url": "https://docs.github.com/rest/copilot/copilot-user-management",
        }
        mock_get.return_value = mock_response

        access_token = "gho_token_no_permission"
        org_slug = "restricted-org"

        # Act & Assert
        with self.assertRaises(CopilotMetricsError) as context:
            fetch_copilot_seats(access_token, org_slug)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_seats_handles_network_error(self, mock_get):
        """Test that fetch_copilot_seats raises CopilotMetricsError on network error."""
        # Arrange
        mock_get.side_effect = Exception("Connection timeout")

        access_token = "gho_token"
        org_slug = "test-org"

        # Act & Assert
        with self.assertRaises(CopilotMetricsError):
            fetch_copilot_seats(access_token, org_slug)

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_fetch_copilot_seats_sends_correct_headers(self, mock_get):
        """Test that fetch_copilot_seats sends correct authorization and accept headers."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_seats": 5,
            "seats": [],
            "seat_breakdown": {"total": 5, "active_this_cycle": 5, "inactive_this_cycle": 0},
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token_headers"
        org_slug = "test-org"

        # Act
        fetch_copilot_seats(access_token, org_slug)

        # Assert
        call_kwargs = mock_get.call_args[1]
        self.assertIn("headers", call_kwargs)
        self.assertEqual(call_kwargs["headers"]["Authorization"], f"Bearer {access_token}")
        self.assertEqual(call_kwargs["headers"]["Accept"], "application/vnd.github+json")


class TestGetSeatUtilization(TestCase):
    """Tests for calculating Copilot seat utilization metrics."""

    def test_get_seat_utilization_calculates_correct_metrics(self):
        """Test that get_seat_utilization calculates all metrics correctly."""
        # Arrange
        seats_data = {
            "total_seats": 10,
            "seats": [
                {"assignee": {"login": "user1"}},
                {"assignee": {"login": "user2"}},
                {"assignee": {"login": "user3"}},
                {"assignee": {"login": "user4"}},
                {"assignee": {"login": "user5"}},
                {"assignee": {"login": "user6"}},
                {"assignee": {"login": "user7"}},
                {"assignee": {"login": "user8"}},
            ],
            "seat_breakdown": {
                "total": 10,
                "active_this_cycle": 8,
                "inactive_this_cycle": 2,
            },
        }

        # Act
        result = get_seat_utilization(seats_data)

        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(result["total_seats"], 10)
        self.assertEqual(result["active_seats"], 8)
        self.assertEqual(result["inactive_seats"], 2)
        self.assertEqual(result["utilization_rate"], Decimal("80.00"))  # 8/10 * 100
        self.assertEqual(result["monthly_cost"], Decimal("190.00"))  # 10 * $19
        self.assertEqual(result["cost_per_active_user"], Decimal("23.75"))  # $190 / 8

    def test_get_seat_utilization_handles_full_utilization(self):
        """Test that get_seat_utilization handles 100% utilization correctly."""
        # Arrange
        seats_data = {
            "total_seats": 5,
            "seats": [{"assignee": {"login": f"user{i}"}} for i in range(5)],
            "seat_breakdown": {
                "total": 5,
                "active_this_cycle": 5,
                "inactive_this_cycle": 0,
            },
        }

        # Act
        result = get_seat_utilization(seats_data)

        # Assert
        self.assertEqual(result["total_seats"], 5)
        self.assertEqual(result["active_seats"], 5)
        self.assertEqual(result["inactive_seats"], 0)
        self.assertEqual(result["utilization_rate"], Decimal("100.00"))
        self.assertEqual(result["monthly_cost"], Decimal("95.00"))  # 5 * $19
        self.assertEqual(result["cost_per_active_user"], Decimal("19.00"))  # $95 / 5

    def test_get_seat_utilization_handles_zero_active_seats(self):
        """Test that get_seat_utilization handles zero active users gracefully."""
        # Arrange
        seats_data = {
            "total_seats": 3,
            "seats": [
                {"assignee": {"login": "user1"}},
                {"assignee": {"login": "user2"}},
                {"assignee": {"login": "user3"}},
            ],
            "seat_breakdown": {
                "total": 3,
                "active_this_cycle": 0,
                "inactive_this_cycle": 3,
            },
        }

        # Act
        result = get_seat_utilization(seats_data)

        # Assert
        self.assertEqual(result["total_seats"], 3)
        self.assertEqual(result["active_seats"], 0)
        self.assertEqual(result["inactive_seats"], 3)
        self.assertEqual(result["utilization_rate"], Decimal("0.00"))
        self.assertEqual(result["monthly_cost"], Decimal("57.00"))  # 3 * $19
        # cost_per_active_user should be None or 0 when no active users
        self.assertIsNone(result["cost_per_active_user"])

    def test_get_seat_utilization_handles_partial_utilization(self):
        """Test that get_seat_utilization calculates metrics for partial utilization."""
        # Arrange
        seats_data = {
            "total_seats": 20,
            "seats": [{"assignee": {"login": f"user{i}"}} for i in range(20)],
            "seat_breakdown": {
                "total": 20,
                "active_this_cycle": 13,
                "inactive_this_cycle": 7,
            },
        }

        # Act
        result = get_seat_utilization(seats_data)

        # Assert
        self.assertEqual(result["total_seats"], 20)
        self.assertEqual(result["active_seats"], 13)
        self.assertEqual(result["inactive_seats"], 7)
        self.assertEqual(result["utilization_rate"], Decimal("65.00"))  # 13/20 * 100
        self.assertEqual(result["monthly_cost"], Decimal("380.00"))  # 20 * $19
        # $380 / 13 = 29.230769... rounds to 29.23
        self.assertEqual(result["cost_per_active_user"], Decimal("29.23"))

    def test_get_seat_utilization_precision(self):
        """Test that get_seat_utilization maintains correct decimal precision."""
        # Arrange - Edge case with precise division
        seats_data = {
            "total_seats": 3,
            "seats": [{"assignee": {"login": f"user{i}"}} for i in range(3)],
            "seat_breakdown": {
                "total": 3,
                "active_this_cycle": 2,
                "inactive_this_cycle": 1,
            },
        }

        # Act
        result = get_seat_utilization(seats_data)

        # Assert
        # 2/3 * 100 = 66.666... should round to 66.67
        self.assertEqual(result["utilization_rate"], Decimal("66.67"))
        # 3 * $19 = $57
        self.assertEqual(result["monthly_cost"], Decimal("57.00"))
        # $57 / 2 = $28.50
        self.assertEqual(result["cost_per_active_user"], Decimal("28.50"))


class TestCopilotMetrics401Handling(TestCase):
    """Edge case #16: Test that 401 errors raise TokenRevokedError."""

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_api_request_raises_token_revoked_on_401(self, mock_get):
        """Test that 401 response raises TokenRevokedError."""
        from apps.integrations.exceptions import TokenRevokedError
        from apps.integrations.services.copilot_metrics import _make_github_api_request

        # Mock a 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Bad credentials"}
        mock_get.return_value = mock_response

        # Act & Assert
        with self.assertRaises(TokenRevokedError) as context:
            _make_github_api_request(
                url="https://api.github.com/orgs/test/copilot/usage",
                headers={"Authorization": "Bearer invalid_token"},
                error_prefix="Copilot metrics",
            )

        # Verify error message includes reconnect guidance
        error_msg = str(context.exception)
        self.assertIn("revoked", error_msg.lower())
        self.assertIn("reconnect", error_msg.lower())

    @patch("apps.integrations.services.copilot_metrics.requests.get")
    def test_api_request_still_raises_copilot_error_on_403(self, mock_get):
        """Test that 403 response still raises CopilotMetricsError (not TokenRevokedError)."""
        # Mock a 403 response
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Copilot not enabled"}
        mock_get.return_value = mock_response

        # Act & Assert - should raise CopilotMetricsError, not TokenRevokedError
        with self.assertRaises(CopilotMetricsError):
            from apps.integrations.services.copilot_metrics import _make_github_api_request

            _make_github_api_request(
                url="https://api.github.com/orgs/test/copilot/usage",
                headers={"Authorization": "Bearer valid_token"},
                error_prefix="Copilot metrics",
            )
