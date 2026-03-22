from decimal import Decimal

from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase

from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.decorators import public_org_required
from apps.public.models import PublicOrgProfile, PublicOrgStats
from apps.teams.context import get_current_team, set_current_team, unset_current_team


class PublicOrgRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.team = TeamFactory()
        self.profile = PublicOrgProfile.objects.create(
            team=self.team,
            public_slug="public-org",
            industry="analytics",
            display_name="Public Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=self.profile,
            total_prs=MIN_PRS_THRESHOLD,
            ai_assisted_pct=Decimal("50.0"),
        )

    def test_decorator_sets_request_team(self):
        @public_org_required
        def _view(request, slug):
            assert request.team == self.team
            return HttpResponse("ok")

        response = _view(self.factory.get("/open-source/public-org/"), slug="public-org")
        assert response.status_code == 200

    def test_decorator_sets_public_flags(self):
        @public_org_required
        def _view(request, slug):
            assert request.is_public_view is True
            assert request.public_profile == self.profile
            return HttpResponse("ok")

        response = _view(self.factory.get("/open-source/public-org/"), slug="public-org")
        assert response.status_code == 200

    def test_decorator_404_invalid_slug(self):
        @public_org_required
        def _view(request, slug):
            return HttpResponse("ok")

        with self.assertRaises(Http404):
            _view(self.factory.get("/open-source/missing/"), slug="missing")

    def test_decorator_404_private_org(self):
        self.profile.is_public = False
        self.profile.save(update_fields=["is_public"])

        @public_org_required
        def _view(request, slug):
            return HttpResponse("ok")

        with self.assertRaises(Http404):
            _view(self.factory.get("/open-source/public-org/"), slug="public-org")

    def test_decorator_404_insufficient_data(self):
        stats = self.profile.stats
        stats.total_prs = max(MIN_PRS_THRESHOLD - 1, 0)
        stats.save(update_fields=["total_prs"])

        @public_org_required
        def _view(request, slug):
            return HttpResponse("ok")

        with self.assertRaises(Http404):
            _view(self.factory.get("/open-source/public-org/"), slug="public-org")

    def test_decorator_cleans_up_team_context(self):
        seed_team = TeamFactory()
        seed_token = set_current_team(seed_team)

        @public_org_required
        def _view(request, slug):
            assert get_current_team() == self.team
            return HttpResponse("ok")

        try:
            response = _view(self.factory.get("/open-source/public-org/"), slug="public-org")
            assert response.status_code == 200
            assert get_current_team() == seed_team
        finally:
            unset_current_team(seed_token)
