#!/usr/bin/env -S uv run
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")

    # Set test-specific environment variables when running tests
    # These are safe test values that should never be used in production
    if "test" in sys.argv:
        os.environ.setdefault(
            "INTEGRATION_ENCRYPTION_KEY",
            "r8pmePXvrfFN4L_IjvTbZP3hWPTIN0y4KDw2wbuIRYg=",
        )
        os.environ.setdefault(
            "SECRET_KEY",
            "django-insecure-test-key-for-unit-tests-only-never-use-in-production",
        )
        os.environ.setdefault("DEBUG", "True")
        os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
