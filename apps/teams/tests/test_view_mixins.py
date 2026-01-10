from django.contrib.auth.models import AnonymousUser
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View

from apps.teams.middleware import TeamsMiddleware
from apps.teams.mixins import LoginAndTeamRequiredMixin, TeamAdminRequiredMixin
from apps.teams.models import Team
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER
from apps.users.models import CustomUser


class BaseView(View):
    def get(self, *args, **kwargs) -> HttpResponse:
        return HttpResponse(f"Go {self.request.team.slug}")


class MemberView(LoginAndTeamRequiredMixin, BaseView):
    pass


class AdminView(TeamAdminRequiredMixin, BaseView):
    pass


class TeamMixinTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = RequestFactory()

        cls.sox = Team.objects.create(name="Red Sox", slug="sox")
        cls.yanks = Team.objects.create(name="Yankees", slug="yanks")

        cls.sox_admin = CustomUser.objects.create(username="tito@redsox.com")
        cls.sox_member = CustomUser.objects.create(username="papi@redsox.com")
        cls.sox.members.add(cls.sox_admin, through_defaults={"role": ROLE_ADMIN})
        cls.sox.members.add(cls.sox_member, through_defaults={"role": ROLE_MEMBER})

        cls.yanks_admin = CustomUser.objects.create(username="joe.torre@yankees.com")
        cls.yanks_member = CustomUser.objects.create(username="derek.jeter@yankees.com")
        cls.yanks.members.add(cls.yanks_admin, through_defaults={"role": ROLE_ADMIN})
        cls.yanks.members.add(cls.yanks_member, through_defaults={"role": ROLE_MEMBER})

        # User with no team membership
        cls.teamless_user = CustomUser.objects.create(username="no.team@example.com")

    def _call_view(self, view_cls, user, team=None):
        """Call view with team selected via ?team= query parameter."""
        url = f"/team/?team={team.id}" if team else "/team/"
        request = self.factory.get(url)
        request.user = user or AnonymousUser()
        request.session = {}
        view_kwargs = {}

        def get_response(req):
            return view_cls.as_view()(req, **view_kwargs)

        middleware = TeamsMiddleware(get_response=get_response)
        middleware.process_view(request, None, None, view_kwargs)
        return middleware(request)

    def assertSuccessfulRequest(self, view_cls, user, team):
        response = self._call_view(view_cls, user, team)
        self.assertEqual(200, response.status_code)
        self.assertEqual(f"Go {team.slug}", response.content.decode("utf-8"))

    def assertRedirectToLogin(self, view_cls, user, team=None):
        response = self._call_view(view_cls, user, team)
        self.assertEqual(302, response.status_code)
        self.assertTrue("/login/" in response.url)

    def assertNotFound(self, view_cls, user, team=None):
        with self.assertRaises(Http404):
            self._call_view(view_cls, user, team)

    def test_anonymous_user_redirect_to_login(self):
        """Anonymous users should redirect to login regardless of team requested."""
        for view_cls in [MemberView, AdminView]:
            self.assertRedirectToLogin(view_cls, AnonymousUser(), self.sox)
            self.assertRedirectToLogin(view_cls, AnonymousUser(), self.yanks)
            self.assertRedirectToLogin(view_cls, AnonymousUser())  # No team param

    def test_member_view_logged_in(self):
        """Members can access views for their own team."""
        # Sox members can access Sox team
        for user in [self.sox_member, self.sox_admin]:
            self.assertSuccessfulRequest(MemberView, user, self.sox)

        # Yankees members can access Yankees team
        for user in [self.yanks_member, self.yanks_admin]:
            self.assertSuccessfulRequest(MemberView, user, self.yanks)

    def test_invalid_team_falls_back_to_default(self):
        """
        When user requests team they're not member of via ?team= param,
        they get their default team (first team they belong to).
        """
        # Sox member requests Yankees → falls back to Sox (their default team)
        response = self._call_view(MemberView, self.sox_member, self.yanks)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Go sox", response.content.decode("utf-8"))

        # Yankees member requests Sox → falls back to Yankees (their default team)
        response = self._call_view(MemberView, self.yanks_member, self.sox)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Go yanks", response.content.decode("utf-8"))

    def test_user_without_team_gets_404(self):
        """Users with no team membership get 404."""
        self.assertNotFound(MemberView, self.teamless_user, self.sox)
        self.assertNotFound(MemberView, self.teamless_user)  # No team param either

    def test_admin_only_views(self):
        """Admin views only accessible by team admins, not regular members."""
        # Admin can access admin view
        self.assertSuccessfulRequest(AdminView, self.sox_admin, self.sox)
        self.assertSuccessfulRequest(AdminView, self.yanks_admin, self.yanks)

        # Member cannot access admin view (gets 404)
        self.assertNotFound(AdminView, self.sox_member, self.sox)
        self.assertNotFound(AdminView, self.yanks_member, self.yanks)

    def test_admin_cross_team_falls_back(self):
        """
        Admin from one team requesting another team via ?team= falls back
        to their default team. They succeed only if they're admin of default team.
        """
        # Yankees admin requests Sox → falls back to Yankees → succeeds (is admin)
        response = self._call_view(AdminView, self.yanks_admin, self.sox)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Go yanks", response.content.decode("utf-8"))

        # Yankees member requests Sox → falls back to Yankees → 404 (not admin)
        self.assertNotFound(AdminView, self.yanks_member, self.sox)
