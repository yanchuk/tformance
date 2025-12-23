"""Tests for team access control decorators.

Tests for login_and_team_required and team_admin_required decorators
that protect team-scoped views from unauthorized access.
"""

from unittest.mock import Mock

from django.http import Http404, HttpRequest, HttpResponse
from django.test import TestCase

from apps.teams.decorators import login_and_team_required, team_admin_required
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER
from apps.users.models import CustomUser


def sample_view(request, *args, **kwargs):
    """Sample view function for testing decorators."""
    return HttpResponse("Success")


class TestLoginAndTeamRequiredDecorator(TestCase):
    """Tests for login_and_team_required decorator."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = Team.objects.create(name="Test Team", slug="test-team")
        cls.admin_user = CustomUser.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
        )
        cls.member_user = CustomUser.objects.create_user(
            username="member",
            email="member@test.com",
            password="testpass123",
        )
        cls.non_member_user = CustomUser.objects.create_user(
            username="nonmember",
            email="nonmember@test.com",
            password="testpass123",
        )
        # Create memberships
        Membership.objects.create(team=cls.team, user=cls.admin_user, role=ROLE_ADMIN)
        Membership.objects.create(team=cls.team, user=cls.member_user, role=ROLE_MEMBER)

    def _create_request(self, user, team=None, path="/test/"):
        """Create a mock request with user and team."""
        request = Mock(spec=HttpRequest)
        request.user = user
        request.team = team
        request.path = path
        return request

    def test_unauthenticated_user_redirected_to_login(self):
        """Test that unauthenticated users are redirected to login."""
        decorated_view = login_and_team_required(sample_view)
        request = self._create_request(Mock(is_authenticated=False), self.team)

        response = decorated_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
        self.assertIn("next=", response.url)

    def test_authenticated_member_can_access(self):
        """Test that authenticated team members can access the view."""
        decorated_view = login_and_team_required(sample_view)
        request = self._create_request(self.member_user, self.team)

        response = decorated_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Success")

    def test_authenticated_admin_can_access(self):
        """Test that authenticated team admins can access the view."""
        decorated_view = login_and_team_required(sample_view)
        request = self._create_request(self.admin_user, self.team)

        response = decorated_view(request)

        self.assertEqual(response.status_code, 200)

    def test_non_member_gets_404(self):
        """Test that non-members get 404 (not 403 to avoid information leakage)."""
        decorated_view = login_and_team_required(sample_view)
        request = self._create_request(self.non_member_user, self.team)

        with self.assertRaises(Http404):
            decorated_view(request)

    def test_no_team_in_request_gets_404(self):
        """Test that requests without team context get 404."""
        decorated_view = login_and_team_required(sample_view)
        request = self._create_request(self.member_user, team=None)

        with self.assertRaises(Http404):
            decorated_view(request)

    def test_preserves_view_function_name(self):
        """Test that decorator preserves the wrapped function's name."""
        decorated_view = login_and_team_required(sample_view)

        self.assertEqual(decorated_view.__name__, "sample_view")


class TestTeamAdminRequiredDecorator(TestCase):
    """Tests for team_admin_required decorator."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = Team.objects.create(name="Admin Test Team", slug="admin-test-team")
        cls.admin_user = CustomUser.objects.create_user(
            username="admin2",
            email="admin2@test.com",
            password="testpass123",
        )
        cls.member_user = CustomUser.objects.create_user(
            username="member2",
            email="member2@test.com",
            password="testpass123",
        )
        # Create memberships
        Membership.objects.create(team=cls.team, user=cls.admin_user, role=ROLE_ADMIN)
        Membership.objects.create(team=cls.team, user=cls.member_user, role=ROLE_MEMBER)

    def _create_request(self, user, team=None, path="/test/"):
        """Create a mock request with user and team."""
        request = Mock(spec=HttpRequest)
        request.user = user
        request.team = team
        request.path = path
        return request

    def test_unauthenticated_user_redirected_to_login(self):
        """Test that unauthenticated users are redirected to login."""
        decorated_view = team_admin_required(sample_view)
        request = self._create_request(Mock(is_authenticated=False), self.team)

        response = decorated_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_admin_can_access(self):
        """Test that team admins can access admin-only views."""
        decorated_view = team_admin_required(sample_view)
        request = self._create_request(self.admin_user, self.team)

        response = decorated_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Success")

    def test_regular_member_gets_404(self):
        """Test that regular members (non-admins) get 404."""
        decorated_view = team_admin_required(sample_view)
        request = self._create_request(self.member_user, self.team)

        with self.assertRaises(Http404):
            decorated_view(request)

    def test_no_team_in_request_gets_404(self):
        """Test that requests without team context get 404."""
        decorated_view = team_admin_required(sample_view)
        request = self._create_request(self.admin_user, team=None)

        with self.assertRaises(Http404):
            decorated_view(request)

    def test_preserves_view_function_name(self):
        """Test that decorator preserves the wrapped function's name."""
        decorated_view = team_admin_required(sample_view)

        self.assertEqual(decorated_view.__name__, "sample_view")


class TestDecoratorNextParameter(TestCase):
    """Tests for the 'next' parameter in login redirects."""

    def _create_request(self, path="/custom/path/"):
        """Create a mock request for unauthenticated user."""
        request = Mock(spec=HttpRequest)
        request.user = Mock(is_authenticated=False)
        request.team = None
        request.path = path
        return request

    def test_login_redirect_includes_next_path(self):
        """Test that redirect includes the original path as 'next' parameter."""
        decorated_view = login_and_team_required(sample_view)
        request = self._create_request(path="/a/my-team/dashboard/")

        response = decorated_view(request)

        self.assertIn("next=/a/my-team/dashboard/", response.url)

    def test_admin_redirect_includes_next_path(self):
        """Test that admin decorator redirect includes 'next' parameter."""
        decorated_view = team_admin_required(sample_view)
        request = self._create_request(path="/a/my-team/admin-page/")

        response = decorated_view(request)

        self.assertIn("next=/a/my-team/admin-page/", response.url)
