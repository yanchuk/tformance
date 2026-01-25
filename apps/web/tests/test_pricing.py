"""Tests for pricing page feature.

Tests cover:
- Annual discount calculation (17% off = 2 months free)
- Pricing view returns 200 with correct context
- Calculator competitors data is passed to template
"""

from django.test import TestCase
from django.urls import reverse

from apps.web.compare_data import (
    OUR_PRICING,
    get_our_annual_cost,
    get_our_annual_cost_discounted,
)


class TestPricingDiscount(TestCase):
    """Tests for annual discount calculation (17% off)."""

    def test_get_our_annual_cost_discounted_starter_tier(self):
        """Starter tier annual cost = $99 * 10 months (17% discount)."""
        cost, tier = get_our_annual_cost_discounted(1)
        assert cost == 99 * 10  # $990/year (2 months free)
        assert tier == "Starter"

        cost, tier = get_our_annual_cost_discounted(10)
        assert cost == 99 * 10
        assert tier == "Starter"

    def test_get_our_annual_cost_discounted_team_tier(self):
        """Team tier annual cost = $299 * 10 months (17% discount)."""
        cost, tier = get_our_annual_cost_discounted(11)
        assert cost == 299 * 10  # $2,990/year
        assert tier == "Team"

        cost, tier = get_our_annual_cost_discounted(50)
        assert cost == 299 * 10
        assert tier == "Team"

    def test_get_our_annual_cost_discounted_business_tier(self):
        """Business tier annual cost = $699 * 10 months (17% discount)."""
        cost, tier = get_our_annual_cost_discounted(51)
        assert cost == 699 * 10  # $6,990/year
        assert tier == "Business"

        cost, tier = get_our_annual_cost_discounted(150)
        assert cost == 699 * 10
        assert tier == "Business"

    def test_get_our_annual_cost_discounted_enterprise_tier(self):
        """Enterprise tier returns None cost (custom pricing)."""
        cost, tier = get_our_annual_cost_discounted(151)
        assert cost is None
        assert tier == "Enterprise"

    def test_discount_is_approximately_17_percent(self):
        """Verify discount is ~17% (2 months free out of 12)."""
        full_cost, _ = get_our_annual_cost(50)  # Team tier: 299 * 12 = 3588
        discounted_cost, _ = get_our_annual_cost_discounted(50)  # 299 * 10 = 2990

        discount_percent = (full_cost - discounted_cost) / full_cost * 100
        # Should be ~16.67% (2/12 months free)
        assert 16 < discount_percent < 18


class TestPricingView(TestCase):
    """Tests for pricing page view."""

    def test_pricing_page_returns_200(self):
        """Pricing page returns 200 status code."""
        response = self.client.get(reverse("web:pricing"))
        assert response.status_code == 200

    def test_pricing_page_uses_correct_template(self):
        """Pricing page uses the correct template."""
        response = self.client.get(reverse("web:pricing"))
        self.assertTemplateUsed(response, "web/pricing.html")

    def test_pricing_page_has_our_pricing_in_context(self):
        """Pricing page includes our_pricing data."""
        response = self.client.get(reverse("web:pricing"))

        assert "our_pricing" in response.context
        assert response.context["our_pricing"] == OUR_PRICING

    def test_pricing_page_has_calculator_competitors_in_context(self):
        """Pricing page includes calculator_competitors for savings calculator."""
        response = self.client.get(reverse("web:pricing"))

        assert "calculator_competitors" in response.context
        calc = response.context["calculator_competitors"]
        # Should include LinearB and Jellyfish pricing data
        assert "linearb" in calc
        assert "jellyfish" in calc
        assert "price_per_seat" in calc["linearb"]
        assert "price_per_seat" in calc["jellyfish"]

    def test_pricing_page_has_seo_metadata(self):
        """Pricing page has SEO title and description."""
        response = self.client.get(reverse("web:pricing"))

        assert "page_title" in response.context
        assert "page_description" in response.context
        assert "Pricing" in response.context["page_title"]
        assert "flat" in response.context["page_description"].lower()

    def test_pricing_page_has_faqs_in_context(self):
        """Pricing page includes FAQ data."""
        response = self.client.get(reverse("web:pricing"))

        assert "pricing_faqs" in response.context
        faqs = response.context["pricing_faqs"]
        assert len(faqs) >= 4  # At least 4 FAQs as specified in plan
        # Each FAQ should have question and answer
        for faq in faqs:
            assert "question" in faq
            assert "answer" in faq
