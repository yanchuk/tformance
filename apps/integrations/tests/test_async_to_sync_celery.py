"""Tests for async pattern enforcement in Celery tasks.

This module verifies that Celery task modules use async_to_sync() instead of
asyncio.run() when calling async functions. Using asyncio.run() in Celery
breaks Django's thread-local storage for database connections, causing
silent failures.

Reference: CLAUDE.md - Celery Async Warning
"""

import ast
from pathlib import Path

from django.test import TestCase


class TestAsyncPatternEnforcement(TestCase):
    """Tests that verify correct async patterns in Celery task modules."""

    def _get_task_modules_dir(self) -> Path:
        """Get the path to the _task_modules directory."""
        return Path(__file__).parent.parent / "_task_modules"

    def _find_asyncio_run_calls(self, filepath: Path) -> list[tuple[int, str]]:
        """Find all asyncio.run() calls in a Python file using AST.

        Returns list of (line_number, code_snippet) tuples.
        """
        violations = []

        with open(filepath) as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return violations  # Skip files with syntax errors

        for node in ast.walk(tree):
            # Look for Call nodes where func is an Attribute named 'run'
            # and the value is a Name 'asyncio'
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "asyncio"
            ):
                # Found asyncio.run() call
                lineno = node.lineno
                # Get the line from source
                lines = source.split("\n")
                if lineno <= len(lines):
                    code_line = lines[lineno - 1].strip()
                    violations.append((lineno, code_line))

        return violations

    def test_no_asyncio_run_in_task_modules(self):
        """Verify that _task_modules/*.py files don't use asyncio.run().

        asyncio.run() creates a new event loop which breaks Django's
        @sync_to_async(thread_sensitive=True) decorators, causing database
        operations to silently fail in Celery workers.

        Use async_to_sync() from asgiref instead.
        """
        task_modules_dir = self._get_task_modules_dir()

        if not task_modules_dir.exists():
            self.skipTest(f"Task modules directory not found: {task_modules_dir}")

        all_violations = {}

        for py_file in task_modules_dir.glob("*.py"):
            # Skip __init__.py and test files
            if py_file.name.startswith("__") or py_file.name.startswith("test_"):
                continue

            violations = self._find_asyncio_run_calls(py_file)
            if violations:
                all_violations[py_file.name] = violations

        if all_violations:
            error_msg = [
                "\n\nFound asyncio.run() usage in Celery task modules!",
                "This causes silent database failures in Celery workers.",
                "",
                "Use async_to_sync() instead:",
                "  from asgiref.sync import async_to_sync",
                "  result = async_to_sync(async_function)(args)",
                "",
                "Violations found:",
            ]
            for filename, violations in all_violations.items():
                error_msg.append(f"\n  {filename}:")
                for lineno, code in violations:
                    error_msg.append(f"    Line {lineno}: {code}")

            self.fail("\n".join(error_msg))

    def test_pr_data_uses_async_to_sync(self):
        """Specifically test that pr_data.py uses async_to_sync for GraphQL calls."""
        pr_data_file = self._get_task_modules_dir() / "pr_data.py"

        if not pr_data_file.exists():
            self.skipTest("pr_data.py not found")

        with open(pr_data_file) as f:
            source = f.read()

        # Check that async_to_sync is imported
        has_async_to_sync_import = "from asgiref.sync import async_to_sync" in source

        # Check that asyncio.run is NOT used (except in comments)
        violations = self._find_asyncio_run_calls(pr_data_file)

        if violations and not has_async_to_sync_import:
            self.fail(
                f"pr_data.py uses asyncio.run() but doesn't import async_to_sync.\n"
                f"Found {len(violations)} asyncio.run() call(s).\n"
                "Replace with: async_to_sync(async_function)(args)"
            )

        if violations:
            violation_details = "\n".join(f"  Line {ln}: {code}" for ln, code in violations)
            self.fail(
                f"pr_data.py still uses asyncio.run() which causes silent DB failures:\n"
                f"{violation_details}\n\n"
                f"Replace with async_to_sync(fetch_pr_complete_data_graphql)(pr, tracked_repo)"
            )


class TestAsyncToSyncImports(TestCase):
    """Verify async_to_sync is properly imported where async functions are called."""

    def test_github_sync_imports_async_to_sync(self):
        """Verify github_sync.py has async_to_sync import."""
        github_sync_file = Path(__file__).parent.parent / "_task_modules" / "github_sync.py"

        if not github_sync_file.exists():
            self.skipTest("github_sync.py not found")

        with open(github_sync_file) as f:
            source = f.read()

        self.assertIn(
            "from asgiref.sync import async_to_sync",
            source,
            "github_sync.py should import async_to_sync for calling async GraphQL functions",
        )

    def test_pr_data_imports_async_to_sync(self):
        """Verify pr_data.py has async_to_sync import after fix."""
        pr_data_file = Path(__file__).parent.parent / "_task_modules" / "pr_data.py"

        if not pr_data_file.exists():
            self.skipTest("pr_data.py not found")

        with open(pr_data_file) as f:
            source = f.read()

        # Check if file calls any async functions (indicated by graphql imports)
        if "fetch_pr_complete_data_graphql" in source:
            self.assertIn(
                "from asgiref.sync import async_to_sync",
                source,
                "pr_data.py calls async functions but doesn't import async_to_sync. "
                "Use async_to_sync() instead of asyncio.run() for Celery tasks.",
            )
