"""Tests for view utilities.

This test module covers:
- get_date_range_from_request: Basic date range extraction (days param)
- get_extended_date_range: Extended date range with custom start/end, granularity
"""

from datetime import date, timedelta
from unittest.mock import MagicMock

from django.test import TestCase
from django.utils import timezone

from apps.metrics.view_utils import (
    get_date_range_from_request,
    get_extended_date_range,
)


class TestGetDateRangeFromRequest(TestCase):
    """Tests for get_date_range_from_request function."""

    def test_default_30_days(self):
        """Test that default is 30 days when no param provided."""
        request = MagicMock()
        request.GET = {}

        start_date, end_date = get_date_range_from_request(request)

        today = timezone.now().date()
        expected_start = today - timedelta(days=30)
        self.assertEqual(end_date, today)
        self.assertEqual(start_date, expected_start)

    def test_days_7(self):
        """Test days=7 param."""
        request = MagicMock()
        request.GET = {"days": "7"}

        start_date, end_date = get_date_range_from_request(request)

        today = timezone.now().date()
        expected_start = today - timedelta(days=7)
        self.assertEqual(end_date, today)
        self.assertEqual(start_date, expected_start)

    def test_days_90(self):
        """Test days=90 param."""
        request = MagicMock()
        request.GET = {"days": "90"}

        start_date, end_date = get_date_range_from_request(request)

        today = timezone.now().date()
        expected_start = today - timedelta(days=90)
        self.assertEqual(end_date, today)
        self.assertEqual(start_date, expected_start)


