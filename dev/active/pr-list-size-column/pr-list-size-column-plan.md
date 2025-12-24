# PR List Size Column & Author Ellipsis - Plan

**Last Updated:** 2025-12-24

## Executive Summary

Replace the "Lines" column (showing `+N -M`) with a "Size" column showing bucket labels (XS, S, M, L, XL). Display exact line counts in a tooltip on hover. Also ensure author names don't overflow by adding ellipsis truncation.

## Current State Analysis

### PR List Table Structure
- **Template:** `templates/metrics/pull_requests/partials/table.html`
- **Service:** `apps/metrics/services/pr_list_service.py`
- **Template Tags:** `apps/metrics/templatetags/pr_list_tags.py`

### Current "Lines" Column (lines 106-109)
```html
<td class="text-right font-mono text-sm">
  <span class="text-success">+{{ pr.additions }}</span>
  <span class="text-error">-{{ pr.deletions }}</span>
</td>
```
- Shows raw additions/deletions counts
- Sortable by "lines" (additions + deletions)

### Current Author Column (lines 69-81)
```html
<td>
  {% if pr.author %}
    {{ pr.author.display_name }}
    ...
  {% endif %}
</td>
```
- No truncation applied
- Long names can overflow column

### Size Bucket Definitions (pr_list_service.py:13-19)
```python
PR_SIZE_BUCKETS = {
    "XS": (0, 10),
    "S": (11, 50),
    "M": (51, 200),
    "L": (201, 500),
    "XL": (501, None),
}
```
- Already used for filtering by size
- Need to reuse for display

## Proposed Future State

### Size Column
- Display: Colored badge with size bucket (XS/S/M/L/XL)
- Tooltip on hover: Shows actual `+additions/-deletions`
- Sortable: Keep existing "lines" sort functionality
- Badge colors: Match PR size chart colors for consistency

### Author Column
- Add `truncate` class to limit width
- Use CSS ellipsis for overflow
- Keep tooltip showing full name on hover

## Implementation Phases

### Phase 1: Add Size Bucket Template Filter [S]

Create a template filter to calculate size bucket from additions/deletions.

**Location:** `apps/metrics/templatetags/pr_list_tags.py`

**New filter:**
```python
@register.filter
def pr_size_bucket(pr) -> str:
    """Return size bucket (XS/S/M/L/XL) based on total lines."""

@register.filter
def pr_size_badge_class(size_bucket: str) -> str:
    """Return DaisyUI badge class for size bucket."""
```

### Phase 2: Update Table Template [S]

Replace Lines column with Size column:
- Change header from "Lines" to "Size"
- Change cell to show badge with bucket label
- Add tooltip with exact line counts
- Keep sorting functionality (still sort by "lines")

### Phase 3: Fix Author Column Ellipsis [S]

Add truncation to author column:
- Add `truncate max-w-[80px]` classes to container
- Add `title` attribute for full name tooltip
- Apply to both regular authors and bot authors

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sorting confusion | Low | Keep "lines" as sort key, tooltip shows exact counts |
| Badge color accessibility | Low | Use existing DaisyUI semantic colors |
| Long author names UX | Low | Tooltip shows full name |

## Success Metrics

- [ ] Size column shows XS/S/M/L/XL badges
- [ ] Hovering on size badge shows exact `+N/-M` counts
- [ ] Sorting by size still works correctly
- [ ] Author names truncate with ellipsis for names > 80px
- [ ] Full author name visible on hover
- [ ] All existing PR list tests pass

## Technical Details

### Size Badge Colors (match PR size chart)
```python
SIZE_BADGE_CLASSES = {
    "XS": "badge-success",   # Green - tiny changes
    "S": "badge-info",       # Blue - small
    "M": "badge-warning",    # Yellow - medium
    "L": "badge-error",      # Red - large
    "XL": "badge-error",     # Red - extra large
}
```

### Tooltip Implementation
Use `title` attribute for native browser tooltip:
```html
<span class="badge {{ size|pr_size_badge_class }}"
      title="+{{ pr.additions }}/-{{ pr.deletions }}">
  {{ size }}
</span>
```

### Author Ellipsis
```html
<td class="truncate max-w-[80px]" title="{{ pr.author.display_name }}">
  {{ pr.author.display_name }}
</td>
```
