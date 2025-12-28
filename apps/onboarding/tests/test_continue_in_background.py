"""Tests for "Continue in Background" button on sync progress page.

TDD RED Phase: These tests verify that the sync progress page displays
a "Continue to Jira" button that allows users to proceed with onboarding
while the sync continues in the background.

Current behavior:
- User must wait for sync to complete before seeing the "Continue" button
- The only link to connect_jira is in the hidden sync-complete section

Desired behavior:
- "Continue to Jira" button is visible in the sync-actions section regardless of sync status
- Button links to the Jira connection step
- Button has secondary styling to indicate it's an optional action
- Sync continues in the background while user proceeds
"""

import re

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class TestContinueInBackgroundButton(TestCase):
    """Tests for the Continue in Background functionality on sync progress page."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(
            username="sync_bg_test@example.com",
            email="sync_bg_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.repo = TrackedRepositoryFactory(team=self.team, integration=self.integration)
        self.client.login(username="sync_bg_test@example.com", password="testpassword123")

    def test_sync_progress_page_has_continue_to_jira_button(self):
        """Test that sync progress page displays a 'Continue to Jira' button.

        The button should be visible immediately, not hidden until sync completes.
        This allows users to proceed with onboarding while sync runs in background.
        """
        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # The button should contain text about continuing to Jira
        self.assertContains(response, "Continue to Jira")

    def test_continue_button_in_sync_actions_section(self):
        """Test that the Continue button is in the sync-actions section (always visible).

        The button must be in the sync-actions div, NOT in the sync-complete div
        which is hidden until sync completes.
        """
        response = self.client.get(reverse("onboarding:sync_progress"))
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)

        # Extract the sync-actions section content
        sync_actions_match = re.search(
            r'id="sync-actions"[^>]*>(.*?)</div>',
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(sync_actions_match, "sync-actions section not found")

        sync_actions_content = sync_actions_match.group(1)

        # The sync-actions section should contain a link to connect_jira
        expected_url = reverse("onboarding:connect_jira")
        self.assertIn(
            expected_url,
            sync_actions_content,
            f"Link to {expected_url} not found in sync-actions section",
        )

    def test_continue_button_has_secondary_styling(self):
        """Test that the Continue button has secondary/outline styling.

        The button should be visually distinct from the main sync UI
        to indicate it's an optional "continue in background" action.
        """
        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Should have secondary button styling (not primary)
        # Look for the button class pattern used in the codebase
        self.assertContains(response, "app-btn-secondary")

    def test_continue_button_links_to_connect_jira_in_visible_section(self):
        """Test that a visible Continue button links to the Jira connection page.

        There should be a link to connect_jira that is NOT in a hidden section.
        The sync-actions section is visible by default (no 'hidden' class).
        """
        response = self.client.get(reverse("onboarding:sync_progress"))
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)

        # Find all anchor tags with href to connect_jira
        expected_url = reverse("onboarding:connect_jira")
        link_pattern = rf'<a[^>]*href="{re.escape(expected_url)}"[^>]*>.*?</a>'
        links = re.findall(link_pattern, content, re.DOTALL)

        # There should be at least 2 links: one in sync-actions (visible) and one in sync-complete (hidden)
        # For the feature to work, we need at least one link outside the hidden section
        self.assertGreaterEqual(
            len(links),
            2,
            f"Expected at least 2 links to connect_jira (one visible, one in completion section), found {len(links)}",
        )

    def test_sync_actions_section_contains_continue_button_with_jira_text(self):
        """Test that the always-visible section has a button/link mentioning Jira.

        The sync-actions div should contain a clickable element that:
        1. Links to connect_jira
        2. Contains text indicating it goes to Jira setup
        """
        response = self.client.get(reverse("onboarding:sync_progress"))
        content = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)

        # Extract the sync-actions section
        sync_actions_match = re.search(
            r'<div[^>]*id="sync-actions"[^>]*>(.*?)</div>\s*(?=<div|$)',
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(sync_actions_match, "sync-actions section not found")

        sync_actions_content = sync_actions_match.group(1)

        # Should contain "Jira" text (case-insensitive)
        self.assertRegex(
            sync_actions_content,
            r"[Jj]ira",
            "sync-actions section should mention Jira",
        )
