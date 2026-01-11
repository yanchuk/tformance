"""Tests for Copilot mock data generator.

This module tests the CopilotMockDataGenerator which produces mock data
in the exact GitHub Copilot metrics API format for testing purposes.
"""

from django.test import TestCase

from apps.integrations.services.copilot_mock_data import CopilotMockDataGenerator


def aggregate_totals_from_nested(day_data: dict) -> dict:
    """Aggregate totals from nested editors > models > languages structure.

    The official GitHub Copilot Metrics API doesn't have top-level totals.
    This helper aggregates from the nested structure for test assertions.

    Args:
        day_data: A single day's data from the generator.

    Returns:
        dict with aggregated totals:
            - total_suggestions: Sum of all suggestions across all languages
            - total_acceptances: Sum of all acceptances
            - total_lines_suggested: Sum of all lines suggested
            - total_lines_accepted: Sum of all lines accepted
    """
    total_suggestions = 0
    total_acceptances = 0
    total_lines_suggested = 0
    total_lines_accepted = 0

    code_completions = day_data.get("copilot_ide_code_completions", {})
    for editor in code_completions.get("editors", []):
        for model in editor.get("models", []):
            for lang in model.get("languages", []):
                total_suggestions += lang.get("total_code_suggestions", 0)
                total_acceptances += lang.get("total_code_acceptances", 0)
                total_lines_suggested += lang.get("total_code_lines_suggested", 0)
                total_lines_accepted += lang.get("total_code_lines_accepted", 0)

    return {
        "total_suggestions": total_suggestions,
        "total_acceptances": total_acceptances,
        "total_lines_suggested": total_lines_suggested,
        "total_lines_accepted": total_lines_accepted,
    }


def aggregate_editor_totals(editor: dict) -> dict:
    """Aggregate totals for a single editor from its nested models > languages.

    Args:
        editor: An editor dict from the generator.

    Returns:
        dict with aggregated totals for this editor.
    """
    total_suggestions = 0
    total_acceptances = 0
    total_lines_suggested = 0
    total_lines_accepted = 0

    for model in editor.get("models", []):
        for lang in model.get("languages", []):
            total_suggestions += lang.get("total_code_suggestions", 0)
            total_acceptances += lang.get("total_code_acceptances", 0)
            total_lines_suggested += lang.get("total_code_lines_suggested", 0)
            total_lines_accepted += lang.get("total_code_lines_accepted", 0)

    return {
        "total_suggestions": total_suggestions,
        "total_acceptances": total_acceptances,
        "total_lines_suggested": total_lines_suggested,
        "total_lines_accepted": total_lines_accepted,
    }


class TestCopilotMockDataDateFormat(TestCase):
    """Tests for date format in generated mock data."""

    def test_generates_correct_date_format(self):
        """Test that generator produces ISO 8601 date strings (YYYY-MM-DD)."""
        # Arrange
        generator = CopilotMockDataGenerator()
        since = "2025-01-01"
        until = "2025-01-05"

        # Act
        data = generator.generate(since=since, until=until)

        # Assert - Each day's data should have ISO 8601 date format
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        for day_data in data:
            self.assertIn("date", day_data)
            # Verify ISO 8601 format (YYYY-MM-DD)
            date_str = day_data["date"]
            self.assertIsInstance(date_str, str)
            self.assertRegex(date_str, r"^\d{4}-\d{2}-\d{2}$")

    def test_date_range_matches_parameters(self):
        """Test that generated dates match since/until parameters."""
        # Arrange
        generator = CopilotMockDataGenerator()
        since = "2025-01-10"
        until = "2025-01-15"

        # Act
        data = generator.generate(since=since, until=until)

        # Assert - Dates should be within the specified range
        dates = [day_data["date"] for day_data in data]

        # First date should be >= since
        self.assertGreaterEqual(min(dates), since)

        # Last date should be <= until
        self.assertLessEqual(max(dates), until)

        # Should have data for each day in range (6 days total)
        expected_days = 6  # Jan 10, 11, 12, 13, 14, 15
        self.assertEqual(len(data), expected_days)


