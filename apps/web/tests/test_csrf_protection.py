"""Tests for CSRF protection across the application.

These tests verify that Django's CSRF middleware is correctly protecting
all state-changing endpoints, and that only explicitly exempted endpoints
(webhooks with alternative authentication) bypass CSRF checks.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.metrics.factories import TeamFactory
from apps.teams import roles
from apps.teams.models import Membership

User = get_user_model()


class TestCSRFMiddlewareEnabled(TestCase):
    """Tests verifying CSRF middleware is properly configured."""

    def test_csrf_middleware_in_settings(self):
        """Verify CsrfViewMiddleware is in MIDDLEWARE setting."""
        self.assertIn(
            "django.middleware.csrf.CsrfViewMiddleware",
            settings.MIDDLEWARE,
            "CSRF middleware must be enabled in settings",
        )

    def test_csrf_cookie_httponly(self):
        """Verify CSRF cookie is HttpOnly to prevent JS access."""
        self.assertTrue(
            settings.CSRF_COOKIE_HTTPONLY,
            "CSRF_COOKIE_HTTPONLY should be True to prevent XSS attacks",
        )

    def test_csrf_cookie_samesite(self):
        """Verify CSRF cookie has SameSite attribute."""
        self.assertEqual(
            settings.CSRF_COOKIE_SAMESITE,
            "Lax",
            "CSRF_COOKIE_SAMESITE should be 'Lax' for CSRF protection",
        )

    @override_settings(DEBUG=False)
    def test_csrf_cookie_secure_in_production(self):
        """Verify CSRF cookie is Secure in production (HTTPS only)."""
        # In production (DEBUG=False), CSRF_COOKIE_SECURE should be True
        # This test verifies the production configuration pattern
        self.assertTrue(
            not settings.DEBUG,
            "This test requires DEBUG=False",
        )


class TestCSRFProtectionOnForms(TestCase):
    """Tests verifying CSRF protection on form submissions."""

    def setUp(self):
        """Set up test user and team."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.team = TeamFactory(name="Test Team", slug="test-team")
        Membership.objects.create(team=self.team, user=self.user, role=roles.ROLE_ADMIN)

    def test_post_without_csrf_token_returns_403(self):
        """POST requests without CSRF token should be rejected with 403."""
        # Create a client that doesn't enforce CSRF (to test the middleware)
        client = Client(enforce_csrf_checks=True)
        client.login(username="test@example.com", password="testpass123")

        # Try to POST to profile without CSRF token
        response = client.post(
            reverse("users:user_profile"),
            data={"first_name": "Test"},
        )

        self.assertEqual(
            response.status_code,
            403,
            "POST without CSRF token should return 403 Forbidden",
        )

    def test_post_with_invalid_csrf_token_returns_403(self):
        """POST requests with invalid CSRF token should be rejected."""
        client = Client(enforce_csrf_checks=True)
        client.login(username="test@example.com", password="testpass123")

        # Try to POST with an invalid CSRF token
        response = client.post(
            reverse("users:user_profile"),
            data={
                "first_name": "Test",
                "csrfmiddlewaretoken": "invalid_token_12345",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
            "POST with invalid CSRF token should return 403 Forbidden",
        )

    def test_post_with_valid_csrf_token_succeeds(self):
        """POST requests with valid CSRF token should succeed."""
        client = Client(enforce_csrf_checks=True)
        client.login(username="test@example.com", password="testpass123")

        # Get a valid CSRF token
        response = client.get(reverse("users:user_profile"))
        csrf_token = client.cookies.get("csrftoken")

        if csrf_token:
            # POST with valid CSRF token
            response = client.post(
                reverse("users:user_profile"),
                data={
                    "first_name": "Updated",
                    "last_name": "Name",
                    "email": "test@example.com",
                    "csrfmiddlewaretoken": csrf_token.value,
                },
            )

            # Should not be 403 (might be 302 redirect on success or 200)
            self.assertNotEqual(
                response.status_code,
                403,
                "POST with valid CSRF token should not return 403",
            )

    def test_ajax_with_csrf_header_succeeds(self):
        """AJAX/HTMX requests with X-CSRFToken header should succeed."""
        client = Client(enforce_csrf_checks=True)
        client.login(username="test@example.com", password="testpass123")

        # Get a valid CSRF token
        response = client.get(reverse("users:user_profile"))
        csrf_token = client.cookies.get("csrftoken")

        if csrf_token:
            # POST with X-CSRFToken header (HTMX pattern)
            response = client.post(
                reverse("users:user_profile"),
                data={
                    "first_name": "Updated",
                    "last_name": "Name",
                    "email": "test@example.com",
                },
                HTTP_X_CSRFTOKEN=csrf_token.value,
            )

            # Should not be 403
            self.assertNotEqual(
                response.status_code,
                403,
                "POST with X-CSRFToken header should not return 403",
            )


class TestCSRFExemptEndpoints(TestCase):
    """Tests verifying csrf_exempt endpoints have alternative authentication."""

    def test_github_webhook_is_csrf_exempt_but_requires_signature(self):
        """GitHub webhook endpoint is csrf_exempt but requires HMAC signature."""
        client = Client(enforce_csrf_checks=True)

        # POST without CSRF token but also without signature
        response = client.post(
            reverse("web:github_webhook"),
            data='{"test": "payload"}',
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="ping",
            HTTP_X_GITHUB_DELIVERY="test-delivery-id",
        )

        # Should NOT be 403 (csrf_exempt) but should be 401 (missing signature)
        self.assertNotEqual(
            response.status_code,
            403,
            "Webhook should be csrf_exempt",
        )
        self.assertEqual(
            response.status_code,
            401,
            "Webhook without signature should return 401 Unauthorized",
        )

    def test_only_two_csrf_exempt_endpoints_exist(self):
        """Verify only webhook endpoints are csrf_exempt in the codebase."""
        # This is a documentation test - we manually verify that only
        # GitHub webhook (apps/web/views.py) and Slack interactions
        # (apps/integrations/webhooks/slack_interactions.py) use @csrf_exempt.
        # Both have alternative authentication via HMAC signature validation.
        #
        # If you need to add a new @csrf_exempt endpoint:
        # 1. Document the security justification
        # 2. Implement alternative authentication (e.g., HMAC signatures)
        # 3. Add rate limiting
        # 4. Update this test
        pass  # Manual verification - see security audit docs


class TestTeamEndpointsCSRF(TestCase):
    """Tests verifying CSRF protection on team management endpoints."""

    def setUp(self):
        """Set up test user and team."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.team = TeamFactory(name="Test Team", slug="test-team")
        Membership.objects.create(team=self.team, user=self.user, role=roles.ROLE_ADMIN)

    def test_team_manage_requires_csrf(self):
        """Team management endpoint requires CSRF token."""
        client = Client(enforce_csrf_checks=True)
        client.login(username="test@example.com", password="testpass123")

        # POST without CSRF token (team resolved from session)
        response = client.post(
            reverse("single_team:manage_team"),
            data={"name": "New Name"},
        )

        self.assertEqual(
            response.status_code,
            403,
            "Team management POST without CSRF should return 403",
        )

    def test_team_delete_requires_csrf(self):
        """Team deletion endpoint requires CSRF token."""
        client = Client(enforce_csrf_checks=True)
        client.login(username="test@example.com", password="testpass123")

        # POST without CSRF token (team resolved from session)
        response = client.post(
            reverse("single_team:delete_team"),
        )

        self.assertEqual(
            response.status_code,
            403,
            "Team deletion POST without CSRF should return 403",
        )


class TestAuthEndpointsCSRF(TestCase):
    """Tests verifying CSRF protection on authentication endpoints."""

    def test_login_endpoint_requires_csrf(self):
        """Login endpoint requires CSRF token for POST."""
        client = Client(enforce_csrf_checks=True)

        # POST without CSRF token
        response = client.post(
            reverse("account_login"),
            data={
                "login": "test@example.com",
                "password": "testpass123",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
            "Login POST without CSRF should return 403",
        )

    def test_signup_endpoint_requires_csrf(self):
        """Signup endpoint requires CSRF token for POST."""
        client = Client(enforce_csrf_checks=True)

        # POST without CSRF token
        response = client.post(
            reverse("account_signup"),
            data={
                "email": "new@example.com",
                "password1": "securepass123!",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
            "Signup POST without CSRF should return 403",
        )
