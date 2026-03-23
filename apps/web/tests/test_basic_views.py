from django.test import TestCase
from django.urls import reverse


class TestBasicViews(TestCase):
    def test_landing_page(self):
        self._assert_200(reverse("web:home"))

    def test_landing_page_has_open_source_benchmarks_nav_and_footer_links(self):
        response = self.client.get(reverse("web:home"))
        self.assertContains(response, "Open Source Benchmarks")
        self.assertContains(response, "/open-source/")

    def test_landing_page_uses_delivery_first_copy(self):
        response = self.client.get(reverse("web:home"))
        content = response.content.decode()
        assert "See how your team is actually delivering." in content
        assert "See if AI tools help" not in content
        assert "Engineering Analytics + AI Impact" not in content
        assert "Champion" not in content
        assert "Needs help" not in content
        assert "You shouldn't—yet" not in content
        assert "Looking for a co-founder" not in content

    def test_signup(self):
        self._assert_200(reverse("account_signup"))

    def test_login(self):
        self._assert_200(reverse("account_login"))

    def test_terms(self):
        self._assert_200(reverse("web:terms"))

    def test_robots(self):
        self._assert_200(reverse("web:robots.txt"))

    def _assert_200(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
