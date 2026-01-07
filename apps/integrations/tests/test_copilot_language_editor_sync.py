"""Tests for syncing language and editor data to CopilotLanguageDaily and CopilotEditorDaily models.

These tests verify that sync_copilot_language_data() and sync_copilot_editor_data()
functions correctly save parsed metrics from parse_metrics_response() to the database.

The functions should be created in apps/integrations/services/copilot_metrics.py:
- sync_copilot_language_data(team, parsed_metrics) - Syncs language data for multiple days
- sync_copilot_editor_data(team, parsed_metrics) - Syncs editor data for multiple days
"""

from datetime import date

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import CopilotEditorDaily, CopilotLanguageDaily


class TestSyncCopilotLanguageData(TestCase):
    """Tests for sync_copilot_language_data function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_sync_language_data_creates_records(self):
        """Test that sync_copilot_language_data creates CopilotLanguageDaily records for each language."""
        from apps.integrations.services.copilot_metrics import sync_copilot_language_data

        # Arrange - parsed metrics with 2 languages for 1 day
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [
                    {
                        "name": "python",
                        "suggestions_shown": 600,
                        "suggestions_accepted": 280,
                        "lines_suggested": 1500,
                        "lines_accepted": 700,
                    },
                    {
                        "name": "typescript",
                        "suggestions_shown": 400,
                        "suggestions_accepted": 160,
                        "lines_suggested": 1000,
                        "lines_accepted": 350,
                    },
                ],
                "editors": [],
            }
        ]

        # Act
        sync_copilot_language_data(self.team, parsed_metrics)

        # Assert - should have 2 records
        records = CopilotLanguageDaily.objects.filter(team=self.team)
        self.assertEqual(records.count(), 2)

        # Verify Python record
        python_record = records.get(language="python")
        self.assertEqual(python_record.date, date(2026, 1, 6))
        self.assertEqual(python_record.suggestions_shown, 600)
        self.assertEqual(python_record.suggestions_accepted, 280)
        self.assertEqual(python_record.lines_suggested, 1500)
        self.assertEqual(python_record.lines_accepted, 700)

        # Verify TypeScript record
        ts_record = records.get(language="typescript")
        self.assertEqual(ts_record.date, date(2026, 1, 6))
        self.assertEqual(ts_record.suggestions_shown, 400)
        self.assertEqual(ts_record.suggestions_accepted, 160)
        self.assertEqual(ts_record.lines_suggested, 1000)
        self.assertEqual(ts_record.lines_accepted, 350)

    def test_sync_language_data_updates_existing_records(self):
        """Test that sync_copilot_language_data updates records on re-sync (update_or_create)."""
        from apps.integrations.services.copilot_metrics import sync_copilot_language_data

        # Arrange - Create initial record
        CopilotLanguageDaily.objects.create(
            team=self.team,
            date=date(2026, 1, 6),
            language="python",
            suggestions_shown=100,
            suggestions_accepted=50,
            lines_suggested=200,
            lines_accepted=100,
        )

        # Parsed metrics with updated values
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [
                    {
                        "name": "python",
                        "suggestions_shown": 600,
                        "suggestions_accepted": 280,
                        "lines_suggested": 1500,
                        "lines_accepted": 700,
                    },
                ],
                "editors": [],
            }
        ]

        # Act
        sync_copilot_language_data(self.team, parsed_metrics)

        # Assert - should still have 1 record (not duplicated)
        records = CopilotLanguageDaily.objects.filter(team=self.team)
        self.assertEqual(records.count(), 1)

        # Verify record was updated with new values
        python_record = records.get(language="python")
        self.assertEqual(python_record.suggestions_shown, 600)
        self.assertEqual(python_record.suggestions_accepted, 280)
        self.assertEqual(python_record.lines_suggested, 1500)
        self.assertEqual(python_record.lines_accepted, 700)

    def test_sync_language_data_handles_multiple_days(self):
        """Test that sync_copilot_language_data creates records for each day."""
        from apps.integrations.services.copilot_metrics import sync_copilot_language_data

        # Arrange - parsed metrics with 2 days, each with 1 language
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [
                    {
                        "name": "python",
                        "suggestions_shown": 600,
                        "suggestions_accepted": 280,
                        "lines_suggested": 1500,
                        "lines_accepted": 700,
                    },
                ],
                "editors": [],
            },
            {
                "date": "2026-01-05",
                "languages": [
                    {
                        "name": "python",
                        "suggestions_shown": 500,
                        "suggestions_accepted": 250,
                        "lines_suggested": 1200,
                        "lines_accepted": 600,
                    },
                ],
                "editors": [],
            },
        ]

        # Act
        sync_copilot_language_data(self.team, parsed_metrics)

        # Assert - should have 2 records (one per day)
        records = CopilotLanguageDaily.objects.filter(team=self.team, language="python")
        self.assertEqual(records.count(), 2)

        # Verify day 1
        day1_record = records.get(date=date(2026, 1, 6))
        self.assertEqual(day1_record.suggestions_shown, 600)

        # Verify day 2
        day2_record = records.get(date=date(2026, 1, 5))
        self.assertEqual(day2_record.suggestions_shown, 500)

    def test_sync_language_data_handles_empty_languages(self):
        """Test that sync_copilot_language_data handles empty languages list without error."""
        from apps.integrations.services.copilot_metrics import sync_copilot_language_data

        # Arrange - parsed metrics with no languages
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [],
                "editors": [],
            }
        ]

        # Act - should not raise exception
        result = sync_copilot_language_data(self.team, parsed_metrics)

        # Assert - no records created
        records = CopilotLanguageDaily.objects.filter(team=self.team)
        self.assertEqual(records.count(), 0)

        # Result should indicate 0 records synced
        self.assertEqual(result, 0)

    def test_sync_language_data_returns_count(self):
        """Test that sync_copilot_language_data returns count of records created/updated."""
        from apps.integrations.services.copilot_metrics import sync_copilot_language_data

        # Arrange - parsed metrics with 3 languages across 2 days
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [
                    {
                        "name": "python",
                        "suggestions_shown": 600,
                        "suggestions_accepted": 280,
                        "lines_suggested": 1500,
                        "lines_accepted": 700,
                    },
                    {
                        "name": "typescript",
                        "suggestions_shown": 400,
                        "suggestions_accepted": 160,
                        "lines_suggested": 1000,
                        "lines_accepted": 350,
                    },
                ],
                "editors": [],
            },
            {
                "date": "2026-01-05",
                "languages": [
                    {
                        "name": "go",
                        "suggestions_shown": 300,
                        "suggestions_accepted": 150,
                        "lines_suggested": 800,
                        "lines_accepted": 400,
                    },
                ],
                "editors": [],
            },
        ]

        # Act
        result = sync_copilot_language_data(self.team, parsed_metrics)

        # Assert - should return 3 (total language records)
        self.assertEqual(result, 3)


class TestSyncCopilotEditorData(TestCase):
    """Tests for sync_copilot_editor_data function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_sync_editor_data_creates_records(self):
        """Test that sync_copilot_editor_data creates CopilotEditorDaily records for each editor."""
        from apps.integrations.services.copilot_metrics import sync_copilot_editor_data

        # Arrange - parsed metrics with 2 editors for 1 day
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [],
                "editors": [
                    {
                        "name": "vscode",
                        "suggestions_shown": 800,
                        "suggestions_accepted": 350,
                        "active_users": 8,
                    },
                    {
                        "name": "jetbrains",
                        "suggestions_shown": 400,
                        "suggestions_accepted": 150,
                        "active_users": 4,
                    },
                ],
            }
        ]

        # Act
        sync_copilot_editor_data(self.team, parsed_metrics)

        # Assert - should have 2 records
        records = CopilotEditorDaily.objects.filter(team=self.team)
        self.assertEqual(records.count(), 2)

        # Verify VS Code record
        vscode_record = records.get(editor="vscode")
        self.assertEqual(vscode_record.date, date(2026, 1, 6))
        self.assertEqual(vscode_record.suggestions_shown, 800)
        self.assertEqual(vscode_record.suggestions_accepted, 350)
        self.assertEqual(vscode_record.active_users, 8)

        # Verify JetBrains record
        jetbrains_record = records.get(editor="jetbrains")
        self.assertEqual(jetbrains_record.date, date(2026, 1, 6))
        self.assertEqual(jetbrains_record.suggestions_shown, 400)
        self.assertEqual(jetbrains_record.suggestions_accepted, 150)
        self.assertEqual(jetbrains_record.active_users, 4)

    def test_sync_editor_data_updates_existing_records(self):
        """Test that sync_copilot_editor_data updates records on re-sync (update_or_create)."""
        from apps.integrations.services.copilot_metrics import sync_copilot_editor_data

        # Arrange - Create initial record
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2026, 1, 6),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=50,
            active_users=2,
        )

        # Parsed metrics with updated values
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [],
                "editors": [
                    {
                        "name": "vscode",
                        "suggestions_shown": 800,
                        "suggestions_accepted": 350,
                        "active_users": 8,
                    },
                ],
            }
        ]

        # Act
        sync_copilot_editor_data(self.team, parsed_metrics)

        # Assert - should still have 1 record (not duplicated)
        records = CopilotEditorDaily.objects.filter(team=self.team)
        self.assertEqual(records.count(), 1)

        # Verify record was updated with new values
        vscode_record = records.get(editor="vscode")
        self.assertEqual(vscode_record.suggestions_shown, 800)
        self.assertEqual(vscode_record.suggestions_accepted, 350)
        self.assertEqual(vscode_record.active_users, 8)

    def test_sync_editor_data_handles_multiple_days(self):
        """Test that sync_copilot_editor_data creates records for each day."""
        from apps.integrations.services.copilot_metrics import sync_copilot_editor_data

        # Arrange - parsed metrics with 2 days, each with 1 editor
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [],
                "editors": [
                    {
                        "name": "vscode",
                        "suggestions_shown": 800,
                        "suggestions_accepted": 350,
                        "active_users": 8,
                    },
                ],
            },
            {
                "date": "2026-01-05",
                "languages": [],
                "editors": [
                    {
                        "name": "vscode",
                        "suggestions_shown": 700,
                        "suggestions_accepted": 300,
                        "active_users": 7,
                    },
                ],
            },
        ]

        # Act
        sync_copilot_editor_data(self.team, parsed_metrics)

        # Assert - should have 2 records (one per day)
        records = CopilotEditorDaily.objects.filter(team=self.team, editor="vscode")
        self.assertEqual(records.count(), 2)

        # Verify day 1
        day1_record = records.get(date=date(2026, 1, 6))
        self.assertEqual(day1_record.suggestions_shown, 800)
        self.assertEqual(day1_record.active_users, 8)

        # Verify day 2
        day2_record = records.get(date=date(2026, 1, 5))
        self.assertEqual(day2_record.suggestions_shown, 700)
        self.assertEqual(day2_record.active_users, 7)

    def test_sync_editor_data_handles_empty_editors(self):
        """Test that sync_copilot_editor_data handles empty editors list without error."""
        from apps.integrations.services.copilot_metrics import sync_copilot_editor_data

        # Arrange - parsed metrics with no editors
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [],
                "editors": [],
            }
        ]

        # Act - should not raise exception
        result = sync_copilot_editor_data(self.team, parsed_metrics)

        # Assert - no records created
        records = CopilotEditorDaily.objects.filter(team=self.team)
        self.assertEqual(records.count(), 0)

        # Result should indicate 0 records synced
        self.assertEqual(result, 0)

    def test_sync_editor_data_returns_count(self):
        """Test that sync_copilot_editor_data returns count of records created/updated."""
        from apps.integrations.services.copilot_metrics import sync_copilot_editor_data

        # Arrange - parsed metrics with 3 editors across 2 days
        parsed_metrics = [
            {
                "date": "2026-01-06",
                "languages": [],
                "editors": [
                    {
                        "name": "vscode",
                        "suggestions_shown": 800,
                        "suggestions_accepted": 350,
                        "active_users": 8,
                    },
                    {
                        "name": "jetbrains",
                        "suggestions_shown": 400,
                        "suggestions_accepted": 150,
                        "active_users": 4,
                    },
                ],
            },
            {
                "date": "2026-01-05",
                "languages": [],
                "editors": [
                    {
                        "name": "neovim",
                        "suggestions_shown": 200,
                        "suggestions_accepted": 100,
                        "active_users": 2,
                    },
                ],
            },
        ]

        # Act
        result = sync_copilot_editor_data(self.team, parsed_metrics)

        # Assert - should return 3 (total editor records)
        self.assertEqual(result, 3)
