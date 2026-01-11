"""Tests for Copilot card status rendering in integrations home.

TDD Phase: RED - These tests verify Copilot card shows correct UI
based on team.copilot_status field values.

Card states:
- disabled: "Connect Copilot" button
- connected: ✓ Connected badge + "Sync Now" button
- insufficient_licenses: ⚠️ Awaiting Data + explanation
- token_revoked: ❌ Reconnect Required
"""

import re

from django.test import Client, TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from apps.integrations.factories import GitHubIntegrationFactory, UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag
from apps.teams.roles import ROLE_ADMIN


def extract_copilot_card(content: str) -> str:
    """Extract the Copilot card section from the integrations page HTML.

    Uses regex to find the card between "GitHub Copilot" heading and
    "Google Workspace" heading, within the app-card divs.
    """
    # Find the section between GitHub Copilot card heading and Google Workspace card
    pattern = r"<h2[^>]*>GitHub Copilot</h2>.*?(?=<h2[^>]*>Google Workspace</h2>|$)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(0)
    return ""


class TestCopilotCardDisabledStatus(TestCase):
    """Tests for Copilot card when status is 'disabled' (default)."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(copilot_status="disabled")
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        # Create GitHub integration (required for Copilot)
        GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.admin)

        # Ensure Copilot flag exists and is enabled
        Flag.objects.get_or_create(name="integration_copilot_enabled")

    @override_flag("integration_copilot_enabled", active=True)
    def test_disabled_status_shows_connect_button(self):
        """Test that disabled status shows 'Connect Copilot' button."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Connect Copilot button
        self.assertIn("Connect Copilot", copilot_section)
        # Should NOT show Connected badge
        self.assertNotIn("app-status-pill-connected", copilot_section)

    @override_flag("integration_copilot_enabled", active=True)
    def test_disabled_status_does_not_show_sync_button(self):
        """Test that disabled status does NOT show Sync Now button."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should NOT show Sync Now button
        self.assertNotIn("Sync Now", copilot_section)


class TestCopilotCardConnectedStatus(TestCase):
    """Tests for Copilot card when status is 'connected'."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(copilot_status="connected")
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.admin)

        Flag.objects.get_or_create(name="integration_copilot_enabled")

    @override_flag("integration_copilot_enabled", active=True)
    def test_connected_status_shows_connected_badge(self):
        """Test that connected status shows 'Connected' badge."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Connected badge
        self.assertIn("Connected", copilot_section)
        self.assertIn("app-status-pill-connected", copilot_section)

    @override_flag("integration_copilot_enabled", active=True)
    def test_connected_status_shows_sync_button(self):
        """Test that connected status shows 'Sync Now' button."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Sync Now button
        self.assertIn("Sync Now", copilot_section)

    @override_flag("integration_copilot_enabled", active=True)
    def test_connected_status_shows_disconnect_button(self):
        """Test that connected status shows 'Disconnect' button."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Disconnect button
        self.assertIn("Disconnect", copilot_section)


class TestCopilotCardInsufficientLicensesStatus(TestCase):
    """Tests for Copilot card when status is 'insufficient_licenses'."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(copilot_status="insufficient_licenses")
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.admin)

        Flag.objects.get_or_create(name="integration_copilot_enabled")

    @override_flag("integration_copilot_enabled", active=True)
    def test_insufficient_licenses_shows_awaiting_data_status(self):
        """Test that insufficient_licenses shows 'Awaiting Data' status."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Awaiting Data status
        self.assertIn("Awaiting Data", copilot_section)

    @override_flag("integration_copilot_enabled", active=True)
    def test_insufficient_licenses_shows_license_requirement_message(self):
        """Test that insufficient_licenses explains the 5+ license requirement."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should explain the license requirement
        self.assertIn("5", copilot_section)  # Mentions 5 licenses
        self.assertIn("license", copilot_section.lower())

    @override_flag("integration_copilot_enabled", active=True)
    def test_insufficient_licenses_shows_check_again_button(self):
        """Test that insufficient_licenses shows 'Check Again' button."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Check Again button
        self.assertIn("Check Again", copilot_section)


class TestCopilotCardTokenRevokedStatus(TestCase):
    """Tests for Copilot card when status is 'token_revoked'."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(copilot_status="token_revoked")
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.admin)

        Flag.objects.get_or_create(name="integration_copilot_enabled")

    @override_flag("integration_copilot_enabled", active=True)
    def test_token_revoked_shows_reconnect_status(self):
        """Test that token_revoked shows reconnection required status."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Reconnection Required status
        self.assertIn("Reconnect", copilot_section)

    @override_flag("integration_copilot_enabled", active=True)
    def test_token_revoked_shows_reconnect_button(self):
        """Test that token_revoked shows 'Reconnect GitHub' button/link."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Reconnect GitHub button/link
        self.assertIn("Reconnect", copilot_section)


