# Pull Request Sidebar Move - Context Document

**Last Updated: 2025-12-30**

## Key Files Reference

### Navigation & Sidebar

| File | Lines | Purpose |
|------|-------|---------|
| `templates/web/components/team_nav.html` | 1-31 | **MODIFY** - Add PR sidebar entry |
| `templates/web/components/app_nav.html` | - | Parent nav structure (reference only) |
| `templates/web/app/app_base.html` | - | Base template for standalone pages |

### Analytics Hub

| File | Lines | Purpose |
|------|-------|---------|
| `templates/metrics/analytics/base_analytics.html` | 1-166 | **MODIFY** - Remove PR tab (line 82-86) |
| `templates/metrics/analytics/overview.html` | 108, 114 | Contains crosslinks to PR list |
| `templates/metrics/analytics/ai_adoption.html` | 122, 128, 134 | Contains crosslinks to PR list |
| `templates/metrics/analytics/delivery.html` | 111, 117, 123 | Contains crosslinks to PR list |
| `templates/metrics/analytics/quality.html` | 141 | Contains crosslinks to PR list |
| `templates/metrics/analytics/team.html` | 116 | Contains crosslinks to PR list |

### PR List Components

| File | Lines | Purpose |
|------|-------|---------|
| `templates/metrics/analytics/pull_requests.html` | 1-388 | Current PR page (extends base_analytics) |
| `templates/metrics/pull_requests/partials/table.html` | 1-252 | PR table partial (reuse) |
| `templates/metrics/pull_requests/partials/expanded_row.html` | - | Expanded row details (reuse) |
| `templates/metrics/partials/date_range_picker.html` | - | Date picker component (reuse) |

### Backend

| File | Lines | Purpose |
|------|-------|---------|
| `apps/metrics/urls.py` | 51-53 | **MODIFY** - URL patterns for PR list |
| `apps/metrics/views/pr_list_views.py` | 156-189 | **MODIFY** - pr_list view function |
| `apps/metrics/views/__init__.py` | - | View exports (may need update) |

### Tests

| File | Purpose |
|------|---------|
| `apps/metrics/tests/test_pr_list_views.py` | Existing PR list tests (extend) |
| `tests/e2e/dashboard.spec.ts` | E2E tests for dashboard/navigation |
| `tests/e2e/smoke.spec.ts` | Smoke tests (may need update) |

### Partials with Crosslinks

| File | Line | Link Target |
|------|------|-------------|
| `templates/metrics/partials/team_breakdown_table.html` | 53 | `?author={{ member_id }}` |
| `templates/metrics/partials/pr_size_chart.html` | 6 | `?size={{ category }}` |

---

## Key Decisions

### Decision 1: URL Structure

**Decision**: Change URL from `/metrics/pull-requests/` to `/pull-requests/`

**Rationale**:
- Cleaner URL for a top-level navigation item
- Aligns with other top-level items (integrations, team settings)
- Shorter, more memorable

**Implementation**:
```python
# New URL pattern (in new app or metrics urls)
path("pull-requests/", views.pr_list, name="pr_list"),
path("pull-requests/table/", views.pr_list_table, name="pr_list_table"),
path("pull-requests/export/", views.pr_list_export, name="pr_list_export"),
```

### Decision 2: Backward Compatibility

**Decision**: Implement permanent redirect (301) from old URL to new URL

**Rationale**:
- Existing bookmarks and shared links continue to work
- Search engines update their indexes
- No user confusion

**Implementation**:
```python
# In metrics/urls.py - keep old pattern as redirect
path("metrics/pull-requests/", RedirectView.as_view(
    pattern_name='pr_list',
    permanent=True
), name="pr_list_redirect"),
```

### Decision 3: Template Strategy

**Decision**: Create new standalone template `list_standalone.html` that doesn't extend `base_analytics.html`

**Rationale**:
- PR page needs its own date picker (not inherited from analytics)
- Cleaner separation of concerns
- Can evolve independently

**Template Structure**:
```
templates/metrics/pull_requests/
├── list_standalone.html  ← NEW (extends app_base.html)
├── partials/
│   ├── table.html        ← REUSE
│   └── expanded_row.html ← REUSE
```

