# Fix Team Switching

**Last Updated:** 2025-12-21

## Executive Summary

Team switching in the UI doesn't work because all teams link to the same URL (`/app/`). When a user clicks to switch teams, they navigate to the same page without changing the active team context. This fix adds a dedicated `switch_team` view that sets the team in the user's session before redirecting to the dashboard.

## Problem Statement

**Current Behavior:**
- User clicks "AI Pioneers" in the team dropdown
- Browser navigates to `/app/`
- Session team remains unchanged (still shows previous team)
- User cannot switch between their teams

**Root Cause:**
The `Team.dashboard_url` property returns `reverse("web_team:home")` which resolves to `/app/` for all teams - the same URL regardless of which team was clicked.

**Expected Behavior:**
- User clicks "AI Pioneers" in the team dropdown
- Session is updated to the new team's ID
- Dashboard loads showing "AI Pioneers" as the active team

## Current State Analysis

### Team Resolution Flow

```
1. User visits /app/
2. TeamsMiddleware.process_view() calls get_team_for_request()
3. get_team_for_request() checks:
   a. team_slug in view_kwargs → None (no slug in URL)
   b. session["team"] → Uses cached team ID from session
   c. user.teams.first() → Falls back to first team
4. Result: Team is set from session, NOT from the clicked link
```

### Files Involved

| File | Role |
|------|------|
| `apps/teams/models.py:50-51` | `dashboard_url` property - returns broken URL |
| `apps/teams/context_processors.py:30-33` | Builds `other_teams` dict with dashboard URLs |
| `templates/web/components/team_nav_items.html:16-20` | Renders team switch links |
| `apps/teams/middleware.py:10-16` | Sets session team from request |
| `apps/teams/helpers.py:28-57` | `get_team_for_request()` resolution logic |

## Proposed Solution

### Add Switch Team View

Create a new view `switch_team(request, team_slug)` that:
1. Verifies user authentication
2. Looks up team by slug
3. Verifies user is a member of the team
4. Sets `request.session["team"] = team.id`
5. Redirects to `/app/` (dashboard)

### Update Dashboard URL

Change `Team.dashboard_url` to return the switch URL:
```python
@property
def dashboard_url(self) -> str:
    return reverse("teams:switch_team", kwargs={"team_slug": self.slug})
```

## Implementation

### Phase 1: Add Switch Team View (TDD)

**Location:** `apps/teams/views/membership_views.py` (existing file for team membership logic)

**View Signature:**
```python
@login_required
def switch_team(request, team_slug):
    """Switch the active team in the user's session."""
    team = get_object_or_404(Team, slug=team_slug)

    # Verify user is a member
    if not request.user.teams.filter(id=team.id).exists():
        raise Http404("Team not found")

    # Update session
    request.session["team"] = team.id

    # Redirect to dashboard
    return redirect("web_team:home")
```

**URL Pattern:**
```python
# In apps/teams/urls.py urlpatterns (not team_urlpatterns)
path("switch/<slug:team_slug>/", views.switch_team, name="switch_team"),
```

### Phase 2: Update Team Model

**File:** `apps/teams/models.py`

```python
@property
def dashboard_url(self) -> str:
    return reverse("teams:switch_team", kwargs={"team_slug": self.slug})
```

### Phase 3: Add Tests

**File:** `apps/teams/tests/test_switch_team.py`

Test cases:
1. `test_switch_team_success` - User can switch to a team they belong to
2. `test_switch_team_updates_session` - Session is updated with new team ID
3. `test_switch_team_redirects_to_dashboard` - Redirects to /app/
4. `test_switch_team_not_member` - 404 if user is not a member
5. `test_switch_team_unauthenticated` - Redirects to login
6. `test_switch_team_nonexistent_team` - 404 for bad slug
7. `test_dashboard_url_returns_switch_url` - Verify property returns correct URL

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing team links | Low | Medium | Keep `web_team:home` URL working, just add new switch URL |
| Session conflicts | Low | Low | Session key "team" already used consistently |
| Performance impact | Very Low | Low | Single DB query to verify membership |

## Success Metrics

1. **Functional**: User can switch teams via dropdown menu
2. **Session**: Session team ID updates after switch
3. **UI**: Dashboard shows correct team after switch
4. **Tests**: All new tests pass, existing tests unchanged

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `apps/teams/views/membership_views.py` | Modify | Add `switch_team` view |
| `apps/teams/views/__init__.py` | Modify | Export `switch_team` |
| `apps/teams/urls.py` | Modify | Add URL pattern |
| `apps/teams/models.py` | Modify | Update `dashboard_url` property |
| `apps/teams/tests/test_switch_team.py` | Create | New test file |

## Estimated Effort

| Task | Effort |
|------|--------|
| Write failing tests | S |
| Implement switch_team view | S |
| Add URL pattern | S |
| Update dashboard_url property | S |
| Verify E2E behavior | S |
| **Total** | **M** |
