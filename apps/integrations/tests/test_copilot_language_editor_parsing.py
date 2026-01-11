"""Tests for parsing nested language/editor data from Copilot Metrics API response.

These tests verify that parse_metrics_response() extracts language and editor
breakdown data from the official GitHub Copilot Metrics API response format.

Official schema: editors > models > languages (nested metrics)
Top-level languages only has name and total_engaged_users.
"""

from django.test import TestCase

from apps.integrations.services.copilot_metrics import parse_metrics_response


def _make_official_schema_fixture(
    *,
    date: str = "2026-01-06",
    total_active_users: int = 12,
    total_engaged_users: int = 10,
    editors: list[dict] | None = None,
    top_level_languages: list[dict] | None = None,
) -> dict:
    """Create test fixture in official GitHub Copilot Metrics API format.

    Official schema has:
    - editors > models > languages (with completion metrics)
    - top-level languages (only name and total_engaged_users)
    """
    if editors is None:
        editors = []
    if top_level_languages is None:
        top_level_languages = []

    return {
        "date": date,
        "total_active_users": total_active_users,
        "total_engaged_users": total_engaged_users,
        "copilot_ide_code_completions": {
            "editors": editors,
            "languages": top_level_languages,
        },
    }


def _make_editor_with_languages(
    name: str,
    total_engaged_users: int,
    languages: list[dict],
) -> dict:
    """Create editor with nested models > languages structure."""
    return {
        "name": name,
        "total_engaged_users": total_engaged_users,
        "models": [
            {
                "name": "default",
                "is_custom_model": False,
                "custom_model_training_date": None,
                "total_engaged_users": total_engaged_users,
                "languages": languages,
            }
        ],
    }


def _make_language(
    name: str,
    suggestions: int,
    acceptances: int,
    lines_suggested: int,
    lines_accepted: int,
    engaged_users: int = 5,
) -> dict:
    """Create language dict with official API field names."""
    return {
        "name": name,
        "total_engaged_users": engaged_users,
        "total_code_suggestions": suggestions,
        "total_code_acceptances": acceptances,
        "total_code_lines_suggested": lines_suggested,
        "total_code_lines_accepted": lines_accepted,
    }


