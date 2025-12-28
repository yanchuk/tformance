"""
Tests for integrations app URL configuration.

This test file verifies that URL routing is properly configured for the integrations app,
including team-scoped URLs under /app/integrations/.
"""

from django.test import TestCase
from django.urls import resolve, reverse


class TestIntegrationsURLs(TestCase):
    """Tests for integrations URL patterns and resolution."""

    def test_integrations_home_url_resolves(self):
        """Test that integrations home URL resolves correctly."""
        url = reverse("integrations:integrations_home")
        self.assertEqual(url, "/app/integrations/")

    def test_integrations_home_url_resolves_to_correct_view(self):
        """Test that integrations home URL resolves to integrations_home view."""
        url = reverse("integrations:integrations_home")
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:integrations_home")

    def test_github_connect_url_resolves(self):
        """Test that GitHub connect URL resolves correctly."""
        url = reverse("integrations:github_connect")
        self.assertEqual(url, "/app/integrations/github/connect/")

    def test_github_connect_url_resolves_to_correct_view(self):
        """Test that GitHub connect URL resolves to github_connect view."""
        url = reverse("integrations:github_connect")
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:github_connect")

    def test_github_disconnect_url_resolves(self):
        """Test that GitHub disconnect URL resolves correctly."""
        url = reverse("integrations:github_disconnect")
        self.assertEqual(url, "/app/integrations/github/disconnect/")

    def test_github_disconnect_url_resolves_to_correct_view(self):
        """Test that GitHub disconnect URL resolves to github_disconnect view."""
        url = reverse("integrations:github_disconnect")
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:github_disconnect")

    def test_github_select_org_url_resolves(self):
        """Test that GitHub select org URL resolves correctly."""
        url = reverse("integrations:github_select_org")
        self.assertEqual(url, "/app/integrations/github/select-org/")

    def test_github_select_org_url_resolves_to_correct_view(self):
        """Test that GitHub select org URL resolves to github_select_org view."""
        url = reverse("integrations:github_select_org")
        resolved = resolve(url)
        self.assertEqual(resolved.view_name, "integrations:github_select_org")

    def test_all_urls_use_app_prefix(self):
        """Test that all team-scoped URLs use /app/ prefix."""
        url_names = [
            "integrations_home",
            "github_connect",
            "github_disconnect",
            "github_select_org",
        ]

        for url_name in url_names:
            with self.subTest(url_name=url_name):
                url = reverse(f"integrations:{url_name}")
                self.assertTrue(url.startswith("/app/"))
                self.assertIn("/integrations/", url)
