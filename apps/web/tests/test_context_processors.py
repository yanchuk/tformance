from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.web.context_processors import auth_mode


class TestAuthModeContextProcessor(TestCase):
    """Tests for auth_mode context processor."""

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

    @override_settings(AUTH_MODE="all", ALLOW_EMAIL_AUTH=True, ALLOW_GOOGLE_AUTH=False)
    def test_auth_mode_all_returns_correct_values(self):
        """Test that AUTH_MODE=all exposes correct template variables."""
        result = auth_mode(self.request)

        self.assertEqual(result["AUTH_MODE"], "all")
        self.assertTrue(result["ALLOW_EMAIL_AUTH"])
        self.assertFalse(result["ALLOW_GOOGLE_AUTH"])

    @override_settings(AUTH_MODE="github_only", ALLOW_EMAIL_AUTH=False, ALLOW_GOOGLE_AUTH=False)
    def test_auth_mode_github_only_returns_correct_values(self):
        """Test that AUTH_MODE=github_only exposes correct template variables."""
        result = auth_mode(self.request)

        self.assertEqual(result["AUTH_MODE"], "github_only")
        self.assertFalse(result["ALLOW_EMAIL_AUTH"])
        self.assertFalse(result["ALLOW_GOOGLE_AUTH"])

    def test_auth_mode_defaults_when_settings_missing(self):
        """Test fallback values when settings are not defined."""
        with patch("apps.web.context_processors.settings") as mock_settings:
            # Simulate missing settings by making getattr return defaults
            mock_settings.ALLOW_EMAIL_AUTH = None
            mock_settings.ALLOW_GOOGLE_AUTH = None
            mock_settings.AUTH_MODE = None

            # Use delattr to ensure getattr returns default
            del mock_settings.ALLOW_EMAIL_AUTH
            del mock_settings.ALLOW_GOOGLE_AUTH
            del mock_settings.AUTH_MODE

            result = auth_mode(self.request)

            # Should return safe defaults
            self.assertEqual(result["AUTH_MODE"], "github_only")
            self.assertFalse(result["ALLOW_EMAIL_AUTH"])
            self.assertFalse(result["ALLOW_GOOGLE_AUTH"])


class TestAuthModeInTemplateContext(TestCase):
    """Tests that auth mode variables are available in templates."""

    @override_settings(AUTH_MODE="all", ALLOW_EMAIL_AUTH=True, ALLOW_GOOGLE_AUTH=False)
    def test_login_page_has_auth_mode_context(self):
        """Test login page receives auth mode context variables."""
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("ALLOW_EMAIL_AUTH", response.context)
        self.assertIn("AUTH_MODE", response.context)
        self.assertTrue(response.context["ALLOW_EMAIL_AUTH"])
        self.assertEqual(response.context["AUTH_MODE"], "all")

    @override_settings(AUTH_MODE="all", ALLOW_EMAIL_AUTH=True, ALLOW_GOOGLE_AUTH=False)
    def test_signup_page_has_auth_mode_context(self):
        """Test signup page receives auth mode context variables."""
        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("ALLOW_EMAIL_AUTH", response.context)
        self.assertIn("AUTH_MODE", response.context)
        self.assertTrue(response.context["ALLOW_EMAIL_AUTH"])

    @override_settings(AUTH_MODE="github_only", ALLOW_EMAIL_AUTH=False, ALLOW_GOOGLE_AUTH=False)
    def test_login_page_github_only_mode(self):
        """Test login page context in github_only mode."""
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["ALLOW_EMAIL_AUTH"])
        self.assertEqual(response.context["AUTH_MODE"], "github_only")


class TestAuthModeTemplateRendering(TestCase):
    """Tests that templates render correctly based on auth mode."""

    @override_settings(AUTH_MODE="all", ALLOW_EMAIL_AUTH=True, ALLOW_GOOGLE_AUTH=False)
    def test_login_shows_email_form_in_all_mode(self):
        """Test login page shows email form when AUTH_MODE=all."""
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Should contain email form elements
        self.assertIn('name="login"', content)  # Email field
        self.assertIn('name="password"', content)  # Password field
        self.assertIn("or continue with", content.lower())  # Divider text

    @override_settings(AUTH_MODE="github_only", ALLOW_EMAIL_AUTH=False, ALLOW_GOOGLE_AUTH=False)
    def test_login_hides_email_form_in_github_only_mode(self):
        """Test login page hides email form when AUTH_MODE=github_only."""
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Should NOT contain email form (login field is email input name)
        self.assertNotIn('name="login"', content)
        self.assertNotIn('name="password"', content)

        # Should contain GitHub-only message
        self.assertIn("Sign in with your GitHub account", content)

    @override_settings(AUTH_MODE="all", ALLOW_EMAIL_AUTH=True, ALLOW_GOOGLE_AUTH=False)
    def test_signup_shows_email_form_in_all_mode(self):
        """Test signup page shows email form when AUTH_MODE=all."""
        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Should contain signup form elements
        self.assertIn('name="email"', content)
        self.assertIn('name="password1"', content)

    @override_settings(AUTH_MODE="github_only", ALLOW_EMAIL_AUTH=False, ALLOW_GOOGLE_AUTH=False)
    def test_signup_hides_email_form_in_github_only_mode(self):
        """Test signup page hides email form when AUTH_MODE=github_only."""
        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Should NOT contain email form
        self.assertNotIn('name="email"', content)
        self.assertNotIn('name="password1"', content)

        # Should contain GitHub-only message
        self.assertIn("Create your account using GitHub", content)

        # Heading should be "Get Started" not "Sign Up"
        self.assertIn("Get Started", content)

    @override_settings(AUTH_MODE="github_only", ALLOW_EMAIL_AUTH=False, ALLOW_GOOGLE_AUTH=False)
    def test_social_buttons_hide_divider_in_github_only_mode(self):
        """Test social buttons component hides divider in github_only mode."""
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode().lower()

        # Should NOT show "or continue with" divider
        self.assertNotIn("or continue with", content)