class TestParseMetricsLanguageData(TestCase):
    """Tests for extracting language breakdown data from Copilot metrics response."""

    def test_parse_metrics_extracts_languages_from_nested_structure(self):
        """Test that parse_metrics_response extracts languages from editors > models > languages."""
        # Arrange - Official API format with nested languages
        raw_data = [
            _make_official_schema_fixture(
                editors=[
                    _make_editor_with_languages(
                        name="vscode",
                        total_engaged_users=8,
                        languages=[
                            _make_language("python", 600, 280, 1500, 700),
                            _make_language("typescript", 400, 160, 1000, 350),
                        ],
                    ),
                ],
            )
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have languages key with aggregated data
        self.assertIn("languages", day_data)
        languages = day_data["languages"]

        # Should have 2 languages
        self.assertEqual(len(languages), 2)

        # Check Python language data
        python_lang = next((lang for lang in languages if lang["name"] == "python"), None)
        self.assertIsNotNone(python_lang)
        self.assertEqual(python_lang["suggestions_shown"], 600)
        self.assertEqual(python_lang["suggestions_accepted"], 280)
        self.assertEqual(python_lang["lines_suggested"], 1500)
        self.assertEqual(python_lang["lines_accepted"], 700)

        # Check TypeScript language data
        ts_lang = next((lang for lang in languages if lang["name"] == "typescript"), None)
        self.assertIsNotNone(ts_lang)
        self.assertEqual(ts_lang["suggestions_shown"], 400)
        self.assertEqual(ts_lang["suggestions_accepted"], 160)
        self.assertEqual(ts_lang["lines_suggested"], 1000)
        self.assertEqual(ts_lang["lines_accepted"], 350)

    def test_parse_metrics_aggregates_languages_across_editors(self):
        """Test that languages are aggregated across multiple editors."""
        # Arrange - Same language in multiple editors
        raw_data = [
            _make_official_schema_fixture(
                editors=[
                    _make_editor_with_languages(
                        name="vscode",
                        total_engaged_users=5,
                        languages=[_make_language("python", 300, 150, 600, 300)],
                    ),
                    _make_editor_with_languages(
                        name="jetbrains",
                        total_engaged_users=3,
                        languages=[_make_language("python", 200, 100, 400, 200)],
                    ),
                ],
            )
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert - Python should have combined totals from both editors
        languages = result[0]["languages"]
        self.assertEqual(len(languages), 1)

        python_lang = languages[0]
        self.assertEqual(python_lang["name"], "python")
        self.assertEqual(python_lang["suggestions_shown"], 500)  # 300 + 200
        self.assertEqual(python_lang["suggestions_accepted"], 250)  # 150 + 100
        self.assertEqual(python_lang["lines_suggested"], 1000)  # 600 + 400
        self.assertEqual(python_lang["lines_accepted"], 500)  # 300 + 200

    def test_parse_metrics_handles_missing_editors(self):
        """Test that parse_metrics_response returns empty list when no editors array."""
        # Arrange - No editors means no nested languages
        raw_data = [_make_official_schema_fixture(editors=[])]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have languages key with empty list
        self.assertIn("languages", day_data)
        self.assertEqual(day_data["languages"], [])

    def test_parse_metrics_handles_empty_languages_in_model(self):
        """Test that parse_metrics_response handles editors with no languages."""
        # Arrange - Editor exists but has no languages
        raw_data = [
            _make_official_schema_fixture(
                editors=[
                    _make_editor_with_languages(
                        name="vscode",
                        total_engaged_users=5,
                        languages=[],
                    ),
                ],
            )
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have languages key with empty list
        self.assertIn("languages", day_data)
        self.assertEqual(day_data["languages"], [])


class TestParseMetricsEditorData(TestCase):
    """Tests for extracting editor breakdown data from Copilot metrics response."""

    def test_parse_metrics_extracts_editors_with_aggregated_totals(self):
        """Test that parse_metrics_response aggregates editor totals from nested languages."""
        # Arrange - Official API format with nested structure
        raw_data = [
            _make_official_schema_fixture(
                editors=[
                    _make_editor_with_languages(
                        name="vscode",
                        total_engaged_users=8,
                        languages=[
                            _make_language("python", 500, 250, 1000, 500),
                            _make_language("typescript", 300, 100, 600, 200),
                        ],
                    ),
                    _make_editor_with_languages(
                        name="jetbrains",
                        total_engaged_users=4,
                        languages=[_make_language("java", 400, 150, 800, 300)],
                    ),
                ],
            )
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have editors key
        self.assertIn("editors", day_data)
        editors = day_data["editors"]

        # Should have 2 editors
        self.assertEqual(len(editors), 2)

        # Check VS Code editor data (aggregated from python + typescript)
        vscode_editor = next((e for e in editors if e["name"] == "vscode"), None)
        self.assertIsNotNone(vscode_editor)
        self.assertEqual(vscode_editor["suggestions_shown"], 800)  # 500 + 300
        self.assertEqual(vscode_editor["suggestions_accepted"], 350)  # 250 + 100
        self.assertEqual(vscode_editor["active_users"], 8)

        # Check JetBrains editor data
        jetbrains_editor = next((e for e in editors if e["name"] == "jetbrains"), None)
        self.assertIsNotNone(jetbrains_editor)
        self.assertEqual(jetbrains_editor["suggestions_shown"], 400)
        self.assertEqual(jetbrains_editor["suggestions_accepted"], 150)
        self.assertEqual(jetbrains_editor["active_users"], 4)

    def test_parse_metrics_handles_missing_editors(self):
        """Test that parse_metrics_response returns empty list when no editors array."""
        # Arrange - API response without editors
        raw_data = [_make_official_schema_fixture(editors=[])]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have editors key with empty list
        self.assertIn("editors", day_data)
        self.assertEqual(day_data["editors"], [])


class TestParseMetricsTotalsAggregation(TestCase):
    """Tests for aggregating top-level totals from nested structure."""

    def test_parse_metrics_aggregates_totals_from_nested(self):
        """Test that top-level totals are aggregated from all editors > models > languages."""
        # Arrange - Multiple editors with multiple languages
        raw_data = [
            _make_official_schema_fixture(
                editors=[
                    _make_editor_with_languages(
                        name="vscode",
                        total_engaged_users=5,
                        languages=[
                            _make_language("python", 500, 250, 1000, 500),
                            _make_language("typescript", 300, 100, 600, 200),
                        ],
                    ),
                    _make_editor_with_languages(
                        name="jetbrains",
                        total_engaged_users=3,
                        languages=[_make_language("java", 200, 80, 400, 160)],
                    ),
                ],
            )
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert - Totals should be sum of all nested languages
        day_data = result[0]
        self.assertEqual(day_data["code_completions_total"], 1000)  # 500 + 300 + 200
        self.assertEqual(day_data["code_completions_accepted"], 430)  # 250 + 100 + 80
        self.assertEqual(day_data["lines_suggested"], 2000)  # 1000 + 600 + 400
        self.assertEqual(day_data["lines_accepted"], 860)  # 500 + 200 + 160

    def test_parse_metrics_handles_empty_editors_for_totals(self):
        """Test that totals are zero when no editors exist."""
        # Arrange - No editors
        raw_data = [_make_official_schema_fixture(editors=[])]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert - Totals should be zero
        day_data = result[0]
        self.assertEqual(day_data["code_completions_total"], 0)
        self.assertEqual(day_data["code_completions_accepted"], 0)
        self.assertEqual(day_data["lines_suggested"], 0)
        self.assertEqual(day_data["lines_accepted"], 0)


class TestParseMetricsMultipleDaysWithLanguageEditorData(TestCase):
    """Tests for extracting per-day language/editor data for multiple days."""

    def test_parse_metrics_multiple_days_with_language_editor_data(self):
        """Test that parse_metrics_response extracts per-day data from official schema."""
        # Arrange - Multiple days with official nested structure
        raw_data = [
            _make_official_schema_fixture(
                date="2026-01-06",
                editors=[
                    _make_editor_with_languages(
                        name="vscode",
                        total_engaged_users=8,
                        languages=[_make_language("python", 600, 280, 1500, 700)],
                    ),
                ],
            ),
            _make_official_schema_fixture(
                date="2026-01-05",
                editors=[
                    _make_editor_with_languages(
                        name="jetbrains",
                        total_engaged_users=5,
                        languages=[_make_language("go", 300, 150, 800, 400)],
                    ),
                ],
            ),
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert - should have 2 days
        self.assertEqual(len(result), 2)

        # Day 1 (2026-01-06)
        day1 = result[0]
        self.assertEqual(day1["date"], "2026-01-06")
        self.assertIn("languages", day1)
        self.assertIn("editors", day1)

        # Day 1 languages
        self.assertEqual(len(day1["languages"]), 1)
        python_lang = day1["languages"][0]
        self.assertEqual(python_lang["name"], "python")
        self.assertEqual(python_lang["suggestions_shown"], 600)
        self.assertEqual(python_lang["suggestions_accepted"], 280)

        # Day 1 editors
        self.assertEqual(len(day1["editors"]), 1)
        vscode_editor = day1["editors"][0]
        self.assertEqual(vscode_editor["name"], "vscode")
        self.assertEqual(vscode_editor["suggestions_shown"], 600)
        self.assertEqual(vscode_editor["active_users"], 8)

        # Day 2 (2026-01-05)
        day2 = result[1]
        self.assertEqual(day2["date"], "2026-01-05")
        self.assertIn("languages", day2)
        self.assertIn("editors", day2)

        # Day 2 languages - different language than day 1
        self.assertEqual(len(day2["languages"]), 1)
        go_lang = day2["languages"][0]
        self.assertEqual(go_lang["name"], "go")
        self.assertEqual(go_lang["suggestions_shown"], 300)
        self.assertEqual(go_lang["suggestions_accepted"], 150)

        # Day 2 editors - different editor than day 1
        self.assertEqual(len(day2["editors"]), 1)
        jetbrains_editor = day2["editors"][0]
        self.assertEqual(jetbrains_editor["name"], "jetbrains")
        self.assertEqual(jetbrains_editor["suggestions_shown"], 300)
        self.assertEqual(jetbrains_editor["active_users"], 5)