class TestCopilotMockDataRequiredFields(TestCase):
    """Tests for required fields in generated mock data."""

    def test_generates_all_required_fields(self):
        """Test that each day's data has all required top-level fields."""
        # Arrange
        generator = CopilotMockDataGenerator()

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        self.assertEqual(len(data), 1)
        day_data = data[0]

        # Verify all required top-level fields are present
        required_fields = [
            "date",
            "total_active_users",
            "total_engaged_users",
            "copilot_ide_code_completions",
            "copilot_ide_chat",
            "copilot_dotcom_chat",
            "copilot_dotcom_pull_requests",
        ]

        for field in required_fields:
            self.assertIn(field, day_data, f"Missing required field: {field}")

        # Verify types
        self.assertIsInstance(day_data["date"], str)
        self.assertIsInstance(day_data["total_active_users"], int)
        self.assertIsInstance(day_data["total_engaged_users"], int)
        self.assertIsInstance(day_data["copilot_ide_code_completions"], dict)
        self.assertIsInstance(day_data["copilot_ide_chat"], dict)
        self.assertIsInstance(day_data["copilot_dotcom_chat"], dict)
        self.assertIsInstance(day_data["copilot_dotcom_pull_requests"], dict)


class TestCopilotMockDataCodeCompletions(TestCase):
    """Tests for copilot_ide_code_completions structure (official GitHub API format)."""

    def test_code_completions_has_required_fields(self):
        """Test that copilot_ide_code_completions contains all required fields per official API."""
        # Arrange
        generator = CopilotMockDataGenerator()

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        code_completions = data[0]["copilot_ide_code_completions"]

        # Official API required fields (NOT legacy total_completions/total_acceptances)
        required_fields = [
            "total_engaged_users",
            "languages",
            "editors",
        ]

        for field in required_fields:
            self.assertIn(field, code_completions, f"Missing required field: {field}")

        # Verify types
        self.assertIsInstance(code_completions["total_engaged_users"], int)
        self.assertIsInstance(code_completions["languages"], list)
        self.assertIsInstance(code_completions["editors"], list)

        # Verify editors have nested models with languages (official schema)
        self.assertGreater(len(code_completions["editors"]), 0, "Should have at least one editor")
        for editor in code_completions["editors"]:
            self.assertIn("models", editor, "Editor should have nested 'models' array")


class TestCopilotMockDataLanguages(TestCase):
    """Tests for languages array structure (official GitHub API format).

    In the official API:
    - Top-level languages only has name and total_engaged_users
    - Completion metrics are in editors > models > languages
    """

    def test_top_level_languages_array_structure(self):
        """Test that top-level languages has name and total_engaged_users only (official schema)."""
        # Arrange
        generator = CopilotMockDataGenerator()

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        languages = data[0]["copilot_ide_code_completions"]["languages"]

        # Should have at least one language
        self.assertGreater(len(languages), 0)

        for lang in languages:
            # Verify required fields (official API)
            self.assertIn("name", lang)
            self.assertIn("total_engaged_users", lang)

            # Verify types
            self.assertIsInstance(lang["name"], str)
            self.assertIsInstance(lang["total_engaged_users"], int)

    def test_nested_languages_have_completion_metrics(self):
        """Test that nested languages (editors > models > languages) have completion metrics.

        These fields are required by parse_metrics_response() to aggregate totals.
        """
        # Arrange
        generator = CopilotMockDataGenerator()

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert - Check nested languages in editors > models
        editors = data[0]["copilot_ide_code_completions"]["editors"]

        for editor in editors:
            for model in editor["models"]:
                for lang in model["languages"]:
                    # Verify official API field names
                    self.assertIn("name", lang)
                    self.assertIn(
                        "total_code_suggestions",
                        lang,
                        f"Nested language {lang.get('name')} missing total_code_suggestions",
                    )
                    self.assertIn(
                        "total_code_acceptances",
                        lang,
                        f"Nested language {lang.get('name')} missing total_code_acceptances",
                    )
                    self.assertIn(
                        "total_code_lines_suggested",
                        lang,
                        f"Nested language {lang.get('name')} missing total_code_lines_suggested",
                    )
                    self.assertIn(
                        "total_code_lines_accepted",
                        lang,
                        f"Nested language {lang.get('name')} missing total_code_lines_accepted",
                    )

                    # Verify types
                    self.assertIsInstance(lang["total_code_suggestions"], int)
                    self.assertIsInstance(lang["total_code_acceptances"], int)
                    self.assertIsInstance(lang["total_code_lines_suggested"], int)
                    self.assertIsInstance(lang["total_code_lines_accepted"], int)

                    # Verify logical constraints
                    self.assertLessEqual(
                        lang["total_code_lines_accepted"],
                        lang["total_code_lines_suggested"],
                        f"Language {lang['name']}: lines_accepted should not exceed lines_suggested",
                    )


