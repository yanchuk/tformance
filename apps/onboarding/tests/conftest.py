"""Pytest configuration for onboarding tests.

Provides proper test isolation for onboarding tests which use Waffle flags
that can cause cross-test contamination when running in parallel.
"""

import pytest


@pytest.fixture(autouse=True)
def use_dummy_cache_for_waffle(settings):
    """Prevent Waffle cache pollution between tests.

    Waffle flags use Django's cache backend. Without isolation,
    flag state can leak between tests causing flaky failures.
    """
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
