"""
Tests for integrations app URL configuration.

This test file verifies that URL routing is properly configured for the integrations app,
including team-scoped URLs under /a/{team_slug}/integrations/.
"""

from django.test import TestCase
from django.urls import resolve, reverse

from apps.integrations.factories import TeamFactory


class TestIntegrationsURLs(TestCase):
    """Tests for integrations URL patterns and resolution."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.team_slug = self.team.slug

    def test_integrations_home_url_resolves(self):
        """Test that integrations home URL resolves correctly."""
        url = reverse("integrations:integrations_home", kwargs={"team_slug": self.team_slug})
        self.assertEqual(url, f"/a/{self.team_slug}/integrations/")

    def test_integrations_home_url_resolves_to_correct_view(self):
        """Test that integrations home URL resolves to integrations_home view."""
        url = reverse("integrations:integrations_home", kwargs={"team_slug": self.team_slug})
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:integrations_home")

    def test_github_connect_url_resolves(self):
        """Test that GitHub connect URL resolves correctly."""
        url = reverse("integrations:github_connect", kwargs={"team_slug": self.team_slug})
        self.assertEqual(url, f"/a/{self.team_slug}/integrations/github/connect/")

    def test_github_connect_url_resolves_to_correct_view(self):
        """Test that GitHub connect URL resolves to github_connect view."""
        url = reverse("integrations:github_connect", kwargs={"team_slug": self.team_slug})
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:github_connect")

    def test_github_callback_url_resolves(self):
        """Test that GitHub callback URL resolves correctly."""
        url = reverse("integrations:github_callback", kwargs={"team_slug": self.team_slug})
        self.assertEqual(url, f"/a/{self.team_slug}/integrations/github/callback/")

    def test_github_callback_url_resolves_to_correct_view(self):
        """Test that GitHub callback URL resolves to github_callback view."""
        url = reverse("integrations:github_callback", kwargs={"team_slug": self.team_slug})
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:github_callback")

    def test_github_disconnect_url_resolves(self):
        """Test that GitHub disconnect URL resolves correctly."""
        url = reverse("integrations:github_disconnect", kwargs={"team_slug": self.team_slug})
        self.assertEqual(url, f"/a/{self.team_slug}/integrations/github/disconnect/")

    def test_github_disconnect_url_resolves_to_correct_view(self):
        """Test that GitHub disconnect URL resolves to github_disconnect view."""
        url = reverse("integrations:github_disconnect", kwargs={"team_slug": self.team_slug})
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:github_disconnect")

    def test_github_select_org_url_resolves(self):
        """Test that GitHub select org URL resolves correctly."""
        url = reverse("integrations:github_select_org", kwargs={"team_slug": self.team_slug})
        self.assertEqual(url, f"/a/{self.team_slug}/integrations/github/select-org/")

    def test_github_select_org_url_resolves_to_correct_view(self):
        """Test that GitHub select org URL resolves to github_select_org view."""
        url = reverse("integrations:github_select_org", kwargs={"team_slug": self.team_slug})
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:github_select_org")

    def test_url_patterns_require_team_slug_parameter(self):
        """Test that all URLs require team_slug parameter."""
        url_names = [
            "integrations_home",
            "github_connect",
            "github_callback",
            "github_disconnect",
            "github_select_org",
        ]

        from django.urls import NoReverseMatch

        for url_name in url_names:
            with self.subTest(url_name=url_name), self.assertRaises(NoReverseMatch):
                reverse(f"integrations:{url_name}")

    def test_all_urls_include_team_slug_in_path(self):
        """Test that all resolved URLs include the team slug in their path."""
        url_names = [
            "integrations_home",
            "github_connect",
            "github_callback",
            "github_disconnect",
            "github_select_org",
        ]

        for url_name in url_names:
            with self.subTest(url_name=url_name):
                url = reverse(f"integrations:{url_name}", kwargs={"team_slug": self.team_slug})
                self.assertIn(f"/a/{self.team_slug}/", url)
                self.assertIn("/integrations/", url)
