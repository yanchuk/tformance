# URL Simplification Plan

**Last Updated: 2025-12-12**

## Executive Summary

Simplify the URL structure for single-team users by removing the `/a/<team_slug>/` pattern and replacing it with `/app/` for a cleaner, more intuitive experience. The current URL pattern (`/a/acme-corp/dashboard/`) is unnecessarily complex when users belong to only one team (the typical CTO use case).

**Target State:**
- Single-team users: `/app/dashboard/` (team resolved from session/user)
- Multi-team users (future): `/app/dashboard/?team=slug` or keep current pattern

---

## Current State Analysis

### URL Structure (Current)
```
/                           → Landing page (public)
/accounts/login/           → Auth (public)
/a/<team_slug>/            → Team-scoped app area
  ├── /                    → App home
  ├── /metrics/dashboard/  → Analytics dashboards
  ├── /integrations/       → Integration management
  ├── /team/               → Team settings
  └── /subscription/       → Billing
```

### Key Files Involved
| File | Purpose | Impact |
|------|---------|--------|
| `tformance/urls.py` | Main URL routing | HIGH - change `/a/<team_slug>/` pattern |
| `apps/teams/middleware.py` | Resolves team from URL | HIGH - change team resolution logic |
| `apps/teams/helpers.py` | `get_team_for_request()` | HIGH - change to use session/user |
| `apps/teams/decorators.py` | `@login_and_team_required` | MEDIUM - may need adjustment |
| All `team_urlpatterns` | Team-scoped URLs in each app | LOW - pattern change handled at root |

### Files with `team_slug` References (182 occurrences in 25 files)
- Most are in `urls.py` files and template `{% url %}` tags
- View signatures use `team_slug` parameter
- Test files reference `team_slug`

---

## Proposed Future State

### New URL Structure
```
/                           → Landing page (public)
/accounts/login/           → Auth (public)
/app/                      → App area (team auto-resolved)
  ├── /                    → App home
  ├── /dashboard/          → Analytics dashboards
  ├── /integrations/       → Integration management
  ├── /team/               → Team settings
  └── /subscription/       → Billing
```

### Team Resolution Logic
```python
# New behavior in middleware
def get_team_for_request(request):
    # 1. Check session for team ID
    if 'team' in request.session:
        return Team.objects.get(id=request.session['team'])

    # 2. Get user's default (first/only) team
    if request.user.is_authenticated:
        return request.user.teams.first()

    return None
```

---

## Implementation Phases

### Phase 1: Core URL Refactoring (Effort: L)

**Objective:** Change URL pattern from `/a/<team_slug>/` to `/app/`

| Task | Description | Effort |
|------|-------------|--------|
| 1.1 | Update `tformance/urls.py` to use `/app/` prefix | S |
| 1.2 | Modify `TeamsMiddleware` to resolve team from session | M |
| 1.3 | Update `get_team_for_request()` helper | S |
| 1.4 | Add session-based team selection for multi-team users | M |

### Phase 2: View Signature Updates (Effort: M)

**Objective:** Remove `team_slug` parameter from view functions

| Task | Description | Effort |
|------|-------------|--------|
| 2.1 | Update metrics app views (~15 views) | M |
| 2.2 | Update integrations app views (~12 views) | M |
| 2.3 | Update subscriptions app views (~8 views) | S |
| 2.4 | Update teams app views (~6 views) | S |
| 2.5 | Update web app views (~4 views) | S |
| 2.6 | Update onboarding app views (~6 views) | S |

### Phase 3: URL Pattern Updates (Effort: M)

**Objective:** Update all `path()` definitions to remove `team_slug`

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 | Update `apps/metrics/urls.py` | S |
| 3.2 | Update `apps/integrations/urls.py` | S |
| 3.3 | Update `apps/subscriptions/urls.py` | S |
| 3.4 | Update `apps/teams/urls.py` | S |
| 3.5 | Update `apps/web/urls.py` | S |

### Phase 4: Template Updates (Effort: L)

**Objective:** Update all `{% url %}` template tags

| Task | Description | Effort |
|------|-------------|--------|
| 4.1 | Update metrics templates (~20 files) | M |
| 4.2 | Update integrations templates (~15 files) | M |
| 4.3 | Update onboarding templates (~7 files) | S |
| 4.4 | Update web/components templates (~10 files) | S |
| 4.5 | Update base templates and navigation | S |

### Phase 5: Test Updates (Effort: M)

**Objective:** Update all test files referencing `team_slug`

| Task | Description | Effort |
|------|-------------|--------|
| 5.1 | Update metrics tests | M |
| 5.2 | Update integrations tests | M |
| 5.3 | Update teams tests | S |
| 5.4 | Update subscriptions tests | S |

### Phase 6: Redirects & Backwards Compatibility (Effort: S)

**Objective:** Ensure old URLs redirect properly

| Task | Description | Effort |
|------|-------------|--------|
| 6.1 | Add redirect from `/a/<team_slug>/` to `/app/` | S |
| 6.2 | Update any hardcoded URLs in JavaScript | S |
| 6.3 | Update API endpoint paths if affected | S |

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing bookmarks | Medium | High | Add redirects (Phase 6) |
| OAuth callback URLs break | High | Low | Callbacks use `/integrations/` not `/a/` |
| Session team conflicts | Medium | Medium | Clear team from session on logout |
| Multi-team user confusion | Low | Low | Not supporting multi-team in MVP |
| Template URL tag errors | High | Medium | Comprehensive testing, grep for patterns |

---

## Success Metrics

1. All URLs use `/app/` prefix instead of `/a/<team_slug>/`
2. All 1072 existing tests pass
3. No 404 errors in production for authenticated users
4. Old `/a/` URLs redirect with 301

---

## Dependencies

- **Blocking:** None (self-contained refactor)
- **Affected by:** Any new features adding team-scoped URLs
- **Documentation:** Update CLAUDE.md URL conventions section

---

## Alternative Considered: Keep Both Patterns

We considered supporting both `/a/<slug>/` and `/app/` patterns, but rejected this because:
1. Increased complexity for little benefit
2. MVP targets single-team CTOs
3. Can add multi-team support later if needed

---

## Estimated Total Effort

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Core URL Refactoring | L | None |
| Phase 2: View Signature Updates | M | Phase 1 |
| Phase 3: URL Pattern Updates | M | Phase 1 |
| Phase 4: Template Updates | L | Phase 3 |
| Phase 5: Test Updates | M | Phase 2, 3 |
| Phase 6: Redirects | S | Phase 1-5 |

**Total: ~40-60 changes across 50+ files**
