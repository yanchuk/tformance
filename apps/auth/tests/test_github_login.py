"""Tests for GitHub login flow via unified OAuth callback.

These tests verify the login flow that allows users to authenticate
with GitHub using minimal scopes (user:email) through our unified
callback URL (/auth/github/callback/).

Tests are written in TDD RED phase - they should FAIL until implementation.
"""

from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from apps.auth.oauth_state import (
    create_oauth_state,
    verify_oauth_state,
)
from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN

# FLOW_TYPE_LOGIN does not exist yet - this is what we're testing
# Import it dynamically to allow tests to run and show failures
try:
    from apps.auth.oauth_state import FLOW_TYPE_LOGIN
except ImportError:
    FLOW_TYPE_LOGIN = None  # Will cause tests to fail with clear message


class TestGitHubLoginView(TestCase):
    """Tests for the github_login view that initiates GitHub OAuth for login."""

    def test_github_login_view_redirects_to_github(self):
        """Test that github_login view redirects to GitHub OAuth URL."""
        # This test will fail because the URL doesn't exist yet
        try:
            login_url = reverse("tformance_auth:github_login")
        except NoReverseMatch:
            self.fail("URL 'tformance_auth:github_login' does not exist. Need to add github_login view and URL.")

        response = self.client.get(login_url)

        # Should redirect to GitHub
        self.assertEqual(response.status_code, 302)
        self.assertIn("github.com", response.url)
        self.assertIn("oauth/authorize", response.url)

    def test_github_login_state_has_login_type(self):
        """Test that OAuth state contains FLOW_TYPE_LOGIN."""
        try:
            login_url = reverse("tformance_auth:github_login")
        except NoReverseMatch:
            self.fail("URL 'tformance_auth:github_login' does not exist.")

        response = self.client.get(login_url)

        # Extract state parameter from redirect URL
        self.assertEqual(response.status_code, 302)
        # Parse state from URL query params
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(response.url)
        query_params = parse_qs(parsed.query)
        state = query_params.get("state", [None])[0]

        self.assertIsNotNone(state)

        # Verify state decodes to login type
        state_data = verify_oauth_state(state)
        self.assertEqual(state_data["type"], "login")

    def test_github_login_uses_minimal_scopes(self):
        """Test that login uses user:email scope, not full repo scopes."""
        try:
            login_url = reverse("tformance_auth:github_login")
        except NoReverseMatch:
            self.fail("URL 'tformance_auth:github_login' does not exist.")

        response = self.client.get(login_url)

        self.assertEqual(response.status_code, 302)

        # Parse scope from URL query params
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(response.url)
        query_params = parse_qs(parsed.query)
        scope = query_params.get("scope", [""])[0]

        # Should use minimal scopes for login
        self.assertIn("user:email", scope)
        # Should NOT have full integration scopes
        self.assertNotIn("repo", scope)
        self.assertNotIn("read:org", scope)


class TestGitHubLoginCallback(TestCase):
    """Tests for github_callback handling FLOW_TYPE_LOGIN."""

    def setUp(self):
        """Set up test fixtures."""
        self.callback_url = reverse("tformance_auth:github_callback")

    def test_github_callback_handles_login_flow(self):
        """Test that callback processes login type correctly."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        # Create state with login type
        state = create_oauth_state(FLOW_TYPE_LOGIN)

        # Mock GitHub OAuth exchange
        with patch("apps.auth.views.github_oauth") as mock_oauth:
            mock_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
            mock_oauth.get_github_user.return_value = {
                "id": 12345,
                "login": "testuser",
                "email": "test@example.com",
                "name": "Test User",
            }

            response = self.client.get(
                self.callback_url,
                {"state": state, "code": "test_code"},
            )

        # Should redirect (either to onboarding or dashboard)
        self.assertEqual(response.status_code, 302)

        # User should be logged in
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated)


class TestLoginCreatesUser(TestCase):
    """Tests for user creation during GitHub login."""

    def setUp(self):
        """Set up test fixtures."""
        self.callback_url = reverse("tformance_auth:github_callback")

    def test_login_creates_new_user(self):
        """Test that new user is created from GitHub profile."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        state = create_oauth_state(FLOW_TYPE_LOGIN)

        with patch("apps.auth.views.github_oauth") as mock_oauth:
            mock_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
            mock_oauth.get_github_user.return_value = {
                "id": 99999,
                "login": "newgithubuser",
                "email": "newuser@example.com",
                "name": "New GitHub User",
            }

            response = self.client.get(
                self.callback_url,
                {"state": state, "code": "test_code"},
            )

        self.assertEqual(response.status_code, 302)

        # User should be created
        from apps.users.models import CustomUser

        user = CustomUser.objects.get(email="newuser@example.com")
        self.assertEqual(user.username, "newgithubuser")

    def test_login_matches_existing_user_by_github_id(self):
        """Test that existing user is matched by GitHub ID (SocialAccount)."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        # Create existing user with GitHub connection
        existing_user = UserFactory(
            username="existinguser",
            email="existing@example.com",
        )
        SocialAccount.objects.create(
            user=existing_user,
            provider="github",
            uid="55555",  # GitHub ID
            extra_data={"login": "existinggithub"},
        )

        state = create_oauth_state(FLOW_TYPE_LOGIN)

        with patch("apps.auth.views.github_oauth") as mock_oauth:
            mock_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
            mock_oauth.get_github_user.return_value = {
                "id": 55555,  # Same GitHub ID
                "login": "existinggithub",
                "email": "different@example.com",  # Different email
                "name": "Existing User",
            }

            response = self.client.get(
                self.callback_url,
                {"state": state, "code": "test_code"},
            )

        self.assertEqual(response.status_code, 302)

        # Should login as existing user, not create new
        user = get_user(self.client)
        self.assertEqual(user.id, existing_user.id)

        # No new user should be created
        from apps.users.models import CustomUser

        self.assertEqual(CustomUser.objects.count(), 1)

    def test_login_matches_existing_user_by_email(self):
        """Test that existing user is matched by email when no SocialAccount."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        # Create existing user without GitHub connection
        existing_user = UserFactory(
            username="emailuser",
            email="samemail@example.com",
        )

        state = create_oauth_state(FLOW_TYPE_LOGIN)

        with patch("apps.auth.views.github_oauth") as mock_oauth:
            mock_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
            mock_oauth.get_github_user.return_value = {
                "id": 77777,
                "login": "githublogin",
                "email": "samemail@example.com",  # Same email
                "name": "Email Match User",
            }

            response = self.client.get(
                self.callback_url,
                {"state": state, "code": "test_code"},
            )

        self.assertEqual(response.status_code, 302)

        # Should login as existing user
        user = get_user(self.client)
        self.assertEqual(user.id, existing_user.id)

        # SocialAccount should be created to link the accounts
        social = SocialAccount.objects.get(user=existing_user)
        self.assertEqual(social.provider, "github")
        self.assertEqual(social.uid, "77777")


