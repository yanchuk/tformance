"""Prompt management package for LLM-based PR analysis.

This package provides:
- Prompt versioning and metadata
- Promptfoo config generation (export.py)
- Response schema validation (schemas.py)
- Jinja2 template rendering (render.py)
- Golden test cases (golden_tests.py)
"""

from apps.metrics.prompts.constants import PROMPT_VERSION
from apps.metrics.prompts.golden_tests import (
    GOLDEN_TESTS,
    GoldenTest,
    GoldenTestCategory,
    get_negative_tests,
    get_positive_tests,
    get_tests_by_category,
    to_promptfoo_test,
)
from apps.metrics.prompts.render import (
    render_insight_system_prompt,
    render_insight_user_prompt,
    render_pr_system_prompt,
    render_pr_user_prompt,
    render_system_prompt,
    render_user_prompt,
)
from apps.metrics.prompts.schemas import validate_llm_response

# Note: get_system_prompt, get_user_prompt, build_llm_pr_context, get_insight_system_prompt
# are NOT re-exported here to avoid circular imports.
# Import directly from:
#   apps.metrics.services.llm_prompts import get_system_prompt, get_user_prompt, build_llm_pr_context
#   apps.metrics.services.insight_llm import get_insight_system_prompt

__all__ = [
    # Version
    "PROMPT_VERSION",
    # PR Analysis rendering (new names)
    "render_pr_system_prompt",
    "render_pr_user_prompt",
    # Insight rendering
    "render_insight_system_prompt",
    "render_insight_user_prompt",
    # Legacy aliases (deprecated)
    "render_system_prompt",
    "render_user_prompt",
    # Note: get_system_prompt, get_user_prompt, build_llm_pr_context, get_insight_system_prompt
    # are imported directly from their service modules (see comment above)
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