### Decision 4: Crosslink URL Updates

**Decision**: Update all crosslinks to use new URL pattern

**Rationale**:
- Direct links are better UX than redirects
- Cleaner HTML output
- Slightly faster page loads

**Files to Update**:
- `overview.html` (2 links)
- `ai_adoption.html` (3 links)
- `delivery.html` (3 links)
- `quality.html` (1 link)
- `team.html` (1 link)
- `partials/team_breakdown_table.html` (1 link)
- `partials/pr_size_chart.html` (1 link)

### Decision 5: Date Range State Management

**Decision**: PR page will initialize Alpine store from URL params, same as analytics pages

**Rationale**:
- Consistent user experience
- State preserved in URL (shareable, bookmarkable)
- No need for separate state management

**Implementation**:
```html
<!-- In standalone template header -->
<div x-data x-init="
  const params = new URLSearchParams(window.location.search);
  const days = parseInt(params.get('days')) || 30;
  $store.dateRange.setDays(days);
">
```

### Decision 6: Active Tab Highlighting

**Decision**: Add new `active_tab` value `'pull_requests'` for sidebar highlighting

**Rationale**:
- Consistent with existing pattern
- Clear visual indication of current location

**Implementation**:
```python
# In pr_list view
context["active_tab"] = "pull_requests"
```

```html
<!-- In team_nav.html -->
<a href="{% url 'pr_list' %}" {% if active_tab == 'pull_requests' %}class="menu-active"{% endif %}>
```

---

## Code Patterns to Follow

### Sidebar Link Pattern (from team_nav.html)

```html
<li>
  <a href="{% url 'metrics:dashboard_redirect' %}" {% if active_tab == 'metrics' %}class="menu-active"{% endif %}>
    <i class="fa fa-chart-bar h-4 w-4"></i>
    {% translate "Analytics" %}
  </a>
</li>
```

### View Decorator Pattern (from pr_list_views.py)

```python
@login_and_team_required
def pr_list(request: HttpRequest) -> HttpResponse:
    """Main PR list page with filters and pagination."""
    team = request.team
    # ... implementation
```

### Template Partialdef Pattern (from pull_requests.html)

```html
{% partialdef page-content inline %}
<div id="page-content">
  <!-- Content here -->
</div>
{% endpartialdef page-content %}
```

---

## Test Patterns to Follow

### View Test Pattern (from test_pr_list_views.py)

```python
class TestPrListView(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.user = UserFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()
        self.client.force_login(self.user)

    def test_pr_list_requires_login(self):
        self.client.logout()
        url = reverse("pr_list")  # Note: URL name will change
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
```

### E2E Test Pattern (from dashboard.spec.ts)

```typescript
test('navigates to pull requests from sidebar', async ({ page }) => {
  await page.goto('/a/test-team/dashboard/');
  await page.click('text=Pull Requests');
  await expect(page).toHaveURL(/\/pull-requests\//);
  await expect(page.locator('h1')).toContainText('Pull Requests');
});
```

---

## Environment Setup

### Create Worktree

```bash
cd /Users/yanchuk/Documents/GitHub/tformance
git worktree add ../tformance-pr-sidebar -b feature/pr-sidebar-move
```

### Development Commands

```bash
# Run tests in worktree
cd ../tformance-pr-sidebar
make test ARGS='apps.metrics.tests.test_pr_list_views -v'

# Run specific test
pytest apps/metrics/tests/test_pr_list_views.py::TestPrListView::test_pr_list_renders_successfully

# Run E2E tests
make e2e-dashboard
```

---

## Migration Notes

### No Database Migrations Required

This change is purely:
- Template changes
- URL pattern changes
- View logic changes (minimal)

No model changes, no database schema changes.

### Deployment Considerations

1. Deploy URL redirect first (old→new)
2. Then deploy template changes
3. Then update analytics crosslinks
4. Finally remove old URL pattern (optional, can keep redirect)

---

## Related Documentation

- `CLAUDE.md` - Project coding guidelines
- `prd/DASHBOARDS.md` - Dashboard requirements
- `dev/guides/HTMX-ALPINE-PATTERNS.md` - HTMX/Alpine patterns (if exists)