class TestLoginCreatesSocialAccount(TestCase):
    """Tests for SocialAccount creation during login."""

    def setUp(self):
        """Set up test fixtures."""
        self.callback_url = reverse("tformance_auth:github_callback")

    def test_login_creates_social_account(self):
        """Test that SocialAccount record is created linking user to GitHub."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        state = create_oauth_state(FLOW_TYPE_LOGIN)

        with patch("apps.auth.views.github_oauth") as mock_oauth:
            mock_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
            mock_oauth.get_github_user.return_value = {
                "id": 88888,
                "login": "socialuser",
                "email": "social@example.com",
                "name": "Social User",
            }

            response = self.client.get(
                self.callback_url,
                {"state": state, "code": "test_code"},
            )

        self.assertEqual(response.status_code, 302)

        # SocialAccount should exist
        from apps.users.models import CustomUser

        user = CustomUser.objects.get(email="social@example.com")
        social = SocialAccount.objects.get(user=user)

        self.assertEqual(social.provider, "github")
        self.assertEqual(social.uid, "88888")
        self.assertEqual(social.extra_data.get("login"), "socialuser")


class TestLoginRedirects(TestCase):
    """Tests for redirect logic after successful login."""

    def setUp(self):
        """Set up test fixtures."""
        self.callback_url = reverse("tformance_auth:github_callback")

    def test_login_redirects_to_onboarding_if_no_team(self):
        """Test that user without team is redirected to onboarding:start."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        state = create_oauth_state(FLOW_TYPE_LOGIN)

        with patch("apps.auth.views.github_oauth") as mock_oauth:
            mock_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
            mock_oauth.get_github_user.return_value = {
                "id": 11111,
                "login": "noteamuser",
                "email": "noteam@example.com",
                "name": "No Team User",
            }

            response = self.client.get(
                self.callback_url,
                {"state": state, "code": "test_code"},
            )

        # Should redirect to onboarding
        self.assertEqual(response.status_code, 302)
        self.assertIn("onboarding", response.url)

    def test_login_redirects_to_dashboard_if_has_team(self):
        """Test that user with team is redirected to web:home (dashboard)."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        # Create user with a team
        existing_user = UserFactory(email="hasteam@example.com")
        team = TeamFactory()
        team.members.add(existing_user, through_defaults={"role": ROLE_ADMIN})

        # Create SocialAccount so user will be matched
        SocialAccount.objects.create(
            user=existing_user,
            provider="github",
            uid="22222",
            extra_data={"login": "teamuser"},
        )

        state = create_oauth_state(FLOW_TYPE_LOGIN)

        with patch("apps.auth.views.github_oauth") as mock_oauth:
            mock_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
            mock_oauth.get_github_user.return_value = {
                "id": 22222,  # Match SocialAccount
                "login": "teamuser",
                "email": "hasteam@example.com",
                "name": "Team User",
            }

            response = self.client.get(
                self.callback_url,
                {"state": state, "code": "test_code"},
            )

        # Should redirect to dashboard, not onboarding
        self.assertEqual(response.status_code, 302)
        # web:home is the dashboard
        expected_url = reverse("web:home")
        self.assertEqual(response.url, expected_url)


class TestLoginFlowTypeInOAuthState(TestCase):
    """Tests for FLOW_TYPE_LOGIN in oauth_state module."""

    def test_flow_type_login_exists(self):
        """Test that FLOW_TYPE_LOGIN constant exists."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist. Add to apps/auth/oauth_state.py: FLOW_TYPE_LOGIN = 'login'")
        self.assertEqual(FLOW_TYPE_LOGIN, "login")

    def test_create_oauth_state_accepts_login_type(self):
        """Test that create_oauth_state accepts FLOW_TYPE_LOGIN."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        state = create_oauth_state(FLOW_TYPE_LOGIN)

        self.assertIsNotNone(state)

        # Should be verifiable
        state_data = verify_oauth_state(state)
        self.assertEqual(state_data["type"], FLOW_TYPE_LOGIN)

    def test_login_flow_does_not_require_team_id(self):
        """Test that FLOW_TYPE_LOGIN does not require team_id."""
        if FLOW_TYPE_LOGIN is None:
            self.fail("FLOW_TYPE_LOGIN does not exist in oauth_state.py")

        # Should not raise ValueError
        state = create_oauth_state(FLOW_TYPE_LOGIN)
        self.assertIsNotNone(state)

        # Should not require team_id
        state_data = verify_oauth_state(state)
        self.assertNotIn("team_id", state_data)
