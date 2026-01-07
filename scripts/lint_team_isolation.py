#!/usr/bin/env python
"""
Lint for unsafe .objects. usage on BaseTeamModel subclasses.

This script detects potential tenant isolation violations by flagging
Model.objects.method() calls that don't include a team= filter.

Rule ID: TEAM001

Usage:
    python scripts/lint_team_isolation.py apps/
    python scripts/lint_team_isolation.py apps/ --exclude-tests
    python scripts/lint_team_isolation.py apps/metrics/views.py

Suppress with: # noqa: TEAM001
"""

import argparse
import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# Models that extend BaseTeamModel - update this list if new models are added
# Run `grep -r "class.*BaseTeamModel" apps/` to find all models
TEAM_MODELS = {
    # metrics/models/team.py
    "TeamMember",
    # metrics/models/github.py
    "PullRequest",
    "PRReview",
    "PRCheckRun",
    "PRFile",
    "PRComment",
    "Commit",
    # metrics/models/jira.py
    "JiraIssue",
    # metrics/models/deployments.py
    "Deployment",
    # metrics/models/surveys.py
    "PRSurvey",
    "PRSurveyReview",
    # metrics/models/aggregations.py
    "AIUsageDaily",
    "WeeklyMetrics",
    "ReviewerCorrelation",
    "CopilotSeatSnapshot",
    "CopilotLanguageDaily",
    "CopilotEditorDaily",
    # metrics/models/insights.py
    "DailyInsight",
    # integrations/models.py
    "IntegrationCredential",
    "GitHubIntegration",
    "TrackedRepository",
    "JiraIntegration",
    "TrackedJiraProject",
    "SlackIntegration",
    "GitHubAppInstallation",
    # feedback/models.py
    "AIFeedback",
    "LLMFeedback",
    # teams_example app (for testing)
    "Player",
}

# Methods that are safe because they require explicit field values including team FK
SAFE_WRITE_METHODS = {"create", "update_or_create", "get_or_create", "bulk_create"}


@dataclass
class Violation:
    """Represents a team isolation lint violation."""

    file: str
    line: int
    col: int
    model: str
    method: str

    def __str__(self) -> str:
        return (
            f"{self.file}:{self.line}:{self.col}: TEAM001 "
            f"{self.model}.objects.{self.method}() without team filter. "
            f"Use {self.model}.for_team.{self.method}() or add team= parameter."
        )


