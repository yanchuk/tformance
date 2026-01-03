# Insight QA Fixes - Task Checklist

**Last Updated:** 2026-01-02
**Status:** COMPLETE

## Overview

| Phase | Issue | Status | Tests | Implementation | Refactor |
|-------|-------|--------|-------|----------------|----------|
| 1 | ISS-005 | Complete | [x] | [x] | [x] |
| 2 | ISS-006 | Complete | [x] | [x] | [x] |
| 3 | ISS-001/007 | Complete | [x] | [x] | [x] |

---

## Phase 1: ISS-005 - Onboarding Team Context

### RED Phase - Write Failing Tests

- [x] **1.1** Create test file structure in `apps/onboarding/tests/test_team_context.py`
- [x] **1.2** Test: `sync_progress` uses `request.team` when set via session
- [x] **1.3** Test: `sync_progress` falls back to first team when no session team
- [x] **1.4** Test: `start_sync` uses session team
- [x] **1.5** Run tests and confirm they FAIL

### GREEN Phase - Minimal Implementation

- [x] **1.6** Update `sync_progress` view in `apps/onboarding/views.py`
- [x] **1.7** Update `start_sync` view similarly
- [x] **1.8** Run tests and confirm they PASS
- [x] **1.9** Run full onboarding test suite (178 tests pass)

### REFACTOR Phase

- [x] **1.10** Review if team resolution pattern should be extracted to helper (used existing `request.default_team`)
- [x] **1.11** Update view docstrings to document team resolution behavior
- [x] **1.12** Run full test suite

---

## Phase 2: ISS-006 - AI Adoption Data Source Alignment

### RED Phase - Write Failing Tests

- [x] **2.1** Add tests to `apps/metrics/tests/dashboard/test_sparkline_data.py`
- [x] **2.2** Test: `ai_adoption` uses survey data, not `is_ai_assisted` field
- [x] **2.3** Test: `ai_adoption` matches `get_key_metrics` calculation
- [x] **2.4** Test: handles PRs without surveys gracefully
- [x] **2.5** Run tests and confirm they FAIL

### GREEN Phase - Minimal Implementation

- [x] **2.6** Update `get_sparkline_data` in `apps/metrics/services/dashboard_service.py`
- [x] **2.7** Run tests and confirm they PASS
- [x] **2.8** Run full dashboard test suite (418 tests pass)

### REFACTOR Phase

- [x] **2.9** Consider extracting common AI percentage calculation to helper (not needed - query is simple)
- [x] **2.10** Ensure query is efficient (check for N+1)
- [x] **2.11** Update docstrings to clarify data source
- [x] **2.12** Run full test suite

---

## Phase 3: ISS-001/ISS-007 - Low-Data Week Handling

### RED Phase - Write Failing Tests

- [x] **3.1** Add tests to `apps/metrics/tests/dashboard/test_sparkline_data.py`
- [x] **3.2** Test: trend ignores first week with insufficient data
- [x] **3.3** Test: trend ignores last week with insufficient data
- [x] **3.4** Test: returns flat when no week has sufficient data
- [x] **3.5** Test: PR count trend also respects minimum sample size
- [x] **3.6** Run tests and confirm they FAIL

### GREEN Phase - Minimal Implementation

- [x] **3.7** Update `_calculate_change_and_trend` function with `sample_sizes` parameter
- [x] **3.8** Update `get_sparkline_data` to pass sample sizes
- [x] **3.9** Run tests and confirm they PASS
- [x] **3.10** Update existing tests to create sufficient test data (>= 3 PRs per week)

### REFACTOR Phase

- [x] **3.11** Add constant `MIN_SPARKLINE_SAMPLE_SIZE = 3`
- [x] **3.12** Update function docstrings
- [x] **3.13** Run full test suite (24 sparkline tests pass)

---

## Final Verification

- [x] **4.1** Run full test suite: 3197 passed (2 unrelated pre-existing failures)
- [x] **4.2** Update backlog issues to "Resolved"
- [ ] **4.3** Manual QA (optional - requires dev server)

---

## Summary

All 4 issues have been fixed using strict TDD methodology:

1. **ISS-005**: Onboarding sync page now respects session team context
2. **ISS-006**: AI Adoption sparkline now uses survey data (matches card)
3. **ISS-001**: Sparkline trends skip weeks with < 3 PRs
4. **ISS-007**: Fixed by same solution as ISS-001

### Files Changed

| File | Changes |
|------|---------|
| `apps/onboarding/views.py` | Use `request.default_team` in sync_progress and start_sync |
| `apps/onboarding/tests/test_team_context.py` | New file with 5 tests |
| `apps/metrics/services/dashboard_service.py` | AI adoption uses surveys; added MIN_SPARKLINE_SAMPLE_SIZE |
| `apps/metrics/tests/dashboard/test_sparkline_data.py` | Added 8 new tests (2 test classes) |

### Test Results

- Onboarding tests: 178 passed
- Dashboard tests: 418 passed
- Sparkline tests: 24 passed
- Full suite: 3197 passed, 2 skipped, 2 unrelated failures (insight cadence)
