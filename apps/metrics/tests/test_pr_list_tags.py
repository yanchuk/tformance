"""Tests for PR list template tags."""

from django.test import TestCase

from apps.metrics.templatetags.pr_list_tags import (
    pr_size_bucket,
    tech_abbrev,
    tech_badge_class,
    tech_display_name,
)


class TestTechAbbrevFilter(TestCase):
    """Tests for tech_abbrev template filter."""

    def test_frontend_abbreviation(self):
        """Test frontend category abbreviation."""
        self.assertEqual(tech_abbrev("frontend"), "FE")

    def test_backend_abbreviation(self):
        """Test backend category abbreviation."""
        self.assertEqual(tech_abbrev("backend"), "BE")

    def test_javascript_abbreviation(self):
        """Test javascript category abbreviation."""
        self.assertEqual(tech_abbrev("javascript"), "JS")

    def test_test_abbreviation(self):
        """Test test category abbreviation."""
        self.assertEqual(tech_abbrev("test"), "TS")

    def test_docs_abbreviation(self):
        """Test docs category abbreviation."""
        self.assertEqual(tech_abbrev("docs"), "DC")

    def test_config_abbreviation(self):
        """Test config category abbreviation."""
        self.assertEqual(tech_abbrev("config"), "CF")

    def test_other_abbreviation(self):
        """Test other category abbreviation."""
        self.assertEqual(tech_abbrev("other"), "OT")

    def test_unknown_category_uses_first_two_chars(self):
        """Test unknown category falls back to first two uppercase chars."""
        self.assertEqual(tech_abbrev("unknown"), "UN")

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        self.assertEqual(tech_abbrev(""), "")

    def test_none_returns_empty(self):
        """Test None value returns empty."""
        self.assertEqual(tech_abbrev(None), "")


class TestTechBadgeClassFilter(TestCase):
    """Tests for tech_badge_class template filter."""

    def test_frontend_badge_class(self):
        """Test frontend badge class."""
        self.assertEqual(tech_badge_class("frontend"), "badge-info")

    def test_backend_badge_class(self):
        """Test backend badge class."""
        self.assertEqual(tech_badge_class("backend"), "badge-success")

    def test_javascript_badge_class(self):
        """Test javascript badge class."""
        self.assertEqual(tech_badge_class("javascript"), "badge-warning")

    def test_test_badge_class(self):
        """Test test badge class."""
        self.assertEqual(tech_badge_class("test"), "badge-secondary")

    def test_unknown_category_uses_ghost(self):
        """Test unknown category falls back to badge-ghost."""
        self.assertEqual(tech_badge_class("unknown"), "badge-ghost")

    def test_empty_string_returns_ghost(self):
        """Test empty string returns badge-ghost."""
        self.assertEqual(tech_badge_class(""), "badge-ghost")

    def test_none_returns_ghost(self):
        """Test None value returns badge-ghost."""
        self.assertEqual(tech_badge_class(None), "badge-ghost")


class TestTechDisplayNameFilter(TestCase):
    """Tests for tech_display_name template filter."""

    def test_frontend_display_name(self):
        """Test frontend display name."""
        self.assertEqual(tech_display_name("frontend"), "Frontend")

    def test_backend_display_name(self):
        """Test backend display name."""
        self.assertEqual(tech_display_name("backend"), "Backend")

    def test_javascript_display_name(self):
        """Test javascript display name."""
        self.assertEqual(tech_display_name("javascript"), "JS/TypeScript")

    def test_test_display_name(self):
        """Test test display name."""
        self.assertEqual(tech_display_name("test"), "Test")

    def test_docs_display_name(self):
        """Test docs display name."""
        self.assertEqual(tech_display_name("docs"), "Documentation")

    def test_config_display_name(self):
        """Test config display name."""
        self.assertEqual(tech_display_name("config"), "Configuration")

    def test_unknown_category_uses_title_case(self):
        """Test unknown category falls back to title case."""
        self.assertEqual(tech_display_name("unknown"), "Unknown")

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        self.assertEqual(tech_display_name(""), "")

    def test_none_returns_empty(self):
        """Test None value returns empty."""
        self.assertEqual(tech_display_name(None), "")


