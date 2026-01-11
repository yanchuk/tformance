# Prompt Single Source of Truth - Implementation Plan

**Last Updated:** 2026-01-11
**Status:** Planning
**Priority:** Critical (LLM Accuracy)

## Executive Summary

Consolidate dual prompt representations (Python hardcoded strings vs Jinja2 templates) into a single authoritative source. Currently:
- `llm_prompts.py` contains 383-line `PR_ANALYSIS_SYSTEM_PROMPT` string
- `prompts/templates/` contains Jinja2 templates that produce identical output
- Comments say "Jinja2 is source of truth" but Python string is kept for "backward compatibility"

This creates **drift risk** where manual sync is required and versions can diverge.

## Current State Analysis

### Problem: Dual Implementations

| Location | Type | Lines | Purpose |
|----------|------|-------|---------|
| `llm_prompts.py:41-416` | Hardcoded string | 375 | `PR_ANALYSIS_SYSTEM_PROMPT` |
| `llm_prompts.py:467-638` | Python function | 171 | `get_user_prompt()` |
| `prompts/templates/system.jinja2` | Jinja2 | 15 | Includes 8 section templates |
| `prompts/templates/user.jinja2` | Jinja2 | 182 | User prompt template |
| `prompts/render.py` | Python | 200 | `render_system_prompt()`, `render_user_prompt()` |

### Current Dependencies

**Direct imports of `PR_ANALYSIS_SYSTEM_PROMPT`:**
- `apps/metrics/tasks.py:28` - Celery task for PR analysis
- `apps/metrics/management/commands/run_llm_analysis.py:24` - CLI command
- `apps/metrics/management/commands/compare_llm_models.py:20` - Model comparison
- `apps/integrations/services/groq_batch.py:33` - Batch processing
- `apps/metrics/prompts/__init__.py:23` - Re-export
- `apps/metrics/prompts/tests/test_export.py:14` - Tests
- `apps/metrics/prompts/tests/test_render.py:13` - Tests

**Direct imports of `get_user_prompt`:**
- `apps/metrics/tasks.py:30` - Celery task
- `apps/metrics/prompts/__init__.py:26` - Re-export
- `apps/metrics/tests/test_llm_prompts.py:8` - Tests
- `apps/metrics/prompts/tests/test_render.py:176,196` - Comparison tests

### What STAYS in llm_prompts.py

These utilities are PR-model-specific and don't belong in prompt templates:

| Export | Purpose | Keep? |
|--------|---------|-------|
| `PROMPT_VERSION` | Version constant | YES - needed by render.py |
| `calculate_relative_hours()` | Timestamp utility | YES |
| `_format_timestamp_prefix()` | Display utility | YES (internal) |
| `_get_member_display_name()` | Member display | YES (internal) |
| `build_llm_pr_context()` | Main context builder | YES - core function |
| `TimelineEvent` | Dataclass | YES |
| `build_timeline()` | Timeline builder | YES |
| `format_timeline()` | Timeline formatter | YES |

## Proposed Future State

### Architecture

```
                    ┌─────────────────────────────┐
                    │  prompts/templates/         │
                    │  (Single Source of Truth)   │
                    │  - system.jinja2            │
                    │  - sections/*.jinja2        │
                    │  - user.jinja2              │
                    └───────────┬─────────────────┘
                                │
                                ▼
                    ┌─────────────────────────────┐
                    │  prompts/render.py          │
                    │  - render_system_prompt()   │
                    │  - render_user_prompt()     │
                    └───────────┬─────────────────┘
                                │
                    ┌───────────┴───────────────────────┐
                    │                                   │
                    ▼                                   ▼
        ┌─────────────────────┐          ┌─────────────────────────┐
        │  llm_prompts.py     │          │  Consumers              │
        │  - PROMPT_VERSION   │          │  - tasks.py             │
        │  - get_user_prompt  │◄─────────│  - groq_batch.py        │
        │    (wrapper)        │          │  - management commands  │
        │  - build_llm_pr_    │          └─────────────────────────┘
        │    context()        │
        │  - TimelineEvent    │
        │  - build_timeline() │
        └─────────────────────┘
```

### Key Changes

1. **Remove** `PR_ANALYSIS_SYSTEM_PROMPT` hardcoded string from `llm_prompts.py`
2. **Replace** with lazy-loaded function that calls `render_system_prompt()`
3. **Replace** `get_user_prompt()` with wrapper calling `render_user_prompt()`
4. **Update** all imports to use the new pattern
5. **Keep** backward compatibility through function wrappers