class TestCopilotMockDataEditors(TestCase):
    """Tests for editors array structure (official GitHub API format).

    In the official API, editors have nested models > languages structure.
    Completion metrics are ONLY in the nested languages, not at editor level.
    """

    def test_editors_array_structure(self):
        """Test that each editor has required fields and nested models structure."""
        # Arrange
        generator = CopilotMockDataGenerator()

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        editors = data[0]["copilot_ide_code_completions"]["editors"]

        # Should have at least one editor
        self.assertGreater(len(editors), 0)

        for editor in editors:
            # Verify required fields for official schema
            self.assertIn("name", editor)
            self.assertIn("total_engaged_users", editor)
            self.assertIn("models", editor)

            # Verify types
            self.assertIsInstance(editor["name"], str)
            self.assertIsInstance(editor["total_engaged_users"], int)
            self.assertIsInstance(editor["models"], list)

            # Verify nested structure has completion metrics
            editor_totals = aggregate_editor_totals(editor)
            self.assertIsInstance(editor_totals["total_suggestions"], int)
            self.assertIsInstance(editor_totals["total_acceptances"], int)

    def test_editors_nested_languages_have_metrics(self):
        """Test that nested languages (editors > models > languages) have all required metrics.

        These fields are used by parse_metrics_response() for aggregating totals.
        """
        # Arrange
        generator = CopilotMockDataGenerator()

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        editors = data[0]["copilot_ide_code_completions"]["editors"]

        for editor in editors:
            # Aggregate totals from nested structure
            editor_totals = aggregate_editor_totals(editor)

            # Verify aggregated values are valid
            self.assertGreaterEqual(editor_totals["total_suggestions"], 0)
            self.assertGreaterEqual(editor_totals["total_acceptances"], 0)
            self.assertGreaterEqual(editor_totals["total_lines_suggested"], 0)
            self.assertGreaterEqual(editor_totals["total_lines_accepted"], 0)

            # Verify logical constraints
            self.assertLessEqual(
                editor_totals["total_lines_accepted"],
                editor_totals["total_lines_suggested"],
                f"Editor {editor['name']}: lines_accepted should not exceed lines_suggested",
            )


class TestCopilotMockDataAcceptanceRates(TestCase):
    """Tests for acceptance rate validity in generated data."""

    def test_acceptance_rate_is_valid(self):
        """Test that acceptance values are valid (acceptances <= completions)."""
        # Arrange
        generator = CopilotMockDataGenerator()

        # Act - Generate multiple days to ensure consistency
        data = generator.generate(since="2025-01-01", until="2025-01-07")

        # Assert
        for day_data in data:
            # Aggregate totals from nested structure (official API has no top-level totals)
            totals = aggregate_totals_from_nested(day_data)

            # total_acceptances should be <= total_suggestions
            self.assertLessEqual(
                totals["total_acceptances"],
                totals["total_suggestions"],
                f"Acceptances ({totals['total_acceptances']}) should not exceed "
                f"suggestions ({totals['total_suggestions']}) for {day_data['date']}",
            )

            # total_lines_accepted should be <= total_lines_suggested
            self.assertLessEqual(
                totals["total_lines_accepted"],
                totals["total_lines_suggested"],
                f"Lines accepted ({totals['total_lines_accepted']}) should not exceed "
                f"lines suggested ({totals['total_lines_suggested']}) for {day_data['date']}",
            )

            # Check nested languages in editors > models
            code_completions = day_data["copilot_ide_code_completions"]
            for editor in code_completions["editors"]:
                for model in editor.get("models", []):
                    for lang in model.get("languages", []):
                        self.assertLessEqual(
                            lang["total_code_acceptances"],
                            lang["total_code_suggestions"],
                            f"Language {lang['name']}: acceptances should not exceed suggestions",
                        )

            # Check editors using aggregated totals
            for editor in code_completions["editors"]:
                editor_totals = aggregate_editor_totals(editor)
                self.assertLessEqual(
                    editor_totals["total_acceptances"],
                    editor_totals["total_suggestions"],
                    f"Editor {editor['name']}: acceptances should not exceed suggestions",
                )

    def test_engaged_users_not_exceeding_active_users(self):
        """Test that total_engaged_users <= total_active_users."""
        # Arrange
        generator = CopilotMockDataGenerator()

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-07")

        # Assert
        for day_data in data:
            self.assertLessEqual(
                day_data["total_engaged_users"],
                day_data["total_active_users"],
                f"Engaged users ({day_data['total_engaged_users']}) should not exceed "
                f"active users ({day_data['total_active_users']}) for {day_data['date']}",
            )


