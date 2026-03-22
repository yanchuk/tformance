"""Tests for directory column header sorting (Task 4, Step 4.3).

Covers: sort + order params, filter preservation, HTMX sort headers.
"""

from django.test import TestCase

from apps.public.models import PublicOrgProfile, PublicOrgStats
from apps.teams.models import Team


class DirectorySortingTests(TestCase):
    """Step 4.3: Server-side column header sorting."""

    @classmethod
    def setUpTestData(cls):
        for i, (name, ai_pct, cycle, prs) in enumerate(
            [
                ("Alpha Org", 10, 30, 2000),
                ("Beta Org", 50, 15, 1500),
                ("Gamma Org", 80, 8, 1000),
            ]
        ):
            team = Team.objects.create(name=name, slug=f"sort-team-{i}")
            org = PublicOrgProfile.objects.create(
                team=team,
                public_slug=f"sort-org-{i}",
                industry="analytics",
                display_name=name,
                is_public=True,
            )
            PublicOrgStats.objects.create(
                org_profile=org,
                total_prs=prs,
                ai_assisted_pct=ai_pct,
                median_cycle_time_hours=cycle,
            )

    def test_sort_by_ai_adoption_desc(self):
        response = self.client.get("/open-source/?sort=ai_adoption&order=desc")
        orgs = response.context["orgs"]
        pcts = [o["ai_assisted_pct"] for o in orgs]
        assert pcts == sorted(pcts, reverse=True)

    def test_sort_by_ai_adoption_asc(self):
        response = self.client.get("/open-source/?sort=ai_adoption&order=asc")
        orgs = response.context["orgs"]
        pcts = [o["ai_assisted_pct"] for o in orgs]
        assert pcts == sorted(pcts)

    def test_sort_preserves_filters(self):
        response = self.client.get("/open-source/?sort=cycle_time&order=asc&industry=analytics")
        assert response.context["current_industry"] == "analytics"
        assert response.context["current_sort"] == "cycle_time"
        assert response.context["current_order"] == "asc"

    def test_default_order_is_desc_for_numeric(self):
        response = self.client.get("/open-source/?sort=total_prs")
        assert response.context["current_order"] == "desc"

    def test_default_order_is_asc_for_name(self):
        response = self.client.get("/open-source/?sort=name")
        assert response.context["current_order"] == "asc"
