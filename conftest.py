"""Root pytest fixtures for tformance project."""

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
    from apps.teams.factories import TeamFactory

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
