# URL Simplification Tasks

**Last Updated: 2025-12-12**

## Phase 1: Core URL Refactoring

### 1.1 Update Main URL Configuration
- [ ] Change `tformance/urls.py` line 61: `path("a/<slug:team_slug>/", ...)` → `path("app/", ...)`
- [ ] Remove `team_slug` from the include pattern
- [ ] Verify URL routing works

### 1.2 Modify Team Resolution Middleware
- [ ] Update `apps/teams/middleware.py` to not rely on `team_slug` in view_kwargs
- [ ] Keep `request.team` assignment working via session/user lookup

### 1.3 Update Team Helper Functions
- [ ] Modify `apps/teams/helpers.py:get_team_for_request()`:
  - Remove `team_slug` extraction from view_kwargs
  - Add session-based team lookup
  - Fall back to user's first team
- [ ] Update `get_default_team_from_request()` if needed

### 1.4 Update Team Decorators
- [ ] Verify `@login_and_team_required` works without URL-based team
- [ ] Verify `@team_admin_required` works without URL-based team
- [ ] Add test for decorator behavior

---

## Phase 2: View Signature Updates

### 2.1 Metrics App Views
- [ ] `apps/metrics/views/dashboard_views.py`:
  - [ ] `dashboard_redirect(request, team_slug)` → `dashboard_redirect(request)`
  - [ ] `cto_overview(request, team_slug)` → `cto_overview(request)`
  - [ ] `team_dashboard(request, team_slug)` → `team_dashboard(request)`
- [ ] `apps/metrics/views/chart_views.py`:
  - [ ] `ai_adoption_chart(request, team_slug)` → `ai_adoption_chart(request)`
  - [ ] `ai_quality_chart(request, team_slug)` → `ai_quality_chart(request)`
  - [ ] `cycle_time_chart(request, team_slug)` → `cycle_time_chart(request)`
  - [ ] `key_metrics_cards(request, team_slug)` → `key_metrics_cards(request)`
  - [ ] `team_breakdown_table(request, team_slug)` → `team_breakdown_table(request)`
  - [ ] `leaderboard_table(request, team_slug)` → `leaderboard_table(request)`
- [ ] `apps/metrics/views.py` (if any additional views)

### 2.2 Integrations App Views
- [ ] `apps/integrations/views.py`:
  - [ ] `integrations_home(request, team_slug)`
  - [ ] `github_members(request, team_slug)`
  - [ ] `github_repos(request, team_slug)`
  - [ ] `github_sync(request, team_slug)`
  - [ ] `github_disconnect(request, team_slug)`
  - [ ] `jira_connect(request, team_slug)`
  - [ ] `jira_callback(request, team_slug)`
  - [ ] `jira_settings(request, team_slug)`
  - [ ] `jira_disconnect(request, team_slug)`
  - [ ] `slack_connect(request, team_slug)`
  - [ ] `slack_callback(request, team_slug)`
  - [ ] `slack_settings(request, team_slug)`
  - [ ] `slack_disconnect(request, team_slug)`

### 2.3 Subscriptions App Views
- [ ] `apps/subscriptions/views/views.py`
- [ ] `apps/subscriptions/views/checkout_views.py`
- [ ] `apps/subscriptions/views/portal_views.py`
- [ ] `apps/subscriptions/views/api_views.py`

### 2.4 Teams App Views
- [ ] `apps/teams/views/manage_team_views.py`
- [ ] `apps/teams/views/membership_views.py`
- [ ] `apps/teams/views/api_views.py`

### 2.5 Web App Views
- [ ] `apps/web/views.py`

### 2.6 Onboarding App Views
- [ ] `apps/onboarding/views.py` (all views with team_slug)

---

## Phase 3: URL Pattern Updates

### 3.1 Update apps/metrics/urls.py
- [ ] Remove `team_slug` from all path patterns
- [ ] Update namespace if needed

### 3.2 Update apps/integrations/urls.py
- [ ] Remove `team_slug` from team_urlpatterns

### 3.3 Update apps/subscriptions/urls.py
- [ ] Remove `team_slug` from team_urlpatterns

### 3.4 Update apps/teams/urls.py
- [ ] Remove `team_slug` from team_urlpatterns

### 3.5 Update apps/web/urls.py
- [ ] Remove `team_slug` from team_urlpatterns

---

## Phase 4: Template Updates

### 4.1 Metrics Templates
- [ ] `templates/metrics/cto_overview.html`
- [ ] `templates/metrics/team_dashboard.html`
- [ ] `templates/metrics/partials/*.html`
- [ ] `templates/metrics/charts/*.html`
- [ ] `templates/metrics/tables/*.html`

### 4.2 Integrations Templates
- [ ] `apps/integrations/templates/integrations/home.html`
- [ ] `apps/integrations/templates/integrations/github_*.html`
- [ ] `apps/integrations/templates/integrations/jira_*.html`
- [ ] `apps/integrations/templates/integrations/slack_*.html`

### 4.3 Onboarding Templates
- [ ] `templates/onboarding/*.html` (all files)

### 4.4 Web/Components Templates
- [ ] `templates/web/components/team_nav.html` (CRITICAL - sidebar navigation)
- [ ] `templates/web/app_home.html`
- [ ] `templates/web/components/*.html`

### 4.5 Base Templates
- [ ] `templates/web/app/app_base.html`
- [ ] Any other base templates with navigation

---

## Phase 5: Test Updates

### 5.1 Metrics Tests
- [ ] `apps/metrics/tests/test_dashboard_views.py`
- [ ] `apps/metrics/tests/test_chart_views.py`
- [ ] `apps/metrics/tests/test_dashboard_service.py` (if URL dependent)

### 5.2 Integrations Tests
- [ ] `apps/integrations/tests/test_views.py`
- [ ] `apps/integrations/tests/test_urls.py`

### 5.3 Teams Tests
- [ ] `apps/teams/tests/test_view_mixins.py`
- [ ] `apps/teams/tests/test_slugs.py`

### 5.4 Subscriptions Tests
- [ ] `apps/subscriptions/tests/test_subscription.py`
- [ ] `apps/subscriptions/tests/test_subscription_gating.py`

---

## Phase 6: Redirects & Cleanup

### 6.1 Add Backwards Compatibility Redirects
- [ ] Add redirect from `/a/<slug>/` to `/app/` in `tformance/urls.py`
- [ ] Test redirect works for all old URL patterns

### 6.2 JavaScript Updates
- [ ] Check `assets/javascript/` for hardcoded URLs
- [ ] Update any API endpoint paths if affected

### 6.3 Documentation Updates
- [ ] Update `CLAUDE.md` URL conventions section
- [ ] Update any API documentation

### 6.4 Final Verification
- [ ] Run full test suite: `make test ARGS='--keepdb'`
- [ ] Manual testing of all main flows
- [ ] Verify 1072+ tests still pass

---

## Completion Checklist

- [ ] Phase 1 complete - Core URL refactoring works
- [ ] Phase 2 complete - All views updated
- [ ] Phase 3 complete - All URL patterns updated
- [ ] Phase 4 complete - All templates updated
- [ ] Phase 5 complete - All tests updated and passing
- [ ] Phase 6 complete - Redirects and cleanup done
- [ ] All 1072+ tests passing
- [ ] Manual smoke test of main flows
- [ ] Code reviewed and committed
