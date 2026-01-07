"""Tests for parsing nested language/editor data from Copilot Metrics API response.

These tests verify that parse_metrics_response() extracts language and editor
breakdown data from the Copilot Metrics API response. The models
CopilotLanguageDaily and CopilotEditorDaily exist in apps/metrics/models/aggregations.py.
"""

from django.test import TestCase

from apps.integrations.services.copilot_metrics import parse_metrics_response


class TestParseMetricsLanguageData(TestCase):
    """Tests for extracting language breakdown data from Copilot metrics response."""

    def test_parse_metrics_extracts_languages_from_response(self):
        """Test that parse_metrics_response extracts languages array with suggestions, acceptances, lines."""
        # Arrange - API response with nested languages array
        raw_data = [
            {
                "date": "2026-01-06",
                "total_active_users": 12,
                "total_engaged_users": 10,
                "copilot_ide_code_completions": {
                    "total_completions": 1200,
                    "total_acceptances": 500,
                    "total_lines_suggested": 3000,
                    "total_lines_accepted": 1200,
                    "languages": [
                        {
                            "name": "python",
                            "total_completions": 600,
                            "total_acceptances": 280,
                            "total_lines_suggested": 1500,
                            "total_lines_accepted": 700,
                        },
                        {
                            "name": "typescript",
                            "total_completions": 400,
                            "total_acceptances": 160,
                            "total_lines_suggested": 1000,
                            "total_lines_accepted": 350,
                        },
                    ],
                },
            }
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have languages key
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

    def test_parse_metrics_handles_missing_languages(self):
        """Test that parse_metrics_response returns empty list when no languages array."""
        # Arrange - API response without languages array
        raw_data = [
            {
                "date": "2026-01-06",
                "total_active_users": 12,
                "total_engaged_users": 10,
                "copilot_ide_code_completions": {
                    "total_completions": 1200,
                    "total_acceptances": 500,
                    "total_lines_suggested": 3000,
                    "total_lines_accepted": 1200,
                    # No "languages" key
                },
            }
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have languages key with empty list
        self.assertIn("languages", day_data)
        self.assertEqual(day_data["languages"], [])

    def test_parse_metrics_handles_empty_languages_array(self):
        """Test that parse_metrics_response returns empty list when languages is []."""
        # Arrange - API response with empty languages array
        raw_data = [
            {
                "date": "2026-01-06",
                "total_active_users": 12,
                "total_engaged_users": 10,
                "copilot_ide_code_completions": {
                    "total_completions": 1200,
                    "total_acceptances": 500,
                    "total_lines_suggested": 3000,
                    "total_lines_accepted": 1200,
                    "languages": [],
                },
            }
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

    def test_parse_metrics_extracts_editors_from_response(self):
        """Test that parse_metrics_response extracts editors array with suggestions, acceptances, active_users."""
        # Arrange - API response with nested editors array
        raw_data = [
            {
                "date": "2026-01-06",
                "total_active_users": 12,
                "total_engaged_users": 10,
                "copilot_ide_code_completions": {
                    "total_completions": 1200,
                    "total_acceptances": 500,
                    "total_lines_suggested": 3000,
                    "total_lines_accepted": 1200,
                    "editors": [
                        {
                            "name": "vscode",
                            "total_completions": 800,
                            "total_acceptances": 350,
                            "total_active_users": 8,
                        },
                        {
                            "name": "jetbrains",
                            "total_completions": 400,
                            "total_acceptances": 150,
                            "total_active_users": 4,
                        },
                    ],
                },
            }
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

        # Check VS Code editor data
        vscode_editor = next((e for e in editors if e["name"] == "vscode"), None)
        self.assertIsNotNone(vscode_editor)
        self.assertEqual(vscode_editor["suggestions_shown"], 800)
        self.assertEqual(vscode_editor["suggestions_accepted"], 350)
        self.assertEqual(vscode_editor["active_users"], 8)

        # Check JetBrains editor data
        jetbrains_editor = next((e for e in editors if e["name"] == "jetbrains"), None)
        self.assertIsNotNone(jetbrains_editor)
        self.assertEqual(jetbrains_editor["suggestions_shown"], 400)
        self.assertEqual(jetbrains_editor["suggestions_accepted"], 150)
        self.assertEqual(jetbrains_editor["active_users"], 4)

    def test_parse_metrics_handles_missing_editors(self):
        """Test that parse_metrics_response returns empty list when no editors array."""
        # Arrange - API response without editors array
        raw_data = [
            {
                "date": "2026-01-06",
                "total_active_users": 12,
                "total_engaged_users": 10,
                "copilot_ide_code_completions": {
                    "total_completions": 1200,
                    "total_acceptances": 500,
                    "total_lines_suggested": 3000,
                    "total_lines_accepted": 1200,
                    # No "editors" key
                },
            }
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have editors key with empty list
        self.assertIn("editors", day_data)
        self.assertEqual(day_data["editors"], [])

    def test_parse_metrics_handles_empty_editors_array(self):
        """Test that parse_metrics_response returns empty list when editors is []."""
        # Arrange - API response with empty editors array
        raw_data = [
            {
                "date": "2026-01-06",
                "total_active_users": 12,
                "total_engaged_users": 10,
                "copilot_ide_code_completions": {
                    "total_completions": 1200,
                    "total_acceptances": 500,
                    "total_lines_suggested": 3000,
                    "total_lines_accepted": 1200,
                    "editors": [],
                },
            }
        ]

        # Act
        result = parse_metrics_response(raw_data)

        # Assert
        self.assertEqual(len(result), 1)
        day_data = result[0]

        # Should have editors key with empty list
        self.assertIn("editors", day_data)
        self.assertEqual(day_data["editors"], [])


class TestParseMetricsMultipleDaysWithLanguageEditorData(TestCase):
    """Tests for extracting per-day language/editor data for multiple days."""

    def test_parse_metrics_multiple_days_with_language_editor_data(self):
        """Test that parse_metrics_response extracts per-day language/editor data for multiple days."""
        # Arrange - API response with multiple days containing different language/editor data
        raw_data = [
            {
                "date": "2026-01-06",
                "total_active_users": 12,
                "total_engaged_users": 10,
                "copilot_ide_code_completions": {
                    "total_completions": 1200,
                    "total_acceptances": 500,
                    "total_lines_suggested": 3000,
                    "total_lines_accepted": 1200,
                    "editors": [
                        {
                            "name": "vscode",
                            "total_completions": 800,
                            "total_acceptances": 350,
                            "total_active_users": 8,
                        },
                    ],
                    "languages": [
                        {
                            "name": "python",
                            "total_completions": 600,
                            "total_acceptances": 280,
                            "total_lines_suggested": 1500,
                            "total_lines_accepted": 700,
                        },
                    ],
                },
            },
            {
                "date": "2026-01-05",
                "total_active_users": 10,
                "total_engaged_users": 8,
                "copilot_ide_code_completions": {
                    "total_completions": 900,
                    "total_acceptances": 400,
                    "total_lines_suggested": 2500,
                    "total_lines_accepted": 1000,
                    "editors": [
                        {
                            "name": "jetbrains",
                            "total_completions": 500,
                            "total_acceptances": 200,
                            "total_active_users": 5,
                        },
                    ],
                    "languages": [
                        {
                            "name": "go",
                            "total_completions": 300,
                            "total_acceptances": 150,
                            "total_lines_suggested": 800,
                            "total_lines_accepted": 400,
                        },
                    ],
                },
            },
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
        self.assertEqual(vscode_editor["suggestions_shown"], 800)
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
        self.assertEqual(jetbrains_editor["suggestions_shown"], 500)
        self.assertEqual(jetbrains_editor["active_users"], 5)
