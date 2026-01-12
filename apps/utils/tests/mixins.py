"""Reusable test mixins for common setUp patterns.

These mixins use setUpTestData() to create fixtures ONCE per test class,
rather than setUp() which runs for EVERY test method. This provides
significant performance improvements for read-only tests.

Usage:
    from apps.utils.tests.mixins import TeamWithAdminMemberMixin
    from django.test import TestCase

    class TestMyView(TeamWithAdminMemberMixin, TestCase):
        # team, admin_user, member_user available automatically

        def test_view_requires_auth(self):
            response = self.client.get("/my-url/")
            self.assertEqual(response.status_code, 302)

When to use setUpTestData (via these mixins):
    - Tests that only READ fixture data
    - Tests checking response codes, templates, context
    - Tests that use assertEqual, assertIn, assertQuerysetEqual

When to keep setUp instead:
    - Tests that MODIFY fixture data (.save(), .delete(), .update())
    - Tests manipulating team context
    - Tests with per-test mock requirements
    - Async tests (use TransactionTestCase)
"""

from django.test import Client

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory, UserFactory
from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class TeamWithAdminMemberMixin:
    """Mixin providing team with admin and member users.

    Use for view tests that need authenticated users with team access.
    Most common pattern - covers 26+ test classes.

    Provides:
        - self.team: Team instance
        - self.admin_user: User with ROLE_ADMIN
        - self.member_user: User with ROLE_MEMBER
        - self.client: Django test client (fresh per test)

    Example:
        class TestAdminView(TeamWithAdminMemberMixin, TestCase):
            def test_admin_can_access(self):
                self.client.force_login(self.admin_user)
                response = self.client.get("/admin-only/")
                self.assertEqual(response.status_code, 200)
    """

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified data for all test methods (runs once per class)."""
        cls.team = TeamFactory()
        cls.admin_user = UserFactory()
        cls.member_user = UserFactory()
        cls.team.members.add(cls.admin_user, through_defaults={"role": ROLE_ADMIN})
        cls.team.members.add(cls.member_user, through_defaults={"role": ROLE_MEMBER})

    def setUp(self):
        """Set up client for each test method (stateful, needs reset)."""
        self.client = Client()


class TeamWithGitHubMixin(TeamWithAdminMemberMixin):
    """Mixin providing team with GitHub integration.

    Extends TeamWithAdminMemberMixin with GitHub-specific fixtures.
    Use for tests that need GitHub integration context.

    Provides all from TeamWithAdminMemberMixin plus:
        - self.integration: GitHubIntegration instance
        - self.repo: TrackedRepository instance

    Example:
        class TestGitHubSync(TeamWithGitHubMixin, TestCase):
            def test_sync_creates_prs(self):
                # integration and repo available
                self.assertEqual(self.repo.team, self.team)
    """

    @classmethod
    def setUpTestData(cls):
        """Set up GitHub integration fixtures."""
        super().setUpTestData()
        cls.integration = GitHubIntegrationFactory(team=cls.team)
        cls.repo = TrackedRepositoryFactory(team=cls.team, integration=cls.integration)


class TeamWithMembersMixin:
    """Mixin providing team with TeamMember instances.

    Use for tests that need team members (not users) - e.g., PR author/reviewer tests.
    Different from TeamWithAdminMemberMixin which creates Users.

    Provides:
        - self.team: Team instance
        - self.member1: TeamMember (display_name="Alice")
        - self.member2: TeamMember (display_name="Bob")
        - self.member3: TeamMember (display_name="Charlie")

    Example:
        class TestPRMetrics(TeamWithMembersMixin, TestCase):
            def test_pr_has_author(self):
                pr = PullRequestFactory(team=self.team, author=self.member1)
                self.assertEqual(pr.author.display_name, "Alice")
    """

    @classmethod
    def setUpTestData(cls):
        """Set up TeamMember fixtures."""
        cls.team = TeamFactory()
        cls.member1 = TeamMemberFactory(team=cls.team, display_name="Alice")
        cls.member2 = TeamMemberFactory(team=cls.team, display_name="Bob")
        cls.member3 = TeamMemberFactory(team=cls.team, display_name="Charlie")


class TeamWithPRDataMixin(TeamWithMembersMixin):
    """Mixin providing team with PR data for dashboard/metrics tests.

    Extends TeamWithMembersMixin with sample PR data.
    Use for tests that need existing PR data to query.

    Provides all from TeamWithMembersMixin plus:
        - self.prs: List of 5 PullRequest instances
        - self.reviews: List of PRReview instances (1 per PR)

    Example:
        class TestDashboardMetrics(TeamWithPRDataMixin, TestCase):
            def test_dashboard_shows_prs(self):
                self.assertEqual(len(self.prs), 5)
    """

    @classmethod
    def setUpTestData(cls):
        """Set up PR fixtures."""
        from apps.metrics.factories import PRReviewFactory, PullRequestFactory

        super().setUpTestData()

        # Create 5 PRs distributed across members
        cls.prs = []
        members = [cls.member1, cls.member2, cls.member3]
        for i in range(5):
            author = members[i % 3]
            cls.prs.append(PullRequestFactory(team=cls.team, author=author))

        # Create 1 review per PR
        cls.reviews = []
        for pr in cls.prs:
            possible_reviewers = [m for m in members if m != pr.author]
            reviewer = possible_reviewers[0] if possible_reviewers else members[0]
            cls.reviews.append(PRReviewFactory(team=cls.team, pull_request=pr, reviewer=reviewer))
