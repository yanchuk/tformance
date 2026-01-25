"""Tests for the Features page."""

from django.test import TestCase
from django.urls import reverse


class FeaturesPageTests(TestCase):
    """Test cases for the /features/ page."""

    def test_features_page_returns_200(self):
        """Features page should return HTTP 200."""
        response = self.client.get(reverse("web:features"))
        self.assertEqual(response.status_code, 200)

    def test_features_page_has_seo_metadata(self):
        """Features page should have SEO title."""
        response = self.client.get(reverse("web:features"))
        self.assertContains(response, "Platform Features")

    def test_features_page_has_ai_impact_anchor(self):
        """Features page should have #ai-impact anchor section."""
        response = self.client.get(reverse("web:features"))
        self.assertContains(response, 'id="ai-impact"')

    def test_features_page_has_team_performance_anchor(self):
        """Features page should have #team-performance anchor section."""
        response = self.client.get(reverse("web:features"))
        self.assertContains(response, 'id="team-performance"')

    def test_features_page_has_integrations_anchor(self):
        """Features page should have #integrations anchor section."""
        response = self.client.get(reverse("web:features"))
        self.assertContains(response, 'id="integrations"')

    def test_features_page_has_cta(self):
        """Features page should include a CTA section."""
        response = self.client.get(reverse("web:features"))
        # CTA terminal has "Start Free" button
        self.assertContains(response, "Start Free")
