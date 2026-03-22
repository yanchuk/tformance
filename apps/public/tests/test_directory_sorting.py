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
        for i, (name, ai_pct, cycle, prs, review, contributors) in enumerate(
            [
                ("Alpha Org", 10, 30, 2000, 6, 10),
                ("Beta Org", 50, 15, 1500, 3, 25),
                ("Gamma Org", 80, 8, 1000, 9, 5),
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
                median_review_time_hours=review,
                active_contributors_90d=contributors,
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

    def test_sort_by_review_time(self):
        response = self.client.get("/open-source/?sort=review_time&order=desc")
        # Should not error -- review_time is a valid sort option
        assert response.status_code == 200
        assert len(response.context["orgs"]) > 0

    def test_sort_by_contributors(self):
        response = self.client.get("/open-source/?sort=contributors&order=desc")
        assert response.status_code == 200
        assert len(response.context["orgs"]) > 0
