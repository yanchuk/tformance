"""Prompt management package for LLM-based PR analysis.

This package provides:
- Prompt versioning and metadata
- Promptfoo config generation (export.py)
- Response schema validation (schemas.py)
- Jinja2 template rendering (render.py)
- Golden test cases (golden_tests.py)
"""

from apps.metrics.prompts.golden_tests import (
    GOLDEN_TESTS,
    GoldenTest,
    GoldenTestCategory,
    get_negative_tests,
    get_positive_tests,
    get_tests_by_category,
    to_promptfoo_test,
)
from apps.metrics.prompts.render import render_system_prompt, render_user_prompt
from apps.metrics.prompts.schemas import validate_llm_response
from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    PROMPT_VERSION,
    build_llm_pr_context,
    get_user_prompt,
)

__all__ = [
    # Version and prompts
    "PR_ANALYSIS_SYSTEM_PROMPT",
    "PROMPT_VERSION",
    "build_llm_pr_context",
    "get_user_prompt",
    # Rendering
    "render_system_prompt",
    "render_user_prompt",
    # Validation
    "validate_llm_response",
    # Golden tests
    "GOLDEN_TESTS",
    "GoldenTest",
    "GoldenTestCategory",
    "get_positive_tests",
    "get_negative_tests",
    "get_tests_by_category",
    "to_promptfoo_test",
]
