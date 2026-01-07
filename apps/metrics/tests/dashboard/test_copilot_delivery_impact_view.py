"""Tests for Copilot Delivery Impact Card view.

Tests verify the HTMX endpoint for Copilot vs Non-Copilot PR comparison,
including admin-only access, feature flag requirements, and date range handling.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.integrations.factories import UserFactory
from apps.metrics.factories import (
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.teams.models import Flag
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER

# Use DummyCache in tests to avoid cache pollution between parallel workers.
# Waffle caches flag-team associations, which can cause flaky tests when
# different workers have different database states but share the same cache.
_DUMMY_CACHE_SETTINGS = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotDeliveryImpactView(TestCase):
    """Tests for copilot_delivery_impact_card view."""

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
        Flag.objects.get_or_create(name="copilot_delivery_impact")

    def _enable_copilot_flags(self):
        """Enable both Copilot feature flags for the team."""
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()  # Flush waffle cache
        copilot_delivery = Flag.objects.get(name="copilot_delivery_impact")
        copilot_delivery.teams.add(self.team)
        copilot_delivery.save()  # Flush waffle cache

    def _create_pr_data(self):
        """Create test PR data with Copilot and non-Copilot users."""
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # Create PRs for both users
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=15),
                merged_at=timezone.now() - timedelta(days=14),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=15),
                merged_at=timezone.now() - timedelta(days=14),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        return copilot_user, non_copilot_user

    def test_returns_comparison_data_with_correct_structure(self):
        """Test that view returns comparison data from service with correct structure."""
        self._enable_copilot_flags()
        self._create_pr_data()
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("comparison_data", response.context)

        comparison_data = response.context["comparison_data"]
        self.assertIsNotNone(comparison_data)

        # Verify structure
        self.assertIn("copilot_prs", comparison_data)
        self.assertIn("non_copilot_prs", comparison_data)
        self.assertIn("improvement", comparison_data)
        self.assertIn("sample_sufficient", comparison_data)

        # Verify copilot_prs sub-structure
        self.assertIn("count", comparison_data["copilot_prs"])
        self.assertIn("avg_cycle_time_hours", comparison_data["copilot_prs"])
        self.assertIn("avg_review_time_hours", comparison_data["copilot_prs"])

    def test_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        self._enable_copilot_flags()

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requires_admin_role(self):
        """Test that non-admin users get 404 (forbidden)."""
        self._enable_copilot_flags()
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        # @team_admin_required returns 404 for non-admins
        self.assertEqual(response.status_code, 404)

    def test_requires_team_membership(self):
        """Test that non-team members get 404."""
        self._enable_copilot_flags()
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        self.assertEqual(response.status_code, 404)

    def test_respects_copilot_delivery_impact_flag(self):
        """Test that view returns None when copilot_delivery_impact flag is off."""
        # Only enable copilot_enabled, not copilot_delivery_impact
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()

        self._create_pr_data()
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("comparison_data", response.context)
        # Should return None when sub-flag is off
        self.assertIsNone(response.context["comparison_data"])

    def test_respects_copilot_enabled_master_flag(self):
        """Test that view returns None when copilot_enabled master flag is off."""
        # Only enable copilot_delivery_impact, not copilot_enabled master flag
        copilot_delivery = Flag.objects.get(name="copilot_delivery_impact")
        copilot_delivery.teams.add(self.team)
        copilot_delivery.save()

        self._create_pr_data()
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        self.assertEqual(response.status_code, 200)
        # Should return None when master flag is off
        self.assertIsNone(response.context["comparison_data"])

    def test_uses_days_parameter_from_request(self):
        """Test that view honors days query param for date range."""
        self._enable_copilot_flags()
        self._create_pr_data()
        self.client.force_login(self.admin_user)

        # Request with specific days parameter
        response = self.client.get(
            reverse("metrics:cards_copilot_delivery"),
            {"days": "60"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("comparison_data", response.context)

    def test_defaults_to_last_30_days(self):
        """Test that view defaults to last 30 days when no date params provided."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        # Create PRs within last 30 days
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # PRs within last 30 days (should be included)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=10),
                merged_at=timezone.now() - timedelta(days=9),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=10),
                merged_at=timezone.now() - timedelta(days=9),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # PRs from 60 days ago (should NOT be included with default 30-day range)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=60),
                merged_at=timezone.now() - timedelta(days=59),
                cycle_time_hours=Decimal("100.00"),  # Different to verify exclusion
                review_time_hours=Decimal("50.00"),
            )

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        self.assertEqual(response.status_code, 200)
        comparison_data = response.context["comparison_data"]
        self.assertIsNotNone(comparison_data)

        # Should only include recent PRs (10 each)
        self.assertEqual(comparison_data["copilot_prs"]["count"], 10)
        self.assertEqual(comparison_data["non_copilot_prs"]["count"], 10)

    def test_renders_correct_template(self):
        """Test that view renders the correct template partial."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/partials/copilot_delivery_impact_card.html")


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotDeliveryImpactTeamIsolation(TestCase):
    """Tests for Copilot delivery impact view team isolation."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.other_team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create and enable feature flags for both teams
        copilot_enabled, _ = Flag.objects.get_or_create(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.teams.add(self.other_team)
        copilot_enabled.save()
        copilot_delivery, _ = Flag.objects.get_or_create(name="copilot_delivery_impact")
        copilot_delivery.teams.add(self.team)
        copilot_delivery.teams.add(self.other_team)
        copilot_delivery.save()

    def test_team_isolation_enforced(self):
        """Test that only data for the current team is returned."""
        self.client.force_login(self.admin_user)

        # Create data for current team
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=10),
                merged_at=timezone.now() - timedelta(days=9),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=10),
                merged_at=timezone.now() - timedelta(days=9),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Create data for another team (should NOT be returned)
        other_copilot_user = TeamMemberFactory(
            team=self.other_team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        other_non_copilot_user = TeamMemberFactory(
            team=self.other_team,
            copilot_last_activity_at=None,
        )

        for _ in range(15):
            PullRequestFactory(
                team=self.other_team,
                author=other_copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=10),
                merged_at=timezone.now() - timedelta(days=9),
                cycle_time_hours=Decimal("4.00"),  # Different values
                review_time_hours=Decimal("1.00"),
            )
            PullRequestFactory(
                team=self.other_team,
                author=other_non_copilot_user,
                state="merged",
                pr_created_at=timezone.now() - timedelta(days=10),
                merged_at=timezone.now() - timedelta(days=9),
                cycle_time_hours=Decimal("48.00"),  # Different values
                review_time_hours=Decimal("8.00"),
            )

        response = self.client.get(reverse("metrics:cards_copilot_delivery"))

        self.assertEqual(response.status_code, 200)
        comparison_data = response.context["comparison_data"]

        # Should only return current team's data (10 each, not 15)
        self.assertEqual(comparison_data["copilot_prs"]["count"], 10)
        self.assertEqual(comparison_data["non_copilot_prs"]["count"], 10)

        # Verify our team's averages (not other team's)
        self.assertEqual(comparison_data["copilot_prs"]["avg_cycle_time_hours"], Decimal("8.00"))
        self.assertEqual(comparison_data["non_copilot_prs"]["avg_cycle_time_hours"], Decimal("24.00"))
