"""Tests for CopilotLanguageDaily model.

Tests verify the model structure, constraints, and calculated properties
for tracking daily Copilot usage metrics broken down by programming language.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import CopilotLanguageDaily


class TestCopilotLanguageDailyModel(TestCase):
    """Tests for CopilotLanguageDaily model structure and behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.today = date.today()

    def test_model_can_be_created(self):
        """Test that CopilotLanguageDaily can be created with all required fields."""
        record = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today,
            language="Python",
            suggestions_shown=200,
            suggestions_accepted=80,
            lines_suggested=500,
            lines_accepted=350,
        )

        self.assertEqual(record.date, self.today)
        self.assertEqual(record.language, "Python")
        self.assertEqual(record.suggestions_shown, 200)
        self.assertEqual(record.suggestions_accepted, 80)
        self.assertEqual(record.lines_suggested, 500)
        self.assertEqual(record.lines_accepted, 350)

    def test_model_has_team_field(self):
        """Test that model has team field from BaseTeamModel."""
        record = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today,
            language="TypeScript",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        self.assertEqual(record.team, self.team)

    def test_synced_at_auto_updates(self):
        """Test that synced_at is automatically set on save."""
        record = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today,
            language="Go",
            suggestions_shown=50,
            suggestions_accepted=25,
        )

        self.assertIsNotNone(record.synced_at)

    def test_lines_fields_default_to_zero(self):
        """Test that lines_suggested and lines_accepted default to 0."""
        record = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today,
            language="Rust",
            suggestions_shown=30,
            suggestions_accepted=15,
        )

        self.assertEqual(record.lines_suggested, 0)
        self.assertEqual(record.lines_accepted, 0)


class TestCopilotLanguageDailyConstraints(TestCase):
    """Tests for CopilotLanguageDaily model constraints."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.today = date.today()

    def test_unique_together_team_date_language(self):
        """Test that team+date+language combination is unique."""
        # Create first record
        CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today,
            language="Python",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Attempting to create another for same team+date+language should fail
        with self.assertRaises(IntegrityError):
            CopilotLanguageDaily.objects.create(
                team=self.team,
                date=self.today,
                language="Python",
                suggestions_shown=200,
                suggestions_accepted=80,
            )

    def test_different_languages_allowed_for_same_team_date(self):
        """Test that different languages are allowed for the same team and date."""
        CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today,
            language="Python",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        record2 = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today,
            language="TypeScript",
            suggestions_shown=150,
            suggestions_accepted=60,
        )

        self.assertEqual(record2.language, "TypeScript")

    def test_same_language_allowed_for_different_dates(self):
        """Test that same language is allowed for different dates."""
        CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today,
            language="Python",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        yesterday = self.today - timedelta(days=1)
        record2 = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=yesterday,
            language="Python",
            suggestions_shown=90,
            suggestions_accepted=35,
        )

        self.assertEqual(record2.date, yesterday)


class TestCopilotLanguageDailyCalculations(TestCase):
    """Tests for CopilotLanguageDaily calculated properties."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_acceptance_rate_property(self):
        """Test acceptance_rate calculated property."""
        record = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=date.today(),
            language="Python",
            suggestions_shown=200,
            suggestions_accepted=80,
        )

        # 80/200 = 40%
        self.assertEqual(record.acceptance_rate, Decimal("40.00"))

    def test_acceptance_rate_zero_suggestions(self):
        """Test acceptance_rate when suggestions_shown is zero."""
        record = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=date.today(),
            language="Python",
            suggestions_shown=0,
            suggestions_accepted=0,
        )

        self.assertEqual(record.acceptance_rate, Decimal("0.00"))

    def test_acceptance_rate_returns_decimal(self):
        """Test that acceptance_rate returns Decimal type, not float."""
        record = CopilotLanguageDaily.objects.create(
            team=self.team,
            date=date.today(),
            language="Python",
            suggestions_shown=100,
            suggestions_accepted=33,
        )

        self.assertIsInstance(record.acceptance_rate, Decimal)
