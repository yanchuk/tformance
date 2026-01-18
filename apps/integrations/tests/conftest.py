"""Pytest configuration for integrations tests.

This conftest provides additional test isolation for the integrations tests
which heavily use Waffle flags and Celery tasks.

Key isolation mechanisms:
1. Pipeline task dispatch is mocked globally (in root conftest.py)
2. Use DummyCache to prevent Waffle flag state pollution
3. Group tests on same xdist worker as additional safety measure

Note: Signal disconnection was moved to root conftest.py as a global mock
of dispatch_pipeline_task. Tests that need real dispatch behavior should
use the `enable_pipeline_dispatch` fixture.
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
def use_dummy_cache_for_waffle(settings):
    """Prevent Waffle cache pollution between tests.

    Waffle flags use Django's cache backend. Without isolation,
    flag state can leak between tests causing flaky failures.
    """
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
