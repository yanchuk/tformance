"""Tests for Copilot editor breakdown chart view.

Tests verify the HTMX endpoint for Copilot editor metrics,
including admin-only access, feature flag requirements, and data aggregation.
"""

from datetime import date
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.metrics.models import CopilotEditorDaily
from apps.teams.models import Flag
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER

# Use DummyCache in tests to avoid cache pollution between parallel workers.
# Waffle caches flag-team associations, which can cause flaky tests when
# different workers have different database states but share the same cache.
_DUMMY_CACHE_SETTINGS = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotEditorChartView(TestCase):
    """Tests for copilot_editor_chart view."""

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
        Flag.objects.get_or_create(name="copilot_language_insights")

    def _enable_copilot_flags(self):
        """Enable both Copilot feature flags for the team."""
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()  # Flush waffle cache
        copilot_language = Flag.objects.get(name="copilot_language_insights")
        copilot_language.teams.add(self.team)
        copilot_language.save()  # Flush waffle cache

    def test_copilot_editor_chart_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        self._enable_copilot_flags()

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_copilot_editor_chart_requires_admin(self):
        """Test that non-admin users get 404 (forbidden)."""
        self._enable_copilot_flags()
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        # @team_admin_required returns 404 for non-admins
        self.assertEqual(response.status_code, 404)

    def test_copilot_editor_chart_respects_flag(self):
        """Test that view returns empty data when feature flag is disabled."""
        # Only enable copilot_enabled, not copilot_language_insights
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()

        self.client.force_login(self.admin_user)

        # Create data that should not be returned
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=30,
            active_users=5,
        )

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("editors", response.context)
        # Should return empty list when flag is off
        self.assertEqual(response.context["editors"], [])

    def test_copilot_editor_chart_returns_editor_data(self):
        """Test that view returns aggregated editor data."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        # Create editor data
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=30,
            active_users=5,
        )
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="jetbrains",
            suggestions_shown=200,
            suggestions_accepted=80,
            active_users=10,
        )

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("editors", response.context)

        editors = response.context["editors"]
        self.assertEqual(len(editors), 2)

        # Find vscode in the results
        vscode_data = next((ed for ed in editors if ed["name"] == "vscode"), None)
        self.assertIsNotNone(vscode_data)
        self.assertEqual(vscode_data["suggestions_shown"], 100)
        self.assertEqual(vscode_data["suggestions_accepted"], 30)
        self.assertEqual(vscode_data["active_users"], 5)

    def test_copilot_editor_chart_calculates_acceptance_rate(self):
        """Test that acceptance rate is calculated correctly."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=30,  # 30% acceptance rate
            active_users=5,
        )

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        editors = response.context["editors"]
        self.assertEqual(len(editors), 1)

        vscode_data = editors[0]
        # 30/100 = 30%
        self.assertEqual(vscode_data["acceptance_rate"], Decimal("30.00"))

    def test_copilot_editor_chart_sorts_by_acceptance_rate(self):
        """Test that editors are sorted by acceptance rate descending."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        # Create editors with different acceptance rates
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=30,  # 30%
            active_users=5,
        )
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="jetbrains",
            suggestions_shown=100,
            suggestions_accepted=50,  # 50%
            active_users=10,
        )
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="neovim",
            suggestions_shown=100,
            suggestions_accepted=40,  # 40%
            active_users=3,
        )

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        editors = response.context["editors"]
        self.assertEqual(len(editors), 3)

        # Should be sorted by acceptance rate descending: jetbrains (50%), neovim (40%), vscode (30%)
        self.assertEqual(editors[0]["name"], "jetbrains")
        self.assertEqual(editors[1]["name"], "neovim")
        self.assertEqual(editors[2]["name"], "vscode")

    def test_copilot_editor_chart_empty_when_no_data(self):
        """Test that view returns empty list when no data exists."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("editors", response.context)
        self.assertEqual(response.context["editors"], [])

    def test_copilot_editor_chart_aggregates_across_dates(self):
        """Test that data is aggregated across multiple days."""
        self._enable_copilot_flags()
        self.client.force_login(self.admin_user)

        # Create data for same editor across multiple days
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 14),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=30,
            active_users=5,
        )
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=40,
            active_users=6,
        )
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 16),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=50,
            active_users=7,
        )

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        editors = response.context["editors"]
        self.assertEqual(len(editors), 1)

        vscode_data = editors[0]
        self.assertEqual(vscode_data["name"], "vscode")
        # Should be sum of all days: 300 shown, 120 accepted, 18 active_users
        self.assertEqual(vscode_data["suggestions_shown"], 300)
        self.assertEqual(vscode_data["suggestions_accepted"], 120)
        self.assertEqual(vscode_data["active_users"], 18)
        # Acceptance rate: 120/300 = 40%
        self.assertEqual(vscode_data["acceptance_rate"], Decimal("40.00"))


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotEditorChartFeatureFlags(TestCase):
    """Tests for Copilot editor chart view feature flag requirements."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create feature flags
        Flag.objects.get_or_create(name="copilot_enabled")
        Flag.objects.get_or_create(name="copilot_language_insights")

    def test_respects_copilot_enabled_flag(self):
        """Test that view returns empty when copilot_enabled flag is off."""
        # Only enable copilot_language_insights, not copilot_enabled
        copilot_language = Flag.objects.get(name="copilot_language_insights")
        copilot_language.teams.add(self.team)
        copilot_language.save()

        self.client.force_login(self.admin_user)

        # Create data
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=30,
            active_users=5,
        )

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        # Should return empty when master flag is off
        self.assertEqual(response.context["editors"], [])

    def test_returns_data_when_both_flags_enabled(self):
        """Test that view returns data when both feature flags are enabled."""
        # Enable both flags
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()
        copilot_language = Flag.objects.get(name="copilot_language_insights")
        copilot_language.teams.add(self.team)
        copilot_language.save()

        self.client.force_login(self.admin_user)

        # Create data
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=30,
            active_users=5,
        )

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["editors"]), 1)
        self.assertEqual(response.context["editors"][0]["name"], "vscode")


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotEditorChartTeamIsolation(TestCase):
    """Tests for Copilot editor chart view team isolation."""

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
        copilot_language, _ = Flag.objects.get_or_create(name="copilot_language_insights")
        copilot_language.teams.add(self.team)
        copilot_language.teams.add(self.other_team)
        copilot_language.save()

    def test_returns_team_scoped_data_only(self):
        """Test that only data for the current team is returned."""
        self.client.force_login(self.admin_user)

        # Create data for current team
        CopilotEditorDaily.objects.create(
            team=self.team,
            date=date(2024, 1, 15),
            editor="vscode",
            suggestions_shown=100,
            suggestions_accepted=30,
            active_users=5,
        )

        # Create data for another team (should not be returned)
        CopilotEditorDaily.objects.create(
            team=self.other_team,
            date=date(2024, 1, 15),
            editor="jetbrains",
            suggestions_shown=500,
            suggestions_accepted=200,
            active_users=20,
        )

        response = self.client.get(reverse("metrics:cards_copilot_editors"))

        self.assertEqual(response.status_code, 200)
        editors = response.context["editors"]
        # Should only return current team's data
        self.assertEqual(len(editors), 1)
        self.assertEqual(editors[0]["name"], "vscode")
        self.assertEqual(editors[0]["suggestions_shown"], 100)
