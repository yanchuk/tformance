"""Tests for Chart Formatting Utilities.

Utilities for converting Django ORM query results and Python data structures
into formats compatible with Chart.js and other visualization libraries.
"""

from datetime import date

from django.test import TestCase

from apps.metrics.services import chart_formatters


class TestFormatTimeSeries(TestCase):
    """Tests for format_time_series function."""

    def test_format_time_series_converts_date_objects_to_iso_strings(self):
        """Test that format_time_series converts date objects to ISO strings."""
        data = [
            {"week": date(2024, 1, 1), "value": 5},
            {"week": date(2024, 1, 8), "value": 10},
            {"week": date(2024, 1, 15), "value": 8},
        ]

        result = chart_formatters.format_time_series(data)

        self.assertEqual(result[0]["date"], "2024-01-01")
        self.assertEqual(result[1]["date"], "2024-01-08")
        self.assertEqual(result[2]["date"], "2024-01-15")

    def test_format_time_series_renames_value_to_count(self):
        """Test that format_time_series renames 'value' key to 'count'."""
        data = [
            {"week": date(2024, 1, 1), "value": 5},
            {"week": date(2024, 1, 8), "value": 10},
        ]

        result = chart_formatters.format_time_series(data)

        self.assertEqual(result[0]["count"], 5)
        self.assertEqual(result[1]["count"], 10)
        self.assertNotIn("value", result[0])
        self.assertNotIn("value", result[1])

    def test_format_time_series_removes_original_week_key(self):
        """Test that format_time_series removes the original 'week' key."""
        data = [{"week": date(2024, 1, 1), "value": 5}]

        result = chart_formatters.format_time_series(data)

        self.assertNotIn("week", result[0])
        self.assertIn("date", result[0])

    def test_format_time_series_handles_empty_list(self):
        """Test that format_time_series handles empty list."""
        data = []

        result = chart_formatters.format_time_series(data)

        self.assertEqual(result, [])

    def test_format_time_series_with_custom_date_key(self):
        """Test that format_time_series accepts custom date_key parameter."""
        data = [
            {"day": date(2024, 1, 1), "value": 5},
            {"day": date(2024, 1, 2), "value": 8},
        ]

        result = chart_formatters.format_time_series(data, date_key="day")

        self.assertEqual(result[0]["date"], "2024-01-01")
        self.assertEqual(result[1]["date"], "2024-01-02")
        self.assertNotIn("day", result[0])

    def test_format_time_series_with_custom_value_key(self):
        """Test that format_time_series accepts custom value_key parameter."""
        data = [
            {"week": date(2024, 1, 1), "total": 15},
            {"week": date(2024, 1, 8), "total": 20},
        ]

        result = chart_formatters.format_time_series(data, value_key="total")

        self.assertEqual(result[0]["count"], 15)
        self.assertEqual(result[1]["count"], 20)
        self.assertNotIn("total", result[0])

    def test_format_time_series_with_both_custom_keys(self):
        """Test that format_time_series accepts both custom key parameters."""
        data = [
            {"month": date(2024, 1, 1), "metric": 100},
            {"month": date(2024, 2, 1), "metric": 150},
        ]

        result = chart_formatters.format_time_series(data, date_key="month", value_key="metric")

        self.assertEqual(result[0]["date"], "2024-01-01")
        self.assertEqual(result[0]["count"], 100)
        self.assertEqual(result[1]["date"], "2024-02-01")
        self.assertEqual(result[1]["count"], 150)

    def test_format_time_series_preserves_order(self):
        """Test that format_time_series preserves the original order."""
        data = [
            {"week": date(2024, 1, 15), "value": 8},
            {"week": date(2024, 1, 1), "value": 5},
            {"week": date(2024, 1, 8), "value": 10},
        ]

        result = chart_formatters.format_time_series(data)

        self.assertEqual(result[0]["date"], "2024-01-15")
        self.assertEqual(result[1]["date"], "2024-01-01")
        self.assertEqual(result[2]["date"], "2024-01-08")


