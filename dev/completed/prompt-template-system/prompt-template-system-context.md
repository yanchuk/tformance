# Prompt Template System - Context

**Last Updated:** 2025-12-25

## Overview

This document captures key context for the prompt template management system for LLM-based PR analysis.

**Status:** All 4 Phases Complete

## Key Files

### Prompt Template System

```
apps/metrics/prompts/
├── __init__.py                 # Package exports
├── render.py                   # render_system_prompt(), template loading
├── schemas.py                  # JSON Schema validation (v6.0.0)
├── export.py                   # Promptfoo config generation
├── golden_tests.py             # GoldenTest dataclass, GOLDEN_TESTS
├── templates/
│   ├── system.jinja2           # Main template (SOURCE OF TRUTH)
│   └── sections/
│       ├── intro.jinja2        # Tasks overview
│       ├── ai_detection.jinja2 # AI detection rules
│       ├── tech_detection.jinja2
│       ├── health_assessment.jinja2
│       ├── response_schema.jinja2
│       ├── definitions.jinja2  # Category & type definitions
│       └── enums.jinja2        # Tool/language/framework lists
└── tests/
    ├── test_export.py          # 16 tests
    ├── test_render.py          # 16 tests (includes equivalence test)
    ├── test_schemas.py         # 32 tests
    ├── test_golden_tests.py    # 27 tests
    └── test_golden_regex_validation.py  # 14 tests
```

### Supporting Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | PROMPT_VERSION, user prompt builder |
| `apps/metrics/management/commands/export_prompts.py` | CLI to generate promptfoo config |
| `apps/integrations/services/groq_batch.py` | Groq API batch processing |

### Generated Files (DO NOT EDIT)

| File | Purpose |
|------|---------|
| `dev/active/ai-detection-pr-descriptions/experiments/promptfoo.yaml` | Auto-generated config |
| `dev/active/ai-detection-pr-descriptions/experiments/prompts/v{VERSION}-system.txt` | Rendered prompt |

## API Reference

### Golden Tests (`apps/metrics/prompts/golden_tests.py`)

```python
from apps.metrics.prompts.golden_tests import (
    GOLDEN_TESTS,          # List of all golden tests (24 tests)
    GoldenTest,            # Dataclass for test cases
    GoldenTestCategory,    # Enum: POSITIVE, NEGATIVE, EDGE_CASE, etc.
    get_positive_tests,    # Get tests that should detect AI
    get_negative_tests,    # Get tests that should NOT detect AI
    get_tests_by_category, # Filter by category
    to_promptfoo_test,     # Convert to promptfoo format
)

# Example: Add a new golden test
new_test = GoldenTest(
    id="pos_new_tool",
    description="New AI tool detection",
    category=GoldenTestCategory.POSITIVE,
    pr_title="Add feature",
    pr_body="Built with NewAI tool.",
    expected_ai_assisted=True,
    expected_tools=["newai"],
    min_confidence=0.8,
)
```

### Render Functions (`apps/metrics/prompts/render.py`)

```python
from apps.metrics.prompts.render import render_system_prompt, get_template_dir

# Render full system prompt from templates
prompt = render_system_prompt()  # Uses PROMPT_VERSION
prompt = render_system_prompt(version="6.3.0")  # Custom version

# Get template directory path
templates_path = get_template_dir()
```

### Schema Validation (`apps/metrics/prompts/schemas.py`)

```python
from apps.metrics.prompts.schemas import validate_llm_response, validate_ai_response

# Validate full LLM response
is_valid, errors = validate_llm_response(response_dict)

# Validate just AI portion
is_valid, errors = validate_ai_response(ai_data)
```

### Export Functions (`apps/metrics/prompts/export.py`)

```python
from apps.metrics.prompts.export import export_promptfoo_config

# Generate and write promptfoo config (includes all golden tests)
paths = export_promptfoo_config(Path("/output/dir"))
# {'prompt': Path(...), 'config': Path(...)}
```

## Adding New Golden Test Cases

### Workflow

