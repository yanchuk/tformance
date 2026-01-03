# Reviewer Pending State - Task Checklist

**Last Updated:** 2026-01-02

## Pre-Flight Check

- [ ] Run `make test` to ensure baseline is green
- [ ] Verify dev server is running
- [ ] Read PLAN.md and CONTEXT.md

## Phase 1: TDD Implementation

### 🔴 RED Phase - Write Failing Tests

- [ ] **1.1** Create test class `TestReviewerNameFilterPendingState` in `test_pr_list_service.py`
- [ ] **1.2** Write `test_excludes_prs_with_approved_latest_review`
- [ ] **1.3** Write `test_excludes_prs_with_commented_latest_review`
- [ ] **1.4** Write `test_excludes_prs_with_changes_requested_latest_review`
- [ ] **1.5** Write `test_includes_prs_with_dismissed_latest_review`
- [ ] **1.6** Write `test_latest_review_wins_over_earlier`
- [ ] **1.7** Write `test_changes_requested_after_approval_included`
- [ ] **1.8** Write `test_mixed_approved_and_pending_prs`
- [ ] **1.9** Run tests and confirm ALL new tests FAIL
  ```bash
  make test ARGS='apps.metrics.tests.test_pr_list_service::TestReviewerNameFilterPendingState'
  ```

### 🟢 GREEN Phase - Make Tests Pass

- [ ] **2.1** Update `reviewer_name` filter in `pr_list_service.py`
- [ ] **2.2** Add subquery for latest review state
- [ ] **2.3** Exclude completed review states (approved, commented, changes_requested)
- [ ] **2.4** Run tests and confirm ALL new tests PASS
  ```bash
  make test ARGS='apps.metrics.tests.test_pr_list_service::TestReviewerNameFilterPendingState'
  ```

### 🔵 REFACTOR Phase - Clean Up

- [ ] **3.1** Review code for duplication
- [ ] **3.2** Add/update docstrings
- [ ] **3.3** Ensure consistent style
- [ ] **3.4** Run tests to confirm still passing
  ```bash
  make test ARGS='apps.metrics.tests.test_pr_list_service::TestReviewerNameFilterPendingState'
  ```

## Quality Assurance

- [ ] **4.1** Run full test suite
  ```bash
  make test
  ```
- [ ] **4.2** Run linting
  ```bash
  make ruff
  ```
- [ ] **4.3** Verify no regressions in existing reviewer_name tests

## Verification with Real Data

- [ ] **5.1** Navigate to posthog-demo team dashboard
- [ ] **5.2** Check insights for `@@` reviewer mentions
- [ ] **5.3** Click `@@pauldambra` link
- [ ] **5.4** Confirm PR #2810 is NOT shown (he approved it)
- [ ] **5.5** Confirm only genuinely pending PRs appear
- [ ] **5.6** Test with other reviewer links

## Completion

- [ ] **6.1** Update PLAN.md with completion status
- [ ] **6.2** Commit changes with descriptive message
- [ ] **6.3** Mark task as complete

---

## Test Results Log

### RED Phase Results

```
Date: ____-__-__
Tests Run: __
Tests Failed: __ (expected: all new tests)
Notes:
```

### GREEN Phase Results

```
Date: ____-__-__
Tests Run: __
Tests Passed: __ (expected: all)
Notes:
```

### Full Suite Results

```
Date: ____-__-__
Tests Run: __
Tests Passed: __
Tests Failed: __ (expected: 0)
Notes:
```
