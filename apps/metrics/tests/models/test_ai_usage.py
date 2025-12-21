from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    AIUsageDaily,
    TeamMember,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


class TestAIUsageDailyModel(TestCase):
    """Tests for AIUsageDaily model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.member1 = TeamMember.objects.create(team=self.team1, display_name="Alice", github_username="alice")
        self.member2 = TeamMember.objects.create(team=self.team2, display_name="Bob", github_username="bob")
        self.test_date = django_timezone.now().date()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_ai_usage_daily_creation_with_required_fields(self):
        """Test that AIUsageDaily can be created with required fields."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertEqual(usage.team, self.team1)
        self.assertEqual(usage.member, self.member1)
        self.assertEqual(usage.date, self.test_date)
        self.assertEqual(usage.source, "copilot")
        self.assertIsNotNone(usage.pk)

    def test_ai_usage_daily_source_choice_copilot(self):
        """Test that AIUsageDaily source 'copilot' works correctly."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertEqual(usage.source, "copilot")

    def test_ai_usage_daily_source_choice_cursor(self):
        """Test that AIUsageDaily source 'cursor' works correctly."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="cursor")
        self.assertEqual(usage.source, "cursor")

    def test_ai_usage_daily_creation_with_all_fields(self):
        """Test that AIUsageDaily can be created with all fields."""
        usage = AIUsageDaily.objects.create(
            team=self.team1,
            member=self.member1,
            date=self.test_date,
            source="copilot",
            active_hours=Decimal("8.50"),
            suggestions_shown=150,
            suggestions_accepted=120,
            acceptance_rate=Decimal("80.00"),
        )
        self.assertEqual(usage.active_hours, Decimal("8.50"))
        self.assertEqual(usage.suggestions_shown, 150)
        self.assertEqual(usage.suggestions_accepted, 120)
        self.assertEqual(usage.acceptance_rate, Decimal("80.00"))

    def test_ai_usage_daily_unique_constraint_team_member_date_source_enforced(self):
        """Test that unique constraint on (team, member, date, source) is enforced."""
        AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        # Attempt to create another usage with same team, member, date, and source
        with self.assertRaises(IntegrityError):
            AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")

    def test_ai_usage_daily_same_member_date_source_allowed_different_teams(self):
        """Test that same member+date+source is allowed in different teams."""
        usage1 = AIUsageDaily.objects.create(
            team=self.team1, member=self.member1, date=self.test_date, source="copilot"
        )
        usage2 = AIUsageDaily.objects.create(
            team=self.team2, member=self.member2, date=self.test_date, source="copilot"
        )
        self.assertEqual(usage1.date, usage2.date)
        self.assertEqual(usage1.source, usage2.source)
        self.assertNotEqual(usage1.team, usage2.team)

    def test_ai_usage_daily_same_member_date_different_sources_allowed(self):
        """Test that same member+date with different sources is allowed."""
        usage1 = AIUsageDaily.objects.create(
            team=self.team1, member=self.member1, date=self.test_date, source="copilot"
        )
        usage2 = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="cursor")
        self.assertEqual(usage1.member, usage2.member)
        self.assertEqual(usage1.date, usage2.date)
        self.assertNotEqual(usage1.source, usage2.source)

    def test_ai_usage_daily_member_cascade_delete(self):
        """Test that AIUsageDaily is cascade deleted when TeamMember is deleted."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        usage_id = usage.pk

        # Delete the member
        self.member1.delete()

        # Verify usage is also deleted
        with self.assertRaises(AIUsageDaily.DoesNotExist):
            AIUsageDaily.objects.get(pk=usage_id)

    def test_ai_usage_daily_default_suggestions_shown_is_zero(self):
        """Test that AIUsageDaily.suggestions_shown defaults to 0."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertEqual(usage.suggestions_shown, 0)

    def test_ai_usage_daily_default_suggestions_accepted_is_zero(self):
        """Test that AIUsageDaily.suggestions_accepted defaults to 0."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertEqual(usage.suggestions_accepted, 0)

    def test_ai_usage_daily_acceptance_rate_can_be_decimal(self):
        """Test that AIUsageDaily.acceptance_rate can store decimal values."""
        usage = AIUsageDaily.objects.create(
            team=self.team1,
            member=self.member1,
            date=self.test_date,
            source="copilot",
            acceptance_rate=Decimal("75.25"),
        )
        self.assertEqual(usage.acceptance_rate, Decimal("75.25"))

    def test_ai_usage_daily_active_hours_can_be_decimal(self):
        """Test that AIUsageDaily.active_hours can store decimal values."""
        usage = AIUsageDaily.objects.create(
            team=self.team1, member=self.member1, date=self.test_date, source="copilot", active_hours=Decimal("3.75")
        )
        self.assertEqual(usage.active_hours, Decimal("3.75"))

    def test_ai_usage_daily_synced_at_auto_updates_on_save(self):
        """Test that AIUsageDaily.synced_at auto-updates when model is saved."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        original_synced_at = usage.synced_at
        self.assertIsNotNone(original_synced_at)

        # Update and save
        usage.suggestions_shown = 100
        usage.save()

        # Refresh from database
        usage.refresh_from_db()
        self.assertGreaterEqual(usage.synced_at, original_synced_at)

    def test_ai_usage_daily_for_team_manager_filters_by_current_team(self):
        """Test that AIUsageDaily.for_team manager filters by current team context."""
        # Create usage for both teams
        usage1 = AIUsageDaily.objects.create(
            team=self.team1, member=self.member1, date=self.test_date, source="copilot"
        )
        usage2 = AIUsageDaily.objects.create(
            team=self.team2, member=self.member2, date=self.test_date, source="copilot"
        )

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_usage = list(AIUsageDaily.for_team.all())
        self.assertEqual(len(team1_usage), 1)
        self.assertEqual(team1_usage[0].pk, usage1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_usage = list(AIUsageDaily.for_team.all())
        self.assertEqual(len(team2_usage), 1)
        self.assertEqual(team2_usage[0].pk, usage2.pk)

    def test_ai_usage_daily_for_team_manager_with_context_manager(self):
        """Test that AIUsageDaily.for_team works with context manager."""
        # Create usage for both teams
        AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        AIUsageDaily.objects.create(team=self.team2, member=self.member2, date=self.test_date, source="copilot")

        with current_team(self.team1):
            self.assertEqual(AIUsageDaily.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(AIUsageDaily.for_team.count(), 1)

    def test_ai_usage_daily_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that AIUsageDaily.for_team returns empty queryset when no team is set."""
        AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(AIUsageDaily.for_team.count(), 0)

    def test_ai_usage_daily_has_created_at_from_base_model(self):
        """Test that AIUsageDaily inherits created_at from BaseModel."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertIsNotNone(usage.created_at)

    def test_ai_usage_daily_has_updated_at_from_base_model(self):
        """Test that AIUsageDaily inherits updated_at from BaseModel."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertIsNotNone(usage.updated_at)