class TestPrSizeBucketFilter(TestCase):
    """Tests for pr_size_bucket template filter."""

    # Edge cases: minimum value for each bucket
    def test_xs_bucket_minimum_zero_lines(self):
        """Test XS bucket with 0 total lines."""
        self.assertEqual(pr_size_bucket(0, 0), "XS")

    def test_s_bucket_minimum_11_lines(self):
        """Test S bucket with 11 total lines (minimum)."""
        self.assertEqual(pr_size_bucket(6, 5), "S")

    def test_m_bucket_minimum_51_lines(self):
        """Test M bucket with 51 total lines (minimum)."""
        self.assertEqual(pr_size_bucket(30, 21), "M")

    def test_l_bucket_minimum_201_lines(self):
        """Test L bucket with 201 total lines (minimum)."""
        self.assertEqual(pr_size_bucket(100, 101), "L")

    def test_xl_bucket_minimum_501_lines(self):
        """Test XL bucket with 501 total lines (minimum)."""
        self.assertEqual(pr_size_bucket(300, 201), "XL")

    # Edge cases: maximum value for each bucket
    def test_xs_bucket_maximum_10_lines(self):
        """Test XS bucket with 10 total lines (maximum)."""
        self.assertEqual(pr_size_bucket(5, 5), "XS")

    def test_s_bucket_maximum_50_lines(self):
        """Test S bucket with 50 total lines (maximum)."""
        self.assertEqual(pr_size_bucket(25, 25), "S")

    def test_m_bucket_maximum_200_lines(self):
        """Test M bucket with 200 total lines (maximum)."""
        self.assertEqual(pr_size_bucket(100, 100), "M")

    def test_l_bucket_maximum_500_lines(self):
        """Test L bucket with 500 total lines (maximum)."""
        self.assertEqual(pr_size_bucket(250, 250), "L")

    # Typical values in each bucket
    def test_xs_bucket_typical_5_lines(self):
        """Test XS bucket with typical 5 total lines."""
        self.assertEqual(pr_size_bucket(3, 2), "XS")

    def test_s_bucket_typical_30_lines(self):
        """Test S bucket with typical 30 total lines."""
        self.assertEqual(pr_size_bucket(20, 10), "S")

    def test_m_bucket_typical_125_lines(self):
        """Test M bucket with typical 125 total lines."""
        self.assertEqual(pr_size_bucket(75, 50), "M")

    def test_l_bucket_typical_350_lines(self):
        """Test L bucket with typical 350 total lines."""
        self.assertEqual(pr_size_bucket(200, 150), "L")

    def test_xl_bucket_typical_1000_lines(self):
        """Test XL bucket with typical 1000 total lines."""
        self.assertEqual(pr_size_bucket(600, 400), "XL")

    # Special cases
    def test_zero_additions_and_deletions(self):
        """Test zero additions and deletions returns XS."""
        self.assertEqual(pr_size_bucket(0, 0), "XS")

    def test_only_additions_no_deletions(self):
        """Test only additions with no deletions."""
        self.assertEqual(pr_size_bucket(100, 0), "M")

    def test_only_deletions_no_additions(self):
        """Test only deletions with no additions."""
        self.assertEqual(pr_size_bucket(0, 100), "M")

    # Invalid inputs
    def test_none_additions_returns_empty(self):
        """Test None additions returns empty string."""
        self.assertEqual(pr_size_bucket(None, 10), "")

    def test_none_deletions_returns_empty(self):
        """Test None deletions returns empty string."""
        self.assertEqual(pr_size_bucket(10, None), "")

    def test_both_none_returns_empty(self):
        """Test both None values return empty string."""
        self.assertEqual(pr_size_bucket(None, None), "")

    def test_negative_additions_returns_empty(self):
        """Test negative additions returns empty string."""
        self.assertEqual(pr_size_bucket(-5, 10), "")

    def test_negative_deletions_returns_empty(self):
        """Test negative deletions returns empty string."""
        self.assertEqual(pr_size_bucket(10, -5), "")