class TestCopilotCardWithoutGitHub(TestCase):
    """Tests for Copilot card when GitHub is not connected."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(copilot_status="disabled")
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        # NO GitHub integration
        self.client = Client()
        self.client.force_login(self.admin)

        Flag.objects.get_or_create(name="integration_copilot_enabled")

    @override_flag("integration_copilot_enabled", active=True)
    def test_no_github_shows_connect_github_first_message(self):
        """Test that without GitHub, Copilot card shows connect GitHub first message."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should explain GitHub needs to be connected first
        self.assertIn("GitHub", copilot_section)


class TestCopilotCardFlagDisabled(TestCase):
    """Tests for Copilot card when feature flag is disabled."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.admin)

        Flag.objects.get_or_create(name="integration_copilot_enabled")

    @override_flag("integration_copilot_enabled", active=False)
    def test_flag_disabled_shows_coming_soon(self):
        """Test that when flag is off, Copilot shows Coming Soon."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show Coming Soon
        self.assertIn("Coming Soon", copilot_section)

    @override_flag("integration_copilot_enabled", active=False)
    def test_flag_disabled_shows_interested_button(self):
        """Test that when flag is off, Copilot shows I'm Interested button."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        copilot_section = extract_copilot_card(content)

        # Should show I'm Interested button
        self.assertIn("I'm Interested", copilot_section)


class TestCopilotActivationEndpoint(TestCase):
    """Tests for the Copilot activation endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(copilot_status="disabled")
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.admin)

        Flag.objects.get_or_create(name="integration_copilot_enabled")

    @override_flag("integration_copilot_enabled", active=True)
    def test_activate_copilot_endpoint_exists(self):
        """Test that the activate Copilot endpoint exists."""
        url = reverse("integrations:activate_copilot")
        response = self.client.post(url)

        # Should not return 404 (endpoint exists)
        self.assertNotEqual(response.status_code, 404)

    @override_flag("integration_copilot_enabled", active=True)
    def test_activate_copilot_sets_status_to_connected(self):
        """Test that activating Copilot sets team.copilot_status to 'connected'."""
        url = reverse("integrations:activate_copilot")
        response = self.client.post(url)

        # Should redirect back to integrations home
        self.assertEqual(response.status_code, 302)

        # Reload team from database
        self.team.refresh_from_db()
        self.assertEqual(self.team.copilot_status, "connected")

    @override_flag("integration_copilot_enabled", active=True)
    def test_activate_copilot_shows_success_message(self):
        """Test that activating Copilot shows a success message."""
        url = reverse("integrations:activate_copilot")
        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, 200)
        # Check for success message in messages
        messages = list(response.context["messages"])
        self.assertTrue(any("Copilot" in str(m) for m in messages))


class TestCopilotDeactivationEndpoint(TestCase):
    """Tests for the Copilot deactivation (disconnect) endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(copilot_status="connected")
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.force_login(self.admin)

        Flag.objects.get_or_create(name="integration_copilot_enabled")

    @override_flag("integration_copilot_enabled", active=True)
    def test_deactivate_copilot_endpoint_exists(self):
        """Test that the deactivate Copilot endpoint exists."""
        url = reverse("integrations:deactivate_copilot")
        response = self.client.post(url)

        # Should not return 404 (endpoint exists)
        self.assertNotEqual(response.status_code, 404)

    @override_flag("integration_copilot_enabled", active=True)
    def test_deactivate_copilot_sets_status_to_disabled(self):
        """Test that deactivating Copilot sets team.copilot_status to 'disabled'."""
        url = reverse("integrations:deactivate_copilot")
        response = self.client.post(url)

        # Should redirect back to integrations home
        self.assertEqual(response.status_code, 302)

        # Reload team from database
        self.team.refresh_from_db()
        self.assertEqual(self.team.copilot_status, "disabled")
