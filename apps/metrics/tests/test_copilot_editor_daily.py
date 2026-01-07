"""Tests for CopilotEditorDaily model.

Tests verify the model structure, constraints, and calculated properties
for tracking daily Copilot usage metrics broken down by IDE/editor.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import CopilotEditorDaily


class TestCopilotEditorDailyModel(TestCase):
    """Tests for CopilotEditorDaily model structure and behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.today = date.today()

    def test_model_can_be_created(self):
        """Test that CopilotEditorDaily can be created with all required fields."""
        record = CopilotEditorDaily.objects.create(
            team=self.team,
            date=self.today,
            editor="vscode",
            suggestions_shown=200,
            suggestions_accepted=80,
            active_users=15,
        )

        self.assertEqual(record.date, self.today)
        self.assertEqual(record.editor, "vscode")
        self.assertEqual(record.suggestions_shown, 200)
        self.assertEqual(record.suggestions_accepted, 80)
        self.assertEqual(record.active_users, 15)

    def test_model_has_team_field(self):
        """Test that model has team field from BaseTeamModel."""
        record = CopilotEditorDaily.objects.create(
            team=self.team,
            date=self.today,
            editor="jetbrains",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        self.assertEqual(record.team, self.team)

    def test_synced_at_auto_updates(self):
        """Test that synced_at is automatically set on save."""
        record = CopilotEditorDaily.objects.create(
            team=self.team,
            date=self.today,
            editor="neovim",
            suggestions_shown=50,
            suggestions_accepted=25,
        )

        self.assertIsNotNone(record.synced_at)

    def test_active_users_defaults_to_zero(self):
        """Test that active_users defaults to 0."""
        record = CopilotEditorDaily.objects.create(
            team=self.team,
            date=self.today,
            editor="vscode",
            suggestions_shown=30,
            suggestions_accepted=15,
        )

        self.assertEqual(record.active_users, 0)


class TestCopilotEditorDailyConstraints(TestCase):
    """Tests for CopilotEditorDaily model constraints."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.today = date.today()

    def test_unique_together_team_date_editor(self):
        """Test that team+date+editor combination is unique."""
        # Create first record
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=self.today,
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Attempting to create another for same team+date+editor should fail
        with self.assertRaises(IntegrityError):
            CopilotEditorDaily.objects.create(
                team=self.team,
                date=self.today,
                editor="vscode",
                suggestions_shown=200,
                suggestions_accepted=80,
            )

    def test_different_editors_allowed_for_same_team_date(self):
        """Test that different editors are allowed for the same team and date."""
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=self.today,
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        record2 = CopilotEditorDaily.objects.create(
            team=self.team,
            date=self.today,
            editor="jetbrains",
            suggestions_shown=150,
            suggestions_accepted=60,
        )

        self.assertEqual(record2.editor, "jetbrains")

    def test_same_editor_allowed_for_different_dates(self):
        """Test that same editor is allowed for different dates."""
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=self.today,
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        yesterday = self.today - timedelta(days=1)
        record2 = CopilotEditorDaily.objects.create(
            team=self.team,
            date=yesterday,
            editor="vscode",
            suggestions_shown=90,
            suggestions_accepted=35,
        )

        self.assertEqual(record2.date, yesterday)


class TestCopilotEditorDailyCalculations(TestCase):
    """Tests for CopilotEditorDaily calculated properties."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_acceptance_rate_property(self):
        """Test acceptance_rate calculated property."""
        record = CopilotEditorDaily.objects.create(
            team=self.team,
            date=date.today(),
            editor="vscode",
            suggestions_shown=200,
            suggestions_accepted=80,
        )

        # 80/200 = 40%
        self.assertEqual(record.acceptance_rate, Decimal("40.00"))

    def test_acceptance_rate_zero_suggestions(self):
        """Test acceptance_rate when suggestions_shown is zero."""
        record = CopilotEditorDaily.objects.create(
            team=self.team,
            date=date.today(),
            editor="vscode",
            suggestions_shown=0,
            suggestions_accepted=0,
        )

        self.assertEqual(record.acceptance_rate, Decimal("0.00"))
