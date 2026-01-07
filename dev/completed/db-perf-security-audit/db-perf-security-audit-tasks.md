# Database Security & Performance Audit - Task Checklist

**Last Updated:** 2026-01-05 (Session 3)
**Status:** In Progress
**Branch:** `feature/db-perf-security-audit`
**Worktree:** `/Users/yanchuk/Documents/GitHub/tformance-db-audit`

---

## Progress Overview

| Phase | Status | Completed | Total |
|-------|--------|-----------|-------|
| Phase 0: Setup | ✅ Complete | 3 | 3 |
| Phase 1: Security | Partial (S2/S3 skipped) | 1 | 1 |
| Phase 2: Critical Perf | ✅ Complete | 3 | 3 |
| Phase 3: Medium Perf | In Progress | 2 | 4 |
| Phase 4: Low Priority | Not Started | 0 | 3 |
| **Total** | | **9** | **14** |

---

## Phase 0: Setup

- [x] **0.1** Create worktree
  - Command: `git worktree add ../tformance-db-audit -b feature/db-perf-security-audit`
  - ✅ Worktree exists at `../tformance-db-audit`

- [x] **0.2** Setup environment in worktree
  - Uses main venv: `/Users/yanchuk/Documents/GitHub/tformance/.venv/bin/pytest`
  - ✅ Tests can run

- [x] **0.3** Verify baseline tests pass
  - ✅ All tests pass

---

## Phase 1: Security Fixes

### S1: GitHub View Integer Validation ✅ COMPLETE

- [x] **1.1** RED: Write failing test for invalid organization_id
  - File: `apps/integrations/tests/test_views.py`
  - Added 2 tests: `test_github_select_org_post_invalid_organization_id_shows_error`
    and `test_github_select_org_post_empty_organization_id_shows_error`

- [x] **1.2** GREEN: Add try/except to github.py:148
  - File: `apps/integrations/views/github.py`
  - ✅ Fixed with proper error message redirect

- [x] **1.3** REFACTOR: N/A - code is clean

- [x] **1.4** Commit S1 fix
  - Committed: `fix(security): add int validation to github org selection`

### S2: Slack Webhook Integer Validation ⏭️ SKIPPED

- [x] **1.5-1.7** SKIPPED per user request
  - Reason: "Slack integration is not done and not active"

### S3: Security Headers Verification ⏭️ SKIPPED

- [x] **1.8-1.9** SKIPPED per user request
  - Reason: Same as S2

---

## Phase 2: Critical Performance Fixes

### P3: Single Aggregation Query ✅ COMPLETE (moved up)

- [x] **P3.1** RED: Write test for single query
  - File: `apps/metrics/tests/dashboard/test_key_metrics.py`
  - Test: `test_calculate_ai_percentage_uses_single_query`
  - Confirmed failure: 2 queries executed when 1 expected

- [x] **P3.2** GREEN: Refactor `_helpers.py:57-70`
  - Added `Count, Q` imports
  - Changed to single `aggregate()` call
  - ✅ Test passes

- [x] **P3.3** Commit: Pending PR commit

### C1: LLM Batch N+1 ✅ COMPLETE

- [x] **C1.1** RED: Identified actual issue - `values_list()` bypasses prefetch
  - **KEY FINDING**: Issue was at lines 304-305, NOT line 307
  - `pr.files.values_list("filename", flat=True)` causes extra queries
  - `pr.commits.values_list("message", flat=True)` causes extra queries
  - Line 307 (`pr.reviews.all()`) was actually correct

- [x] **C1.2** GREEN: Fix in tasks.py:304-305
  - Changed from: `list(pr.files.values_list("filename", flat=True))`
  - Changed to: `[f.filename for f in pr.files.all()]`
  - Same pattern for commits
  - ✅ All 23 LLM task tests pass

- [x] **C1.3** Added tests to `test_llm_tasks.py`:
  - `TestLLMBatchQueryOptimization::test_data_extraction_uses_prefetch_cache`
  - `TestLLMBatchQueryOptimization::test_values_list_bypasses_prefetch_cache`

### C2: Requeue Depth Limit ✅ COMPLETE

