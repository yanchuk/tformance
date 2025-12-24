# PR Table Enhancements - Implementation Plan

**Last Updated: 2025-12-24**

## Executive Summary

Enhance the Pull Requests data explorer table with three improvements:
1. Add Comments column displaying `total_comments` from PullRequest model
2. Add sortable column headers (ascending/descending) via HTMX
3. Fix time range button highlighting on HTMX navigation

## Current State Analysis

### Comments Column
- `total_comments` field exists in `PullRequest` model (IntegerField, nullable)
- Already included in CSV export (line 202 of pr_list_views.py)
- NOT displayed in table template

### Table Sorting
- Currently NO sorting UI - just hardcoded `order_by("-merged_at", "-pr_created_at")`
- View supports pagination via HTMX partials
- Need to add `sort` and `order` URL params

### Time Range Button Bug
- Buttons (7d/30d/90d) use HTMX to update `#page-content`
- But buttons themselves are in `base_analytics.html` (outside the target)
- Result: URL updates but button highlighting doesn't change until page refresh
- Existing JS only handles tab navigation, not time range buttons

## Proposed Future State

### Phase 1: Comments Column (S effort)
Add Comments column to table between "Lines" and "AI" columns.

### Phase 2: Sortable Columns (M effort)
Click column header to sort ascending, click again for descending.
- Add sort indicator icons (▲/▼)
- Persist sort via URL params (`?sort=cycle_time&order=desc`)
- HTMX updates table partial only

### Phase 3: Fix Time Range Highlighting (S effort)
Add JavaScript to update button classes after HTMX navigation.

## Implementation Phases

### Phase 1: Comments Column

**Files to modify:**
- `templates/metrics/pull_requests/partials/table.html`

**Changes:**
1. Add `<th>` for Comments header (between Lines and AI)
2. Add `<td>` displaying `pr.total_comments|default:0`
3. Adjust column widths (reduce Title from 30% to 28%)
4. Update colspan in empty state row (9 → 10)

### Phase 2: Sortable Column Headers

**Files to modify:**
- `apps/metrics/views/pr_list_views.py` - Add sort/order param handling
- `templates/metrics/pull_requests/partials/table.html` - Sortable headers
- `apps/metrics/templatetags/pr_list_tags.py` - Add sort_url tag

**Sortable columns:**
- Cycle Time (`cycle_time_hours`)
- Review Time (`review_time_hours`)
- Lines (sort by `additions + deletions` or just `additions`)
- Comments (`total_comments`)
- Merged (`merged_at`)

**URL format:** `?sort=cycle_time&order=asc` or `?sort=cycle_time&order=desc`

**UI pattern:**
```html
<th class="cursor-pointer hover:bg-base-300"
    hx-get="?sort=cycle_time&order={% if sort == 'cycle_time' and order == 'asc' %}desc{% else %}asc{% endif %}"
    hx-target="#pr-table-container"
    hx-swap="innerHTML">
  Cycle Time
  {% if sort == 'cycle_time' %}
    {% if order == 'asc' %}▲{% else %}▼{% endif %}
  {% endif %}
</th>
```

### Phase 3: Time Range Button Fix

**Files to modify:**
- `templates/metrics/analytics/base_analytics.html`

**Solution:** Add JavaScript to update button classes on HTMX URL change:
```javascript
function updateTimeRangeButtons() {
  const params = new URLSearchParams(window.location.search);
  const days = parseInt(params.get('days')) || 30;

  document.querySelectorAll('.join a[href^="?days="]').forEach(btn => {
    const btnDays = parseInt(new URL(btn.href, window.location.origin).searchParams.get('days'));
    btn.classList.toggle('btn-primary', btnDays === days);
    btn.classList.toggle('btn-ghost', btnDays !== days);
  });
}

document.body.addEventListener('htmx:pushedIntoHistory', updateTimeRangeButtons);
document.body.addEventListener('htmx:replacedInHistory', updateTimeRangeButtons);
window.addEventListener('popstate', updateTimeRangeButtons);
```

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sort performance on large datasets | Medium | Use DB-level ordering, test with pagination |
| Column width overflow | Low | Test with long values, use truncation |
| HTMX state conflicts | Low | Preserve all URL params on sort/pagination |

## Success Metrics

- [ ] Comments column visible with correct values
- [ ] All sortable columns respond to clicks
- [ ] Sort indicators show current sort state
- [ ] Pagination preserves sort order
- [ ] Time range buttons highlight correctly on HTMX navigation
- [ ] All existing E2E tests pass
- [ ] New E2E tests cover sorting functionality

## Dependencies

- No model changes needed (`total_comments` already exists)
- No migrations needed
- HTMX already configured for partial updates
