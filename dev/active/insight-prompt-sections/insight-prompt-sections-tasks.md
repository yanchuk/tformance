# Insight Prompt Sections - Tasks

**Last Updated:** 2026-01-11
**Status:** COMPLETED

## Phase 1: TDD Setup (RED) - COMPLETED

### 1.1 Write Failing Tests
- [x] Create test class `TestInsightSystemPromptSections` in `test_render.py`
- [x] Test: `test_insight_sections_directory_exists` (uses updated `list_template_sections('insight')`)
- [x] Test: `test_insight_system_prompt_with_copilot_includes_guidance`
- [x] Test: `test_insight_system_prompt_without_copilot_excludes_guidance`
- [x] Test: `test_insight_system_prompt_without_copilot_is_shorter` (~800 chars difference)
- [x] Test: `test_insight_system_prompt_contains_all_sections` (verifies all sections present)
- [x] Test: `test_insight_system_prompt_examples_exclude_copilot_when_disabled`
- [x] Run tests and confirm they FAIL (RED phase)

### 1.2 Update list_template_sections() First
- [x] Update `list_template_sections()` in render.py to accept `template_type` parameter
- [x] Default to `"pr_analysis"` for backward compatibility

## Phase 2: Template Split (GREEN - Part 1) - COMPLETED

### 2.1 Create Directory Structure
- [x] Create `templates/insight/sections/` directory

### 2.2 Extract Section Files
- [x] Create `identity.jinja2`
- [x] Create `output_format.jinja2`
- [x] Create `mention_syntax.jinja2`
- [x] Create `writing_rules.jinja2` (with conditional Copilot number conversions)
- [x] Create `copilot_guidance.jinja2`
- [x] Create `action_types.jinja2` (with conditional view_copilot_usage)
- [x] Create `examples.jinja2` (with conditional copilot-waste example)
- [x] Add `{% if include_copilot %}` around Copilot-specific sections

### 2.3 Update Main Template
- [x] Update `system.jinja2` with includes
- [x] Add `{% if include_copilot %}` conditional for copilot_guidance.jinja2
- [x] Verify template renders without errors

## Phase 3: Update Render Functions (GREEN - Part 2) - COMPLETED

### 3.1 Update render.py
- [x] Add `include_copilot: bool = True` parameter to `render_insight_system_prompt()`
- [x] Pass parameter to template render
- [x] Keep `@lru_cache(maxsize=2)` for both boolean variants

### 3.2 Fix insight_llm.py Cache Issue
- [x] **REMOVED** `@lru_cache` from `get_insight_system_prompt()` (render.py handles caching)
- [x] Add `include_copilot: bool = True` parameter

### 3.3 Update insight_llm.py Functions
- [x] `_LazyInsightPrompt` defaults `include_copilot=True` (backward compat - no change needed)
- [x] Update `generate_insight()` to detect Copilot presence (`data.get("copilot_metrics") is not None`)
- [x] Pass `include_copilot=has_copilot` to `get_insight_system_prompt()`

## Phase 4: Verification (GREEN) - COMPLETED

### 4.1 Run Tests
- [x] Run new tests: `pytest apps/metrics/prompts/tests/test_render.py::TestInsightSystemPromptSections -v`
- [x] Confirmed all 6 new tests PASS (plus 13 subtests)
- [x] Run existing tests: `pytest apps/metrics/prompts/tests/ -v`
- [x] 137 passed, 2 skipped, 1 xfailed, 762 subtests passed

### 4.2 Manual Verification
- [x] Verify with Copilot: prompt contains "Copilot Metrics Guidance"
- [x] Verify without Copilot: prompt does NOT contain "Copilot"
- [x] Token savings verified: ~800+ chars difference

## Phase 5: Refactor (REFACTOR) - COMPLETED

### 5.1 Code Cleanup
- [x] No unused imports
- [x] Consistent formatting
- [x] Docstrings updated in insight_llm.py
- [x] pyright: 0 errors, 0 warnings, 0 informations

### 5.2 Documentation
- [x] Updated render.py docstrings
- [x] Added comments to system.jinja2 explaining conditional

## Completion Checklist

- [x] All new tests pass (6 tests, 13 subtests)
- [x] All existing tests pass (137 total)
- [x] Template structure matches pr_analysis/ pattern
- [x] Copilot conditional works correctly
- [x] Token savings verified (~800 chars)
- [x] Code linted with pyright (0 errors)

## Summary

Successfully implemented TDD RED-GREEN-REFACTOR cycle:

1. **RED**: Wrote 6 failing tests for insight prompt sections
2. **GREEN**:
   - Created 7 section files in `templates/insight/sections/`
   - Updated `system.jinja2` with includes and conditionals
   - Added `include_copilot` parameter throughout the call chain
   - Fixed nested cache issue (removed redundant `@lru_cache` from insight_llm.py)
3. **REFACTOR**: Cleaned up code, verified types, updated documentation

Key files modified:
- `apps/metrics/prompts/render.py` - Added `template_type` param, `include_copilot` param
- `apps/metrics/prompts/templates/insight/system.jinja2` - Replaced with includes
- `apps/metrics/prompts/templates/insight/sections/*.jinja2` - 7 new section files
- `apps/metrics/services/insight_llm.py` - Added Copilot detection, fixed cache
- `apps/metrics/prompts/tests/test_render.py` - Added 6 new tests
