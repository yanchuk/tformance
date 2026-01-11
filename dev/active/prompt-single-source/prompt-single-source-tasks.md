# Prompt Single Source of Truth - Tasks

**Last Updated:** 2026-01-11
**Status:** Ready for Implementation

## Phase 0: Baseline Verification & Prerequisites

### 0.1 Run Baseline Tests
- [ ] Run prompt tests: `.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -v`
- [ ] Run render tests: `.venv/bin/pytest apps/metrics/prompts/tests/ -v`
- [ ] Run task tests: `.venv/bin/pytest apps/metrics/tests/test_llm_tasks.py -v`
- [ ] Document passing count: _____ tests pass

### 0.2 Verify Current State
- [ ] Confirm `render_system_prompt()` output matches `PR_ANALYSIS_SYSTEM_PROMPT`
- [ ] Confirm `render_user_prompt()` output matches `get_user_prompt()`
- [ ] Count lines in `llm_prompts.py`: _____ lines

### 0.3 Fix Circular Import (CRITICAL - Do First)
- [ ] Create `apps/metrics/prompts/constants.py` with `PROMPT_VERSION = "8.2.0"`
- [ ] Update `apps/metrics/services/llm_prompts.py` to import from constants
- [ ] Update `apps/metrics/prompts/render.py` to import from constants
- [ ] Verify imports work: `python -c "from apps.metrics.prompts.constants import PROMPT_VERSION"`
- [ ] Run tests to confirm no breakage

### 0.4 Verify Promptfoo Export Works (Baseline)
- [ ] Run: `make export-prompts` (or equivalent)
- [ ] Confirm export succeeds before changes

## Phase 1: TDD Setup (RED)

### 1.1 Write Failing Tests
- [ ] Create `apps/metrics/tests/test_single_source_of_truth.py`
- [ ] Add test: `test_no_hardcoded_prompt_string` - verify no string literal
- [ ] Add test: `test_get_system_prompt_function_exists`
- [ ] Add test: `test_get_system_prompt_matches_templates`
- [ ] Add test: `test_get_user_prompt_delegates_to_render`
- [ ] Run tests - confirm they FAIL (expected at this stage)

## Phase 2: Refactor llm_prompts.py (GREEN)

### 2.1 Add New Functions
- [ ] Add `from functools import lru_cache` import
- [ ] Add `get_system_prompt()` function with `@lru_cache(maxsize=1)`
- [ ] Update module docstring to reference templates as source of truth
- [ ] Run tests - confirm new function tests pass

### 2.2 Remove Hardcoded String Completely
- [ ] Remove lines 41-416 (the `PR_ANALYSIS_SYSTEM_PROMPT = """..."""` string)
- [ ] Do NOT add backward-compat constant (will update imports instead)
- [ ] Run tests - some will fail (expected - imports need updating)

### 2.3 Update get_user_prompt()
- [ ] Verify parameter alignment with `render_user_prompt()`:
  - `timeline`, `commit_co_authors`, `ai_config_files` must match
- [ ] Replace function body with delegation to `render_user_prompt()`
- [ ] Keep function signature identical for backward compatibility
- [ ] Keep docstring for documentation

### 2.4 Verify File Size Reduction
- [ ] Count lines: should be ~600 (down from 1043)
- [ ] Verify no functionality lost

## Phase 3: Update All Import Sites (GREEN)

**Strategy:** Update all 7 import sites to use `get_system_prompt()` instead of `PR_ANALYSIS_SYSTEM_PROMPT`

### 3.1 Update Core Files
- [ ] `apps/metrics/tasks.py:28` - change `PR_ANALYSIS_SYSTEM_PROMPT` → `get_system_prompt()`
- [ ] `apps/integrations/services/groq_batch.py:33` - change import
- [ ] Run: `.venv/bin/pytest apps/metrics/tests/test_llm_tasks.py -v`

### 3.2 Update Management Commands
- [ ] `apps/metrics/management/commands/run_llm_analysis.py:24` - change import
- [ ] `apps/metrics/management/commands/compare_llm_models.py:20` - change import
- [ ] Test commands still work (optional - manual verification)

### 3.3 Update Module Exports
- [ ] `apps/metrics/prompts/__init__.py:23` - remove `PR_ANALYSIS_SYSTEM_PROMPT`, add `get_system_prompt`
- [ ] Run: `.venv/bin/pytest apps/metrics/prompts/tests/ -v`

### 3.4 Update Test Files
- [ ] `apps/metrics/prompts/tests/test_export.py:14` - update import
- [ ] `apps/metrics/prompts/tests/test_render.py:13` - update import
- [ ] `apps/metrics/tests/test_llm_prompts.py:6` - update import

## Phase 4: Update Tests (GREEN)

### 4.1 Clean Up Comparison Tests
- [ ] `apps/metrics/prompts/tests/test_render.py` - remove/update `test_matches_original`
- [ ] `apps/metrics/prompts/tests/test_export.py` - update to use function
- [ ] `apps/metrics/tests/test_llm_prompts.py` - use `get_system_prompt()`

### 4.2 Run Full Test Suite
- [ ] Run: `.venv/bin/pytest apps/metrics -v`
- [ ] Confirm all tests pass
- [ ] Document final count: _____ tests pass

## Phase 5: Simplification (REFACTOR)

### 5.1 Code Review
- [ ] Review `llm_prompts.py` for dead code
- [ ] Remove any unused imports
- [ ] Verify docstrings are accurate

### 5.2 Optional: Use code-simplifier Agent
- [ ] Run simplifier on `llm_prompts.py` if helpful
- [ ] Verify tests still pass after simplification

### 5.3 Final Verification
- [ ] Run full test suite: `make test`
- [ ] Run pre-commit: `pre-commit run --all-files`
- [ ] Verify pyright passes

## Phase 6: Documentation & Commit

### 6.1 Update Documentation
- [ ] Update module docstrings
- [ ] Add comment in templates explaining they are source of truth

### 6.2 Commit
- [ ] Stage all changes
- [ ] Commit with message: `refactor(prompts): consolidate to Jinja2 single source of truth`
- [ ] Verify pre-commit hooks pass

## Completion Checklist

- [ ] `PROMPT_VERSION` extracted to `constants.py` (circular import fix)
- [ ] `PR_ANALYSIS_SYSTEM_PROMPT` hardcoded string removed entirely
- [ ] `get_system_prompt()` function added with caching
- [ ] `get_user_prompt()` delegates to `render_user_prompt()`
- [ ] All 7 import sites updated to use `get_system_prompt()`
- [ ] All tests pass
- [ ] Pre-commit hooks pass
- [ ] `llm_prompts.py` reduced to ~600 lines
- [ ] Promptfoo export still works

## Notes

### Circular Import Solution
`render.py` imports `PROMPT_VERSION` from `llm_prompts.py`. To avoid circular imports when `llm_prompts.py` imports from `render.py`, use late imports inside function bodies.

### Cache Invalidation
If prompts need to be reloaded at runtime (rare):
```python
get_system_prompt.cache_clear()
```

### Testing Note
The test `test_matches_original` in `test_render.py` compares Jinja2 output to Python string. After refactoring, this test becomes redundant since there's only one implementation. Consider removing or repurposing.
