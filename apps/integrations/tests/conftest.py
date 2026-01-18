"""Pytest configuration for integrations tests.

This conftest applies xdist_group marker to ALL tests in this directory
to ensure they run on the same pytest-xdist worker, preventing cross-test
contamination that causes flaky failures.

The integrations tests heavily share database state (Teams, Integrations, Flags)
which can interfere when running in parallel across workers.
"""

import pytest


def pytest_collection_modifyitems(items):
    """Add xdist_group marker to all tests in this directory.

    This ensures all integrations tests run on the same worker,
    preventing database state contamination between tests.
    """
    for item in items:
        # Only mark tests in apps/integrations/tests/
        if "apps/integrations/tests" in str(item.fspath):
            item.add_marker(pytest.mark.xdist_group(name="integrations"))
