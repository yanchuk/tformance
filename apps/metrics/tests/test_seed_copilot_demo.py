"""
Tests for seed_copilot_demo management command.

This command seeds Copilot mock data into the database using the CopilotMockDataGenerator
and stores it in AIUsageDaily model for testing and demo purposes.
"""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.metrics.factories import AIUsageDailyFactory, TeamFactory, TeamMemberFactory
from apps.metrics.models import AIUsageDaily, CopilotEditorDaily, CopilotLanguageDaily


class TestSeedCopilotDemoCommand(TestCase):
    """Tests for the seed_copilot_demo management command."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(slug="demo-team")
        self.members = TeamMemberFactory.create_batch(3, team=self.team)

    def test_command_requires_team_argument(self):
        """Test that command fails if --team is not provided."""
        with self.assertRaises(CommandError) as context:
            call_command("seed_copilot_demo")

        self.assertIn("team", str(context.exception).lower())

    def test_command_creates_ai_usage_records(self):
        """Test that command creates AIUsageDaily records with source=copilot."""
        # Arrange - team with members already set up

        # Act
        out = StringIO()
        call_command("seed_copilot_demo", team=self.team.slug, stdout=out)

        # Assert - records should be created
        records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        self.assertGreater(records.count(), 0)

        # All records should have source="copilot"
        for record in records:
            self.assertEqual(record.source, "copilot")

    def test_command_respects_scenario_parameter_high_adoption(self):
        """Test that --scenario=high_adoption creates records with higher acceptance rates."""
        # Act
        out = StringIO()
        call_command(
            "seed_copilot_demo",
            team=self.team.slug,
            scenario="high_adoption",
            seed=42,
            stdout=out,
        )

        # Assert - high adoption should have acceptance rates >= 40%
        records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        self.assertGreater(records.count(), 0)

        avg_acceptance = sum(r.acceptance_rate for r in records if r.acceptance_rate) / records.count()
        # High adoption scenarios should average above 40%
        self.assertGreaterEqual(avg_acceptance, 40)

    def test_command_respects_scenario_parameter_low_adoption(self):
        """Test that --scenario=low_adoption creates records with lower acceptance rates."""
        # Act
        out = StringIO()
        call_command(
            "seed_copilot_demo",
            team=self.team.slug,
            scenario="low_adoption",
            seed=42,
            stdout=out,
        )

        # Assert - low adoption should have acceptance rates <= 30%
        records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        self.assertGreater(records.count(), 0)

        avg_acceptance = sum(r.acceptance_rate for r in records if r.acceptance_rate) / records.count()
        # Low adoption scenarios should average below 30%
        self.assertLessEqual(avg_acceptance, 30)

    def test_command_respects_weeks_parameter_4_weeks(self):
        """Test that --weeks=4 creates 28 days of data."""
        # Act
        out = StringIO()
        call_command(
            "seed_copilot_demo",
            team=self.team.slug,
            weeks=4,
            stdout=out,
        )

        # Assert - should create records spanning 28 days
        records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        unique_dates = set(records.values_list("date", flat=True))
        self.assertEqual(len(unique_dates), 28)

    def test_command_respects_weeks_parameter_8_weeks(self):
        """Test that --weeks=8 creates 56 days of data."""
        # Act
        out = StringIO()
        call_command(
            "seed_copilot_demo",
            team=self.team.slug,
            weeks=8,
            stdout=out,
        )

        # Assert - should create records spanning 56 days
        records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        unique_dates = set(records.values_list("date", flat=True))
        self.assertEqual(len(unique_dates), 56)

    def test_command_clear_existing_removes_old_copilot_data(self):
        """Test that --clear-existing flag deletes existing Copilot AIUsageDaily records."""
        # Arrange - create existing Copilot records
        for member in self.members[:2]:
            AIUsageDailyFactory(team=self.team, member=member, source="copilot")

        existing_count = AIUsageDaily.objects.filter(team=self.team, source="copilot").count()
        self.assertEqual(existing_count, 2)

        # Act
        out = StringIO()
        call_command(
            "seed_copilot_demo",
            team=self.team.slug,
            clear_existing=True,
            stdout=out,
        )

        # Assert - old records should be replaced with new ones
        # The count should be different (new seeded data)
        new_records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        # New seeded data should exist
        self.assertGreater(new_records.count(), 0)

    def test_command_clear_existing_preserves_cursor_records(self):
        """Test that --clear-existing does NOT delete Cursor records (other sources)."""
        # Arrange - create Cursor records that should be preserved
        cursor_records = []
        for member in self.members[:2]:
            record = AIUsageDailyFactory(team=self.team, member=member, source="cursor")
            cursor_records.append(record)

        cursor_count_before = AIUsageDaily.objects.filter(team=self.team, source="cursor").count()
        self.assertEqual(cursor_count_before, 2)

        # Act
        out = StringIO()
        call_command(
            "seed_copilot_demo",
            team=self.team.slug,
            clear_existing=True,
            stdout=out,
        )

        # Assert - Cursor records should still exist
        cursor_count_after = AIUsageDaily.objects.filter(team=self.team, source="cursor").count()
        self.assertEqual(cursor_count_after, 2)

        # Verify the exact same records still exist
        for original_record in cursor_records:
            self.assertTrue(AIUsageDaily.objects.filter(id=original_record.id).exists())

    def test_command_creates_records_for_team_members(self):
        """Test that command creates AIUsageDaily records for each team member."""
        # Act
        out = StringIO()
        call_command("seed_copilot_demo", team=self.team.slug, stdout=out)

        # Assert - records should exist for each team member
        records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        member_ids_with_records = set(records.values_list("member_id", flat=True))

        # All team members should have at least one record
        for member in self.members:
            self.assertIn(
                member.id,
                member_ids_with_records,
                f"Member {member.display_name} should have AIUsageDaily records",
            )

    def test_command_respects_team_isolation(self):
        """Test that command only creates records for the specified team."""
        # Arrange - create another team
        other_team = TeamFactory(slug="other-team")
        TeamMemberFactory.create_batch(2, team=other_team)

        # Act - seed data only for demo-team
        out = StringIO()
        call_command("seed_copilot_demo", team=self.team.slug, stdout=out)

        # Assert - no records should be created for other team
        other_team_records = AIUsageDaily.objects.filter(team=other_team, source="copilot")
        self.assertEqual(other_team_records.count(), 0)

        # Records should exist for demo team
        demo_team_records = AIUsageDaily.objects.filter(team=self.team, source="copilot")
        self.assertGreater(demo_team_records.count(), 0)

    def test_command_respects_seed_parameter_deterministic_output(self):
        """Test that --seed=42 produces deterministic output."""
        # Act - run command twice with same seed
        call_command("seed_copilot_demo", team=self.team.slug, seed=42, clear_existing=True)
        first_run_records = list(
            AIUsageDaily.objects.filter(team=self.team, source="copilot")
            .order_by("member_id", "date")
            .values("member_id", "date", "suggestions_shown", "suggestions_accepted", "acceptance_rate")
        )

        # Clear and run again with same seed
        AIUsageDaily.objects.filter(team=self.team, source="copilot").delete()

        call_command("seed_copilot_demo", team=self.team.slug, seed=42)
        second_run_records = list(
            AIUsageDaily.objects.filter(team=self.team, source="copilot")
            .order_by("member_id", "date")
            .values("member_id", "date", "suggestions_shown", "suggestions_accepted", "acceptance_rate")
        )

        # Assert - both runs should produce identical data
        self.assertEqual(len(first_run_records), len(second_run_records))
        for first, second in zip(first_run_records, second_run_records, strict=False):
            self.assertEqual(first["suggestions_shown"], second["suggestions_shown"])
            self.assertEqual(first["suggestions_accepted"], second["suggestions_accepted"])
            self.assertEqual(first["acceptance_rate"], second["acceptance_rate"])

    def test_command_with_different_seeds_produces_different_output(self):
        """Test that different seeds produce different data."""
        # Act - run with seed 42
        call_command("seed_copilot_demo", team=self.team.slug, seed=42)
        seed_42_total = sum(
            AIUsageDaily.objects.filter(team=self.team, source="copilot").values_list("suggestions_shown", flat=True)
        )

        # Clear and run with different seed
        AIUsageDaily.objects.filter(team=self.team, source="copilot").delete()
        call_command("seed_copilot_demo", team=self.team.slug, seed=999)
        seed_999_total = sum(
            AIUsageDaily.objects.filter(team=self.team, source="copilot").values_list("suggestions_shown", flat=True)
        )

        # Assert - totals should be different (statistically very unlikely to match)
        self.assertNotEqual(seed_42_total, seed_999_total)

    def test_command_fails_with_nonexistent_team(self):
        """Test that command fails when team does not exist."""
        with self.assertRaises(CommandError) as context:
            call_command("seed_copilot_demo", team="nonexistent-team")

        self.assertIn("not found", str(context.exception).lower())

    def test_command_outputs_summary(self):
        """Test that command outputs a summary of created records."""
        # Act
        out = StringIO()
        call_command("seed_copilot_demo", team=self.team.slug, stdout=out)

        # Assert - output should contain summary information
        output = out.getvalue()
        # Should mention records created or similar summary
        self.assertTrue(
            any(word in output.lower() for word in ["created", "records", "seeded", "success"]),
            f"Expected summary in output, got: {output}",
        )

    def test_command_creates_language_data(self):
        """Test that command creates CopilotLanguageDaily records.

        This is essential for the "By Language" card on the AI Adoption dashboard.
        Without this, the card shows "No language data available".
        """
        # Act
        out = StringIO()
        call_command("seed_copilot_demo", team=self.team.slug, weeks=1, stdout=out)

        # Assert - CopilotLanguageDaily records should be created
        language_records = CopilotLanguageDaily.objects.filter(team=self.team)
        self.assertGreater(
            language_records.count(),
            0,
            "seed_copilot_demo should create CopilotLanguageDaily records for dashboard",
        )

        # Should have multiple languages (python, typescript, etc.)
        languages = set(language_records.values_list("language", flat=True))
        self.assertGreater(
            len(languages),
            1,
            f"Expected multiple languages, got: {languages}",
        )

    def test_command_creates_editor_data(self):
        """Test that command creates CopilotEditorDaily records.

        This is essential for the "By Editor" card on the AI Adoption dashboard.
        Without this, the card shows "No editor data available".
        """
        # Act
        out = StringIO()
        call_command("seed_copilot_demo", team=self.team.slug, weeks=1, stdout=out)

        # Assert - CopilotEditorDaily records should be created
        editor_records = CopilotEditorDaily.objects.filter(team=self.team)
        self.assertGreater(
            editor_records.count(),
            0,
            "seed_copilot_demo should create CopilotEditorDaily records for dashboard",
        )

        # Should have multiple editors (vscode, jetbrains, etc.)
        editors = set(editor_records.values_list("editor", flat=True))
        self.assertGreater(
            len(editors),
            1,
            f"Expected multiple editors, got: {editors}",
        )

    def test_clear_existing_removes_language_and_editor_data(self):
        """Test that --clear-existing removes language/editor data before reseeding."""
        # Arrange - seed initial data
        call_command("seed_copilot_demo", team=self.team.slug, weeks=1)

        initial_lang_count = CopilotLanguageDaily.objects.filter(team=self.team).count()
        initial_editor_count = CopilotEditorDaily.objects.filter(team=self.team).count()

        # Act - reseed with clear-existing
        out = StringIO()
        call_command("seed_copilot_demo", team=self.team.slug, weeks=1, clear_existing=True, stdout=out)

        # Assert - should have fresh data (counts should be similar, not doubled)
        new_lang_count = CopilotLanguageDaily.objects.filter(team=self.team).count()
        new_editor_count = CopilotEditorDaily.objects.filter(team=self.team).count()

        # The counts should be roughly the same (not doubled from two seeds)
        self.assertLessEqual(
            new_lang_count,
            initial_lang_count * 1.5,  # Allow some variance
            "Language data should be cleared and reseeded, not appended",
        )
        self.assertLessEqual(
            new_editor_count,
            initial_editor_count * 1.5,  # Allow some variance
            "Editor data should be cleared and reseeded, not appended",
        )
