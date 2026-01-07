"""Tests for CopilotSeatSnapshot model.

Tests verify the model structure, constraints, and basic functionality
for tracking Copilot seat utilization snapshots.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import CopilotSeatSnapshot


class TestCopilotSeatSnapshotModel(TestCase):
    """Tests for CopilotSeatSnapshot model structure and behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.today = date.today()

    def test_model_can_be_created(self):
        """Test that CopilotSeatSnapshot can be created with required fields."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=25,
            active_this_cycle=18,
            inactive_this_cycle=4,
        )

        self.assertEqual(snapshot.total_seats, 25)
        self.assertEqual(snapshot.active_this_cycle, 18)
        self.assertEqual(snapshot.inactive_this_cycle, 4)
        self.assertEqual(snapshot.pending_cancellation, 0)  # default

    def test_model_has_team_field(self):
        """Test that model has team field from BaseTeamModel."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        self.assertEqual(snapshot.team, self.team)

    def test_synced_at_auto_updates(self):
        """Test that synced_at is automatically set on save."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        self.assertIsNotNone(snapshot.synced_at)

    def test_pending_cancellation_defaults_to_zero(self):
        """Test that pending_cancellation defaults to 0."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        self.assertEqual(snapshot.pending_cancellation, 0)

    def test_pending_cancellation_can_be_set(self):
        """Test that pending_cancellation can be set explicitly."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=25,
            active_this_cycle=18,
            inactive_this_cycle=4,
            pending_cancellation=3,
        )

        self.assertEqual(snapshot.pending_cancellation, 3)


class TestCopilotSeatSnapshotConstraints(TestCase):
    """Tests for CopilotSeatSnapshot model constraints."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.today = date.today()

    def test_unique_together_team_date(self):
        """Test that team+date combination is unique."""
        # Create first snapshot
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        # Attempting to create another for same team+date should fail
        with self.assertRaises(IntegrityError):
            CopilotSeatSnapshot.objects.create(
                team=self.team,
                date=self.today,
                total_seats=15,
                active_this_cycle=12,
                inactive_this_cycle=3,
            )

    def test_different_dates_allowed_for_same_team(self):
        """Test that different dates are allowed for the same team."""
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        yesterday = self.today - timedelta(days=1)
        snapshot2 = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=yesterday,
            total_seats=9,
            active_this_cycle=7,
            inactive_this_cycle=2,
        )

        self.assertEqual(snapshot2.date, yesterday)

    def test_same_date_allowed_for_different_teams(self):
        """Test that same date is allowed for different teams."""
        team2 = TeamFactory()

        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        snapshot2 = CopilotSeatSnapshot.objects.create(
            team=team2,
            date=self.today,
            total_seats=20,
            active_this_cycle=15,
            inactive_this_cycle=5,
        )

        self.assertEqual(snapshot2.team, team2)


class TestCopilotSeatSnapshotTeamIsolation(TestCase):
    """Tests for CopilotSeatSnapshot team isolation."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = TeamFactory()
        self.team2 = TeamFactory()
        self.today = date.today()

    def test_objects_filter_by_team_works(self):
        """Test that filtering by team returns correct snapshots."""
        # Create snapshots for both teams
        CopilotSeatSnapshot.objects.create(
            team=self.team1,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )
        CopilotSeatSnapshot.objects.create(
            team=self.team2,
            date=self.today,
            total_seats=20,
            active_this_cycle=15,
            inactive_this_cycle=5,
        )

        # Query using objects manager with team filter
        team1_snapshots = CopilotSeatSnapshot.objects.filter(team=self.team1)

        self.assertEqual(team1_snapshots.count(), 1)
        self.assertEqual(team1_snapshots.first().total_seats, 10)


class TestCopilotSeatSnapshotCalculations(TestCase):
    """Tests for CopilotSeatSnapshot calculated properties."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_utilization_rate_property(self):
        """Test utilization_rate calculated property."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date.today(),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        # 20/25 = 80%
        self.assertEqual(snapshot.utilization_rate, Decimal("80.00"))

    def test_utilization_rate_zero_seats(self):
        """Test utilization_rate when total_seats is zero."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date.today(),
            total_seats=0,
            active_this_cycle=0,
            inactive_this_cycle=0,
        )

        self.assertEqual(snapshot.utilization_rate, Decimal("0.00"))

    def test_monthly_cost_property(self):
        """Test monthly_cost calculated property at $19/seat."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date.today(),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        # 25 * $19 = $475
        self.assertEqual(snapshot.monthly_cost, Decimal("475.00"))

    def test_wasted_spend_property(self):
        """Test wasted_spend calculated property."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date.today(),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        # 5 inactive * $19 = $95 wasted
        self.assertEqual(snapshot.wasted_spend, Decimal("95.00"))

    def test_cost_per_active_user_property(self):
        """Test cost_per_active_user calculated property."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date.today(),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        # $475 / 20 active = $23.75 per active user
        self.assertEqual(snapshot.cost_per_active_user, Decimal("23.75"))

    def test_cost_per_active_user_zero_active(self):
        """Test cost_per_active_user when no active users."""
        snapshot = CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date.today(),
            total_seats=5,
            active_this_cycle=0,
            inactive_this_cycle=5,
        )

        self.assertIsNone(snapshot.cost_per_active_user)
