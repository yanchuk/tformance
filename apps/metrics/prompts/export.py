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

from apps.metrics.prompts.golden_tests import GOLDEN_TESTS, to_promptfoo_test
from apps.metrics.prompts.render import render_system_prompt
from apps.metrics.services.llm_prompts import PROMPT_VERSION


def get_promptfoo_config(prompt_filename: str) -> dict[str, Any]:
    """Generate promptfoo configuration dictionary.

    Args:
        prompt_filename: Filename of the system prompt (e.g., "v6.2.0-system.txt")

    Returns:
        Dictionary representing promptfoo.yaml configuration
    """
    return {
        "description": f"AI Detection Prompt Evaluation (v{PROMPT_VERSION}) - Auto-generated",
        "providers": [
            {
                "id": "groq:llama-3.3-70b-versatile",
                "config": {
                    "temperature": 0,
                    "max_tokens": 800,
                    "response_format": {"type": "json_object"},
                },
            }
        ],
        "prompts": [
            {
                "id": f"v{PROMPT_VERSION}",
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
                "system_prompt": f"file://prompts/{prompt_filename}",
                "user_prompt": (
                    "Analyze this pull request:\n\n"
                    "Title: {{pr_title}}\n"
                    "Lines: +{{additions}}/-{{deletions}}\n\n"
                    "Description:\n{{pr_body}}"
                ),
                "pr_title": "",
                "pr_body": "",
                "additions": 0,
                "deletions": 0,
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

    Returns a promptfoo assertion that checks:
    - Response has all required top-level keys (ai, tech, summary, health)
    - AI object has required fields (is_assisted, tools, confidence)
    - Confidence is within valid range (0.0-1.0)
    - Enums contain valid values
    """
    # JavaScript code to validate the schema
    validation_code = """
(function() {
    const data = JSON.parse(output);

    // Check required top-level keys
    const requiredKeys = ['ai', 'tech', 'summary', 'health'];
    for (const key of requiredKeys) {
        if (!(key in data)) return false;
    }

    // Validate AI section
    const ai = data.ai;
    if (typeof ai.is_assisted !== 'boolean') return false;
    if (!Array.isArray(ai.tools)) return false;
    if (typeof ai.confidence !== 'number') return false;
    if (ai.confidence < 0 || ai.confidence > 1) return false;

    // Validate Tech section
    const tech = data.tech;
    if (!Array.isArray(tech.languages)) return false;
    if (!Array.isArray(tech.frameworks)) return false;
    if (!Array.isArray(tech.categories)) return false;
    const validCategories = ['backend', 'frontend', 'devops', 'mobile', 'data'];
    for (const cat of tech.categories) {
        if (!validCategories.includes(cat)) return false;
    }

    // Validate Summary section
    const summary = data.summary;
    if (typeof summary.title !== 'string' || summary.title.length === 0) return false;
    if (typeof summary.description !== 'string' || summary.description.length === 0) return false;
    const validTypes = ['feature', 'bugfix', 'refactor', 'docs', 'test', 'chore', 'ci'];
    if (!validTypes.includes(summary.type)) return false;

    // Validate Health section
    const health = data.health;
    const validFriction = ['low', 'medium', 'high'];
    const validScope = ['small', 'medium', 'large', 'xlarge'];
    const validRisk = ['low', 'medium', 'high'];
    if (!validFriction.includes(health.review_friction)) return false;
    if (!validScope.includes(health.scope)) return false;
    if (!validRisk.includes(health.risk_level)) return false;
    if (!Array.isArray(health.insights)) return false;

    return true;
})()
""".strip()

    return {
        "type": "javascript",
        "value": validation_code,
        "description": "Response matches v6 schema structure",
    }


def _get_test_cases_from_golden() -> list[dict[str, Any]]:
    """Generate promptfoo test cases from GOLDEN_TESTS.

    Converts all GoldenTest instances to promptfoo format with
    appropriate assertions for each test's expectations.

    Returns:
        List of promptfoo test case dictionaries
    """
    schema_assertion = _get_schema_validation_assertion()
    return [to_promptfoo_test(test, schema_assertion) for test in GOLDEN_TESTS]


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
