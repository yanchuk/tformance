# Fix Team Switching - Context

**Last Updated:** 2025-12-21

## Key Files

### Core Files to Modify

| File | Lines | Purpose |
|------|-------|---------|
| `apps/teams/models.py` | 49-51 | `Team.dashboard_url` property |
| `apps/teams/views/membership_views.py` | EOF | Add `switch_team` view |
| `apps/teams/views/__init__.py` | 4 | Export new view |
| `apps/teams/urls.py` | 8-15 | Add URL pattern |

### Supporting Files (Read-Only Context)

| File | Purpose |
|------|---------|
| `apps/teams/middleware.py` | Shows how session["team"] is used |
| `apps/teams/helpers.py` | `get_team_for_request()` logic |
| `apps/teams/context_processors.py` | Builds `other_teams` dict |
| `templates/web/components/team_nav_items.html` | Renders team switch links |

## Key Code Snippets

### Current Broken Code

```python
# apps/teams/models.py:49-51
@property
def dashboard_url(self) -> str:
    return reverse("web_team:home")  # Returns /app/ for ALL teams
```

### Session Handling Pattern (Reference)

```python
# apps/teams/middleware.py:10-16
def _get_team(request, view_kwargs):
    if not hasattr(request, "_cached_team"):
        team = get_team_for_request(request, view_kwargs)
        if team:
            request.session["team"] = team.id  # ← This is how session is set
        request._cached_team = team
    return request._cached_team
```

### Template Using dashboard_url

```html
<!-- templates/web/components/team_nav_items.html:16-20 -->
{% for name, url in other_teams.items %}
<li>
  <a href="{{ url }}"><i class="fa fa-arrow-right"></i>{{ name }}</a>
</li>
{% endfor %}
```

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| View location | `membership_views.py` | Team membership-related logic |
| URL pattern | `/teams/switch/<slug>/` | Under `teams:` namespace, not team_urlpatterns |
| Verification | `user.teams.filter(id=team.id).exists()` | Single query, efficient |
| Error handling | 404 for non-member | Don't leak team existence info |

## Dependencies

- No new packages required
- No model changes (no migrations)
- No JavaScript changes
- No template changes (uses existing `{{ url }}`)

## Test Strategy

Use Django TestCase with:
- `TeamFactory` for creating teams
- `CustomUser` for creating users
- `Membership` for linking users to teams
- `self.client` for HTTP requests

## Verification Commands

```bash
# Run just the new tests
make test ARGS='apps.teams.tests.test_switch_team'

# Run all team tests
make test ARGS='apps.teams.tests'

# Manual verification
# 1. Login as admin@example.com
# 2. Navigate to /app/
# 3. Click team dropdown
# 4. Click "AI Pioneers" (or other team)
# 5. Verify team name in header changes
```
