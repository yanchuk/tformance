"""Tests for Copilot seat stats card view.

Tests verify the HTMX endpoint for Copilot seat utilization stats,
including admin-only access, feature flag requirements, and data display.
"""

from datetime import date
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.metrics.models import CopilotSeatSnapshot
from apps.teams.models import Flag
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER

# Use DummyCache in tests to avoid cache pollution between parallel workers.
# Waffle caches flag-team associations, which can cause flaky tests when
# different workers have different database states but share the same cache.
_DUMMY_CACHE_SETTINGS = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotSeatStatsView(TestCase):
    """Tests for copilot_seat_stats_card view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.member_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member_user, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

        # Create feature flags for Copilot
        Flag.objects.get_or_create(name="copilot_enabled")
        Flag.objects.get_or_create(name="copilot_seat_utilization")

    def _enable_copilot_flags(self):
        """Enable both Copilot feature flags for the team."""
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()  # Flush waffle cache
        copilot_seat = Flag.objects.get(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()  # Flush waffle cache

    def test_copilot_seat_stats_returns_latest_snapshot(self):
        """Test that view returns data from most recent snapshot."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        # Create multiple snapshots - should return the latest
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date(2024, 1, 1),
            total_seats=20,
            active_this_cycle=15,
            inactive_this_cycle=5,
        )
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("seat_stats", response.context)

        seat_stats = response.context["seat_stats"]
        self.assertIsNotNone(seat_stats)
        self.assertEqual(seat_stats["total_seats"], 25)
        self.assertEqual(seat_stats["active_seats"], 20)
        self.assertEqual(seat_stats["inactive_seats"], 5)
        # Utilization rate: 20/25 = 80%
        self.assertEqual(seat_stats["utilization_rate"], Decimal("80.00"))
        # Monthly cost: 25 * $19 = $475
        self.assertEqual(seat_stats["monthly_cost"], Decimal("475.00"))
        # Wasted spend: 5 * $19 = $95
        self.assertEqual(seat_stats["wasted_spend"], Decimal("95.00"))
        # Cost per active user: $475 / 20 = $23.75
        self.assertEqual(seat_stats["cost_per_active_user"], Decimal("23.75"))

    def test_copilot_seat_stats_empty_when_no_data(self):
        """Test that view returns empty state when no snapshots exist."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("seat_stats", response.context)
        self.assertIsNone(response.context["seat_stats"])

    def test_copilot_seat_stats_requires_admin(self):
        """Test that non-admin users get 404 (forbidden)."""
        self._enable_copilot_flags()
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        # @team_admin_required returns 404 for non-admins
        self.assertEqual(response.status_code, 404)

    def test_copilot_seat_stats_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        self._enable_copilot_flags()

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_copilot_seat_stats_requires_team_membership(self):
        """Test that non-team members get 404."""
        self._enable_copilot_flags()
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 404)


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotSeatStatsFeatureFlags(TestCase):
    """Tests for Copilot seat stats view feature flag requirements."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create feature flags
        Flag.objects.get_or_create(name="copilot_enabled")
        Flag.objects.get_or_create(name="copilot_seat_utilization")

    def test_respects_copilot_enabled_flag(self):
        """Test that view returns empty when copilot_enabled flag is off."""
        # Only enable seat_utilization, not copilot_enabled
        copilot_seat = Flag.objects.get(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()  # Flush waffle cache

        self.client.force_login(self.admin_user)

        # Create snapshot data
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        # Should return None/empty when master flag is off
        self.assertIsNone(response.context["seat_stats"])

    def test_respects_copilot_seat_utilization_flag(self):
        """Test that view returns empty when copilot_seat_utilization flag is off."""
        # Only enable copilot_enabled, not seat_utilization
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()  # Flush waffle cache

        self.client.force_login(self.admin_user)

        # Create snapshot data
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        # Should return None/empty when sub-flag is off
        self.assertIsNone(response.context["seat_stats"])

    def test_returns_data_when_both_flags_enabled(self):
        """Test that view returns data when both feature flags are enabled."""
        # Enable both flags
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()  # Flush waffle cache
        copilot_seat = Flag.objects.get(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()  # Flush waffle cache

        self.client.force_login(self.admin_user)

        # Create snapshot data
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["seat_stats"])
        self.assertEqual(response.context["seat_stats"]["total_seats"], 25)


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotSeatStatsTemplate(TestCase):
    """Tests for Copilot seat stats view template rendering."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create and enable feature flags
        copilot_enabled, _ = Flag.objects.get_or_create(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()  # Flush waffle cache
        copilot_seat, _ = Flag.objects.get_or_create(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()  # Flush waffle cache

    def test_renders_correct_template(self):
        """Test that view renders the correct template partial."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/copilot_seat_stats_card.html")

    def test_context_has_seat_stats_key(self):
        """Test that context always has seat_stats key."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("seat_stats", response.context)


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotSeatStatsCalculations(TestCase):
    """Tests for Copilot seat stats calculations."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create and enable feature flags
        copilot_enabled, _ = Flag.objects.get_or_create(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()  # Flush waffle cache
        copilot_seat, _ = Flag.objects.get_or_create(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()  # Flush waffle cache

    def test_handles_zero_active_users(self):
        """Test that cost_per_active_user is None when no active users."""
        self.client.force_login(self.admin_user)

        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            total_seats=10,
            active_this_cycle=0,
            inactive_this_cycle=10,
        )

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        seat_stats = response.context["seat_stats"]
        self.assertIsNone(seat_stats["cost_per_active_user"])
        self.assertEqual(seat_stats["utilization_rate"], Decimal("0.00"))

    def test_handles_full_utilization(self):
        """Test correct calculations when all seats are active."""
        self.client.force_login(self.admin_user)

        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            total_seats=10,
            active_this_cycle=10,
            inactive_this_cycle=0,
        )

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        seat_stats = response.context["seat_stats"]
        self.assertEqual(seat_stats["utilization_rate"], Decimal("100.00"))
        self.assertEqual(seat_stats["wasted_spend"], Decimal("0.00"))
        # $190 / 10 = $19 per active user
        self.assertEqual(seat_stats["cost_per_active_user"], Decimal("19.00"))

    def test_returns_team_scoped_data_only(self):
        """Test that only data for the current team is returned."""
        self.client.force_login(self.admin_user)

        # Create snapshot for current team
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        # Create snapshot for another team
        other_team = TeamFactory()
        CopilotSeatSnapshot.objects.create(
            team=other_team,
            date=date(2024, 1, 15),
            total_seats=100,
            active_this_cycle=80,
            inactive_this_cycle=20,
        )

        response = self.client.get(reverse("metrics:cards_copilot_seats"))

        self.assertEqual(response.status_code, 200)
        seat_stats = response.context["seat_stats"]
        # Should return current team's data, not other team's
        self.assertEqual(seat_stats["total_seats"], 25)
        self.assertEqual(seat_stats["active_seats"], 20)
