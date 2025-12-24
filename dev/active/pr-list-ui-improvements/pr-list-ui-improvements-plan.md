# PR List UI Improvements Plan

**Last Updated: 2025-12-24**

## Executive Summary

This plan addresses two UI issues in the Pull Requests page (`/a/<team>/metrics/pull-requests/`):

1. **Export CSV Button Position** - Move from inside filter form to header row next to "Pull Requests" heading
2. **Date Filter Pre-population** - When using Time Range buttons (7d/30d/90d), the Date From/Date To fields should display the calculated dates instead of showing empty

## Current State Analysis

### Template Structure
- Base template: `templates/metrics/analytics/base_analytics.html`
- PR list template: `templates/metrics/analytics/pull_requests.html`
- Both templates share the time range selector (7d/30d/90d buttons)

### Current Behavior

**Export CSV Button:**
- Located at line 154-160 in `pull_requests.html`
- Positioned inside the filter form's action row alongside "Apply Filters" and "Clear" buttons
- User wants it elevated to header level for better visibility/accessibility

**Date Filters:**
- View function `_get_filters_from_request()` converts `days` param to `date_from`/`date_to` (lines 57-68 in `pr_list_views.py`)
- However, when no explicit `date_from`/`date_to` in URL, the template shows empty date fields
- The `days` param IS being converted to dates for filtering, but those dates aren't in the `filters` dict shown in template

### Root Cause of Date Bug

In `pr_list_views.py`, `_get_filters_from_request()`:
```python
days_param = request.GET.get("days")
if days_param and not filters.get("date_from"):
    days = int(days_param)
    filters["date_from"] = (today - timedelta(days=days)).isoformat()
    filters["date_to"] = today.isoformat()
```

This correctly adds dates to filters, BUT only when `days` param exists. The issue is:
1. Default page load has NO `days` param in URL
2. View sets `context["days"] = 30` as default for tab highlighting
3. But `filters` dict has no `date_from`/`date_to` since no `days` param was present

**The fix:** Ensure that default behavior (30 days) is applied to both the time range highlight AND the filters dict.

## Proposed Future State

### Export CSV Button
- Moved to header row, right-aligned
- Same visual styling but positioned on same level as "Pull Requests" heading
- Creates cleaner separation between page-level actions and filtering actions

### Date Filters
- When page loads with default 30d selection, Date From/Date To fields show actual dates
- When clicking 7d/30d/90d, date fields update to reflect selection
- Custom date entry still supported and overrides time range buttons

## Implementation Phases

### Phase 1: Move Export CSV Button (UI Change)

**File:** `templates/metrics/analytics/pull_requests.html`

1. Remove Export CSV link from filter actions row (lines 154-160)
2. Add Export CSV button to header row (line 10-12)
3. Ensure proper responsive behavior

### Phase 2: Fix Date Filter Pre-population (Bug Fix)

**File:** `apps/metrics/views/pr_list_views.py`

1. Apply default `days=30` to filters when no explicit date params present
2. Ensure filters dict always contains `date_from`/`date_to` reflecting current selection
3. Keep the days-to-date conversion logic centralized

## Detailed Tasks

### Task 1: Move Export CSV Button to Header [S]
**Acceptance Criteria:**
- Export CSV button appears on same row as "Pull Requests" heading
- Button is right-aligned
- Button preserves current filter params in export URL
- Visual styling consistent with page design

### Task 2: Fix Date Filter Default Population [S]
**Acceptance Criteria:**
- Page load shows 30-day date range in Date From/Date To fields
- Clicking 7d shows calculated 7-day range in date fields
- Clicking 30d shows calculated 30-day range in date fields
- Clicking 90d shows calculated 90-day range in date fields
- Manually entering dates still works and takes precedence
- "Clear" button resets to default 30-day range

### Task 3: Test Changes [S]
**Acceptance Criteria:**
- Manual verification of both features
- Existing PR list tests still pass

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| HTMX partial updates break date sync | Low | Medium | Test all interaction paths |
| Export URL loses filter params | Low | Medium | Verify request.GET.urlencode() works |

## Success Metrics

1. Export CSV button visible in header on page load
2. Date From/Date To fields populated with dates matching Time Range selection
3. All existing tests pass
4. No regressions in filter/export functionality