class TeamIsolationVisitor(ast.NodeVisitor):
    """AST visitor to detect unsafe .objects. usage on BaseTeamModel subclasses."""

    def __init__(self, filename: str, source_lines: list[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[Violation] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function/method calls to check for unsafe patterns."""
        # Check for Model.objects.method() pattern
        if self._is_objects_method_call(node):
            model_name, method_name = self._extract_model_and_method(node)

            if model_name and model_name in TEAM_MODELS:
                # Check if this line has a noqa comment
                if self._has_noqa_comment(node.lineno):
                    self.generic_visit(node)
                    return

                # Check if method is in safe write methods (create, etc.)
                if method_name in SAFE_WRITE_METHODS:
                    self.generic_visit(node)
                    return

                # Check if team= is in the call arguments
                # Also check for chained .filter(team=...) calls on the same line
                if not self._has_team_filter(node) and not self._has_chained_team_filter(node.lineno):
                    self.violations.append(
                        Violation(
                            file=self.filename,
                            line=node.lineno,
                            col=node.col_offset,
                            model=model_name,
                            method=method_name,
                        )
                    )

        self.generic_visit(node)

    def _is_objects_method_call(self, node: ast.Call) -> bool:
        """Check if this is a Model.objects.method() call."""
        # Pattern: Model.objects.method()
        # AST: Call(func=Attribute(value=Attribute(value=Name, attr='objects'), attr='method'))
        if not isinstance(node.func, ast.Attribute):
            return False

        func_attr = node.func
        if not isinstance(func_attr.value, ast.Attribute):
            return False

        objects_attr = func_attr.value
        return objects_attr.attr == "objects"

    def _extract_model_and_method(self, node: ast.Call) -> tuple[str, str]:
        """Extract model name and method name from Model.objects.method() call."""
        func_attr = node.func
        method_name = func_attr.attr

        objects_attr = func_attr.value
        model_node = objects_attr.value

        model_name = model_node.id if isinstance(model_node, ast.Name) else ""

        return model_name, method_name

    def _has_team_filter(self, node: ast.Call) -> bool:
        """Check if the call has team= or related __in= in its arguments.

        Safe patterns include:
        - team=team (direct team filter)
        - related__field__in=team_scoped_var (filtering through team-scoped relation)
        - pull_request__in=prs (where prs is already team-filtered)
        """
        for keyword in node.keywords:
            if keyword.arg == "team":
                return True
            # Check for __in= patterns that filter through team-scoped relations
            # e.g., survey__pull_request__in=prs (where prs is team-scoped)
            if keyword.arg and "__in" in keyword.arg:
                return True
        return False

    def _has_chained_team_filter(self, lineno: int) -> bool:
        """Check for chained .filter(team=...) patterns on the same line.

        Example: Model.objects.filter(...).filter(team=team)
        """
        if lineno > len(self.source_lines):
            return False
        line = self.source_lines[lineno - 1]
        # Check for team= or team__ (for related lookups like team__slug)
        return "team=" in line or "team__" in line

    def _has_noqa_comment(self, lineno: int) -> bool:
        """Check if line has # noqa: TEAM001 comment."""
        if lineno > len(self.source_lines):
            return False
        line = self.source_lines[lineno - 1]
        return "noqa: TEAM001" in line or "noqa:TEAM001" in line


def lint_file(filepath: Path) -> list[Violation]:
    """Lint a single Python file for team isolation violations."""
    try:
        source = filepath.read_text()
        source_lines = source.splitlines()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []

    visitor = TeamIsolationVisitor(str(filepath), source_lines)
    visitor.visit(tree)
    return visitor.violations


def find_python_files(paths: list[Path], exclude_patterns: list[str] | None = None) -> Iterator[Path]:
    """Find Python files, excluding specified patterns."""
    exclude_patterns = exclude_patterns or []

    for path in paths:
        if path.is_file() and path.suffix == ".py":
            # Check exclusions for single file
            skip = False
            for pattern in exclude_patterns:
                if pattern in str(path):
                    skip = True
                    break
            if not skip:
                yield path
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                # Skip excluded patterns
                skip = False
                for pattern in exclude_patterns:
                    if pattern in str(py_file):
                        skip = True
                        break
                if not skip:
                    yield py_file


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lint for unsafe .objects. usage on BaseTeamModel subclasses")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["apps"],
        help="Paths to check (default: apps/)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Patterns to exclude (e.g., --exclude /tests/ --exclude /migrations/)",
    )
    parser.add_argument(
        "--exclude-tests",
        action="store_true",
        help="Exclude test files (*/tests/*)",
    )

    args = parser.parse_args()

    # Build exclusion list
    exclude_patterns = list(args.exclude) if args.exclude else []
    if args.exclude_tests:
        exclude_patterns.append("/tests/")
        exclude_patterns.append("_test.py")
        exclude_patterns.append("/tests.py")  # e.g., apps/teams_example/tests.py
    exclude_patterns.append("/migrations/")  # Always exclude migrations

    # Convert paths
    paths = [Path(p) for p in args.paths]

    # Find and lint files
    all_violations = []
    for filepath in find_python_files(paths, exclude_patterns):
        violations = lint_file(filepath)
        all_violations.extend(violations)

    # Print violations sorted by file and line
    for v in sorted(all_violations, key=lambda x: (x.file, x.line)):
        print(v)

    # Summary
    if all_violations:
        print(
            f"\nFound {len(all_violations)} team isolation violation(s)",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
