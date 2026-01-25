"""
Tests for Copilot graceful degradation (Phase 6).

This module tests that:
1. Non-Copilot users (flag disabled) see no Copilot UI
2. Empty states are shown when Copilot is connected but no data exists
3. Partial data scenarios are handled gracefully

These tests ensure the Analytics dashboard handles Copilot features
gracefully based on feature flags and data availability.

Note: Tests use analytics_ai_adoption page where Copilot features are displayed.
The legacy cto_overview URL now redirects to analytics_overview.
"""

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import AIUsageDailyFactory, PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.teams.models import Flag
from apps.teams.roles import ROLE_ADMIN

# Use DummyCache in tests to avoid cache pollution between parallel workers.
# Waffle caches flag-team associations, which can cause flaky tests when
# different workers have different database states but share the same cache.
_DUMMY_CACHE_SETTINGS = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotGracefulDegradationFlagGating(TestCase):
    """Tests for Copilot UI visibility based on feature flags.

    Task 6.1: Verify that Analytics AI Adoption page properly hides/shows Copilot
    sections based on the copilot_enabled and copilot_seat_utilization flags.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        # Use status="complete" to ensure dashboard is accessible
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Ensure Copilot feature flags exist (required for flag checks to work)
        Flag.objects.get_or_create(name="copilot_enabled", defaults={"everyone": False})
        Flag.objects.get_or_create(name="copilot_seat_utilization", defaults={"everyone": False})

    def test_ai_adoption_hides_copilot_seat_section_when_flag_disabled(self):
        """Test that AI Adoption page hides Copilot seat utilization when flag is disabled.

        When copilot_seat_utilization flag is not enabled for the team,
        the Seat Utilization & ROI section should not appear in the template.
        """
        # Arrange - flags are disabled by default (setUp)
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert
        self.assertEqual(response.status_code, 200)
        # The copilot_seat_utilization_enabled context should be False
        self.assertFalse(response.context.get("copilot_seat_utilization_enabled", False))
        # The Seat Utilization section should NOT be rendered
        self.assertNotContains(response, "Seat Utilization")
        self.assertNotContains(response, "copilot-seats-container")

    def test_ai_adoption_shows_copilot_seat_section_when_flag_enabled(self):
        """Test that AI Adoption page shows Copilot seat utilization when flag is enabled.

        When both copilot_enabled and copilot_seat_utilization flags are enabled,
        the Seat Utilization & ROI section should appear in the template.
        """
        # Arrange - enable both Copilot flags for the team
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()

        copilot_seat = Flag.objects.get(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()

        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert
        self.assertEqual(response.status_code, 200)
        # The copilot_seat_utilization_enabled context should be True
        self.assertTrue(response.context.get("copilot_seat_utilization_enabled", False))
        # The Seat Utilization section should be rendered
        self.assertContains(response, "Seat Utilization")
        self.assertContains(response, "copilot-seats-container")

    def test_ai_adoption_context_includes_copilot_flag_status(self):
        """Test that AI Adoption page includes copilot_seat_utilization_enabled in context."""
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        self.assertEqual(response.status_code, 200)
        # Context should include the flag status key
        self.assertIn("copilot_seat_utilization_enabled", response.context)

    def test_existing_ai_adoption_section_renders_without_copilot_flags(self):
        """Test that AI Adoption sections (pattern-based) still render when Copilot flags are off.

        Task 6.1: Existing AI detection still works (pattern-based) even when
        Copilot features are disabled. The ai_adoption page shows AI Adoption Trend
        and AI Tools Breakdown charts which use PR-based AI detection.
        """
        # Arrange - Copilot flags are disabled, but AI adoption sections should work
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert
        self.assertEqual(response.status_code, 200)
        # AI Adoption sections should always be present (from PR content analysis)
        self.assertContains(response, "AI Adoption Trend")
        self.assertContains(response, "ai-adoption-container")

    def test_ai_adoption_no_errors_when_all_copilot_flags_disabled(self):
        """Test that AI Adoption page renders without errors when all Copilot flags are off.

        This ensures no broken UI or errors when Copilot features are disabled.
        """
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert - page renders successfully
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/analytics/ai_adoption.html")


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotEmptyStates(TestCase):
    """Tests for empty states when Copilot is connected but no data exists.

    Task 6.2: Verify proper empty state handling for various Copilot data scenarios.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create and enable Copilot feature flags
        Flag.objects.get_or_create(name="copilot_enabled", defaults={"everyone": False})
        Flag.objects.get_or_create(name="copilot_seat_utilization", defaults={"everyone": False})

        # Enable flags for the team
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()

        copilot_seat = Flag.objects.get(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()

    def test_copilot_metrics_card_shows_empty_state_message(self):
        """Test that Copilot metrics card shows empty state message when no data exists.

        When Copilot is connected but no metrics data exists,
        the card should show a helpful empty state message:
        "No Copilot data available"
        """
        # Arrange - Copilot flags enabled but no AIUsageDaily data
        self.client.force_login(self.admin_user)

        # Act - request the copilot metrics cards endpoint
        response = self.client.get(reverse("metrics:cards_copilot"), {"days": "30"})

        # Assert - should return 200 with empty state message
        self.assertEqual(response.status_code, 200)
        # Should show the specific empty state message from template
        self.assertContains(response, "No Copilot data available")

    def test_copilot_seats_card_shows_empty_state_message(self):
        """Test that Copilot seats card shows empty state message when no data exists.

        When copilot_seat_utilization is enabled but no CopilotSeatSnapshot exists,
        the card should show:
        "No seat utilization data available"
        """
        # Arrange - Copilot flags enabled but no seat snapshot data
        self.client.force_login(self.admin_user)

        # Act - request the copilot seats endpoint
        response = self.client.get(reverse("metrics:cards_copilot_seats"), {"days": "30"})

        # Assert - should return 200 with empty state message
        self.assertEqual(response.status_code, 200)
        # Should show the specific empty state message from template
        self.assertContains(response, "No seat utilization data available")

    def test_copilot_trend_chart_handles_no_data(self):
        """Test that Copilot trend chart handles empty data gracefully."""
        # Arrange
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:chart_copilot_trend"), {"days": "30"})

        # Assert
        self.assertEqual(response.status_code, 200)

    def test_copilot_members_table_handles_no_data(self):
        """Test that Copilot members table handles empty data gracefully."""
        # Arrange
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:table_copilot_members"), {"days": "30"})

        # Assert
        self.assertEqual(response.status_code, 200)


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotPartialData(TestCase):
    """Tests for partial data scenarios.

    Task 6.3: Verify that the dashboard handles partial Copilot data gracefully,
    showing what's available without breaking.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create and enable Copilot feature flags
        Flag.objects.get_or_create(name="copilot_enabled", defaults={"everyone": False})
        Flag.objects.get_or_create(name="copilot_seat_utilization", defaults={"everyone": False})

        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()

        copilot_seat = Flag.objects.get(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()

    def test_shows_copilot_metrics_when_usage_data_exists_but_no_seats(self):
        """Test that Copilot metrics show when usage data exists but no seat data.

        Has metrics but no seats -> show metrics section.
        """
        # Arrange - Create Copilot usage data but no seat snapshot
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:cards_copilot"), {"days": "30"})

        # Assert - should return data successfully
        self.assertEqual(response.status_code, 200)

    def test_dashboard_renders_with_partial_copilot_data(self):
        """Test that AI Adoption page renders successfully with partial Copilot data.

        When only some Copilot data exists, the dashboard should still render
        without errors, showing available data.
        """
        # Arrange - Create only usage data, no seat snapshots
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            source="copilot",
            suggestions_shown=50,
            suggestions_accepted=20,
        )
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/analytics/ai_adoption.html")

    def test_delivery_section_renders_when_no_prs_exist(self):
        """Test that delivery section handles no PR data gracefully.

        When Copilot is connected but no PRs exist, the delivery impact
        section should show appropriate empty state.
        """
        # Arrange - No PRs created
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert - should render without errors
        self.assertEqual(response.status_code, 200)

    def test_dashboard_handles_mixed_data_availability(self):
        """Test dashboard handles mixed data availability across sections.

        Some sections may have data while others don't. The dashboard
        should render all sections appropriately.
        """
        # Arrange - Create PRs but no Copilot usage data
        PullRequestFactory(team=self.team, author=self.member, state="merged")
        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert
        self.assertEqual(response.status_code, 200)
        # AI Adoption sections should still show (uses PR data for pattern-based detection)
        self.assertContains(response, "AI Adoption Trend")


@override_settings(CACHES=_DUMMY_CACHE_SETTINGS)
class TestCopilotFlagHierarchy(TestCase):
    """Tests for Copilot feature flag hierarchy.

    The master flag (copilot_enabled) must be active for any sub-flag
    (copilot_seat_utilization, etc.) to be considered active.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(onboarding_pipeline_status="complete")
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

        # Create feature flags
        Flag.objects.get_or_create(name="copilot_enabled", defaults={"everyone": False})
        Flag.objects.get_or_create(name="copilot_seat_utilization", defaults={"everyone": False})

    def test_seat_section_hidden_when_master_flag_disabled_but_subflag_enabled(self):
        """Test that seat section is hidden when master flag is off but subflag is on.

        Even if copilot_seat_utilization is enabled for the team,
        if copilot_enabled master flag is off, the section should be hidden.
        """
        # Arrange - Enable only the sub-flag, not master flag
        copilot_seat = Flag.objects.get(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()
        # copilot_enabled is NOT enabled

        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert
        self.assertEqual(response.status_code, 200)
        # copilot_seat_utilization_enabled should be False (master flag check)
        self.assertFalse(response.context.get("copilot_seat_utilization_enabled", False))
        # Seat section should not appear
        self.assertNotContains(response, "copilot-seats-container")

    def test_seat_section_shown_when_both_flags_enabled(self):
        """Test that seat section shows when both master and sub flags are enabled."""
        # Arrange - Enable both flags
        copilot_enabled = Flag.objects.get(name="copilot_enabled")
        copilot_enabled.teams.add(self.team)
        copilot_enabled.save()

        copilot_seat = Flag.objects.get(name="copilot_seat_utilization")
        copilot_seat.teams.add(self.team)
        copilot_seat.save()

        self.client.force_login(self.admin_user)

        # Act
        response = self.client.get(reverse("metrics:analytics_ai_adoption"))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("copilot_seat_utilization_enabled", False))
        self.assertContains(response, "copilot-seats-container")
