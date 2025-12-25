# Prompt Template System - Tasks

**Last Updated:** 2025-12-25

## Progress Overview

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Eliminate Manual Sync | ✅ Complete | 4/4 |
| Phase 2: Extract Response Schema | ✅ Complete | 5/5 |
| Phase 3: Template Composition | ✅ Complete | 7/7 |
| Phase 4: Golden Test Unification | ✅ Complete | 6/6 |

---

## Phase 1: Eliminate Manual Sync

**Goal:** Auto-generate promptfoo configuration from Python code

### Tasks

- [x] **1.1** Create `apps/metrics/prompts/` package structure ✅
- [x] **1.2** Create `export_prompts` management command ✅
- [x] **1.3** Generate `promptfoo.yaml` dynamically ✅
- [x] **1.4** Update documentation and Makefile ✅

---

## Phase 2: Extract Response Schema

**Goal:** Move JSON response schema from prose to actual JSON Schema

### Tasks

- [x] **2.1** Add `jsonschema` dependency ✅
- [x] **2.2** Create `apps/metrics/prompts/schemas.py` ✅
- [x] **2.3** Create `validate_llm_response()` helper ✅
- [x] **2.4** Add schema validation to unit tests ✅
- [x] **2.5** Generate schema for promptfoo assertions ✅

---

## Phase 3: Template Composition (Jinja2)

**Goal:** Split monolithic prompt into composable Jinja2 templates

### Tasks

- [x] **3.1** Verify Jinja2 availability ✅
- [x] **3.2** Create template directory structure ✅
- [x] **3.3** Extract system prompt sections to templates ✅
- [x] **3.4** Create `render.py` with render functions ✅
- [x] **3.5** Add output equivalence test ✅
- [x] **3.6** Update `llm_prompts.py` to use render functions ✅
- [x] **3.7** Update `export_prompts` to use render functions ✅

---

## Phase 4: Golden Test Unification

**Goal:** Single source of truth for prompt test cases

### Tasks

- [x] **4.1** Create `GoldenTest` dataclass ✅
  - Created `apps/metrics/prompts/golden_tests.py`
  - Includes `GoldenTestCategory` enum (POSITIVE, NEGATIVE, EDGE_CASE, etc.)
  - Full dataclass with all expected fields
  - **Effort:** S

- [x] **4.2** Migrate promptfoo test cases to Python ✅
  - Created 24 golden tests covering all scenarios
  - Categories: positive (6), negative (7), edge cases (3), tech detection (4), summary (5)
  - Each test includes expected values and notes
  - **Effort:** M

- [x] **4.3** Create `to_promptfoo_test()` function ✅
  - Converts `GoldenTest` to promptfoo YAML format
  - Generates JavaScript assertions from expectations
  - Includes schema validation assertion
  - **Effort:** M

- [x] **4.4** Update `export_prompts` to include tests ✅
  - `export.py` uses `_get_test_cases_from_golden()`
  - All 24 tests included in generated promptfoo.yaml
  - **Effort:** S

- [x] **4.5** Create Python unit tests using golden tests ✅
  - Created `test_golden_tests.py` (27 tests)
  - Created `test_golden_regex_validation.py` (14 tests)
  - Tests validate both promptfoo format and regex detection
  - Documents known limitations (skipped/xfail)
  - **Effort:** M

- [x] **4.6** Document workflow for adding new test cases ✅
  - Updated context file with API reference
  - Added workflow documentation
  - **Effort:** S

### Phase 4 Verification ✅

```bash
# All verified:
python -c "from apps.metrics.prompts.golden_tests import GOLDEN_TESTS; print(f'{len(GOLDEN_TESTS)} tests')"  # 24 tests
.venv/bin/pytest apps/metrics/prompts/tests/ -v  # 102 passed
python manage.py export_prompts  # Includes all tests
```

---

## Final Stats

| Test File | Tests | Purpose |
|-----------|-------|---------|
| `test_export.py` | 16 | Promptfoo config generation |
| `test_render.py` | 16 | Template rendering, equivalence |
| `test_schemas.py` | 32 | JSON Schema validation |
| `test_golden_tests.py` | 27 | Golden test dataclass & conversion |
| `test_golden_regex_validation.py` | 14 | Regex detection using golden tests |
| **Total** | **102** + 224 subtests | All passing |

---

## Commands Reference

```bash
# Development
.venv/bin/pytest apps/metrics/prompts/tests/ -v  # Run all prompts tests
python manage.py export_prompts                   # Generate promptfoo config

# Promptfoo testing
cd dev/active/ai-detection-pr-descriptions/experiments
export GROQ_API_KEY="your-key"
npx promptfoo eval                                # Run evaluation
npx promptfoo view                                # View results in browser
```
