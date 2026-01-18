"""Root pytest fixtures for tformance project.

Performance-Optimized Fixtures
------------------------------
When writing tests, prefer using these shared fixtures over creating your own
test data in setUp(). This reduces database operations and speeds up tests.

Key Fixtures:
- team: Basic team fixture
- team_with_members: Team with 5 members
- team_context: Sets team in context var, cleans up after test
- authenticated_team_client: Logged-in client with team access
- sample_prs: 10 PRs with reviews and commits

For Django TestCase with Class-Level Sharing:
Use setUpTestData() for class-level shared data:

    class TestSomething(TestCase):
        @classmethod
        def setUpTestData(cls):
            cls.team = TeamFactory()
            cls.members = TeamMemberFactory.create_batch(5, team=cls.team)

        def test_read_only_operation(self):
            assert len(self.members) == 5
"""

import pytest
from django.test import Client


# Override production security settings for tests
# (production settings enable these when DEBUG=False)
@pytest.fixture(scope="session", autouse=True)
def configure_test_settings(django_db_setup):
    """Configure settings for test environment."""
    from django.conf import settings

    # Disable HTTPS redirect for test client
    settings.SECURE_SSL_REDIRECT = False

    # Allow silent empty queryset when team context is missing
    # (production raises EmptyTeamContextException)
    settings.STRICT_TEAM_CONTEXT = False


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the cache before each test to avoid cross-test contamination.

    This is especially important for webhook idempotency checks that use cache.
    """
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def mock_pipeline_task_dispatch():
    """Mock pipeline task dispatch for ALL tests to prevent cross-test pollution.

    The pipeline signals dispatch Celery tasks when Team is saved. By mocking
    at the dispatch level:
    - Signals still fire (so signal wiring is tested)
    - Tasks aren't actually invoked
    - No timing issues with setUp() vs fixture ordering

    This fixture prevents the "51 calls instead of 1" flaky test failures caused
    by mocks capturing calls from other tests in the same xdist worker.
    """
    from unittest.mock import patch

    # Import and store the original function BEFORE patching
    from apps.integrations.pipeline_signals import (
        dispatch_pipeline_task as original_dispatch,
    )

    with patch(
        "apps.integrations.pipeline_signals.dispatch_pipeline_task",
        return_value=False,
    ) as mock:
        # Store original for enable_pipeline_dispatch fixture
        mock._original_dispatch = original_dispatch
        yield mock


@pytest.fixture
def enable_pipeline_dispatch(mock_pipeline_task_dispatch):
    """Allow real pipeline task dispatch for tests that need it.

    Use this fixture in tests that verify actual task dispatch behavior,
    such as test_pipeline_signals.py and test_onboarding_pipeline.py.

    This works by setting side_effect to call the original function,
    so the mock still tracks calls but executes the real dispatch logic.

    Usage:
        @pytest.mark.usefixtures("enable_pipeline_dispatch")
        class TestPipelineSignals:
            def test_signal_dispatches_task(self):
                # Real dispatch happens here
                ...
    """
    # Set side_effect to call the original function
    # This makes the mock pass through to real implementation while still tracking calls
    original = mock_pipeline_task_dispatch._original_dispatch
    mock_pipeline_task_dispatch.side_effect = original
    mock_pipeline_task_dispatch.reset_mock()
    yield
    # Restore mock behavior after test
    mock_pipeline_task_dispatch.side_effect = None


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def admin_client(admin_user):
    """Logged-in admin client."""
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def team(db):
    """Create a team for testing."""
    from apps.metrics.factories import TeamFactory

    return TeamFactory()


@pytest.fixture
def user(db):
    """Create a user for testing."""
    from apps.integrations.factories import UserFactory

    return UserFactory()


@pytest.fixture
def team_member(team):
    """Create a team member for testing."""
    from apps.metrics.factories import TeamMemberFactory

    return TeamMemberFactory(team=team)


# =============================================================================
# Performance-Optimized Fixtures
# =============================================================================


@pytest.fixture
def team_with_members(db):
    """Create a team with 5 members for testing.

    Returns:
        tuple: (team, list of 5 TeamMember instances)

    Usage:
        def test_something(team_with_members):
            team, members = team_with_members
            assert len(members) == 5
    """
    from apps.metrics.factories import TeamFactory, TeamMemberFactory

    team = TeamFactory()
    members = TeamMemberFactory.create_batch(5, team=team)
    return team, members


@pytest.fixture
def team_context(team):
    """Set team in context for the duration of the test.

    This fixture sets the current team context (used by for_team manager)
    and automatically cleans up after the test.

    Usage:
        def test_team_scoped_query(team_context):
            # team context is set, for_team manager will work
            prs = PullRequest.for_team.all()
    """
    from apps.teams.context import set_current_team, unset_current_team

    token = set_current_team(team)
    yield team
    unset_current_team(token)


@pytest.fixture
def authenticated_team_client(team, user, db):
    """Create an authenticated client with team membership.

    Creates a user with team admin access and returns a logged-in client.

    Returns:
        tuple: (client, team, user)

    Usage:
        def test_authenticated_view(authenticated_team_client):
            client, team, user = authenticated_team_client
            response = client.get("/app/")
            assert response.status_code == 200
    """
    from apps.teams.models import Membership
    from apps.teams.roles import ROLE_ADMIN

    # Create team membership for user
    Membership.objects.create(team=team, user=user, role=ROLE_ADMIN)

    test_client = Client()
    test_client.force_login(user)
    return test_client, team, user


@pytest.fixture
def sample_prs(db):
    """Create 10 PRs with reviews and commits for testing.

    Returns:
        dict with keys:
        - team: Team instance
        - members: list of 3 TeamMember instances
        - prs: list of 10 PullRequest instances
        - reviews: list of PRReview instances (1 per PR)
        - commits: list of Commit instances (2-5 per PR)

    Usage:
        def test_pr_metrics(sample_prs):
            assert len(sample_prs['prs']) == 10
    """
    from apps.metrics.factories import (
        CommitFactory,
        PRReviewFactory,
        PullRequestFactory,
        TeamFactory,
        TeamMemberFactory,
    )

    team = TeamFactory()
    members = TeamMemberFactory.create_batch(3, team=team)

    # Create 10 PRs distributed across members
    prs = []
    for i in range(10):
        author = members[i % 3]
        prs.append(PullRequestFactory(team=team, author=author))

    # Create 1 review per PR
    reviews = []
    for pr in prs:
        # Select a reviewer that isn't the author
        possible_reviewers = [m for m in members if m != pr.author]
        reviewer = possible_reviewers[0] if possible_reviewers else members[0]
        reviews.append(PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer))

    # Create 2-5 commits per PR
    commits = []
    for pr in prs:
        num_commits = 2 + (pr.github_pr_id % 4)  # 2-5 commits deterministically
        for _ in range(num_commits):
            commits.append(CommitFactory(team=team, pull_request=pr, author=pr.author))

    return {
        "team": team,
        "members": members,
        "prs": prs,
        "reviews": reviews,
        "commits": commits,
    }
