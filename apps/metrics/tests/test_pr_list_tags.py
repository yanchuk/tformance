"""Tests for PR list template tags."""

from django.test import TestCase

from apps.metrics.templatetags.pr_list_tags import (
    get_item,
    pr_size_bucket,
    repo_name,
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

    # LLM category abbreviations
    def test_devops_abbreviation(self):
        """Test devops LLM category abbreviation."""
        self.assertEqual(tech_abbrev("devops"), "DO")

    def test_mobile_abbreviation(self):
        """Test mobile LLM category abbreviation."""
        self.assertEqual(tech_abbrev("mobile"), "MB")

    def test_data_abbreviation(self):
        """Test data LLM category abbreviation."""
        self.assertEqual(tech_abbrev("data"), "DA")

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

    # LLM category badge classes
    def test_devops_badge_class(self):
        """Test devops LLM category badge class."""
        self.assertEqual(tech_badge_class("devops"), "badge-warning")

    def test_mobile_badge_class(self):
        """Test mobile LLM category badge class."""
        self.assertEqual(tech_badge_class("mobile"), "badge-secondary")

    def test_data_badge_class(self):
        """Test data LLM category badge class."""
        self.assertEqual(tech_badge_class("data"), "badge-primary")

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

    # LLM category display names
    def test_devops_display_name(self):
        """Test devops LLM category display name."""
        self.assertEqual(tech_display_name("devops"), "DevOps")

    def test_mobile_display_name(self):
        """Test mobile LLM category display name."""
        self.assertEqual(tech_display_name("mobile"), "Mobile")

    def test_data_display_name(self):
        """Test data LLM category display name."""
        self.assertEqual(tech_display_name("data"), "Data")

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


class TestRepoNameFilter(TestCase):
    """Tests for repo_name template filter."""

    def test_extracts_repo_from_owner_repo_format(self):
        """Test extracting repo name from 'owner/repo' format."""
        self.assertEqual(repo_name("antiwork/gumroad"), "gumroad")

    def test_extracts_repo_from_different_owner(self):
        """Test extracting repo name from different organization."""
        self.assertEqual(repo_name("facebook/react"), "react")

    def test_handles_repo_with_hyphens(self):
        """Test repo names with hyphens."""
        self.assertEqual(repo_name("vercel/next.js"), "next.js")

    def test_handles_repo_with_dots(self):
        """Test repo names with dots."""
        self.assertEqual(repo_name("org/my-project.v2"), "my-project.v2")

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        self.assertEqual(repo_name(""), "")

    def test_none_returns_empty(self):
        """Test None value returns empty."""
        self.assertEqual(repo_name(None), "")

    def test_no_slash_returns_original(self):
        """Test string without slash returns as-is."""
        self.assertEqual(repo_name("just-repo-name"), "just-repo-name")

    def test_multiple_slashes_returns_last_segment(self):
        """Test multiple slashes returns last segment only."""
        self.assertEqual(repo_name("org/sub/repo"), "repo")


class TestAIConfidenceLevelFilter(TestCase):
    """Tests for ai_confidence_level template filter."""

    def test_high_confidence_above_threshold(self):
        """Test score >= 0.5 returns 'high'."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(0.5), "high")

    def test_high_confidence_at_max(self):
        """Test score of 1.0 returns 'high'."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(1.0), "high")

    def test_medium_confidence_at_lower_bound(self):
        """Test score of 0.2 returns 'medium'."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(0.2), "medium")

    def test_medium_confidence_typical(self):
        """Test score of 0.35 returns 'medium'."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(0.35), "medium")

    def test_medium_confidence_just_below_high(self):
        """Test score of 0.49 returns 'medium'."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(0.49), "medium")

    def test_low_confidence_positive(self):
        """Test score of 0.1 returns 'low'."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(0.1), "low")

    def test_low_confidence_just_below_medium(self):
        """Test score of 0.19 returns 'low'."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(0.19), "low")

    def test_zero_returns_empty(self):
        """Test score of 0.0 returns empty string."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(0.0), "")

    def test_none_returns_empty(self):
        """Test None value returns empty string."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(None), "")

    def test_decimal_type_supported(self):
        """Test Decimal type is handled correctly."""
        from decimal import Decimal

        from apps.metrics.templatetags.pr_list_tags import ai_confidence_level

        self.assertEqual(ai_confidence_level(Decimal("0.5")), "high")
        self.assertEqual(ai_confidence_level(Decimal("0.25")), "medium")
        self.assertEqual(ai_confidence_level(Decimal("0.1")), "low")


class TestAIConfidenceBadgeClassFilter(TestCase):
    """Tests for ai_confidence_badge_class template filter."""

    def test_high_returns_success(self):
        """Test 'high' returns badge-success."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_badge_class

        self.assertEqual(ai_confidence_badge_class("high"), "badge-success")

    def test_medium_returns_warning(self):
        """Test 'medium' returns badge-warning."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_badge_class

        self.assertEqual(ai_confidence_badge_class("medium"), "badge-warning")

    def test_low_returns_ghost(self):
        """Test 'low' returns badge-ghost."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_badge_class

        self.assertEqual(ai_confidence_badge_class("low"), "badge-ghost")

    def test_empty_returns_ghost(self):
        """Test empty string returns badge-ghost."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_badge_class

        self.assertEqual(ai_confidence_badge_class(""), "badge-ghost")

    def test_none_returns_ghost(self):
        """Test None returns badge-ghost."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_badge_class

        self.assertEqual(ai_confidence_badge_class(None), "badge-ghost")

    def test_unknown_returns_ghost(self):
        """Test unknown level returns badge-ghost."""
        from apps.metrics.templatetags.pr_list_tags import ai_confidence_badge_class

        self.assertEqual(ai_confidence_badge_class("unknown"), "badge-ghost")


class TestAISignalsTooltipFilter(TestCase):
    """Tests for ai_signals_tooltip template filter."""

    def test_all_signals_present(self):
        """Test tooltip with all signal sources active."""
        from apps.metrics.templatetags.pr_list_tags import ai_signals_tooltip

        signals = {
            "llm": {"score": 0.4, "is_assisted": True, "tools": ["claude"]},
            "regex": {"score": 0.2, "is_assisted": True, "tools": ["cursor"]},
            "commits": {"score": 0.25, "has_ai": True},
            "reviews": {"score": 0.1, "has_ai": True},
            "files": {"score": 0.05, "has_ai": True},
        }
        tooltip = ai_signals_tooltip(signals)
        self.assertIn("LLM", tooltip)
        self.assertIn("Regex", tooltip)
        self.assertIn("Commits", tooltip)
        self.assertIn("Reviews", tooltip)
        self.assertIn("Files", tooltip)

    def test_partial_signals(self):
        """Test tooltip with only some signals active."""
        from apps.metrics.templatetags.pr_list_tags import ai_signals_tooltip

        signals = {
            "llm": {"score": 0.4, "is_assisted": True, "tools": ["claude"]},
            "regex": {"score": 0.0, "is_assisted": False, "tools": []},
            "commits": {"score": 0.0, "has_ai": False},
            "reviews": {"score": 0.0, "has_ai": False},
            "files": {"score": 0.0, "has_ai": False},
        }
        tooltip = ai_signals_tooltip(signals)
        self.assertIn("LLM", tooltip)
        self.assertNotIn("Regex", tooltip)
        self.assertNotIn("Commits", tooltip)

    def test_empty_signals_returns_no_signals(self):
        """Test empty signals dict returns 'No AI signals'."""
        from apps.metrics.templatetags.pr_list_tags import ai_signals_tooltip

        self.assertEqual(ai_signals_tooltip({}), "No AI signals")

    def test_none_returns_no_signals(self):
        """Test None returns 'No AI signals'."""
        from apps.metrics.templatetags.pr_list_tags import ai_signals_tooltip

        self.assertEqual(ai_signals_tooltip(None), "No AI signals")

    def test_all_zero_scores_returns_no_signals(self):
        """Test all zero scores returns 'No AI signals'."""
        from apps.metrics.templatetags.pr_list_tags import ai_signals_tooltip

        signals = {
            "llm": {"score": 0.0, "is_assisted": False},
            "regex": {"score": 0.0, "is_assisted": False},
            "commits": {"score": 0.0, "has_ai": False},
            "reviews": {"score": 0.0, "has_ai": False},
            "files": {"score": 0.0, "has_ai": False},
        }
        self.assertEqual(ai_signals_tooltip(signals), "No AI signals")

    def test_includes_tools_for_llm(self):
        """Test LLM signal includes tool names."""
        from apps.metrics.templatetags.pr_list_tags import ai_signals_tooltip

        signals = {
            "llm": {"score": 0.4, "is_assisted": True, "tools": ["claude", "cursor"]},
            "regex": {"score": 0.0, "is_assisted": False, "tools": []},
            "commits": {"score": 0.0, "has_ai": False},
            "reviews": {"score": 0.0, "has_ai": False},
            "files": {"score": 0.0, "has_ai": False},
        }
        tooltip = ai_signals_tooltip(signals)
        self.assertIn("claude", tooltip.lower())
        self.assertIn("cursor", tooltip.lower())


class TestGetItemFilter(TestCase):
    """Tests for get_item template filter."""

    def test_get_existing_key(self):
        """Test getting an existing key from dictionary."""
        data = {"feature": {"name": "Feature", "color": "#F97316"}}
        self.assertEqual(get_item(data, "feature"), {"name": "Feature", "color": "#F97316"})

    def test_get_nested_value(self):
        """Test getting a nested value (simulating chained filter calls)."""
        config = {"feature": {"name": "Feature", "color": "#F97316"}}
        # First call gets the inner dict
        inner = get_item(config, "feature")
        # Second call gets the color
        self.assertEqual(get_item(inner, "color"), "#F97316")

    def test_missing_key_returns_empty_dict(self):
        """Test missing key returns empty dict."""
        data = {"feature": {"name": "Feature"}}
        self.assertEqual(get_item(data, "nonexistent"), {})

    def test_none_dictionary_returns_empty_dict(self):
        """Test None dictionary returns empty dict."""
        self.assertEqual(get_item(None, "key"), {})

    def test_empty_dictionary_returns_empty_dict(self):
        """Test empty dictionary returns empty dict for any key."""
        self.assertEqual(get_item({}, "key"), {})

    def test_non_dict_returns_empty_dict(self):
        """Test non-dict input returns empty dict."""
        self.assertEqual(get_item("string", "key"), {})
        self.assertEqual(get_item(123, "key"), {})
        self.assertEqual(get_item(["list"], "key"), {})

    def test_pr_type_config_usage(self):
        """Test typical usage with PR type config."""
        pr_type_config = {
            "feature": {"name": "Feature", "color": "#F97316"},
            "bugfix": {"name": "Bugfix", "color": "#F87171"},
            "unknown": {"name": "Other", "color": "#6B7280"},
        }
        # Get the config for a type
        feature_config = get_item(pr_type_config, "feature")
        self.assertEqual(feature_config["name"], "Feature")
        self.assertEqual(feature_config["color"], "#F97316")

        # Get color directly with chained call
        self.assertEqual(get_item(get_item(pr_type_config, "bugfix"), "color"), "#F87171")
