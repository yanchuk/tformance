"""Tests for number_filters template tags."""

from django.test import TestCase

from apps.web.templatetags.number_filters import format_compact


class FormatCompactFilterTests(TestCase):
    """Test the format_compact template filter."""

    def test_format_millions(self):
        """Large numbers should display with M suffix."""
        # These are the actual values from Copilot metrics that were overflowing
        self.assertEqual(format_compact(1816130), "1.8M")
        self.assertEqual(format_compact(1500000), "1.5M")
        self.assertEqual(format_compact(2345678), "2.3M")

    def test_format_thousands(self):
        """Medium numbers should display with K suffix."""
        self.assertEqual(format_compact(906710), "906.7K")
        self.assertEqual(format_compact(15810), "15.8K")
        self.assertEqual(format_compact(1234), "1.2K")
        self.assertEqual(format_compact(1000), "1.0K")

    def test_format_small_numbers(self):
        """Small numbers should display as-is without suffix."""
        self.assertEqual(format_compact(999), "999")
        self.assertEqual(format_compact(500), "500")
        self.assertEqual(format_compact(0), "0")

    def test_handles_floats(self):
        """Should handle float input correctly."""
        self.assertEqual(format_compact(1500000.0), "1.5M")
        self.assertEqual(format_compact(15810.5), "15.8K")

    def test_handles_invalid_input(self):
        """Should return original value for invalid input."""
        self.assertEqual(format_compact(None), None)
        self.assertEqual(format_compact("not a number"), "not a number")
        self.assertEqual(format_compact(""), "")
