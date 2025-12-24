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

## Phase 4: Self-Reviewed Detection (S effort) ✅

### Backend Changes
- [x] Add reviewer_count and has_author_review annotations to get_prs_queryset
- [x] ~~Add self_reviewed filter parameter ('yes'/'no')~~ (Removed - data shows <1% usage)
- [x] ~~Add self_reviewed to filter_keys in views~~ (Removed)

### Template Changes
- [x] ~~Add Self-Reviewed filter dropdown to pull_requests.html~~ (Removed - low usage)
- [x] Add "Self" badge next to author name when PR is self-reviewed
- [x] Badge uses warning color (yellow) to indicate potential code quality concern

**Note**: Self-reviewed filter removed because only 6 PRs (0.36%) across all data are self-reviewed. Badge kept as informational indicator.

## Phase 5: Testing (M effort) ✅

### Unit Tests
- [x] Test `_get_sort_from_request()` extracts params correctly
- [x] Test invalid order defaults to 'desc'
- [x] Test sort by each sortable field
- [x] Test sort order toggling
- [x] Test sort with filters combined
- [x] Test sort handles null values (nulls last)
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
   - ~~Filter dropdown~~ (Removed - <1% of data matches this filter)

## Files Modified

| File | Changes |
|------|---------|
| `templates/metrics/pull_requests/partials/table.html` | Added Comments column, sortable headers, Self badge |
| `templates/metrics/analytics/base_analytics.html` | Added time range button JS |
| `templates/metrics/analytics/pull_requests.html` | Added Self-Reviewed filter dropdown |
| `apps/metrics/views/pr_list_views.py` | Added sort param handling, self_reviewed filter |
| `apps/metrics/services/pr_list_service.py` | Added self-reviewed annotations and filtering |
| `apps/metrics/templatetags/pr_list_tags.py` | Added sort_url tag |
| `apps/metrics/tests/test_pr_list_views.py` | 12 sorting tests + 2 badge tests |
| `tests/e2e/analytics.spec.ts` | Added 11 new E2E tests |

## Test Results

- **34 unit tests passing** (view tests only: 18 original + 12 sorting + 2 badge + 2 other)
- **E2E tests passing** for PR table features

## Phase 6: Size Column Improvements (S effort) ✅

**Completed: 2025-12-24**

### Changes Made
- [x] Replace "Lines" column with "Size" buckets (XS/S/M/L/XL)
- [x] Add `calculate_pr_size_bucket()` utility function in `pr_list_service.py`
- [x] Add `pr_size_bucket` template filter in `pr_list_tags.py`
- [x] Add author name truncation with ellipsis (100px max, tooltip on hover)
- [x] Change native `title` tooltip to DaisyUI `tooltip` with `data-tip` for instant display (no 500ms delay)
- [x] Use neutral `badge-ghost` for all size buckets (no colors per user preference)
- [x] 22 unit tests for size bucket filter (TDD)

### Size Buckets
| Bucket | Lines Changed |
|--------|---------------|
| XS | 0-10 |
| S | 11-50 |
| M | 51-200 |
| L | 201-500 |
| XL | 501+ |

### Commits
- `d1a5b5f` - Replace Lines column with Size column, add author ellipsis
- `0cc0c55` - Move pr-list-size-column to dev/completed
- `1b49a0f` - Use DaisyUI tooltip for instant Size hover display
