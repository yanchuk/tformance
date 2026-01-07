# Individual Performance Analytics - Tasks Checklist

**Last Updated**: 2026-01-05 (Phase 1 Complete)

## Setup

- [x] Create feature branch: `feature/individual-performance-analytics`
- [x] Create worktree: `git worktree add ../tformance-individual-perf feature/individual-performance-analytics`
- [x] Navigate to worktree and verify setup

---

## Phase 1: Service Layer Enhancement (TDD) ✅ COMPLETE

### 1.1 Add Tests for New Metrics (RED Phase) ✅

- [x] **T1.1.1** Write test for `avg_pr_size` in `get_team_breakdown()` [S]
- [x] **T1.1.2** Write test for `reviews_given` in `get_team_breakdown()` [S]
- [x] **T1.1.3** Write test for `avg_review_response_hours` [M]
- [x] **T1.1.4** Write test for `ai_pct` using `is_ai_assisted` field [S]
- [x] **T1.1.5** Write test for `get_team_averages()` function [M]
- [ ] **T1.1.6** Write test for comparison flags [S] - DEFERRED to Phase 3

### 1.2 Implement New Metrics (GREEN Phase) ✅

- [x] **T1.2.1** Add `avg_pr_size` to `get_team_breakdown()` [S]
- [x] **T1.2.2** Add `reviews_given` aggregation [M]
- [x] **T1.2.3** Add `avg_review_response_hours` calculation [M]
- [x] **T1.2.4** Switch `ai_pct` to use `is_ai_assisted` field [M]
- [x] **T1.2.5** Implement `get_team_averages()` function [S]
- [ ] **T1.2.6** Add comparison flags to result [S] - DEFERRED to Phase 3

### 1.3 Add New Sort Options ✅

- [x] **T1.3.1** Add `pr_size` to SORT_FIELDS in `get_team_breakdown()`
- [x] **T1.3.2** Add `reviews` to SORT_FIELDS
- [x] **T1.3.3** Add `response_time` to SORT_FIELDS
- [x] **T1.3.4** Tests for new sort options covered by existing tests

**Commit**: `d2dba34` - 27 tests pass (10 new)

---

## Phase 2: View Layer Updates ✅ COMPLETE

### 2.1 Update View Function ✅

- [x] **T2.1.1** Add new sort fields to ALLOWED_SORT_FIELDS [S]
  - Added: `pr_size`, `reviews`, `response_time`

- [x] **T2.1.2** Call `get_team_averages()` and add to context [S]
  - Pass `team_averages` dict to template

- [x] **T2.1.3** Write integration test for new sort options [S]
  - 4 new tests added: sort by pr_size, reviews, response_time, and team_averages context

**Tests**: 20 view tests pass (4 new)

---

## Phase 3: Template Enhancement ✅ COMPLETE

### 3.1 Add Column Headers ✅

- [x] **T3.1.1** Add "PR Size" column header with sort [S]
- [x] **T3.1.2** Add "Reviews" column header with sort [S]
- [x] **T3.1.3** Add "Response" column header with sort [S]
- [x] **T3.1.4** Update AI-Assisted header text to "AI %" [S]

### 3.2 Add Data Cells ✅

- [x] **T3.2.1** Add PR Size cell with formatting (floatformat:0, handle null)
- [x] **T3.2.2** Add Reviews Given cell (default:0)
- [x] **T3.2.3** Add Response Time cell (floatformat:1 + "h", handle null)
- [x] **T3.2.4** AI % works with service data

### 3.3 Add Team Average Footer Row ✅

- [x] **T3.3.1** Add `<tfoot>` element with Team Average row
  - `bg-base-200 font-semibold` styling
  - Displays all 7 averages

### 3.4 Add Visual Highlighting - DEFERRED

- [ ] **T3.4.1** Add conditional CSS classes for better/worse [M]
  - Requires custom template filter for decimal comparisons
  - Can be added in future iteration

### 3.5 Responsive Design ✅

- [x] **T3.5.1** Hide PR Size, Reviews columns on mobile (`hidden md:table-cell`)
- [x] **T3.5.2** Hide Response Time column on tablet (`hidden lg:table-cell`)

**Commit**: `1baf56c`

---

## Phase 4: Testing & Polish ✅ COMPLETE

### 4.1 Unit Tests ✅

- [x] **T4.1.1** Verify all new service tests pass - 27 tests pass
- [x] **T4.1.2** Edge cases covered (empty team, zero values, null handling)

### 4.2 Integration Tests ✅

- [x] **T4.2.1** View tests pass - 20 tests pass
- [x] **T4.2.2** Sorting on all new columns tested
- [x] **T4.2.3** Repo filter works with new metrics

### 4.3 Manual Verification

- [ ] **T4.3.1** Visual check on desktop - PENDING (requires merge to main)
- [ ] **T4.3.2** Visual check on mobile - PENDING
- [ ] **T4.3.3** Color highlighting - DEFERRED
- [ ] **T4.3.4** Team Average row formatting - PENDING
- [ ] **T4.3.5** Test with real data on dev.ianchuk.com - PENDING

**Note**: Visual verification pending because dev server needs to run from main branch.
Automated tests pass - visual verification can be done after merge.

---

## Completion Checklist

- [x] All feature tests passing (40 tests: 27 service + 4 view + 9 existing)
- [x] Ruff linting passes
- [ ] Manual visual verification - PENDING merge to main
- [ ] PR created with description
- [ ] Moved task docs to `dev/completed/`

---

## Effort Legend

- **S** = Small (< 30 min)
- **M** = Medium (30 min - 2 hours)
- **L** = Large (2-4 hours)
- **XL** = Extra Large (> 4 hours)

## Task Dependencies

```
T1.1.* (RED) → T1.2.* (GREEN) → T1.3.* (sort options)
                    ↓
              T2.1.* (view)
                    ↓
              T3.*.* (template)
                    ↓
              T4.*.* (testing)
```
