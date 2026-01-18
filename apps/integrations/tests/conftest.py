"""Pytest configuration for integrations tests.

This conftest provides proper test isolation for the integrations tests
which heavily use signals, Waffle flags, and Celery tasks that can cause
cross-test contamination.

Key isolation mechanisms:
1. Disconnect pipeline signals that dispatch Celery tasks on Team save
2. Use DummyCache to prevent Waffle flag state pollution
3. Group tests on same xdist worker as additional safety measure
"""

import pytest


def pytest_collection_modifyitems(items):
    """Add xdist_group marker to all tests in this directory.

    This ensures all integrations tests run on the same worker,
    providing an additional layer of isolation.
    """
    for item in items:
        # Only mark tests in apps/integrations/tests/
        if "apps/integrations/tests" in str(item.fspath):
            item.add_marker(pytest.mark.xdist_group(name="integrations"))


@pytest.fixture(autouse=True)
def isolate_pipeline_signals(request):
    """Disconnect pipeline signals that cause side effects during tests.

    The post_save signal on Team dispatches Celery tasks via transaction.on_commit().
    When TeamFactory() creates a team, this signal fires and can cause test pollution.

    Exception: Tests in test_pipeline_signals.py and test_onboarding_pipeline.py
    need the signals connected because they're testing the signal behavior itself.
    """
    # Skip signal disconnection for tests that specifically test signals
    test_file = str(request.fspath)
    if "test_pipeline_signals.py" in test_file or "test_onboarding_pipeline.py" in test_file:
        yield
        return

    from django.db.models.signals import post_save

    from apps.teams.models import Team

    # Import the signal handlers
    try:
        from apps.integrations.pipeline_signals import on_pipeline_status_change

        # Disconnect the signal
        post_save.disconnect(on_pipeline_status_change, sender=Team)
        yield
        # Reconnect after test
        post_save.connect(on_pipeline_status_change, sender=Team)
    except ImportError:
        # If signal doesn't exist, just yield
        yield


@pytest.fixture(autouse=True)
def use_dummy_cache_for_waffle(settings):
    """Prevent Waffle cache pollution between tests.

    Waffle flags use Django's cache backend. Without isolation,
    flag state can leak between tests causing flaky failures.
    """
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
