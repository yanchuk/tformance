# PR Size Chart Clickable Links - Context

**Last Updated: 2025-12-24**

## Key Files

### Primary File to Modify

| File | Purpose |
|------|---------|
| `templates/metrics/partials/pr_size_chart.html` | PR size distribution bar chart partial |

### Pages Using the Chart

| File | Description |
|------|-------------|
| `templates/metrics/team_dashboard.html` | Team Dashboard (line 88-93) |
| `templates/metrics/analytics/overview.html` | Analytics Overview (line 93-97) |
| `templates/metrics/analytics/delivery.html` | Analytics Delivery (line 57-62) |

### Supporting Infrastructure (No Changes Needed)

| File | Purpose |
|------|---------|
| `apps/metrics/services/pr_list_service.py` | Size filter implementation (lines 102-109) |
| `apps/metrics/views/pr_list_views.py` | PR list view handling size param |
| `apps/metrics/urls.py` | URL pattern for `metrics:pr_list` |

## PR Size Buckets Reference

From `apps/metrics/services/pr_list_service.py`:

```python
PR_SIZE_BUCKETS = {
    "XS": (0, 10),      # 0-10 lines changed
    "S": (11, 50),      # 11-50 lines changed
    "M": (51, 200),     # 51-200 lines changed
    "L": (201, 500),    # 201-500 lines changed
    "XL": (501, None),  # 501+ lines changed
}
```

## Current Chart Data Structure

The chart receives `chart_data` from `dashboard_service.get_pr_size_distribution()`:

```python
# Returns list of dicts:
[
    {"category": "XS", "count": 5},
    {"category": "S", "count": 12},
    {"category": "M", "count": 8},
    {"category": "L", "count": 3},
    {"category": "XL", "count": 1},
]
```

## Existing Pattern Reference

From `templates/metrics/analytics/delivery.html` (line 123):
```html
<a href="{% url 'metrics:pr_list' %}?size=L" class="btn btn-outline btn-sm justify-start gap-2">
  {% trans "Large PRs" %}
</a>
```

## Color Scheme

| Size Category | Bar Color | Meaning |
|--------------|-----------|---------|
| XS, S | `bg-success` (green) | Good - small PRs |
| M | `bg-warning` (yellow) | Moderate |
| L, XL | `bg-error` (red) | Attention needed - large PRs |

## Key Decisions

1. **Open in new tab** - Use `target="_blank"` to preserve user's current dashboard view
2. **No date filter preservation** - PR List has its own date filters; don't pass dashboard dates
3. **Use group hover** - Tailwind `group` class for coordinated hover effects

## Test URLs

After implementation, verify these work:
- `/a/<team_slug>/metrics/pull-requests/?size=XS`
- `/a/<team_slug>/metrics/pull-requests/?size=S`
- `/a/<team_slug>/metrics/pull-requests/?size=M`
- `/a/<team_slug>/metrics/pull-requests/?size=L`
- `/a/<team_slug>/metrics/pull-requests/?size=XL`
