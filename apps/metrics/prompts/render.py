"""Jinja2 template rendering for LLM prompts.

This module provides functions to render prompts from Jinja2 templates,
enabling composable and maintainable prompt definitions.

Usage:
    from apps.metrics.prompts.render import render_system_prompt

    prompt = render_system_prompt()  # Full prompt with all sections
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from apps.metrics.services.llm_prompts import PROMPT_VERSION

# Template directory path
_TEMPLATE_DIR = Path(__file__).parent / "templates"

# Create Jinja2 environment with template loader
# trim_blocks=False to preserve blank lines between sections
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    trim_blocks=False,
    lstrip_blocks=False,
    keep_trailing_newline=False,
)


def render_system_prompt(version: str | None = None) -> str:
    """Render the system prompt from Jinja2 templates.

    Args:
        version: Optional version string to include in template.
                 Defaults to PROMPT_VERSION from llm_prompts.py.

    Returns:
        The fully rendered system prompt string.

    Example:
        >>> prompt = render_system_prompt()
        >>> "AI Detection Rules" in prompt
        True
    """
    template = _env.get_template("system.jinja2")
    rendered = template.render(version=version or PROMPT_VERSION)

    # Normalize whitespace: collapse multiple blank lines to single
    lines = rendered.split("\n")
    normalized = []
    prev_blank = False

    for line in lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        normalized.append(line)
        prev_blank = is_blank

    # Remove trailing whitespace from each line and trailing newlines
    result = "\n".join(line.rstrip() for line in normalized).rstrip()
    return result


def get_template_dir() -> Path:
    """Get the path to the templates directory.

    Returns:
        Path to the templates directory.
    """
    return _TEMPLATE_DIR


def list_template_sections() -> list[str]:
    """List all available template section files.

    Returns:
        List of section template filenames (without path).
    """
    sections_dir = _TEMPLATE_DIR / "sections"
    if not sections_dir.exists():
        return []

    return sorted(f.name for f in sections_dir.glob("*.jinja2"))