class TestFormatCategorical(TestCase):
    """Tests for format_categorical function."""

    def test_format_categorical_converts_tuples_to_lists(self):
        """Test that format_categorical converts list of tuples to list of lists."""
        data = [
            ("Alice", 10),
            ("Bob", 8),
            ("Charlie", 15),
        ]

        result = chart_formatters.format_categorical(data)

        self.assertEqual(result, [["Alice", 10], ["Bob", 8], ["Charlie", 15]])

    def test_format_categorical_returns_lists_not_tuples(self):
        """Test that format_categorical returns lists, not tuples."""
        data = [("Alice", 10), ("Bob", 8)]

        result = chart_formatters.format_categorical(data)

        self.assertIsInstance(result[0], list)
        self.assertIsInstance(result[1], list)
        self.assertNotIsInstance(result[0], tuple)

    def test_format_categorical_handles_empty_list(self):
        """Test that format_categorical handles empty list."""
        data = []

        result = chart_formatters.format_categorical(data)

        self.assertEqual(result, [])

    def test_format_categorical_preserves_order(self):
        """Test that format_categorical preserves the original order."""
        data = [("Charlie", 15), ("Alice", 10), ("Bob", 8)]

        result = chart_formatters.format_categorical(data)

        self.assertEqual(result[0][0], "Charlie")
        self.assertEqual(result[1][0], "Alice")
        self.assertEqual(result[2][0], "Bob")

    def test_format_categorical_handles_various_value_types(self):
        """Test that format_categorical handles different value types."""
        data = [
            ("String", 10),
            ("Float", 15.5),
            ("Zero", 0),
        ]

        result = chart_formatters.format_categorical(data)

        self.assertEqual(result[0][1], 10)
        self.assertEqual(result[1][1], 15.5)
        self.assertEqual(result[2][1], 0)

    def test_format_categorical_handles_single_item(self):
        """Test that format_categorical handles single item list."""
        data = [("Only One", 42)]

        result = chart_formatters.format_categorical(data)

        self.assertEqual(result, [["Only One", 42]])


class TestCalculatePercentageChange(TestCase):
    """Tests for calculate_percentage_change function."""

    def test_calculate_percentage_change_positive_increase(self):
        """Test that calculate_percentage_change calculates positive change correctly."""
        result = chart_formatters.calculate_percentage_change(current=120, previous=100)

        self.assertEqual(result, 20.0)

    def test_calculate_percentage_change_negative_decrease(self):
        """Test that calculate_percentage_change calculates negative change correctly."""
        result = chart_formatters.calculate_percentage_change(current=80, previous=100)

        self.assertEqual(result, -20.0)

    def test_calculate_percentage_change_no_change(self):
        """Test that calculate_percentage_change returns 0.0 when values are equal."""
        result = chart_formatters.calculate_percentage_change(current=100, previous=100)

        self.assertEqual(result, 0.0)

    def test_calculate_percentage_change_previous_zero(self):
        """Test that calculate_percentage_change handles division by zero."""
        result = chart_formatters.calculate_percentage_change(current=50, previous=0)

        self.assertEqual(result, 0.0)

    def test_calculate_percentage_change_both_zero(self):
        """Test that calculate_percentage_change handles both values being zero."""
        result = chart_formatters.calculate_percentage_change(current=0, previous=0)

        self.assertEqual(result, 0.0)

    def test_calculate_percentage_change_current_none(self):
        """Test that calculate_percentage_change handles None current value."""
        result = chart_formatters.calculate_percentage_change(current=None, previous=100)

        self.assertEqual(result, 0.0)

    def test_calculate_percentage_change_previous_none(self):
        """Test that calculate_percentage_change handles None previous value."""
        result = chart_formatters.calculate_percentage_change(current=100, previous=None)

        self.assertEqual(result, 0.0)

    def test_calculate_percentage_change_both_none(self):
        """Test that calculate_percentage_change handles both values being None."""
        result = chart_formatters.calculate_percentage_change(current=None, previous=None)

        self.assertEqual(result, 0.0)

    def test_calculate_percentage_change_from_zero_to_positive(self):
        """Test that calculate_percentage_change handles increase from zero."""
        result = chart_formatters.calculate_percentage_change(current=100, previous=0)

        self.assertEqual(result, 0.0)

    def test_calculate_percentage_change_large_percentage(self):
        """Test that calculate_percentage_change handles large percentage changes."""
        result = chart_formatters.calculate_percentage_change(current=500, previous=100)

        self.assertEqual(result, 400.0)

    def test_calculate_percentage_change_small_decimal_values(self):
        """Test that calculate_percentage_change handles decimal values."""
        result = chart_formatters.calculate_percentage_change(current=1.5, previous=1.0)

        self.assertEqual(result, 50.0)

    def test_calculate_percentage_change_returns_float(self):
        """Test that calculate_percentage_change always returns a float."""
        result = chart_formatters.calculate_percentage_change(current=120, previous=100)

        self.assertIsInstance(result, float)
