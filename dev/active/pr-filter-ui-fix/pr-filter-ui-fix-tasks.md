# PR Filter UI Fix - Tasks

**Last Updated: 2025-12-24**

## Completed Tasks

- [x] Add Size filter dropdown to pull_requests.html
- [x] Add Reviewer filter dropdown to pull_requests.html
- [x] Add AI Tool filter dropdown to pull_requests.html (conditional)
- [x] Add Has Jira filter dropdown to pull_requests.html
- [x] Handle `days` URL parameter - convert to date_from/date_to
- [x] Verify date inputs preserve values from analytics tabs
- [x] Adjust table column widths (Title 30%, State 6%)
- [x] Run unit tests (20 passed)
- [ ] Update old list.html template to match (if still used) - SKIPPED (old template not in use)

## Bug Fix Needed (HIGH PRIORITY)

- [ ] **BUG: Time range button highlighting doesn't update on HTMX navigation**
  - Issue: When clicking 7d/30d/90d buttons via HTMX, the URL updates but button highlighting stays wrong
  - Root cause: HTMX only replaces `#page-content`, not the time range buttons in base_analytics.html
  - Works correctly on full page refresh
  - **Fix needed**: Either include time range buttons in HTMX partial, or use JavaScript to update button classes based on URL

## Testing Required (TDD)

### Unit Tests to Add
- [ ] Test `_get_filters_from_request()` with days parameter conversion
- [ ] Test `pr_list()` view sets correct `days` context variable
- [ ] Test all filter dropdowns render with correct options
- [ ] Test filter value preservation on form submit

### E2E Tests to Add
- [ ] Test time range button highlighting updates correctly on click
- [ ] Test all 4 new filter dropdowns are visible and functional
- [ ] Test days URL parameter converts to date range in date inputs
- [ ] Test filter combinations work together
- [ ] Test CSV export includes all active filters

## Files Modified

| File | Changes |
|------|---------|
| `apps/metrics/views/pr_list_views.py` | Added days→date conversion, days context |
| `templates/metrics/analytics/pull_requests.html` | Added 4 filter dropdowns |
| `templates/metrics/pull_requests/partials/table.html` | Column width adjustments |
| `templates/metrics/analytics/base_analytics.html` | **NEEDS FIX**: time range buttons |
