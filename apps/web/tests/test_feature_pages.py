"""TDD tests for feature marketing pages.

Tests URL routing, view responses, and template rendering for:
- /features/dashboard/
- /features/analytics/
- /features/pr-explorer/
"""

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestFeaturePageURLs:
    """Test that feature page URLs resolve correctly."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_features_dashboard_url_resolves(self, client):
        """Dashboard feature page should return 200."""
        response = client.get("/features/dashboard/")
        assert response.status_code == 200

    def test_features_analytics_url_resolves(self, client):
        """Analytics feature page should return 200."""
        response = client.get("/features/analytics/")
        assert response.status_code == 200

    def test_features_pr_explorer_url_resolves(self, client):
        """PR Explorer feature page should return 200."""
        response = client.get("/features/pr-explorer/")
        assert response.status_code == 200

    def test_features_dashboard_uses_correct_template(self, client):
        """Dashboard page should use the dashboard template."""
        response = client.get("/features/dashboard/")
        assert "web/features/dashboard.html" in [t.name for t in response.templates]

    def test_features_analytics_uses_correct_template(self, client):
        """Analytics page should use the analytics template."""
        response = client.get("/features/analytics/")
        assert "web/features/analytics.html" in [t.name for t in response.templates]

    def test_features_pr_explorer_uses_correct_template(self, client):
        """PR Explorer page should use the pr_explorer template."""
        response = client.get("/features/pr-explorer/")
        assert "web/features/pr_explorer.html" in [t.name for t in response.templates]


@pytest.mark.django_db
class TestFeaturePageContent:
    """Test that feature pages contain expected content."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_dashboard_page_has_hero_headline(self, client):
        """Dashboard page should have the correct hero headline."""
        response = client.get("/features/dashboard/")
        assert b"One dashboard. Weekly clarity." in response.content

    def test_analytics_page_has_hero_headline(self, client):
        """Analytics page should have the correct hero headline."""
        response = client.get("/features/analytics/")
        assert b"See what matters. Ignore what doesn" in response.content

    def test_pr_explorer_page_has_hero_headline(self, client):
        """PR Explorer page should have the correct hero headline."""
        response = client.get("/features/pr-explorer/")
        assert b"Your PR data. Your way." in response.content

    def test_analytics_page_has_anchor_sections(self, client):
        """Analytics page should have all anchor sections."""
        response = client.get("/features/analytics/")
        content = response.content.decode()
        assert 'id="overview"' in content
        assert 'id="ai-adoption"' in content
        assert 'id="delivery"' in content
        assert 'id="quality"' in content
        assert 'id="team"' in content
        assert 'id="trends"' in content


@pytest.mark.django_db
class TestFeaturePageSEO:
    """Test SEO elements on feature pages."""

    @pytest.fixture
    def client(self):
        return Client()

    def test_dashboard_page_has_page_title(self, client):
        """Dashboard page should have a descriptive page title."""
        response = client.get("/features/dashboard/")
        assert b"<title>" in response.content
        assert b"Dashboard" in response.content

    def test_analytics_page_has_page_title(self, client):
        """Analytics page should have a descriptive page title."""
        response = client.get("/features/analytics/")
        assert b"<title>" in response.content
        assert b"Analytics" in response.content

    def test_pr_explorer_page_has_page_title(self, client):
        """PR Explorer page should have a descriptive page title."""
        response = client.get("/features/pr-explorer/")
        assert b"<title>" in response.content
        assert b"PR Explorer" in response.content


class TestFeaturePageURLNames:
    """Test that URL names resolve correctly."""

    def test_features_dashboard_url_name(self):
        """Should be able to reverse features_dashboard URL."""
        url = reverse("web:features_dashboard")
        assert url == "/features/dashboard/"

    def test_features_analytics_url_name(self):
        """Should be able to reverse features_analytics URL."""
        url = reverse("web:features_analytics")
        assert url == "/features/analytics/"

    def test_features_pr_explorer_url_name(self):
        """Should be able to reverse features_pr_explorer URL."""
        url = reverse("web:features_pr_explorer")
        assert url == "/features/pr-explorer/"


class TestFeaturePageSitemap:
    """Test that feature pages are included in sitemap via FeaturesSitemap class."""

    def test_features_sitemap_contains_all_pages(self):
        """FeaturesSitemap should include all feature pages."""
        from apps.web.sitemaps import FeaturesSitemap

        sitemap = FeaturesSitemap()
        items = sitemap.items()

        assert "web:features" in items
        assert "web:features_dashboard" in items
        assert "web:features_analytics" in items
        assert "web:features_pr_explorer" in items

    def test_features_sitemap_locations_resolve(self):
        """FeaturesSitemap locations should resolve to correct URLs."""
        from apps.web.sitemaps import FeaturesSitemap

        sitemap = FeaturesSitemap()

        assert sitemap.location("web:features") == "/features/"
        assert sitemap.location("web:features_dashboard") == "/features/dashboard/"
        assert sitemap.location("web:features_analytics") == "/features/analytics/"
        assert sitemap.location("web:features_pr_explorer") == "/features/pr-explorer/"

    def test_features_sitemap_priority(self):
        """FeaturesSitemap should have appropriate priority."""
        from apps.web.sitemaps import FeaturesSitemap

        sitemap = FeaturesSitemap()
        assert sitemap.priority == 0.8

    def test_features_sitemap_changefreq(self):
        """FeaturesSitemap should have appropriate changefreq."""
        from apps.web.sitemaps import FeaturesSitemap

        sitemap = FeaturesSitemap()
        assert sitemap.changefreq == "monthly"
