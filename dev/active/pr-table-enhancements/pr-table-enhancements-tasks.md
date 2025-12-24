# PR Table Enhancements - Tasks

**Last Updated: 2025-12-24**

## Phase 1: Comments Column (S effort)

- [ ] Add Comments column header to table.html (between Lines and AI)
- [ ] Add Comments data cell displaying `pr.total_comments|default:0`
- [ ] Adjust all column widths to fit new column (total 100%)
- [ ] Update empty state colspan (9 → 10)
- [ ] Test column renders correctly with data

## Phase 2: Time Range Button Fix (S effort)

- [ ] Add `updateTimeRangeButtons()` function to base_analytics.html
- [ ] Register HTMX event listeners for URL changes
- [ ] Test: Click 7d → 7d button highlights immediately (no refresh needed)
- [ ] Test: Click 30d → 30d button highlights immediately
- [ ] Test: Click 90d → 90d button highlights immediately

## Phase 3: Sortable Columns (M effort)

### Backend Changes
- [ ] Add `SORT_FIELDS` mapping dict to pr_list_views.py
- [ ] Add `_get_sort_from_request()` helper function
- [ ] Modify `_get_pr_list_context()` to accept and apply sort params
- [ ] Update `pr_list()` view to pass sort/order to context
- [ ] Update `pr_list_table()` view to pass sort/order to context
- [ ] Add `sort_url` template tag to pr_list_tags.py

### Template Changes
- [ ] Make Cycle Time header sortable with HTMX
- [ ] Make Review Time header sortable with HTMX
- [ ] Make Lines header sortable with HTMX
- [ ] Make Comments header sortable with HTMX
- [ ] Make Merged header sortable with HTMX
- [ ] Add sort indicator (▲/▼) to sorted column
- [ ] Add cursor-pointer and hover styles to sortable headers

### URL Param Handling
- [ ] Sort URL preserves all existing filters
- [ ] Sort URL resets page to 1
- [ ] Pagination preserves sort params

## Phase 4: Testing (M effort)

### Unit Tests
- [ ] Test `_get_sort_from_request()` extracts params correctly
- [ ] Test invalid order defaults to 'desc'
- [ ] Test sort by each sortable field
- [ ] Test sort order toggling
- [ ] Test sort with filters combined
- [ ] Test sort resets pagination

### E2E Tests (tests/e2e/pr_table.spec.ts)
- [ ] Test Comments column visible with values
- [ ] Test click Cycle Time sorts ascending (shows ▲)
- [ ] Test click Cycle Time again sorts descending (shows ▼)
- [ ] Test pagination links preserve sort order
- [ ] Test filter + sort combination works
- [ ] Test time range buttons highlight on HTMX click

## Acceptance Criteria

1. **Comments Column**
   - Column visible between Lines and AI
   - Shows integer count or 0 for null
   - Right-aligned, monospace font

2. **Time Range Buttons**
   - Clicking 7d/30d/90d immediately updates button highlighting
   - No manual page refresh required
   - Works with browser back/forward

3. **Sortable Columns**
   - 5 columns sortable: Cycle Time, Review Time, Lines, Comments, Merged
   - Click toggles asc/desc
   - Active sort shows ▲ or ▼ indicator
   - Sorting preserves all filters
   - Sorting resets to page 1
   - Pagination preserves sort order

## Files to Modify

| File | Changes |
|------|---------|
| `templates/metrics/pull_requests/partials/table.html` | Add Comments column, sortable headers |
| `templates/metrics/analytics/base_analytics.html` | Add time range button JS |
| `apps/metrics/views/pr_list_views.py` | Add sort param handling |
| `apps/metrics/templatetags/pr_list_tags.py` | Add sort_url tag |
| `apps/metrics/tests/test_pr_list_views.py` | Add sort tests |
| `tests/e2e/pr_table.spec.ts` | Add E2E tests (new file) |

## Dependencies

- No migrations needed
- No model changes needed
- HTMX already configured
