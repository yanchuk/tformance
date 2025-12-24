# Team Analytics Fixes - Context

**Last Updated:** 2025-12-24

## Key Files

### Views
- `apps/metrics/views/chart_views.py` - `team_breakdown_table()` view (line 79)
- `apps/metrics/views/analytics_views.py` - `analytics_team()` main page view

### Services
- `apps/metrics/services/dashboard_service.py` - `get_team_breakdown()` (line 314)
- `apps/metrics/services/dashboard_service.py` - `get_review_distribution()`

### Templates
- `templates/metrics/analytics/team.html` - Main analytics team page
- `templates/metrics/partials/team_breakdown_table.html` - Team breakdown partial

### Template Tags
- `apps/metrics/templatetags/pr_list_tags.py` - `sort_url` tag for sortable columns

### Models
- `apps/metrics/models/team.py` - `TeamMember` model with `github_id` field

### Tests
- `apps/metrics/tests/dashboard/test_team_breakdown.py` - Existing tests
- `apps/metrics/tests/test_chart_views.py` - View tests

## Key Decisions

1. **Avatar URL Construction**: Using GitHub's avatar service with github_id:
   ```python
   avatar_url = f"https://avatars.githubusercontent.com/u/{github_id}?s=80"
   ```

2. **Sorting Pattern**: Reuse PR list sorting pattern with HTMX:
   - Query params: `?sort=field&order=asc|desc`
   - Template tag: `{% sort_url 'field' %}`
   - Headers with `hx-get` attributes

3. **User Links**: Link to PR list with author filter:
   ```html
   <a href="{% url 'metrics:pr_list' %}?author={{ row.member_id }}" target="_blank">
   ```

## Database Context

### TeamMember Fields Used
```sql
SELECT github_id, github_username, display_name FROM metrics_teammember
```

### Polar Team Member Sample
```
id: 686, display_name: Birk Jernström, github_id: 281715, github_username: birkjernstrom
```

## Dependencies

- HTMX for dynamic sorting
- DaisyUI for table styling
- `sort_url` template tag from `pr_list_tags.py`

## URL Patterns

- Team breakdown partial: `path("tables/breakdown/", views.team_breakdown_table, name="table_breakdown")`
- PR list: `path("pull-requests/", pr_list_views.pr_list, name="pr_list")`

## Test Commands

```bash
# Run team breakdown tests
make test ARGS='apps.metrics.tests.dashboard.test_team_breakdown'

# Run chart views tests
make test ARGS='apps.metrics.tests.test_chart_views'
```