class TestCopilotScenarios(TestCase):
    """Tests for Copilot mock data scenarios.

    These tests verify that different scenarios produce distinct data patterns
    for testing various dashboard and analytics states.
    """

    def test_scenario_parameter_passed_to_generate(self):
        """Test that generate() accepts optional scenario parameter."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act - Should accept scenario parameter without error
        data = generator.generate(
            since="2025-01-01",
            until="2025-01-07",
            scenario="mixed_usage",
        )

        # Assert - Should return valid data
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 7)

    def test_high_adoption_scenario(self):
        """Test high_adoption scenario produces higher acceptance rates and more active users."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act
        data = generator.generate(
            since="2025-01-01",
            until="2025-01-07",
            scenario="high_adoption",
        )

        # Assert - Acceptance rate should be around 40-55% with ±5% per-language variance
        # Effective range: 35-60% (scenario range ± 5% variance)
        for day_data in data:
            # Use aggregation from nested structure (official API)
            totals = aggregate_totals_from_nested(day_data)
            if totals["total_suggestions"] > 0:
                acceptance_rate = totals["total_acceptances"] / totals["total_suggestions"]
                self.assertGreaterEqual(
                    acceptance_rate,
                    0.35,  # Scenario min (0.40) - variance (0.05)
                    f"High adoption acceptance rate {acceptance_rate:.2%} should be >= 35%",
                )
                self.assertLessEqual(
                    acceptance_rate,
                    0.60,  # Scenario max (0.55) + variance (0.05)
                    f"High adoption acceptance rate {acceptance_rate:.2%} should be <= 60%",
                )

            # More active users (15-30 vs default 10-20)
            self.assertGreaterEqual(
                day_data["total_active_users"],
                15,
                f"High adoption should have >= 15 active users, got {day_data['total_active_users']}",
            )
            self.assertLessEqual(
                day_data["total_active_users"],
                30,
                f"High adoption should have <= 30 active users, got {day_data['total_active_users']}",
            )

    def test_low_adoption_scenario(self):
        """Test low_adoption scenario produces lower acceptance rates and fewer active users."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act
        data = generator.generate(
            since="2025-01-01",
            until="2025-01-07",
            scenario="low_adoption",
        )

        # Assert - Acceptance rate should be around 15-25% with ±5% per-language variance
        # Plus integer rounding effects. Effective range widened for robustness.
        for day_data in data:
            # Use aggregation from nested structure (official API)
            totals = aggregate_totals_from_nested(day_data)
            if totals["total_suggestions"] > 0:
                acceptance_rate = totals["total_acceptances"] / totals["total_suggestions"]
                self.assertGreaterEqual(
                    acceptance_rate,
                    0.05,  # Allow for variance + integer rounding
                    f"Low adoption acceptance rate {acceptance_rate:.2%} should be >= 5%",
                )
                self.assertLessEqual(
                    acceptance_rate,
                    0.35,  # Allow for variance + integer rounding
                    f"Low adoption acceptance rate {acceptance_rate:.2%} should be <= 35%",
                )

            # Fewer active users (5-15)
            self.assertGreaterEqual(
                day_data["total_active_users"],
                5,
                f"Low adoption should have >= 5 active users, got {day_data['total_active_users']}",
            )
            self.assertLessEqual(
                day_data["total_active_users"],
                15,
                f"Low adoption should have <= 15 active users, got {day_data['total_active_users']}",
            )

    def test_growth_scenario_weekly_progression(self):
        """Test growth scenario shows clear upward trend over 8 weeks."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act - Generate 8 weeks of data
        data = generator.generate(
            since="2025-01-01",
            until="2025-02-25",  # 56 days = 8 weeks
            scenario="growth",
        )

        # Assert - Calculate weekly averages
        week_1_data = data[:7]
        week_8_data = data[49:56]

        week_1_avg_acceptance = self._calculate_avg_acceptance_rate(week_1_data)
        week_8_avg_acceptance = self._calculate_avg_acceptance_rate(week_8_data)

        # Week 1 should be around 30%
        self.assertGreaterEqual(
            week_1_avg_acceptance,
            0.25,
            f"Growth scenario week 1 should start around 30%, got {week_1_avg_acceptance:.2%}",
        )
        self.assertLessEqual(
            week_1_avg_acceptance,
            0.35,
            f"Growth scenario week 1 should start around 30%, got {week_1_avg_acceptance:.2%}",
        )

        # Week 8 should be around 70%
        self.assertGreaterEqual(
            week_8_avg_acceptance,
            0.65,
            f"Growth scenario week 8 should reach around 70%, got {week_8_avg_acceptance:.2%}",
        )
        self.assertLessEqual(
            week_8_avg_acceptance,
            0.75,
            f"Growth scenario week 8 should reach around 70%, got {week_8_avg_acceptance:.2%}",
        )

        # Verify upward trend
        self.assertGreater(
            week_8_avg_acceptance,
            week_1_avg_acceptance,
            f"Growth scenario should show upward trend: week 8 ({week_8_avg_acceptance:.2%}) "
            f"should be > week 1 ({week_1_avg_acceptance:.2%})",
        )

    def test_decline_scenario_weekly_progression(self):
        """Test decline scenario shows clear downward trend over 8 weeks."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act - Generate 8 weeks of data
        data = generator.generate(
            since="2025-01-01",
            until="2025-02-25",  # 56 days = 8 weeks
            scenario="decline",
        )

        # Assert - Calculate weekly averages
        week_1_data = data[:7]
        week_8_data = data[49:56]

        week_1_avg_acceptance = self._calculate_avg_acceptance_rate(week_1_data)
        week_8_avg_acceptance = self._calculate_avg_acceptance_rate(week_8_data)

        # Week 1 should be around 70%
        self.assertGreaterEqual(
            week_1_avg_acceptance,
            0.65,
            f"Decline scenario week 1 should start around 70%, got {week_1_avg_acceptance:.2%}",
        )
        self.assertLessEqual(
            week_1_avg_acceptance,
            0.75,
            f"Decline scenario week 1 should start around 70%, got {week_1_avg_acceptance:.2%}",
        )

        # Week 8 should be around 30%
        self.assertGreaterEqual(
            week_8_avg_acceptance,
            0.25,
            f"Decline scenario week 8 should drop to around 30%, got {week_8_avg_acceptance:.2%}",
        )
        self.assertLessEqual(
            week_8_avg_acceptance,
            0.35,
            f"Decline scenario week 8 should drop to around 30%, got {week_8_avg_acceptance:.2%}",
        )

        # Verify downward trend
        self.assertLess(
            week_8_avg_acceptance,
            week_1_avg_acceptance,
            f"Decline scenario should show downward trend: week 8 ({week_8_avg_acceptance:.2%}) "
            f"should be < week 1 ({week_1_avg_acceptance:.2%})",
        )

    def test_mixed_usage_scenario(self):
        """Test mixed_usage scenario produces high variance between days."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act
        data = generator.generate(
            since="2025-01-01",
            until="2025-01-14",  # 2 weeks
            scenario="mixed_usage",
        )

        # Assert - Calculate acceptance rates for all days using aggregation
        acceptance_rates = []
        for day_data in data:
            totals = aggregate_totals_from_nested(day_data)
            if totals["total_suggestions"] > 0:
                rate = totals["total_acceptances"] / totals["total_suggestions"]
                acceptance_rates.append(rate)

        # Calculate variance
        mean_rate = sum(acceptance_rates) / len(acceptance_rates)
        variance = sum((r - mean_rate) ** 2 for r in acceptance_rates) / len(acceptance_rates)

        # Mixed usage should have high variance (> 0.01 which is 10% standard deviation squared)
        self.assertGreater(
            variance,
            0.01,
            f"Mixed usage should have high variance, got {variance:.4f}",
        )

        # Should have both high and low days
        min_rate = min(acceptance_rates)
        max_rate = max(acceptance_rates)
        rate_range = max_rate - min_rate

        self.assertGreater(
            rate_range,
            0.20,
            f"Mixed usage should have at least 20% range between min/max, got {rate_range:.2%}",
        )

    def test_inactive_licenses_scenario(self):
        """Test inactive_licenses scenario includes days with very low or zero usage."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act
        data = generator.generate(
            since="2025-01-01",
            until="2025-01-14",  # 2 weeks
            scenario="inactive_licenses",
        )

        # Assert - Should have at least some days with 0 active users or very low completions
        has_zero_active_users = False
        has_very_low_completions = False

        for day_data in data:
            if day_data["total_active_users"] == 0:
                has_zero_active_users = True
            # Use aggregation from nested structure (official API)
            totals = aggregate_totals_from_nested(day_data)
            if totals["total_suggestions"] <= 5:
                has_very_low_completions = True

        # At least one of these conditions should be true
        self.assertTrue(
            has_zero_active_users or has_very_low_completions,
            "Inactive licenses scenario should have days with 0 active users or <= 5 suggestions",
        )

        # Count inactive days
        inactive_days = sum(
            1
            for day_data in data
            if day_data["total_active_users"] == 0 or aggregate_totals_from_nested(day_data)["total_suggestions"] <= 5
        )

        # Should have multiple inactive days in 2 weeks
        self.assertGreaterEqual(
            inactive_days,
            3,
            f"Inactive licenses scenario should have >= 3 inactive days in 2 weeks, got {inactive_days}",
        )

    def test_default_scenario_is_mixed_usage(self):
        """Test that default scenario (no parameter) behaves like mixed_usage."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act - Generate without scenario parameter
        data_default = generator.generate(since="2025-01-01", until="2025-01-07")

        # Reset RNG and generate with explicit mixed_usage
        generator_explicit = CopilotMockDataGenerator(seed=42)
        data_explicit = generator_explicit.generate(
            since="2025-01-01",
            until="2025-01-07",
            scenario="mixed_usage",
        )

        # Assert - Both should produce the same data
        self.assertEqual(len(data_default), len(data_explicit))
        for i, (default_day, explicit_day) in enumerate(zip(data_default, data_explicit, strict=False)):
            self.assertEqual(
                default_day["total_active_users"],
                explicit_day["total_active_users"],
                f"Day {i}: active users should match between default and explicit mixed_usage",
            )
            # Use aggregation from nested structure (official API)
            default_totals = aggregate_totals_from_nested(default_day)
            explicit_totals = aggregate_totals_from_nested(explicit_day)
            self.assertEqual(
                default_totals["total_suggestions"],
                explicit_totals["total_suggestions"],
                f"Day {i}: suggestions should match between default and explicit mixed_usage",
            )

    def test_unknown_scenario_raises_value_error(self):
        """Test that unknown scenario raises ValueError with helpful message."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            generator.generate(
                since="2025-01-01",
                until="2025-01-07",
                scenario="unknown_scenario",
            )

        # Verify error message contains valid scenarios
        error_message = str(context.exception)
        self.assertIn("unknown_scenario", error_message)
        self.assertIn("high_adoption", error_message)
        self.assertIn("low_adoption", error_message)
        self.assertIn("mixed_usage", error_message)

    def _calculate_avg_acceptance_rate(self, data: list[dict]) -> float:
        """Helper to calculate average acceptance rate across days.

        Uses aggregation from nested structure (official GitHub API format).
        """
        total_suggestions = 0
        total_acceptances = 0

        for day_data in data:
            # Aggregate from nested editors > models > languages
            totals = aggregate_totals_from_nested(day_data)
            total_suggestions += totals["total_suggestions"]
            total_acceptances += totals["total_acceptances"]

        if total_suggestions == 0:
            return 0.0
        return total_acceptances / total_suggestions


class TestOfficialGitHubAPISchema(TestCase):
    """Tests for official GitHub Copilot Metrics API schema compliance.

    The official GitHub API uses a nested structure:
    - editors > models > languages (with completion metrics)
    - Top-level languages only has name and total_engaged_users

    Field names use 'total_code_suggestions' not 'total_completions'.

    Reference: https://docs.github.com/en/rest/copilot/copilot-metrics
    """

    def test_editors_have_models_array(self):
        """Test that each editor has a nested 'models' array (official schema)."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        self.assertEqual(len(data), 1)
        day_data = data[0]
        editors = day_data["copilot_ide_code_completions"]["editors"]

        self.assertGreater(len(editors), 0, "Should have at least one editor")

        for editor in editors:
            self.assertIn("name", editor)
            self.assertIn("models", editor, f"Editor {editor['name']} should have 'models' array")
            self.assertIsInstance(editor["models"], list)
            self.assertGreater(len(editor["models"]), 0, "Should have at least one model")

    def test_models_have_languages_with_official_field_names(self):
        """Test that models contain languages with official API field names."""
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        editors = data[0]["copilot_ide_code_completions"]["editors"]

        for editor in editors:
            for model in editor["models"]:
                # Verify model structure
                self.assertIn("name", model, "Model should have 'name'")
                self.assertIn("is_custom_model", model, "Model should have 'is_custom_model'")
                self.assertIn("languages", model, "Model should have 'languages' array")

                # Verify language metrics use OFFICIAL field names
                for lang in model["languages"]:
                    self.assertIn("name", lang)
                    self.assertIn(
                        "total_code_suggestions",
                        lang,
                        f"Language {lang.get('name')} should use 'total_code_suggestions' (official API field)",
                    )
                    self.assertIn(
                        "total_code_acceptances",
                        lang,
                        f"Language {lang.get('name')} should use 'total_code_acceptances' (official API field)",
                    )
                    self.assertIn(
                        "total_code_lines_suggested",
                        lang,
                        f"Language {lang.get('name')} should use 'total_code_lines_suggested'",
                    )
                    self.assertIn(
                        "total_code_lines_accepted",
                        lang,
                        f"Language {lang.get('name')} should use 'total_code_lines_accepted'",
                    )

    def test_top_level_languages_has_no_completion_metrics(self):
        """Test that top-level languages only has name and engaged users (official schema).

        In the official GitHub API, completion metrics are ONLY in editors > models > languages,
        NOT in the top-level languages array.
        """
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        top_level_languages = data[0]["copilot_ide_code_completions"]["languages"]

        for lang in top_level_languages:
            # Top-level languages should ONLY have these fields per official API
            self.assertIn("name", lang)
            self.assertIn("total_engaged_users", lang)

            # Should NOT have completion metrics at top level
            self.assertNotIn(
                "total_completions",
                lang,
                "Top-level languages should NOT have 'total_completions' (official API)",
            )
            self.assertNotIn(
                "total_code_suggestions",
                lang,
                "Top-level languages should NOT have completion metrics (official API)",
            )

    def test_no_top_level_completion_totals(self):
        """Test that copilot_ide_code_completions has no top-level totals (official schema).

        Official GitHub API does NOT have aggregate totals at copilot_ide_code_completions level.
        Totals must be computed by aggregating from editors > models > languages.
        """
        # Arrange
        generator = CopilotMockDataGenerator(seed=42)

        # Act
        data = generator.generate(since="2025-01-01", until="2025-01-01")

        # Assert
        code_completions = data[0]["copilot_ide_code_completions"]

        # Should NOT have these top-level fields (not in official API)
        self.assertNotIn(
            "total_completions",
            code_completions,
            "Official API has no top-level 'total_completions'",
        )
        self.assertNotIn(
            "total_acceptances",
            code_completions,
            "Official API has no top-level 'total_acceptances'",
        )
        self.assertNotIn(
            "total_lines_suggested",
            code_completions,
            "Official API has no top-level 'total_lines_suggested'",
        )
        self.assertNotIn(
            "total_lines_accepted",
            code_completions,
            "Official API has no top-level 'total_lines_accepted'",
        )

        # Should have total_engaged_users at this level
        self.assertIn("total_engaged_users", code_completions)
