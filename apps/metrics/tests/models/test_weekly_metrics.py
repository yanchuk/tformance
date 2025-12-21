from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    TeamMember,
    WeeklyMetrics,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


class TestWeeklyMetricsModel(TestCase):
    """Tests for WeeklyMetrics model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.member1 = TeamMember.objects.create(team=self.team1, display_name="Alice", github_username="alice")
        self.member2 = TeamMember.objects.create(team=self.team2, display_name="Bob", github_username="bob")
        # Use a Monday date for week_start
        self.week_start = django_timezone.now().date().replace(day=2)  # Monday, Dec 2, 2024

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_weekly_metrics_creation_with_required_fields(self):
        """Test that WeeklyMetrics can be created with required fields (team, member, week_start)."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertEqual(metrics.team, self.team1)
        self.assertEqual(metrics.member, self.member1)
        self.assertEqual(metrics.week_start, self.week_start)
        self.assertIsNotNone(metrics.pk)

    def test_weekly_metrics_default_values(self):
        """Test that WeeklyMetrics default values work correctly."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        # Count fields should default to 0
        self.assertEqual(metrics.prs_merged, 0)
        self.assertEqual(metrics.commits_count, 0)
        self.assertEqual(metrics.lines_added, 0)
        self.assertEqual(metrics.lines_removed, 0)
        self.assertEqual(metrics.revert_count, 0)
        self.assertEqual(metrics.hotfix_count, 0)
        self.assertEqual(metrics.issues_resolved, 0)
        self.assertEqual(metrics.ai_assisted_prs, 0)
        self.assertEqual(metrics.surveys_completed, 0)
        self.assertEqual(metrics.story_points_completed, Decimal("0"))
        # Average fields should be null by default
        self.assertIsNone(metrics.avg_cycle_time_hours)
        self.assertIsNone(metrics.avg_review_time_hours)
        self.assertIsNone(metrics.avg_quality_rating)
        self.assertIsNone(metrics.guess_accuracy)

    def test_weekly_metrics_unique_constraint_team_member_week_enforced(self):
        """Test that unique constraint on (team, member, week_start) is enforced."""
        WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        # Attempt to create another metric for the same team, member, and week
        with self.assertRaises(IntegrityError):
            WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)

    def test_weekly_metrics_same_member_week_allowed_different_teams(self):
        """Test that same member+week is allowed in different teams."""
        metrics1 = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        metrics2 = WeeklyMetrics.objects.create(team=self.team2, member=self.member2, week_start=self.week_start)
        self.assertEqual(metrics1.week_start, metrics2.week_start)
        self.assertNotEqual(metrics1.team, metrics2.team)
        self.assertNotEqual(metrics1.member, metrics2.member)

    def test_weekly_metrics_member_cascade_delete(self):
        """Test that WeeklyMetrics is cascade deleted when TeamMember is deleted."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        metrics_id = metrics.pk

        # Delete the member
        self.member1.delete()

        # Verify metrics is also deleted
        with self.assertRaises(WeeklyMetrics.DoesNotExist):
            WeeklyMetrics.objects.get(pk=metrics_id)

    def test_weekly_metrics_creation_with_all_fields(self):
        """Test that WeeklyMetrics can be created with all fields."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1,
            member=self.member1,
            week_start=self.week_start,
            prs_merged=5,
            avg_cycle_time_hours=Decimal("24.50"),
            avg_review_time_hours=Decimal("3.75"),
            commits_count=25,
            lines_added=1500,
            lines_removed=300,
            revert_count=1,
            hotfix_count=2,
            story_points_completed=Decimal("13.5"),
            issues_resolved=8,
            ai_assisted_prs=3,
            avg_quality_rating=Decimal("2.75"),
            surveys_completed=5,
            guess_accuracy=Decimal("85.50"),
        )
        self.assertEqual(metrics.prs_merged, 5)
        self.assertEqual(metrics.avg_cycle_time_hours, Decimal("24.50"))
        self.assertEqual(metrics.avg_review_time_hours, Decimal("3.75"))
        self.assertEqual(metrics.commits_count, 25)
        self.assertEqual(metrics.lines_added, 1500)
        self.assertEqual(metrics.lines_removed, 300)
        self.assertEqual(metrics.revert_count, 1)
        self.assertEqual(metrics.hotfix_count, 2)
        self.assertEqual(metrics.story_points_completed, Decimal("13.5"))
        self.assertEqual(metrics.issues_resolved, 8)
        self.assertEqual(metrics.ai_assisted_prs, 3)
        self.assertEqual(metrics.avg_quality_rating, Decimal("2.75"))
        self.assertEqual(metrics.surveys_completed, 5)
        self.assertEqual(metrics.guess_accuracy, Decimal("85.50"))

    def test_weekly_metrics_decimal_field_avg_cycle_time_hours(self):
        """Test that WeeklyMetrics.avg_cycle_time_hours can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, avg_cycle_time_hours=Decimal("48.25")
        )
        self.assertEqual(metrics.avg_cycle_time_hours, Decimal("48.25"))

    def test_weekly_metrics_decimal_field_avg_review_time_hours(self):
        """Test that WeeklyMetrics.avg_review_time_hours can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, avg_review_time_hours=Decimal("2.50")
        )
        self.assertEqual(metrics.avg_review_time_hours, Decimal("2.50"))

    def test_weekly_metrics_decimal_field_story_points_completed(self):
        """Test that WeeklyMetrics.story_points_completed can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, story_points_completed=Decimal("8.5")
        )
        self.assertEqual(metrics.story_points_completed, Decimal("8.5"))

    def test_weekly_metrics_decimal_field_avg_quality_rating(self):
        """Test that WeeklyMetrics.avg_quality_rating can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, avg_quality_rating=Decimal("2.33")
        )
        self.assertEqual(metrics.avg_quality_rating, Decimal("2.33"))

    def test_weekly_metrics_decimal_field_guess_accuracy(self):
        """Test that WeeklyMetrics.guess_accuracy can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, guess_accuracy=Decimal("92.75")
        )
        self.assertEqual(metrics.guess_accuracy, Decimal("92.75"))

    def test_weekly_metrics_null_handling_avg_cycle_time(self):
        """Test that avg_cycle_time_hours can be null (no PRs merged)."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, prs_merged=0
        )
        self.assertIsNone(metrics.avg_cycle_time_hours)
        self.assertEqual(metrics.prs_merged, 0)

    def test_weekly_metrics_null_handling_avg_review_time(self):
        """Test that avg_review_time_hours can be null (no reviews)."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertIsNone(metrics.avg_review_time_hours)

    def test_weekly_metrics_null_handling_avg_quality_rating(self):
        """Test that avg_quality_rating can be null (no survey responses)."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, surveys_completed=0
        )
        self.assertIsNone(metrics.avg_quality_rating)
        self.assertEqual(metrics.surveys_completed, 0)

    def test_weekly_metrics_null_handling_guess_accuracy(self):
        """Test that guess_accuracy can be null (no guesses made)."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertIsNone(metrics.guess_accuracy)

    def test_weekly_metrics_zero_vs_null_count_fields(self):
        """Test that count fields use 0 as default, not null."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        # All count fields should be 0, not None
        self.assertEqual(metrics.prs_merged, 0)
        self.assertEqual(metrics.commits_count, 0)
        self.assertEqual(metrics.lines_added, 0)
        self.assertEqual(metrics.lines_removed, 0)
        self.assertEqual(metrics.revert_count, 0)
        self.assertEqual(metrics.hotfix_count, 0)
        self.assertEqual(metrics.issues_resolved, 0)
        self.assertEqual(metrics.ai_assisted_prs, 0)
        self.assertEqual(metrics.surveys_completed, 0)

    def test_weekly_metrics_zero_vs_null_average_fields(self):
        """Test that average fields use null as default, not 0."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        # All average fields should be None, not 0
        self.assertIsNone(metrics.avg_cycle_time_hours)
        self.assertIsNone(metrics.avg_review_time_hours)
        self.assertIsNone(metrics.avg_quality_rating)
        self.assertIsNone(metrics.guess_accuracy)

    def test_weekly_metrics_for_team_manager_filters_by_current_team(self):
        """Test that WeeklyMetrics.for_team manager filters by current team context."""
        # Create metrics for both teams
        metrics1 = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        metrics2 = WeeklyMetrics.objects.create(team=self.team2, member=self.member2, week_start=self.week_start)

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_metrics = list(WeeklyMetrics.for_team.all())
        self.assertEqual(len(team1_metrics), 1)
        self.assertEqual(team1_metrics[0].pk, metrics1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_metrics = list(WeeklyMetrics.for_team.all())
        self.assertEqual(len(team2_metrics), 1)
        self.assertEqual(team2_metrics[0].pk, metrics2.pk)

    def test_weekly_metrics_for_team_manager_with_context_manager(self):
        """Test that WeeklyMetrics.for_team works with context manager."""
        # Create metrics for both teams
        WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        WeeklyMetrics.objects.create(team=self.team2, member=self.member2, week_start=self.week_start)

        with current_team(self.team1):
            self.assertEqual(WeeklyMetrics.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(WeeklyMetrics.for_team.count(), 1)

    def test_weekly_metrics_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that WeeklyMetrics.for_team returns empty queryset when no team is set."""
        WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(WeeklyMetrics.for_team.count(), 0)

    def test_weekly_metrics_has_created_at_from_base_model(self):
        """Test that WeeklyMetrics inherits created_at from BaseModel."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertIsNotNone(metrics.created_at)

    def test_weekly_metrics_has_updated_at_from_base_model(self):
        """Test that WeeklyMetrics inherits updated_at from BaseModel."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertIsNotNone(metrics.updated_at)

    def test_weekly_metrics_has_team_foreign_key_from_base_team_model(self):
        """Test that WeeklyMetrics has team ForeignKey from BaseTeamModel."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertEqual(metrics.team, self.team1)
        self.assertIsInstance(metrics.team, Team)

    def test_weekly_metrics_updated_at_changes_on_save(self):
        """Test that updated_at timestamp changes when WeeklyMetrics is saved."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        original_updated_at = metrics.updated_at

        # Update and save
        metrics.prs_merged = 10
        metrics.save()

        # Refresh from database
        metrics.refresh_from_db()
        self.assertGreater(metrics.updated_at, original_updated_at)

    def test_weekly_metrics_multiple_weeks_per_member(self):
        """Test that multiple week entries can be created for same member."""
        week1 = self.week_start
        week2 = week1 + django_timezone.timedelta(days=7)  # Next Monday

        metrics1 = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=week1)
        metrics2 = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=week2)

        self.assertEqual(metrics1.member, metrics2.member)
        self.assertNotEqual(metrics1.week_start, metrics2.week_start)
        self.assertEqual(WeeklyMetrics.objects.filter(team=self.team1, member=self.member1).count(), 2)

    def test_weekly_metrics_verbose_name(self):
        """Test that WeeklyMetrics has correct verbose_name."""
        self.assertEqual(WeeklyMetrics._meta.verbose_name, "Weekly Metrics")

    def test_weekly_metrics_verbose_name_plural(self):
        """Test that WeeklyMetrics has correct verbose_name_plural."""
        self.assertEqual(WeeklyMetrics._meta.verbose_name_plural, "Weekly Metrics")
