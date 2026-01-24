"""Tests for comparison pages feature.

Tests cover:
- Data functions (get_competitor, calculate_savings, etc.)
- Views (200 response, correct context, 404 on invalid slug)
- Sitemap (8 URLs generated: hub + 7 competitors)
"""

from django.test import TestCase
from django.urls import reverse

from apps.web.compare_data import (
    COMPETITORS,
    LIVE,
    NO,
    PLANNED,
    SOON,
    calculate_savings,
    get_all_competitors,
    get_competitor,
    get_competitors_by_priority,
    get_feature_status_display,
    get_our_annual_cost,
)
from apps.web.sitemaps import ComparisonSitemap


class TestCompareData(TestCase):
    """Tests for compare_data.py functions."""

    # =========================================================================
    # get_competitor()
    # =========================================================================

    def test_get_competitor_valid_slug(self):
        """get_competitor returns correct data for valid slug."""
        comp = get_competitor("linearb")

        assert comp is not None
        assert comp["name"] == "LinearB"
        assert comp["slug"] == "linearb"
        assert "their_strengths" in comp
        assert "our_advantages" in comp

    def test_get_competitor_invalid_slug(self):
        """get_competitor returns None for invalid slug."""
        assert get_competitor("nonexistent") is None
        assert get_competitor("") is None
        assert get_competitor("LINEARB") is None  # Case sensitive

    # =========================================================================
    # get_all_competitors()
    # =========================================================================

    def test_get_all_competitors(self):
        """get_all_competitors returns all 7 competitors."""
        competitors = get_all_competitors()

        assert len(competitors) == 7
        assert "linearb" in competitors
        assert "jellyfish" in competitors
        assert "swarmia" in competitors
        assert "span" in competitors
        assert "workweave" in competitors
        assert "mesmer" in competitors
        assert "nivara" in competitors

    # =========================================================================
    # get_competitors_by_priority()
    # =========================================================================

    def test_get_competitors_by_priority_high(self):
        """get_competitors_by_priority filters correctly for high priority."""
        high_priority = get_competitors_by_priority("high")

        slugs = [c["slug"] for c in high_priority]
        assert "linearb" in slugs
        assert "jellyfish" in slugs
        assert "swarmia" in slugs
        # Low/medium priority should not be included
        assert "mesmer" not in slugs
        assert "nivara" not in slugs

    def test_get_competitors_by_priority_medium(self):
        """get_competitors_by_priority filters correctly for medium priority."""
        medium_priority = get_competitors_by_priority("medium")

        slugs = [c["slug"] for c in medium_priority]
        assert "span" in slugs
        assert "workweave" in slugs

    def test_get_competitors_by_priority_low(self):
        """get_competitors_by_priority filters correctly for low priority."""
        low_priority = get_competitors_by_priority("low")

        slugs = [c["slug"] for c in low_priority]
        assert "mesmer" in slugs
        assert "nivara" in slugs

    # =========================================================================
    # get_our_annual_cost()
    # =========================================================================

    def test_get_our_annual_cost_starter_tier(self):
        """get_our_annual_cost returns Starter tier for 1-10 devs."""
        cost, tier = get_our_annual_cost(1)
        assert cost == 99 * 12
        assert tier == "Starter"

        cost, tier = get_our_annual_cost(10)
        assert cost == 99 * 12
        assert tier == "Starter"

    def test_get_our_annual_cost_team_tier(self):
        """get_our_annual_cost returns Team tier for 11-50 devs."""
        cost, tier = get_our_annual_cost(11)
        assert cost == 299 * 12
        assert tier == "Team"

        cost, tier = get_our_annual_cost(50)
        assert cost == 299 * 12
        assert tier == "Team"

    def test_get_our_annual_cost_business_tier(self):
        """get_our_annual_cost returns Business tier for 51-150 devs."""
        cost, tier = get_our_annual_cost(51)
        assert cost == 699 * 12
        assert tier == "Business"

        cost, tier = get_our_annual_cost(150)
        assert cost == 699 * 12
        assert tier == "Business"

    def test_get_our_annual_cost_enterprise_tier(self):
        """get_our_annual_cost returns Enterprise (None) for 151+ devs."""
        cost, tier = get_our_annual_cost(151)
        assert cost is None
        assert tier == "Enterprise"

        cost, tier = get_our_annual_cost(500)
        assert cost is None
        assert tier == "Enterprise"

    # =========================================================================
    # calculate_savings()
    # =========================================================================

    def test_calculate_savings_linearb_50_devs(self):
        """calculate_savings correctly computes savings vs LinearB for 50 devs."""
        savings = calculate_savings(50, "linearb")

        assert savings is not None
        # Our cost: Team tier = $299 * 12 = $3,588
        assert savings["our_cost"] == 299 * 12
        assert savings["our_tier"] == "Team"
        # Their cost: avg($35, $46) = $40.50 * 50 * 12 = $24,300
        assert savings["their_cost"] == 24300
        # Savings should be significant
        assert savings["savings"] > 20000
        assert savings["percent_savings"] > 80

    def test_calculate_savings_invalid_competitor(self):
        """calculate_savings returns None for invalid competitor."""
        assert calculate_savings(50, "nonexistent") is None

    def test_calculate_savings_enterprise_team_size(self):
        """calculate_savings returns None for enterprise team sizes."""
        # 200 devs = Enterprise tier = custom pricing
        assert calculate_savings(200, "linearb") is None

    def test_calculate_savings_custom_pricing_competitor(self):
        """calculate_savings returns None for competitors with custom pricing."""
        # Mesmer has custom pricing (no price_per_seat_low)
        assert calculate_savings(50, "mesmer") is None

    # =========================================================================
    # get_feature_status_display()
    # =========================================================================

    def test_get_feature_status_display_live(self):
        """get_feature_status_display returns correct format for LIVE features."""
        display = get_feature_status_display(LIVE)

        assert display["status"] == "live"
        assert display["icon"] == "✅"
        assert display["label"] == "Available"

    def test_get_feature_status_display_true(self):
        """get_feature_status_display treats True same as LIVE."""
        display = get_feature_status_display(True)

        assert display["status"] == "live"

    def test_get_feature_status_display_soon(self):
        """get_feature_status_display returns correct format for SOON features."""
        display = get_feature_status_display(SOON)

        assert display["status"] == "soon"
        assert display["icon"] == "🔜"
        assert display["label"] == "Coming Soon"

    def test_get_feature_status_display_planned(self):
        """get_feature_status_display returns correct format for PLANNED features."""
        display = get_feature_status_display(PLANNED)

        assert display["status"] == "planned"
        assert display["icon"] == "📋"
        assert display["label"] == "Planned"

    def test_get_feature_status_display_partial(self):
        """get_feature_status_display returns correct format for partial features."""
        display = get_feature_status_display("partial")

        assert display["status"] == "partial"
        assert display["icon"] == "◐"
        assert display["label"] == "Partial"

    def test_get_feature_status_display_no(self):
        """get_feature_status_display returns correct format for NO features."""
        display = get_feature_status_display(NO)

        assert display["status"] == "no"
        assert display["icon"] == "❌"
        assert display["label"] == "Not Available"


