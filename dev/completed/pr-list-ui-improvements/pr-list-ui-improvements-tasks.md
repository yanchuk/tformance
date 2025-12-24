# PR List UI Improvements - Tasks

**Last Updated: 2025-12-24**

## Progress Overview

- [x] Phase 1: Move Export CSV Button
- [x] Phase 2: Fix Date Filter Pre-population
- [x] Phase 3: Verification

---

## Phase 1: Move Export CSV Button

### Task 1.1: Update Template Header [S]
- [x] Add Export CSV button to header div (line 10-12)
- [x] Style button to match page design (right-aligned)
- [x] Ensure filter params preserved in export URL

### Task 1.2: Remove Old Button Location [S]
- [x] Remove Export CSV from filter actions row (lines 154-160)
- [x] Adjust filter actions row layout (now just Apply + Clear)

---

## Phase 2: Fix Date Filter Pre-population

### Task 2.1: Apply Default Dates to Filters [S]
- [x] In `_get_filters_from_request()`, apply 30-day default when no date params
- [x] Ensure filters dict always has date_from/date_to when using days param
- [x] Update logic to handle both explicit dates and days param

### Task 2.2: Verify Date Sync with Time Range [S]
- [x] Test that clicking 7d updates date fields
- [x] Test that clicking 30d updates date fields
- [x] Test that clicking 90d updates date fields
- [x] Test that manual date entry overrides time range

---

## Phase 3: Verification

### Task 3.1: Run Existing Tests [S]
- [x] Run `pytest apps/metrics/tests/test_pr_list_views.py -v`
- [x] All 34 tests pass

### Task 3.2: Manual Testing [S]
- [x] Verify Export button in header row
- [x] Verify date fields populated on page load
- [x] Verify date fields update on time range change
- [x] Verify export works with filters
- [x] Verify Clear button behavior

---

## Summary of Changes

### Files Modified:
1. `templates/metrics/analytics/pull_requests.html`
   - Moved Export CSV button to header row (next to "Pull Requests" title)
   - Removed from filter actions row

2. `apps/metrics/views/pr_list_views.py`
   - Added `default_days=30` parameter to `_get_filters_from_request()`
   - Applied default 30-day date range when no explicit date params

3. `apps/metrics/tests/test_pr_list_views.py`
   - Updated tests to use explicit `state="merged"` and `merged_at` dates
   - All 34 tests pass
