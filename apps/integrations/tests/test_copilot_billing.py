"""Tests for Copilot Billing API service functions.

Tests verify the billing data fetch, parsing, and sync to CopilotSeatSnapshot.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.integrations.services.copilot_metrics import (
    CopilotMetricsError,
    fetch_copilot_billing,
    parse_billing_response,
    sync_copilot_seats_to_snapshot,
)
from apps.metrics.factories import TeamFactory
from apps.metrics.models import CopilotSeatSnapshot


class TestFetchCopilotBilling(TestCase):
    """Tests for fetch_copilot_billing function."""

    @patch("apps.integrations.services.copilot_metrics._make_github_api_request")
    def test_fetch_copilot_billing_success(self, mock_request):
        """Test successful billing data fetch."""
        mock_request.return_value = {
            "seat_breakdown": {
                "total": 25,
                "active_this_cycle": 18,
                "inactive_this_cycle": 4,
                "added_this_cycle": 2,
                "pending_cancellation": 1,
            },
            "seat_management_setting": "assign_all",
            "public_code_suggestions": "allow",
            "ide_chat": "enabled",
            "platform_chat": "enabled",
            "cli": "enabled",
            "plan_type": "business",
        }

        result = fetch_copilot_billing("test_token", "test-org")

        self.assertEqual(result["seat_breakdown"]["total"], 25)
        self.assertEqual(result["seat_breakdown"]["active_this_cycle"], 18)
        mock_request.assert_called_once()

    @patch("apps.integrations.services.copilot_metrics._make_github_api_request")
    def test_fetch_copilot_billing_uses_correct_url(self, mock_request):
        """Test that fetch uses the correct billing API URL."""
        mock_request.return_value = {"seat_breakdown": {}}

        fetch_copilot_billing("test_token", "test-org")

        call_args = mock_request.call_args
        url = call_args[0][0]
        self.assertIn("/orgs/test-org/copilot/billing", url)

    @patch("apps.integrations.services.copilot_metrics._make_github_api_request")
    def test_fetch_copilot_billing_handles_403(self, mock_request):
        """Test that 403 errors are properly raised."""
        mock_request.side_effect = CopilotMetricsError("Billing API unavailable (403)")

        with self.assertRaises(CopilotMetricsError) as ctx:
            fetch_copilot_billing("test_token", "test-org")

        self.assertIn("403", str(ctx.exception))


class TestParseBillingResponse(TestCase):
    """Tests for parse_billing_response function."""

    def test_parse_billing_extracts_seat_counts(self):
        """Test that billing response is parsed correctly."""
        billing_data = {
            "seat_breakdown": {
                "total": 25,
                "active_this_cycle": 18,
                "inactive_this_cycle": 4,
                "added_this_cycle": 2,
                "pending_cancellation": 1,
            },
        }

        result = parse_billing_response(billing_data)

        self.assertEqual(result["total_seats"], 25)
        self.assertEqual(result["active_this_cycle"], 18)
        self.assertEqual(result["inactive_this_cycle"], 4)
        self.assertEqual(result["pending_cancellation"], 1)

    def test_parse_billing_defaults_missing_fields(self):
        """Test that missing fields default to 0."""
        billing_data = {
            "seat_breakdown": {
                "total": 10,
            },
        }

        result = parse_billing_response(billing_data)

        self.assertEqual(result["total_seats"], 10)
        self.assertEqual(result["active_this_cycle"], 0)
        self.assertEqual(result["inactive_this_cycle"], 0)
        self.assertEqual(result["pending_cancellation"], 0)

    def test_parse_billing_handles_empty_breakdown(self):
        """Test handling of empty seat_breakdown."""
        billing_data = {}

        result = parse_billing_response(billing_data)

        self.assertEqual(result["total_seats"], 0)
        self.assertEqual(result["active_this_cycle"], 0)


class TestSyncCopilotSeatsToSnapshot(TestCase):
    """Tests for sync_copilot_seats_to_snapshot function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_creates_new_snapshot(self):
        """Test that a new snapshot is created."""
        parsed_billing = {
            "total_seats": 25,
            "active_this_cycle": 18,
            "inactive_this_cycle": 4,
            "pending_cancellation": 1,
        }

        snapshot = sync_copilot_seats_to_snapshot(self.team, parsed_billing)

        self.assertEqual(snapshot.total_seats, 25)
        self.assertEqual(snapshot.active_this_cycle, 18)
        self.assertEqual(snapshot.inactive_this_cycle, 4)
        self.assertEqual(snapshot.pending_cancellation, 1)
        self.assertEqual(snapshot.date, date.today())

    def test_updates_existing_snapshot(self):
        """Test that existing snapshot for same date is updated."""
        # Create existing snapshot
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date.today(),
            total_seats=20,
            active_this_cycle=15,
            inactive_this_cycle=5,
        )

        # Sync with new data
        parsed_billing = {
            "total_seats": 25,
            "active_this_cycle": 18,
            "inactive_this_cycle": 4,
            "pending_cancellation": 1,
        }

        snapshot = sync_copilot_seats_to_snapshot(self.team, parsed_billing)

        # Should update existing
        self.assertEqual(CopilotSeatSnapshot.objects.filter(team=self.team).count(), 1)
        self.assertEqual(snapshot.total_seats, 25)
        self.assertEqual(snapshot.active_this_cycle, 18)

    def test_snapshot_has_correct_team(self):
        """Test that snapshot is associated with correct team."""
        parsed_billing = {
            "total_seats": 10,
            "active_this_cycle": 8,
            "inactive_this_cycle": 2,
            "pending_cancellation": 0,
        }

        snapshot = sync_copilot_seats_to_snapshot(self.team, parsed_billing)

        self.assertEqual(snapshot.team, self.team)

    def test_calculated_properties_work_after_sync(self):
        """Test that calculated properties work on synced snapshot."""
        parsed_billing = {
            "total_seats": 25,
            "active_this_cycle": 20,
            "inactive_this_cycle": 5,
            "pending_cancellation": 0,
        }

        snapshot = sync_copilot_seats_to_snapshot(self.team, parsed_billing)

        # Verify calculated properties
        self.assertEqual(snapshot.utilization_rate, Decimal("80.00"))
        self.assertEqual(snapshot.monthly_cost, Decimal("475.00"))
        self.assertEqual(snapshot.wasted_spend, Decimal("95.00"))
        self.assertEqual(snapshot.cost_per_active_user, Decimal("23.75"))
