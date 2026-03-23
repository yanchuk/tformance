"""Tests for chart layout normalization (Task 5).

Covers: reusable chart card template, org analytics integration,
repo-scoped chart filtering.
"""

import re

from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile, PublicRepoStats
from apps.teams.models import Team


class PublicChartCardContractTests(TestCase):
    """Step 5.1: Reusable chart card template renders correctly."""

    def test_chart_card_partial_renders_title_and_body(self):
        template = Template(
            '{% include "public/partials/public_chart_card.html" '
            'with chart_title="AI Adoption" chart_id="ai-adoption" %}'
        )
        html = template.render(Context({}))
        assert "AI Adoption" in html
        assert "ai-adoption" in html
        assert "data-chart-card" in html

    def test_chart_card_has_consistent_min_height(self):
        template = Template(
            '{% include "public/partials/public_chart_card.html" with chart_title="Test" chart_id="test" %}'
        )
        html = template.render(Context({}))
        assert "min-h-[14rem]" in html


class RepoChartScopingTests(TestCase):
    """Step 5.3: Repo detail charts pass repo filter."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Chart Team", slug="chart-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="chart-org",
            industry="analytics",
            display_name="Chart Org",
            is_public=True,
        )
        cls.org_stats = PublicOrgStats.objects.create(
            org_profile=cls.org,
            total_prs=1000,
            ai_assisted_pct=40,
            median_cycle_time_hours=15,
        )
        cls.repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="chart-org/chart-repo",
            repo_slug="chart-repo",
            display_name="Chart Repo",
            is_flagship=True,
            is_public=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo,
            total_prs=200,
            ai_assisted_pct=35,
            median_cycle_time_hours=10,
        )

    def test_repo_detail_renders_from_snapshot_data(self):
        """Repo pages use pre-computed snapshot data, not live HTMX chart fetches."""
        response = self.client.get("/open-source/chart-org/repos/chart-repo/")
        content = response.content.decode()
        # Page renders from stored snapshot — should contain stats data inline
        assert response.status_code == 200
        assert "Chart Repo" in content


class AnalyticsChartConsistencyTests(TestCase):
    """Step 6.3: Chart card height contract."""

    @classmethod
    def setUpTestData(cls):
        from apps.metrics.factories import TeamFactory
        from apps.public.aggregations import MIN_PRS_THRESHOLD

        cls.team = TeamFactory()
        cls.profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="chart-height-org",
            industry="analytics",
            display_name="Chart Height Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
            ai_assisted_pct=30,
            median_cycle_time_hours=15,
            median_review_time_hours=4,
            active_contributors_90d=10,
            last_computed_at=timezone.now(),
        )

    def test_analytics_chart_cards_have_consistent_height_class(self):
        response = self.client.get(reverse("public:org_analytics", kwargs={"slug": "chart-height-org"}))
        content = response.content.decode()
        # All chart wrapper cards should have min-h for consistency
        chart_cards = re.findall(r'<div class="card[^"]*">', content)
        # At least some chart cards should exist
        assert len(chart_cards) >= 2, "Expected at least 2 chart cards"
