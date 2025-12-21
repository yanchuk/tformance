# Fix Team Switching - Context

**Last Updated:** 2025-12-21
**Status:** COMPLETE ✅

## Problem

Users couldn't switch between teams in the dropdown. Clicking a different team didn't change the active team.

## Root Cause

`Team.dashboard_url` property returned `reverse("web_team:home")` which resolves to `/app/` for ALL teams. The team switcher dropdown used this property to build team links, so all teams pointed to the same URL.

## Solution

Created a dedicated `switch_team` view that:
1. Takes `team_slug` as a URL parameter
2. Verifies the user is a member of that team
3. Updates `request.session["team"]` with the new team ID
4. Redirects to the dashboard

## Key Files Modified

| File | Lines | Change |
|------|-------|--------|
| `apps/teams/views/membership_views.py` | 91-103 | New `switch_team` view |
| `apps/teams/urls.py` | 12 | URL pattern `switch/<slug:team_slug>/` |
| `apps/teams/models.py` | 50-51 | Updated `dashboard_url` property |
| `apps/teams/tests/test_switch_team.py` | 1-85 | 6 new tests |
| `templates/web/app_home.html` | 68,84,100 | Badge `whitespace-nowrap` fix |

## Implementation Details

### View Code

```python
@login_required
def switch_team(request, team_slug):
    """Switch the active team in the user's session."""
    team = get_object_or_404(Team, slug=team_slug)
    if not request.user.teams.filter(id=team.id).exists():
        raise Http404("Team not found")
    request.session["team"] = team.id
    return redirect("web_team:home")
```

### URL Pattern

```python
path("switch/<slug:team_slug>/", views.switch_team, name="switch_team"),
```

### Model Property

```python
@property
def dashboard_url(self) -> str:
    return reverse("teams:switch_team", kwargs={"team_slug": self.slug})
```

## Test Coverage

All 6 tests pass:
- `test_switch_team_success` - User can switch to team they belong to
- `test_switch_team_updates_session` - Session is updated with new team ID
- `test_switch_team_not_member` - Returns 404 for non-members
- `test_switch_team_unauthenticated` - Redirects to login
- `test_switch_team_nonexistent_team` - Returns 404 for invalid slug
- `test_dashboard_url_returns_switch_url` - Verifies property returns correct URL

## Related Fixes

### Badge Truncation (9cf184e)
Fixed "Connected" text being truncated to "Connec" in app_home.html by adding `whitespace-nowrap` class to all integration status badges.

### Onboarding Background (029c3b6)
Fixed dark background in onboarding wizard for light theme by changing `.app-bg` from hardcoded `bg-deep` to theme-aware `bg-base-100`.

### Warning Text Contrast (029c3b6)
Added `text-warning` contrast override for light theme WCAG AA compliance.

## Commits

1. `9cf184e` - Fix team switching and badge truncation
2. `029c3b6` - Fix onboarding background and text-warning contrast for light theme
