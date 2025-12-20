#!/usr/bin/env python3
"""
Color linting script for template files.

Detects hardcoded Tailwind color classes that should be replaced with
semantic DaisyUI colors for theme consistency.

Usage:
    python scripts/lint_colors.py templates/
    python scripts/lint_colors.py templates/ --fix-suggestions
"""

import argparse
import re
import sys
from pathlib import Path

# Patterns that indicate hardcoded colors (should use semantic alternatives)
HARDCODED_PATTERNS = {
    # Gray scale colors (should use text-base-content variants)
    r"text-(?:stone|slate|gray|zinc|neutral)-[0-9]{2,3}": "text-base-content or text-base-content/XX",
    r"bg-(?:stone|slate|gray|zinc|neutral)-[0-9]{2,3}": "bg-base-100/200/300",
    r"border-(?:stone|slate|gray|zinc|neutral)-[0-9]{2,3}": "border-base-300",
    # Status colors (should use semantic status classes)
    r"text-(?:emerald|green)-[0-9]{2,3}": "text-success or app-status-connected",
    r"text-(?:red|rose)-[0-9]{2,3}": "text-error or app-status-error",
    r"text-(?:amber|yellow|orange)-[0-9]{2,3}": "text-warning",
    r"text-(?:blue|indigo|violet)-[0-9]{2,3}": "text-info or text-primary",
    # Background status colors
    r"bg-(?:emerald|green)-[0-9]{2,3}": "bg-success",
    r"bg-(?:red|rose)-[0-9]{2,3}": "bg-error",
    r"bg-(?:amber|yellow)-[0-9]{2,3}": "bg-warning",
    r"bg-(?:blue|indigo)-[0-9]{2,3}": "bg-info or bg-primary",
    # Legacy custom colors (should use DaisyUI tokens)
    r"(?<!pg-)bg-deep(?!\w)": "bg-base-100",
    r"(?<!pg-)bg-surface(?!\w)": "bg-base-200",
    r"(?<!pg-)border-elevated(?!\w)": "border-base-300",
    # Note: text-muted is OK when used in pg-text-muted (Pegasus class)
}

# Patterns that are acceptable (don't flag these)
ALLOWED_PATTERNS = [
    # DaisyUI semantic colors
    r"text-base-content",
    r"bg-base-[123]00",
    r"border-base-[123]00",
    r"text-(?:primary|secondary|accent|neutral|info|success|warning|error)",
    r"bg-(?:primary|secondary|accent|neutral|info|success|warning|error)",
    # Status classes from design system
    r"app-status-",
    r"app-badge-",
    # Opacity variants of semantic colors
    r"text-base-content/[0-9]+",
    # Explicitly allowed for specific use cases
    r"text-white",  # OK on colored backgrounds
    r"text-black",  # OK on light backgrounds
    # Marketing terminal (always dark, intentional hardcoded)
    r"terminal-",
    # Pegasus framework classes (pg- prefix)
    r"pg-text-",
    r"pg-bg-",
    r"pg-border-",
    # Teal-400 is allowed in marketing (has light theme override)
    r"text-teal-400",
    # Brand colors for company logos (Jira, Slack, Copilot)
    r"integration-logo",  # Context marker for brand icons
    r"text-pink-500",  # Slack brand
    r"text-cyan\b",  # Slack brand
    r"text-emerald-500",  # Slack brand
    r"text-violet-[0-9]+",  # Copilot brand
    r"text-purple-[0-9]+",  # Copilot brand fallback
    r"border-(?:blue|purple|violet)-500",  # Integration card hover states
    r"text-blue-[0-9]+",  # Jira brand colors in logos
    r"text-amber-500",  # Slack brand yellow segment
]

# Files/directories to skip
SKIP_PATTERNS = [
    "**/node_modules/**",
    "**/.git/**",
    "**/static/**",
    "**/vendor/**",
]

# Legacy Pegasus templates (not used in our customized app)
LEGACY_TEMPLATE_PATTERNS = [
    "**/allauth/**",  # Pegasus allauth templates
]


def should_skip_file(path: Path) -> bool:
    """Check if file should be skipped based on patterns."""
    path_str = str(path)
    for pattern in SKIP_PATTERNS + LEGACY_TEMPLATE_PATTERNS:
        # Path.match works with ** but needs pattern to start with **
        if Path(path_str).match(pattern):
            return True
        # Also check if any path component matches (for allauth, etc.)
        if "/allauth/" in path_str:
            return True
    return False


def is_in_terminal_context(line: str) -> bool:
    """Check if the line is within terminal styling context."""
    return "terminal-" in line or "terminal_" in line


def check_file(filepath: Path, show_suggestions: bool = False) -> list[dict]:
    """Check a single file for hardcoded color patterns."""
    issues = []

    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return issues

    for line_num, line in enumerate(content.splitlines(), 1):
        # Skip lines in terminal context (intentionally dark)
        if is_in_terminal_context(line):
            continue

        # Skip if line has noqa comment
        if "noqa: COLOR" in line or "noqa:COLOR" in line:
            continue

        for pattern, suggestion in HARDCODED_PATTERNS.items():
            matches = re.findall(pattern, line)
            for match in matches:
                # Check if it's actually an allowed pattern in context
                is_allowed = any(re.search(allowed, line) for allowed in ALLOWED_PATTERNS)
                if not is_allowed:
                    issue = {
                        "file": str(filepath),
                        "line": line_num,
                        "match": match,
                        "suggestion": suggestion,
                        "context": line.strip()[:100],
                    }
                    issues.append(issue)

    return issues


def main():
    parser = argparse.ArgumentParser(description="Lint template files for hardcoded colors")
    parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to check (files or directories)",
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        help="Show fix suggestions for each issue",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output if there are issues",
    )

    args = parser.parse_args()

    all_issues = []

    for path_str in args.paths:
        path = Path(path_str)

        if path.is_file():
            if path.suffix in (".html", ".htm", ".jinja", ".jinja2"):
                issues = check_file(path, args.fix_suggestions)
                all_issues.extend(issues)
        elif path.is_dir():
            for ext in ("*.html", "*.htm", "*.jinja", "*.jinja2"):
                for filepath in path.rglob(ext):
                    if should_skip_file(filepath):
                        continue
                    issues = check_file(filepath, args.fix_suggestions)
                    all_issues.extend(issues)

    if all_issues:
        print(f"\n❌ Found {len(all_issues)} hardcoded color issue(s):\n")

        # Group by file
        by_file = {}
        for issue in all_issues:
            file = issue["file"]
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(issue)

        for file, issues in sorted(by_file.items()):
            print(f"📄 {file}")
            for issue in issues:
                print(f"   Line {issue['line']}: {issue['match']}")
                if args.fix_suggestions:
                    print(f"      → Replace with: {issue['suggestion']}")
                    print(f"      Context: {issue['context']}")
            print()

        print("💡 Tip: Add '# noqa: COLOR' comment to suppress false positives")
        print("📚 See CLAUDE.md 'Design System' section for color guidelines")
        sys.exit(1)
    else:
        if not args.quiet:
            print("✅ No hardcoded color issues found")
        sys.exit(0)


if __name__ == "__main__":
    main()
