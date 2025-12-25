"""Export prompts and configuration for promptfoo testing.

This module generates promptfoo configuration from Jinja2 templates,
eliminating manual sync between code and test files.

The prompt is rendered from templates in:
    apps/metrics/prompts/templates/

Usage:
    from apps.metrics.prompts.export import export_promptfoo_config
    export_promptfoo_config(Path("dev/active/ai-detection-pr-descriptions/experiments"))

Or via management command:
    python manage.py export_prompts
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from apps.metrics.prompts.golden_tests import GOLDEN_TESTS, GoldenTest
from apps.metrics.prompts.render import render_system_prompt, render_user_prompt
from apps.metrics.services.llm_prompts import PROMPT_VERSION


def get_promptfoo_config(prompt_filename: str) -> dict[str, Any]:
    """Generate promptfoo configuration dictionary.

    Args:
        prompt_filename: Filename of the system prompt (e.g., "v6.2.0-system.txt")

    Returns:
        Dictionary representing promptfoo.yaml configuration
    """
    # Inline the full system prompt so it's visible in promptfoo UI
    system_prompt_content = render_system_prompt()

    return {
        "description": f"AI Detection Prompt Evaluation (v{PROMPT_VERSION}) - Auto-generated",
        "providers": [
            {
                "id": "groq:openai/gpt-oss-20b",
                "label": "GPT-OSS-20B",
                "config": {
                    "temperature": 0,
                    "max_tokens": 800,
                    "include_reasoning": False,  # Disable "Thinking:" prefix
                    "response_format": {"type": "json_object"},
                },
            },
        ],
        "prompts": [
            {
                "id": f"v{PROMPT_VERSION}",
                # user_prompt is pre-rendered with all PR context by _render_user_prompt()
                # This ensures the full context is visible in promptfoo UI
                "raw": (
                    "[\n"
                    '  {"role": "system", "content": "{{system_prompt}}"},\n'
                    '  {"role": "user", "content": "{{user_prompt}}"}\n'
                    "]"
                ),
            }
        ],
        "defaultTest": {
            "vars": {
                # Inline full system prompt for visibility in promptfoo UI
                "system_prompt": system_prompt_content,
                "user_prompt": "Analyze this pull request:\n\n(No PR data provided)",
            }
        },
        "tests": _get_test_cases_from_golden(),
        "outputPath": "./results/promptfoo-results.json",
        "evaluateOptions": {
            "maxConcurrency": 5,
            "showProgressBar": True,
        },
    }


def _get_schema_validation_assertion() -> dict[str, Any]:
    """Get a JavaScript assertion that validates response schema.

    Returns a promptfoo assertion that checks basic structure.
    Simple expression (no IIFE) for promptfoo compatibility.
    """
    # Simple validation - check required top-level keys exist
    return {
        "type": "javascript",
        "value": (
            "typeof JSON.parse(output).ai === 'object' && "
            "typeof JSON.parse(output).tech === 'object' && "
            "typeof JSON.parse(output).summary === 'object' && "
            "typeof JSON.parse(output).health === 'object'"
        ),
        "description": "Response has required sections (ai, tech, summary, health)",
    }


def _render_user_prompt_from_test(test: GoldenTest) -> str:
    """Render the full user prompt for a GoldenTest using Jinja templates.

    This pre-renders the complete prompt with all PR context so it's visible
    in the promptfoo UI for each test case. Uses render_user_prompt() which
    is the Jinja-based equivalent of get_user_prompt().

    Args:
        test: The golden test case

    Returns:
        Fully rendered user prompt string
    """
    return render_user_prompt(
        pr_body=test.pr_body,
        pr_title=test.pr_title,
        file_count=test.file_count,
        additions=test.additions,
        deletions=test.deletions,
        comment_count=test.comment_count,
        repo_languages=test.repo_languages if test.repo_languages else None,
        state=test.state,
        labels=test.labels if test.labels else None,
        is_draft=test.is_draft,
        is_hotfix=test.is_hotfix,
        is_revert=test.is_revert,
        cycle_time_hours=test.cycle_time_hours,
        review_time_hours=test.review_time_hours,
        commits_after_first_review=test.commits_after_first_review,
        review_rounds=test.review_rounds,
        file_paths=test.file_paths if test.file_paths else None,
        commit_messages=test.commit_messages if test.commit_messages else None,
        milestone=test.milestone,
        assignees=test.assignees if test.assignees else None,
        linked_issues=test.linked_issues if test.linked_issues else None,
        jira_key=test.jira_key,
        author_name=test.author_name,
        reviewers=test.reviewers if test.reviewers else None,
        review_comments=test.review_comments if test.review_comments else None,
        timeline=test.timeline,
        repo_name=test.repo_name,
    )


def _to_promptfoo_test_with_rendered_prompt(test: GoldenTest, schema_assertion: dict[str, Any]) -> dict[str, Any]:
    """Convert a GoldenTest to promptfoo test format with pre-rendered user_prompt.

    Args:
        test: The golden test case
        schema_assertion: The schema validation assertion to include

    Returns:
        Dictionary in promptfoo test format with full user_prompt
    """
    assertions: list[dict[str, Any]] = [
        {"type": "is-json"},
        schema_assertion,
    ]

    # AI detection assertions
    if test.expected_ai_assisted is not None:
        value = "true" if test.expected_ai_assisted else "false"
        assertions.append(
            {
                "type": "javascript",
                "value": f"JSON.parse(output).ai.is_assisted === {value}",
            }
        )

    # Expected tools assertions
    for tool in test.expected_tools:
        assertions.append(
            {
                "type": "javascript",
                "value": f'JSON.parse(output).ai.tools.includes("{tool}")',
            }
        )

    # Not-expected tools assertions
    for tool in test.expected_not_tools:
        assertions.append(
            {
                "type": "javascript",
                "value": f'!JSON.parse(output).ai.tools.includes("{tool}")',
            }
        )

    # Confidence threshold assertion
    if test.min_confidence > 0:
        assertions.append(
            {
                "type": "javascript",
                "value": f"JSON.parse(output).ai.confidence >= {test.min_confidence}",
            }
        )

    # Category assertions
    for category in test.expected_categories:
        assertions.append(
            {
                "type": "javascript",
                "value": f'JSON.parse(output).tech.categories.includes("{category}")',
            }
        )

    # PR type assertion
    if test.expected_pr_type:
        assertions.append(
            {
                "type": "javascript",
                "value": f'JSON.parse(output).summary.type === "{test.expected_pr_type}"',
            }
        )

    return {
        "description": f"[{test.id}] {test.description}",
        "vars": {
            "user_prompt": _render_user_prompt_from_test(test),
        },
        "assert": assertions,
    }


def _get_test_cases_from_golden() -> list[dict[str, Any]]:
    """Generate promptfoo test cases from GOLDEN_TESTS.

    Converts all GoldenTest instances to promptfoo format with
    pre-rendered user prompts showing full PR context.

    Returns:
        List of promptfoo test case dictionaries
    """
    schema_assertion = _get_schema_validation_assertion()
    return [_to_promptfoo_test_with_rendered_prompt(test, schema_assertion) for test in GOLDEN_TESTS]


def export_promptfoo_config(output_dir: Path) -> dict[str, Path]:
    """Export promptfoo configuration and prompt files.

    Args:
        output_dir: Directory to write files to

    Returns:
        Dictionary mapping file types to created paths:
        {
            "prompt": Path to system prompt file,
            "config": Path to promptfoo.yaml
        }
    """
    output_dir = Path(output_dir)
    prompts_dir = output_dir / "prompts"

    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write system prompt to versioned file (rendered from templates)
    prompt_filename = f"v{PROMPT_VERSION}-system.txt"
    prompt_path = prompts_dir / prompt_filename
    prompt_path.write_text(render_system_prompt())

    # 2. Generate and write promptfoo.yaml
    config = get_promptfoo_config(prompt_filename)
    config_path = output_dir / "promptfoo.yaml"

    # Use custom representer for cleaner YAML output
    yaml.add_representer(str, _str_representer)
    with open(config_path, "w") as f:
        f.write("# Auto-generated by: python manage.py export_prompts\n")
        f.write(f"# Prompt version: {PROMPT_VERSION}\n")
        f.write("# DO NOT EDIT - regenerate with export_prompts command\n\n")
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return {
        "prompt": prompt_path,
        "config": config_path,
    }


def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.Node:
    """Custom string representer for cleaner multi-line YAML output."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)