- [x] **C2.1** RED: Write test for max requeue depth
  - File: `apps/integrations/tests/test_metrics_task.py` (NEW FILE)
  - Tests: `test_max_requeue_depth_constant_exists`, `test_requeue_depth_parameter_accepted`,
    `test_requeue_stops_at_max_depth`, `test_requeue_increments_depth`

- [x] **C2.2** GREEN: Add depth counter to metrics.py
  - Added `MAX_REQUEUE_DEPTH = 50` constant
  - Added `requeue_depth: int = 0` parameter to task
  - Added depth checking and increment logic
  - ✅ All 4 tests pass

---

## Phase 3: Medium Priority Optimizations

### P2: AI Categorization .only() ✅ COMPLETE

- [x] **P2.1** RED: Write test for field limitation
  - File: `apps/metrics/tests/dashboard/test_ai_metrics.py`
  - Test: `test_uses_only_for_memory_efficiency`
  - Confirmed query was loading ALL columns including "body"

- [x] **P2.2** GREEN: Add .only() to ai_metrics.py:249-253
  - Added `.only("id", "llm_summary", "ai_tools_detected")` to queryset
  - All 21 ai_metrics tests pass

- [ ] **P2.3** Commit P2 fix (pending final PR commit)

### P1: Survey Prefetch Bypass (Deferred)

- [ ] **P1.1-P1.4** - Investigation showed prefetch should work correctly
  - May be false positive - needs more investigation

### C3: Parallelize Weekly Insights

- [ ] **C3.1-C3.3** Not started

### C4: Subscription Error Handling

- [ ] **C4.1-C4.3** Not started

---

## Phase 4: Lower Priority Improvements

### P4, P5, C5 - Not Started

---

## Final Steps

- [ ] Run full test suite
- [ ] Run linting
- [ ] Create PR
- [ ] Manual QA
- [ ] Merge PR
- [ ] Clean up worktree
- [ ] Move docs to completed

---

## Session Notes

### Session 3 (2026-01-05)

**Completed:**
1. P2: Added `.only("id", "llm_summary", "ai_tools_detected")` to ai_metrics.py:249-253
   - All 21 ai_metrics tests pass

**Files Modified This Session:**
- `apps/metrics/services/dashboard/ai_metrics.py` - P2 fix (lines 249-253)

**Note:** Discovered pre-existing flaky test `test_groups_by_month` in `test_trend_comparison.py` - fails due to date boundary at start of January (5 days and 35 days from Jan 5 both land in December). Unrelated to our changes.

---

### Session 2 (2025-01-05)

**Completed:**
1. S1: Integer validation in github.py - COMPLETE with TDD
2. P3: Single aggregation query - COMPLETE with TDD
3. C1: Fixed N+1 in LLM batch (actual issue was values_list, not reviews.all)
4. C2: Added requeue depth limit with MAX_REQUEUE_DEPTH=50

**Key Discoveries:**
1. **C1 Misdiagnosis**: Original plan said line 307 was the issue, but actual N+1
   was at lines 304-305 where `values_list()` bypasses prefetch cache.
   Django's `.all()` correctly uses prefetch cache.

2. **Query Count Behavior**: Django's QuerySet.count() uses `_result_cache` if
   the queryset was already evaluated, so iteration + count() = 1 query, not 2.

3. **S2/S3 Skipped**: User confirmed Slack integration not active, skip for now.

**Files Modified:**
- `apps/integrations/views/github.py` - S1 fix
- `apps/integrations/tests/test_views.py` - S1 tests
- `apps/metrics/services/dashboard/_helpers.py` - P3 fix
- `apps/metrics/tests/dashboard/test_key_metrics.py` - P3 test
- `apps/metrics/tasks.py` - C1 fix (lines 304-305)
- `apps/metrics/tests/test_llm_tasks.py` - C1 tests
- `apps/integrations/_task_modules/metrics.py` - C2 fix
- `apps/integrations/tests/test_metrics_task.py` - C2 tests (NEW FILE)
- `apps/metrics/tests/dashboard/test_ai_metrics.py` - P2 RED test

**No Migrations Needed**: All changes are logic/query optimization, no model changes.