1. **Add the test case** to `GOLDEN_TESTS` in `golden_tests.py`:
   ```python
   GoldenTest(
       id="pos_new_pattern",  # Unique ID with category prefix
       description="Detection of new AI pattern",
       category=GoldenTestCategory.POSITIVE,
       pr_title="Feature PR",
       pr_body="## AI Disclosure\nBuilt with NewAI.",
       expected_ai_assisted=True,
       expected_tools=["newai"],
       min_confidence=0.7,
       notes="Tracks new AI tool adoption",
   ),
   ```

2. **Run tests** to verify:
   ```bash
   .venv/bin/pytest apps/metrics/prompts/tests/test_golden_tests.py -v
   ```

3. **Regenerate promptfoo config**:
   ```bash
   make export-prompts
   ```

4. **Run LLM evaluation**:
   ```bash
   cd dev/active/ai-detection-pr-descriptions/experiments
   export GROQ_API_KEY="your-key"
   npx promptfoo eval
   ```

### Test Naming Conventions

| Category | ID Prefix | Example |
|----------|-----------|---------|
| Positive (should detect) | `pos_` | `pos_cursor_explicit` |
| Negative (should NOT detect) | `neg_` | `neg_explicit_no_ai` |
| Edge case | `edge_` | `edge_brainstorm_only` |
| Tech detection | `tech_` | `tech_python_django` |
| PR type | `type_` | `type_bugfix` |

### Expected Values

| Field | When to Use |
|-------|-------------|
| `expected_ai_assisted` | True/False for POSITIVE/NEGATIVE tests |
| `expected_tools` | List of tools that SHOULD be detected |
| `expected_not_tools` | List of tools that should NOT be detected |
| `min_confidence` | Minimum confidence threshold (0.0-1.0) |
| `expected_categories` | Tech categories like ["backend", "frontend"] |
| `expected_pr_type` | PR type like "feature", "bugfix", etc. |

## Regex Detection Validation

Golden tests also validate the regex-based AI detector. Known limitations:

| Test ID | Status | Reason |
|---------|--------|--------|
| `pos_aider_commit` | Skipped | "aider:" prefix pattern not implemented |
| `pos_windsurf_codeium` | Skipped | Windsurf IDE pattern not implemented |
| `neg_claude_product_discussion` | xfail | Claude pattern too broad (false positive) |

To add regex validation for a new test, add it to `test_golden_regex_validation.py`.

## Running Tests

```bash
# All prompts package tests (102 tests)
.venv/bin/pytest apps/metrics/prompts/tests/ -v

# Just golden test tests
.venv/bin/pytest apps/metrics/prompts/tests/test_golden_tests.py -v

# Just regex validation tests
.venv/bin/pytest apps/metrics/prompts/tests/test_golden_regex_validation.py -v
```

## Response Schema (v6.0.0)

```json
{
  "ai": {
    "is_assisted": boolean,
    "tools": ["string"],
    "usage_type": "authored" | "assisted" | "reviewed" | "brainstorm" | null,
    "confidence": 0.0-1.0
  },
  "tech": {
    "languages": ["string"],
    "frameworks": ["string"],
    "categories": ["backend", "frontend", "devops", "mobile", "data"]
  },
  "summary": {
    "title": "string (5-10 words)",
    "description": "string (1-2 sentences)",
    "type": "feature" | "bugfix" | "refactor" | "docs" | "test" | "chore" | "ci"
  },
  "health": {
    "review_friction": "low" | "medium" | "high",
    "scope": "small" | "medium" | "large" | "xlarge",
    "risk_level": "low" | "medium" | "high",
    "insights": ["string"]
  }
}
```

## Test Coverage Summary

| Test File | Tests | Subtests | Purpose |
|-----------|-------|----------|---------|
| `test_export.py` | 16 | - | Promptfoo config generation |
| `test_render.py` | 16 | - | Template rendering, equivalence |
| `test_schemas.py` | 32 | - | JSON Schema validation |
| `test_golden_tests.py` | 27 | 88 | Golden test structure & conversion |
| `test_golden_regex_validation.py` | 14 | 6 | Regex detection using golden tests |
| **Total** | **102** | **224** | All passing |