class TestCompareViews(TestCase):
    """Tests for comparison page views."""

    # =========================================================================
    # Hub Page
    # =========================================================================

    def test_compare_hub_returns_200(self):
        """Compare hub page returns 200."""
        response = self.client.get(reverse("web:compare"))

        assert response.status_code == 200

    def test_compare_hub_uses_correct_template(self):
        """Compare hub page uses the correct template."""
        response = self.client.get(reverse("web:compare"))

        self.assertTemplateUsed(response, "web/compare/hub.html")

    def test_compare_hub_has_competitors_in_context(self):
        """Compare hub page includes competitors in context."""
        response = self.client.get(reverse("web:compare"))

        assert "competitors" in response.context
        assert len(response.context["competitors"]) == 7
        assert "linearb" in response.context["competitors"]

    def test_compare_hub_has_our_features_in_context(self):
        """Compare hub page includes our_features in context."""
        response = self.client.get(reverse("web:compare"))

        assert "our_features" in response.context
        assert "github" in response.context["our_features"]

    def test_compare_hub_has_pricing_comparison_in_context(self):
        """Compare hub page includes pricing comparison data."""
        response = self.client.get(reverse("web:compare"))

        assert "pricing_comparison" in response.context
        # Should have 4 team sizes (10, 25, 50, 100)
        assert len(response.context["pricing_comparison"]) == 4

    def test_compare_hub_has_seo_metadata(self):
        """Compare hub page has SEO title and description."""
        response = self.client.get(reverse("web:compare"))

        assert "page_title" in response.context
        assert "page_description" in response.context
        assert "2026" in response.context["page_title"]

    # =========================================================================
    # Individual Competitor Pages
    # =========================================================================

    def test_compare_competitor_returns_200(self):
        """Individual competitor page returns 200 for valid slug."""
        response = self.client.get(reverse("web:compare_competitor", kwargs={"competitor": "linearb"}))

        assert response.status_code == 200

    def test_compare_competitor_uses_correct_template(self):
        """Individual competitor page uses the correct template."""
        response = self.client.get(reverse("web:compare_competitor", kwargs={"competitor": "linearb"}))

        self.assertTemplateUsed(response, "web/compare/competitor.html")

    def test_compare_competitor_has_competitor_in_context(self):
        """Individual competitor page includes competitor data in context."""
        response = self.client.get(reverse("web:compare_competitor", kwargs={"competitor": "linearb"}))

        assert "competitor" in response.context
        assert response.context["competitor"]["name"] == "LinearB"
        assert response.context["competitor"]["slug"] == "linearb"

    def test_compare_competitor_has_savings_table(self):
        """Individual competitor page includes savings table."""
        response = self.client.get(reverse("web:compare_competitor", kwargs={"competitor": "linearb"}))

        assert "savings_table" in response.context
        # Should have 4 team sizes
        assert len(response.context["savings_table"]) == 4

    def test_compare_competitor_has_seo_metadata(self):
        """Individual competitor page uses SEO data from competitor config."""
        response = self.client.get(reverse("web:compare_competitor", kwargs={"competitor": "linearb"}))

        assert "page_title" in response.context
        assert "LinearB" in response.context["page_title"]

    def test_compare_competitor_invalid_slug_returns_404(self):
        """Invalid competitor slug returns 404."""
        response = self.client.get(reverse("web:compare_competitor", kwargs={"competitor": "nonexistent"}))

        assert response.status_code == 404

    def test_all_competitors_pages_return_200(self):
        """All competitor pages return 200."""
        for slug in COMPETITORS:
            with self.subTest(competitor=slug):
                response = self.client.get(reverse("web:compare_competitor", kwargs={"competitor": slug}))
                assert response.status_code == 200


