from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse


class PublicRepoURLResolutionTests(SimpleTestCase):
    def test_repo_detail_route_resolves(self):
        match = resolve("/open-source/posthog/repos/posthog/")
        assert match.url_name == "repo_detail"
        assert match.kwargs == {"slug": "posthog", "repo_slug": "posthog"}

    def test_repo_pr_list_route_resolves(self):
        match = resolve("/open-source/posthog/repos/posthog/pull-requests/")
        assert match.url_name == "repo_pr_list"

    def test_repo_pr_list_table_route_resolves(self):
        match = resolve("/open-source/posthog/repos/posthog/pull-requests/table/")
        assert match.url_name == "repo_pr_list_table"

    def test_org_detail_still_resolves(self):
        match = resolve("/open-source/posthog/")
        assert match.url_name == "org_detail"

    def test_no_duplicate_org_overview_name(self):
        """org_overview was a duplicate of org_detail — should be consolidated."""
        url = reverse("public:org_detail", kwargs={"slug": "posthog"})
        assert url == "/open-source/posthog/"


class PublicRepoReverseTests(TestCase):
    def test_repo_detail_reverse(self):
        url = reverse("public:repo_detail", kwargs={"slug": "posthog", "repo_slug": "posthog"})
        assert url == "/open-source/posthog/repos/posthog/"

    def test_repo_pr_list_reverse(self):
        url = reverse("public:repo_pr_list", kwargs={"slug": "posthog", "repo_slug": "posthog"})
        assert url == "/open-source/posthog/repos/posthog/pull-requests/"
