# PR Filter UI Fix - Context

**Last Updated: 2025-12-24**

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/pr_list_service.py` | Backend filter logic, PR_SIZE_BUCKETS |
| `apps/metrics/views/pr_list_views.py` | View that extracts filters from request |
| `templates/metrics/analytics/pull_requests.html` | Main template with filter UI |
| `templates/metrics/pull_requests/list.html` | Old standalone template (same issue) |

## Filter Options Available in Context

The view passes `filter_options` to templates:
```python
{
    "repos": [...],           # List of repo names
    "authors": [{"id": "", "name": ""}],
    "reviewers": [{"id": "", "name": ""}],
    "ai_tools": [...],        # List of detected AI tools
    "size_buckets": PR_SIZE_BUCKETS,
    "states": ["open", "merged", "closed"],
}
```

## Missing Filter UI Elements

### 1. Size Filter
```html
<!-- PR Size Filter -->
<div class="form-control">
  <label class="label">
    <span class="label-text text-base-content/80">{% trans "PR Size" %}</span>
  </label>
  <select name="size" class="select select-bordered select-sm w-full">
    <option value="">{% trans "All Sizes" %}</option>
    <option value="XS" {% if filters.size == 'XS' %}selected{% endif %}>XS (0-10 lines)</option>
    <option value="S" {% if filters.size == 'S' %}selected{% endif %}>S (11-50 lines)</option>
    <option value="M" {% if filters.size == 'M' %}selected{% endif %}>M (51-200 lines)</option>
    <option value="L" {% if filters.size == 'L' %}selected{% endif %}>L (201-500 lines)</option>
    <option value="XL" {% if filters.size == 'XL' %}selected{% endif %}>XL (501+ lines)</option>
  </select>
</div>
```

### 2. Reviewer Filter
```html
<!-- Reviewer Filter -->
<div class="form-control">
  <label class="label">
    <span class="label-text text-base-content/80">{% trans "Reviewer" %}</span>
  </label>
  <select name="reviewer" class="select select-bordered select-sm w-full">
    <option value="">{% trans "All Reviewers" %}</option>
    {% for reviewer in filter_options.reviewers %}
    <option value="{{ reviewer.id }}" {% if filters.reviewer == reviewer.id %}selected{% endif %}>{{ reviewer.name }}</option>
    {% endfor %}
  </select>
</div>
```

### 3. AI Tool Filter
```html
<!-- AI Tool Filter -->
{% if filter_options.ai_tools %}
<div class="form-control">
  <label class="label">
    <span class="label-text text-base-content/80">{% trans "AI Tool" %}</span>
  </label>
  <select name="ai_tool" class="select select-bordered select-sm w-full">
    <option value="">{% trans "All Tools" %}</option>
    {% for tool in filter_options.ai_tools %}
    <option value="{{ tool }}" {% if filters.ai_tool == tool %}selected{% endif %}>{{ tool }}</option>
    {% endfor %}
  </select>
</div>
{% endif %}
```

### 4. Has Jira Filter
```html
<!-- Has Jira Link Filter -->
<div class="form-control">
  <label class="label">
    <span class="label-text text-base-content/80">{% trans "Jira Link" %}</span>
  </label>
  <select name="has_jira" class="select select-bordered select-sm w-full">
    <option value="">{% trans "All" %}</option>
    <option value="yes" {% if filters.has_jira == 'yes' %}selected{% endif %}>{% trans "Has Jira" %}</option>
    <option value="no" {% if filters.has_jira == 'no' %}selected{% endif %}>{% trans "No Jira" %}</option>
  </select>
</div>
```

## Dependencies

- No model changes required
- No new backend code needed
- Template-only changes
