"""Tests for chart layout normalization (Task 5).

Covers: reusable chart card template, org analytics integration,
repo-scoped chart filtering.
"""

from django.template import Context, Template
from django.test import TestCase

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

    def test_repo_detail_charts_pass_repo_filter(self):
        response = self.client.get("/open-source/chart-org/repos/chart-repo/")
        content = response.content.decode()
        # Chart HTMX endpoints should include repo filter
        assert "?repo=" in content or "repo=" in content
