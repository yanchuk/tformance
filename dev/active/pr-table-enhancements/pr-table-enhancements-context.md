# PR Table Enhancements - Context

**Last Updated: 2025-12-24**

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/views/pr_list_views.py` | View handling filters, pagination, sorting |
| `templates/metrics/pull_requests/partials/table.html` | PR table template |
| `templates/metrics/analytics/base_analytics.html` | Base template with time range buttons |
| `apps/metrics/templatetags/pr_list_tags.py` | Custom template tags for pagination URLs |
| `apps/metrics/models/github.py:119` | PullRequest.total_comments field |

## Current Table Columns

1. Title (30%) - with Jira badge
2. Repository (12%)
3. Author (10%)
4. State (6%) - badge
5. Cycle Time (8%) - right aligned
6. Review Time (9%) - right aligned
7. Lines (9%) - +additions/-deletions
8. AI (5%) - center badge
9. Merged (11%) - date

## Columns to Add/Modify

### Add: Comments Column
- Position: Between Lines and AI
- Width: 6%
- Content: `{{ pr.total_comments|default:0 }}`
- Alignment: right, font-mono

### New Column Widths (total 100%)
```
Title: 28% (was 30%)
Repository: 11% (was 12%)
Author: 9% (was 10%)
State: 6%
Cycle Time: 8%
Review Time: 8% (was 9%)
Lines: 8% (was 9%)
Comments: 6% (NEW)
AI: 5%
Merged: 11%
```

## Sorting Implementation

### URL Parameters
- `sort` - field to sort by
- `order` - `asc` or `desc`

### Sortable Fields Mapping
```python
SORT_FIELDS = {
    "cycle_time": "cycle_time_hours",
    "review_time": "review_time_hours",
    "lines": "additions",  # or F('additions') + F('deletions')
    "comments": "total_comments",
    "merged": "merged_at",
}
```

### View Changes (pr_list_views.py)

```python
def _get_sort_from_request(request: HttpRequest) -> tuple[str, str]:
    """Extract sort parameters from request."""
    sort = request.GET.get("sort", "merged")
    order = request.GET.get("order", "desc")
    if order not in ("asc", "desc"):
        order = "desc"
    return sort, order

def _get_pr_list_context(team, filters: dict, page_number: int = 1, sort: str = "merged", order: str = "desc") -> dict:
    # Get filtered queryset
    prs = get_prs_queryset(team, filters)

    # Apply sorting
    sort_field = SORT_FIELDS.get(sort, "merged_at")
    if order == "desc":
        sort_field = f"-{sort_field}"
    prs = prs.order_by(sort_field, "-pr_created_at")  # Secondary sort by created

    # ... rest unchanged

    return {
        # ... existing fields
        "sort": sort,
        "order": order,
    }
```

### Template Tag (pr_list_tags.py)

```python
@register.simple_tag(takes_context=True)
def sort_url(context, field):
    """Generate URL for sorting by field, toggling order if already sorted."""
    request = context['request']
    current_sort = context.get('sort', 'merged')
    current_order = context.get('order', 'desc')

    # Build new params
    params = request.GET.copy()
    params['sort'] = field

    # Toggle order if clicking same field
    if field == current_sort:
        params['order'] = 'asc' if current_order == 'desc' else 'desc'
    else:
        params['order'] = 'desc'  # Default desc for new sort

    params['page'] = '1'  # Reset to first page on sort change

    return '?' + params.urlencode()
```

### Sortable Header Template Pattern

```html
<th class="w-[8%] text-right cursor-pointer hover:bg-base-300 select-none"
    hx-get="{% url 'metrics:pr_list_table' %}{% sort_url 'cycle_time' %}"
    hx-target="#pr-table-container"
    hx-swap="innerHTML"
    hx-push-url="{% sort_url 'cycle_time' %}">
  {% trans "Cycle Time" %}
  {% if sort == 'cycle_time' %}
    <span class="ml-1">{% if order == 'asc' %}▲{% else %}▼{% endif %}</span>
  {% endif %}
</th>
```

## Time Range Button Fix

### Current JavaScript (lines 108-135 of base_analytics.html)
Only handles tab navigation, not time range buttons.

### Add This Function
```javascript
function updateTimeRangeButtons() {
  const params = new URLSearchParams(window.location.search);
  const days = parseInt(params.get('days')) || 30;

  document.querySelectorAll('.join a[href^="?days="]').forEach(btn => {
    const btnHref = btn.getAttribute('href');
    const btnDays = parseInt(new URLSearchParams(btnHref.split('?')[1]).get('days'));

    if (btnDays === days) {
      btn.classList.add('btn-primary');
      btn.classList.remove('btn-ghost');
    } else {
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-ghost');
    }
  });
}

// Add to existing event listeners
document.body.addEventListener('htmx:pushedIntoHistory', updateTimeRangeButtons);
document.body.addEventListener('htmx:replacedInHistory', updateTimeRangeButtons);
window.addEventListener('popstate', updateTimeRangeButtons);
```

## Test Requirements

### Unit Tests (apps/metrics/tests/test_pr_list_views.py)
- Test sort param handling
- Test order param validation
- Test default sort behavior
- Test sort URL preservation with filters

### E2E Tests (tests/e2e/pr_table.spec.ts)
- Test comments column visible
- Test clicking sortable header changes order
- Test sort indicator displays correctly
- Test pagination preserves sort
- Test time range buttons highlight correctly

## Commands

```bash
# Run PR list tests
make test ARGS='apps/metrics/tests/test_pr_list_views.py -v'

# Run E2E tests
npx playwright test tests/e2e/pr_table.spec.ts

# Check lint
make ruff
```
