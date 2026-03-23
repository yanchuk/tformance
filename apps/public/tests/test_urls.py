from django.test import SimpleTestCase
from django.urls import resolve, reverse

from apps.public.views.analytics_views import org_analytics
from apps.public.views.org_views import org_detail


class PublicUrlsTests(SimpleTestCase):
    def test_org_detail_route_resolves(self):
        match = resolve("/open-source/posthog/")
        assert match.func == org_detail
        assert match.url_name == "org_detail"

    def test_org_detail_reverse(self):
        assert reverse("public:org_detail", kwargs={"slug": "posthog"}) == "/open-source/posthog/"

    def test_org_analytics_route_resolves(self):
        match = resolve("/open-source/posthog/analytics/")
        assert match.func == org_analytics
        assert match.url_name == "org_analytics"