class TestGetExtendedDateRange(TestCase):
    """Tests for get_extended_date_range function."""

    def test_default_returns_30_days_weekly(self):
        """Test default returns 30 days with weekly granularity."""
        request = MagicMock()
        request.GET = {}

        result = get_extended_date_range(request)

        today = timezone.now().date()
        expected_start = today - timedelta(days=30)
        self.assertEqual(result["start_date"], expected_start)
        self.assertEqual(result["end_date"], today)
        self.assertEqual(result["granularity"], "weekly")
        self.assertEqual(result["days"], 30)

    def test_days_param_overrides_default(self):
        """Test days param overrides default 30."""
        request = MagicMock()
        request.GET = {"days": "90"}

        result = get_extended_date_range(request)

        today = timezone.now().date()
        expected_start = today - timedelta(days=90)
        self.assertEqual(result["start_date"], expected_start)
        self.assertEqual(result["end_date"], today)
        self.assertEqual(result["days"], 90)

    def test_custom_start_and_end_dates(self):
        """Test custom start and end date params."""
        request = MagicMock()
        request.GET = {"start": "2024-01-01", "end": "2024-12-31"}

        result = get_extended_date_range(request)

        self.assertEqual(result["start_date"], date(2024, 1, 1))
        self.assertEqual(result["end_date"], date(2024, 12, 31))

    def test_custom_dates_override_days(self):
        """Test that custom start/end dates take precedence over days."""
        request = MagicMock()
        request.GET = {"days": "7", "start": "2024-06-01", "end": "2024-06-30"}

        result = get_extended_date_range(request)

        self.assertEqual(result["start_date"], date(2024, 6, 1))
        self.assertEqual(result["end_date"], date(2024, 6, 30))

    def test_granularity_weekly(self):
        """Test granularity=weekly param."""
        request = MagicMock()
        request.GET = {"granularity": "weekly"}

        result = get_extended_date_range(request)

        self.assertEqual(result["granularity"], "weekly")

    def test_granularity_monthly(self):
        """Test granularity=monthly param."""
        request = MagicMock()
        request.GET = {"granularity": "monthly"}

        result = get_extended_date_range(request)

        self.assertEqual(result["granularity"], "monthly")

    def test_granularity_daily(self):
        """Test granularity=daily param."""
        request = MagicMock()
        request.GET = {"granularity": "daily"}

        result = get_extended_date_range(request)

        self.assertEqual(result["granularity"], "daily")

    def test_invalid_granularity_defaults_to_weekly(self):
        """Test that invalid granularity defaults to weekly."""
        request = MagicMock()
        request.GET = {"granularity": "invalid"}

        result = get_extended_date_range(request)

        self.assertEqual(result["granularity"], "weekly")

    def test_preset_this_year(self):
        """Test preset=this_year returns Jan 1 to today."""
        request = MagicMock()
        request.GET = {"preset": "this_year"}

        result = get_extended_date_range(request)

        today = timezone.now().date()
        expected_start = date(today.year, 1, 1)
        self.assertEqual(result["start_date"], expected_start)
        self.assertEqual(result["end_date"], today)

    def test_preset_last_year(self):
        """Test preset=last_year returns full previous year."""
        request = MagicMock()
        request.GET = {"preset": "last_year"}

        result = get_extended_date_range(request)

        today = timezone.now().date()
        last_year = today.year - 1
        self.assertEqual(result["start_date"], date(last_year, 1, 1))
        self.assertEqual(result["end_date"], date(last_year, 12, 31))

    def test_preset_this_quarter(self):
        """Test preset=this_quarter returns start of current quarter to today."""
        request = MagicMock()
        request.GET = {"preset": "this_quarter"}

        result = get_extended_date_range(request)

        today = timezone.now().date()
        quarter = (today.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        expected_start = date(today.year, quarter_start_month, 1)
        self.assertEqual(result["start_date"], expected_start)
        self.assertEqual(result["end_date"], today)

    def test_preset_yoy_returns_comparison_data(self):
        """Test preset=yoy includes comparison dates."""
        request = MagicMock()
        request.GET = {"preset": "yoy"}

        result = get_extended_date_range(request)

        today = timezone.now().date()
        expected_start = date(today.year, 1, 1)
        self.assertEqual(result["start_date"], expected_start)
        self.assertEqual(result["end_date"], today)
        # YoY should include comparison dates
        self.assertIn("compare_start", result)
        self.assertIn("compare_end", result)
        # Comparison should be previous year same period
        self.assertEqual(result["compare_start"], date(today.year - 1, 1, 1))

    def test_invalid_date_format_falls_back_to_days(self):
        """Test that invalid date format falls back to days param."""
        request = MagicMock()
        request.GET = {"start": "invalid-date", "end": "2024-12-31", "days": "30"}

        result = get_extended_date_range(request)

        # Should fall back to days=30
        today = timezone.now().date()
        expected_start = today - timedelta(days=30)
        self.assertEqual(result["start_date"], expected_start)
        self.assertEqual(result["end_date"], today)

    def test_start_after_end_returns_valid_range(self):
        """Test that start > end swaps the dates."""
        request = MagicMock()
        request.GET = {"start": "2024-12-31", "end": "2024-01-01"}

        result = get_extended_date_range(request)

        # Should swap dates
        self.assertEqual(result["start_date"], date(2024, 1, 1))
        self.assertEqual(result["end_date"], date(2024, 12, 31))

    def test_max_range_365_days_enforced(self):
        """Test that ranges over 730 days are clamped."""
        request = MagicMock()
        request.GET = {"start": "2020-01-01", "end": "2024-12-31"}

        result = get_extended_date_range(request)

        # Range should be clamped to 730 days (2 years)
        days_diff = (result["end_date"] - result["start_date"]).days
        self.assertLessEqual(days_diff, 730)

    def test_auto_granularity_for_long_ranges(self):
        """Test that granularity auto-adjusts to monthly for ranges > 90 days."""
        request = MagicMock()
        request.GET = {"start": "2024-01-01", "end": "2024-12-31"}

        result = get_extended_date_range(request)

        # Should auto-adjust to monthly for year-long range
        self.assertEqual(result["granularity"], "monthly")

    def test_auto_granularity_short_range_stays_weekly(self):
        """Test that granularity stays weekly for ranges <= 90 days."""
        request = MagicMock()
        request.GET = {"days": "30"}

        result = get_extended_date_range(request)

        self.assertEqual(result["granularity"], "weekly")