### Backward Compatibility Strategy

```python
# llm_prompts.py - NEW PATTERN
from functools import lru_cache

@lru_cache(maxsize=1)
def get_system_prompt() -> str:
    """Get the system prompt from Jinja2 templates (cached).

    This is the SINGLE SOURCE OF TRUTH for system prompts.
    Templates are in: apps/metrics/prompts/templates/
    """
    from apps.metrics.prompts.render import render_system_prompt
    return render_system_prompt()

# For backward compatibility - deprecation warning
@property
def PR_ANALYSIS_SYSTEM_PROMPT():
    warnings.warn("Use get_system_prompt() instead", DeprecationWarning)
    return get_system_prompt()
```

## Implementation Phases

### Phase 1: TDD Setup (RED)
Write failing tests that verify single source of truth behavior:
- Test that `get_system_prompt()` returns same as templates
- Test that modifying template changes output
- Test that no hardcoded string exists in source

### Phase 2: Refactor llm_prompts.py (GREEN)
1. Add `get_system_prompt()` function with caching
2. Keep `get_user_prompt()` but delegate to `render_user_prompt()`
3. Remove 375-line hardcoded `PR_ANALYSIS_SYSTEM_PROMPT` string
4. Update module docstring

### Phase 3: Update Consumers (GREEN)
Update all files importing `PR_ANALYSIS_SYSTEM_PROMPT`:
- `apps/metrics/tasks.py`
- `apps/integrations/services/groq_batch.py`
- `apps/metrics/management/commands/run_llm_analysis.py`
- `apps/metrics/management/commands/compare_llm_models.py`
- `apps/metrics/prompts/__init__.py`

### Phase 4: Update Tests (GREEN)
- Remove tests comparing hardcoded string to templates (no longer needed)
- Update tests to use `get_system_prompt()`
- Ensure all tests pass

### Phase 5: Simplification (REFACTOR)
- Use code-simplifier agent to clean up
- Remove unused code
- Optimize imports

## Critical Issues (From Plan Review)

### Issue 1: Parameter Signature Mismatch
`render_user_prompt()` has 3 additional parameters not in `get_user_prompt()`:
- `timeline: str | None`
- `commit_co_authors: list[str] | None`
- `ai_config_files: list[str] | None`

**Solution:** These ARE in `get_user_prompt()` but in different location - verify alignment before delegation.

### Issue 2: Module Load Timing
`PR_ANALYSIS_SYSTEM_PROMPT = get_system_prompt()` at module level can fail if imported before Django configures.

**Solution:** Use **Alternative 1** - Update all 7 import sites to use `get_system_prompt()` function directly. Remove `PR_ANALYSIS_SYSTEM_PROMPT` constant entirely. This is cleaner and only affects 7 files.

### Issue 3: Circular Import
`render.py` imports `PROMPT_VERSION` from `llm_prompts.py`, creating circular dependency.

**Solution:** Extract `PROMPT_VERSION` to `apps/metrics/prompts/constants.py`.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports | High | High | Extract PROMPT_VERSION to constants.py |
| Module load timing | Medium | High | Use function, not module-level constant |
| Breaking imports | Medium | High | Update all 7 import sites atomically |
| Performance regression | Low | Low | Jinja2 caches compiled templates |
| Template loading errors | Low | High | Comprehensive tests |

## Success Metrics

1. **Zero hardcoded prompts** - `PR_ANALYSIS_SYSTEM_PROMPT` string removed
2. **All tests pass** - No regressions
3. **Single source** - All prompt changes only require template edits
4. **File size reduction** - `llm_prompts.py` reduced from 1043 to ~600 lines

## Dependencies

- `apps/metrics/prompts/render.py` - Must work without Django setup for tests
- `apps/metrics/prompts/templates/` - All templates must be complete
- Existing test suite must pass as baseline

## Effort Estimate

| Phase | Effort | Time |
|-------|--------|------|
| Phase 1: TDD Setup | S | 30 min |
| Phase 2: Refactor llm_prompts.py | M | 1 hr |
| Phase 3: Update Consumers | M | 1 hr |
| Phase 4: Update Tests | M | 1 hr |
| Phase 5: Simplification | S | 30 min |
| **Total** | **M** | **4 hrs** |
