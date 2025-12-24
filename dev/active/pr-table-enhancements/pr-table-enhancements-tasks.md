# PR Table Enhancements - Tasks

**Last Updated: 2025-12-24**

## Phase 1: Comments Column (S effort) ✅

- [x] Add Comments column header to table.html (between Lines and AI)
- [x] Add Comments data cell displaying `pr.total_comments|default:0`
- [x] Adjust all column widths to fit new column (total 100%)
- [x] Update empty state colspan (9 → 10)
- [x] Test column renders correctly with data

## Phase 2: Time Range Button Fix (S effort) ✅

- [x] Add `updateTimeRangeButtons()` function to base_analytics.html
- [x] Register HTMX event listeners for URL changes
- [x] Test: Click 7d → 7d button highlights immediately (no refresh needed)
- [x] Test: Click 30d → 30d button highlights immediately
- [x] Test: Click 90d → 90d button highlights immediately

## Phase 3: Sortable Columns (M effort) ✅

### Backend Changes
- [x] Add `SORT_FIELDS` mapping dict to pr_list_views.py
- [x] Add `_get_sort_from_request()` helper function
- [x] Modify `_get_pr_list_context()` to accept and apply sort params
- [x] Update `pr_list()` view to pass sort/order to context
- [x] Update `pr_list_table()` view to pass sort/order to context
- [x] Add `sort_url` template tag to pr_list_tags.py

### Template Changes
- [x] Make Cycle Time header sortable with HTMX
- [x] Make Review Time header sortable with HTMX
- [x] Make Lines header sortable with HTMX
- [x] Make Comments header sortable with HTMX
- [x] Make Merged header sortable with HTMX
- [x] Add sort indicator (▲/▼) to sorted column
- [x] Add cursor-pointer and hover styles to sortable headers

### URL Param Handling
- [x] Sort URL preserves all existing filters
- [x] Sort URL resets page to 1
- [x] Pagination preserves sort params

## Phase 4: Self-Reviewed Detection (M effort) ✅

### Backend Changes
- [x] Add reviewer_count and has_author_review annotations to get_prs_queryset
- [x] Add self_reviewed filter parameter ('yes'/'no')
- [x] Add self_reviewed to filter_keys in views

### Template Changes
- [x] Add Self-Reviewed filter dropdown to pull_requests.html
- [x] Add "Self" badge next to author name when PR is self-reviewed
- [x] Badge uses warning color (yellow) to indicate potential code quality concern

## Phase 5: Testing (M effort) ✅

### Unit Tests
- [x] Test `_get_sort_from_request()` extracts params correctly
- [x] Test invalid order defaults to 'desc'
- [x] Test sort by each sortable field
- [x] Test sort order toggling
- [x] Test sort with filters combined
- [x] Test sort handles null values (nulls last)
- [x] Test self_reviewed=yes filter
- [x] Test self_reviewed=no filter
- [x] Test self-reviewed badge displays
- [x] Test multi-reviewer PRs not marked as self-reviewed

### E2E Tests (tests/e2e/analytics.spec.ts)
- [x] Test Comments column visible
- [x] Test sortable columns have cursor-pointer class
- [x] Test click Cycle Time sorts and updates URL
- [x] Test clicking same column toggles asc/desc
- [x] Test sort indicator shows on active column
- [x] Test sorting preserves filters
- [x] Test time range buttons highlight on HTMX click

## Acceptance Criteria - ALL MET ✅

1. **Comments Column** ✅
   - Column visible between Lines and AI
   - Shows integer count or 0 for null
   - Right-aligned, monospace font

2. **Time Range Buttons** ✅
   - Clicking 7d/30d/90d immediately updates button highlighting
   - No manual page refresh required
   - Works with browser back/forward

3. **Sortable Columns** ✅
   - 5 columns sortable: Cycle Time, Review Time, Lines, Comments, Merged
   - Click toggles asc/desc
   - Active sort shows ▲ or ▼ indicator
   - Sorting preserves all filters
   - Sorting resets to page 1
   - Pagination preserves sort order

4. **Self-Reviewed Detection** ✅
   - "Self" badge shown when author is the only reviewer
   - Filter dropdown to show only self-reviewed or externally-reviewed PRs
   - Works with all other filters

## Files Modified

| File | Changes |
|------|---------|
| `templates/metrics/pull_requests/partials/table.html` | Added Comments column, sortable headers, Self badge |
| `templates/metrics/analytics/base_analytics.html` | Added time range button JS |
| `templates/metrics/analytics/pull_requests.html` | Added Self-Reviewed filter dropdown |
| `apps/metrics/views/pr_list_views.py` | Added sort param handling, self_reviewed filter |
| `apps/metrics/services/pr_list_service.py` | Added self-reviewed annotations and filtering |
| `apps/metrics/templatetags/pr_list_tags.py` | Added sort_url tag |
| `apps/metrics/tests/test_pr_list_views.py` | Added 16 new tests (12 sorting + 4 self-reviewed) |
| `tests/e2e/analytics.spec.ts` | Added 11 new E2E tests |

## Test Results

- **72 unit tests passing** (36 original + 12 sorting + 4 self-reviewed + 20 other)
- **E2E tests passing** for PR table features
