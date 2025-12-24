# PR List UI Improvements - Context

**Last Updated: 2025-12-24**

## Key Files

| File | Purpose |
|------|---------|
| `templates/metrics/analytics/pull_requests.html` | Main PR list template - modify header and filter sections |
| `apps/metrics/views/pr_list_views.py` | View logic - fix date filter default population |
| `templates/metrics/analytics/base_analytics.html` | Base template with tabs and time range buttons |

## Key Code Sections

### Current Header (pull_requests.html:10-12)
```html
<div class="flex justify-between items-center mb-6">
  <h1 class="pg-title">{% trans "Pull Requests" %}</h1>
</div>
```

### Current Export Button Location (pull_requests.html:154-160)
```html
<a href="{% url 'metrics:pr_list_export' %}{% if request.GET.urlencode %}?{{ request.GET.urlencode }}{% endif %}"
   class="btn btn-outline btn-sm ml-auto">
  <svg ...>...</svg>
  {% trans "Export CSV" %}
</a>
```

### Date Filter Logic (pr_list_views.py:57-68)
```python
days_param = request.GET.get("days")
if days_param and not filters.get("date_from"):
    try:
        days = int(days_param)
        if days > 0:
            today = date.today()
            filters["date_from"] = (today - timedelta(days=days)).isoformat()
            filters["date_to"] = today.isoformat()
    except (ValueError, TypeError):
        pass
```

### Default Days Setting (pr_list_views.py:151-159)
```python
days_param = request.GET.get("days")
if days_param:
    try:
        context["days"] = int(days_param)
    except (ValueError, TypeError):
        context["days"] = 30
else:
    context["days"] = 30  # Default
```

## Dependencies

- No external dependencies
- Uses existing HTMX patterns
- Uses existing DaisyUI styling

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Apply default dates in view, not template | Keeps logic centralized, ensures consistency |
| Move button outside form | Export is a page-level action, not a filter action |
| Keep time range buttons in base template | Maintains consistency across analytics pages |

## Related URLs

- PR List: `/a/<team>/metrics/pull-requests/`
- PR List Export: `/a/<team>/metrics/pull-requests/export/`