class TestComparisonSitemap(TestCase):
    """Tests for ComparisonSitemap."""

    def test_sitemap_returns_8_items(self):
        """Sitemap returns 8 items (hub + 7 competitors)."""
        sitemap = ComparisonSitemap()
        items = list(sitemap.items())

        assert len(items) == 8

    def test_sitemap_includes_hub(self):
        """Sitemap includes hub page."""
        sitemap = ComparisonSitemap()
        items = list(sitemap.items())

        assert "hub" in items

    def test_sitemap_includes_all_competitors(self):
        """Sitemap includes all competitor slugs."""
        sitemap = ComparisonSitemap()
        items = list(sitemap.items())

        for slug in COMPETITORS:
            assert slug in items

    def test_sitemap_hub_location(self):
        """Sitemap returns correct URL for hub."""
        sitemap = ComparisonSitemap()

        location = sitemap.location("hub")

        assert location == "/compare/"

    def test_sitemap_competitor_location(self):
        """Sitemap returns correct URL for competitor."""
        sitemap = ComparisonSitemap()

        location = sitemap.location("linearb")

        assert location == "/compare/linearb/"

    def test_sitemap_hub_priority(self):
        """Hub page has higher priority than competitors."""
        sitemap = ComparisonSitemap()

        hub_priority = sitemap.priority("hub")
        competitor_priority = sitemap.priority("linearb")

        assert hub_priority > competitor_priority
        assert hub_priority == 0.8
        assert competitor_priority == 0.7

    def test_sitemap_changefreq(self):
        """Sitemap has monthly changefreq."""
        sitemap = ComparisonSitemap()

        assert sitemap.changefreq == "monthly"
