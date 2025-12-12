# URL Simplification Context

**Last Updated: 2025-12-12**

## Key Files

### Core Routing
| File | Purpose |
|------|---------|
| `tformance/urls.py:61` | Main pattern: `path("a/<slug:team_slug>/", include(team_urlpatterns))` |
| `apps/teams/middleware.py` | `TeamsMiddleware` - sets `request.team` from URL |
| `apps/teams/helpers.py:28-33` | `get_team_for_request()` - extracts team from `view_kwargs['team_slug']` |
| `apps/teams/decorators.py` | `@login_and_team_required`, `@team_admin_required` |

### URL Pattern Files
```
apps/metrics/urls.py         - team_urlpatterns for dashboards/charts
apps/integrations/urls.py    - team_urlpatterns for OAuth/settings
apps/subscriptions/urls.py   - team_urlpatterns for billing
apps/teams/urls.py           - team_urlpatterns for team management
apps/web/urls.py             - team_urlpatterns for app home
```

### View Files with `team_slug` Parameter
```python
# Pattern to change in ALL views:
def dashboard_redirect(request, team_slug):  # BEFORE
def dashboard_redirect(request):              # AFTER
```

**Files affected:**
- `apps/metrics/views/dashboard_views.py` (4 views)
- `apps/metrics/views/chart_views.py` (6 views)
- `apps/integrations/views.py` (~12 views)
- `apps/subscriptions/views/*.py` (~8 views)
- `apps/teams/views/*.py` (~6 views)
- `apps/web/views.py` (~4 views)
- `apps/onboarding/views.py` (~6 views)

---

## Key Decisions

### Decision 1: Session-Based Team Resolution
**Chosen:** Resolve team from user's session/first team
**Rationale:**
- MVP targets single-team CTOs
- No team switching UI needed
- Simpler implementation

**Code Change:**
```python
# apps/teams/helpers.py
def get_team_for_request(request, view_kwargs):
    # OLD: team_slug = view_kwargs.get("team_slug", None)
    # NEW:
    if not request.user.is_authenticated:
        return None

    # Check session first
    if 'team' in request.session:
        try:
            return request.user.teams.get(id=request.session['team'])
        except Team.DoesNotExist:
            del request.session['team']

    # Default to user's first team
    return request.user.teams.first()
```

### Decision 2: URL Prefix `/app/` vs No Prefix
**Chosen:** Use `/app/` prefix
**Rationale:**
- Clear separation from public pages
- Easier to add middleware/security
- Consistent with SaaS conventions (Notion, Linear use similar)

### Decision 3: Remove `team_slug` from View Signatures
**Chosen:** Remove parameter entirely
**Rationale:**
- Team available via `request.team`
- Less boilerplate in every view
- Already set by middleware

---

## Template URL Tag Changes

### Before
```html
{% url 'metrics:dashboard_redirect' team_slug=request.team.slug %}
{% url 'integrations:home' team_slug=request.team.slug %}
```

### After
```html
{% url 'metrics:dashboard_redirect' %}
{% url 'integrations:home' %}
```

**Grep pattern to find:**
```bash
grep -r "team_slug=request.team.slug" templates/
grep -r "team_slug=" templates/
```

---

## Test File Changes

### Pattern
```python
# Before
def test_dashboard_redirect(self):
    response = self.client.get(f"/a/{self.team.slug}/metrics/dashboard/")

# After
def test_dashboard_redirect(self):
    response = self.client.get("/app/metrics/dashboard/")
```

**Test files affected:**
- `apps/metrics/tests/test_dashboard_views.py`
- `apps/metrics/tests/test_chart_views.py`
- `apps/integrations/tests/test_views.py`
- `apps/teams/tests/*.py`
- `apps/subscriptions/tests/*.py`

---

## Backwards Compatibility

### Redirect Rule
```python
# Add to tformance/urls.py
from django.views.generic import RedirectView

urlpatterns = [
    # Redirect old URLs to new pattern
    path("a/<slug:team_slug>/", RedirectView.as_view(url="/app/", permanent=True)),
    # ... rest of patterns
]
```

**Note:** This catches any old bookmarks/links and redirects them.

---

## Navigation Changes

### `templates/web/components/team_nav.html`
All `{% url %}` tags need updating:
```html
<!-- Before -->
<a href="{% url 'metrics:dashboard_redirect' team_slug=request.team.slug %}">

<!-- After -->
<a href="{% url 'metrics:dashboard_redirect' %}">
```

---

## OAuth Callback URLs (Unaffected)

These use non-team URLs and remain unchanged:
- `/integrations/github/callback/`
- `/integrations/jira/callback/`
- `/integrations/slack/callback/`

Webhooks also unaffected:
- `/webhooks/github/`
- `/webhooks/slack/interactions/`

---

## Files Summary

| Category | Count | Action |
|----------|-------|--------|
| URL routing files | 6 | Update patterns |
| View files | 8 | Remove `team_slug` param |
| Template files | ~50 | Update `{% url %}` tags |
| Test files | ~10 | Update URL paths |
| Middleware/helpers | 3 | Update team resolution |
