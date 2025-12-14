# Dashboard UX Improvements - Tasks

**Last Updated:** 2025-12-14

## Phase 0: Critical Bug Fixes (NEW - Priority: Critical)

### 0.1 HTMX Days Filter Bug - Full Page Nested Inside Content ✅ FIXED

**Bug**: Clicking 7d/30d/90d filter buttons on Team Dashboard causes the entire page (header, sidebar, content) to be nested inside the content area, resulting in duplicate navigation.

**Root Cause**: The `team_dashboard` view always returns full template, even for HTMX requests.

**Fix Location**: `apps/metrics/views/dashboard_views.py:55-58`

- [x] Update `team_dashboard` view to check `request.htmx`
  ```python
  @login_and_team_required
  def team_dashboard(request: HttpRequest) -> HttpResponse:
      context = _get_date_range_context(request)
      template = "metrics/team_dashboard.html#page-content" if request.htmx else "metrics/team_dashboard.html"
      return TemplateResponse(request, template, context)
  ```
- [x] Apply same fix to `cto_overview` view
- [x] Add E2E test for days filter to prevent regression (tests/e2e/dashboard.spec.ts)

### 0.2 Quick Stats Data Structure Mismatch

**Bug**: App home page shows "-" for all quick stats (Cycle Time, AI-Assisted, Quality).

**Root Cause**: Service returns flat keys but template expects nested structure.

**Service returns**:
```python
{"prs_merged": 7, "prs_merged_change": -22.0, "avg_cycle_time_hours": 26.0, ...}
```

**Template expects**:
```django
{{ quick_stats.prs_merged.count }}
{{ quick_stats.prs_merged.change_percent }}
```

**Fix Options**:
- [ ] Option A: Update service to return nested dicts (breaks other consumers)
- [ ] Option B: Update template to use flat keys (simpler, recommended)

**Recommended fix** - update `templates/web/components/quick_stats.html`:
```django
{{ quick_stats.prs_merged }}
{{ quick_stats.prs_merged_change|floatformat:0 }}%
{{ quick_stats.avg_cycle_time_hours|floatformat:1 }}
```

### 0.3 Slack Icon Color (Low Priority)

**Issue**: Slack icon uses brand red (#E01E5A) which may be confused with error state.

**Location**: `templates/web/app_home.html:92`
```html
<svg class="h-5 w-5" viewBox="0 0 24 24" fill="#E01E5A">
```

**Options**:
- [ ] Keep as-is (official brand color)
- [ ] Use multi-color logo like on landing page
- [ ] Use teal to match app theme

---

## Phase 1: App Home Page Redesign

### 1.1 Backend Services

- [ ] Create `apps/integrations/services/status.py`
  - [ ] Implement `get_team_integration_status(team)` function
  - [ ] Return GitHub, Jira, Slack connection status
  - [ ] Include org/site names and counts
  - [ ] Add `has_data` flag based on PR count
  - [ ] Write tests for status service

- [ ] Create `apps/metrics/services/quick_stats.py`
  - [ ] Implement `get_team_quick_stats(team, days=7)` function
  - [ ] Calculate PRs merged count and change %
  - [ ] Calculate average cycle time and change %
  - [ ] Calculate AI-assisted % and change
  - [ ] Calculate average quality rating and change
  - [ ] Get recent activity list (last 5 items)
  - [ ] Write tests for quick stats service

### 1.2 View Updates

- [ ] Update `apps/web/views.py::team_home()`
  - [ ] Import new services
  - [ ] Call `get_team_integration_status()`
  - [ ] Conditionally call `get_team_quick_stats()` if has_data
  - [ ] Pass context to template
  - [ ] Write/update view tests

### 1.3 Template: New User State

- [ ] Create `templates/web/components/setup_wizard.html`
  - [ ] Step 1: Connect GitHub (required badge)
  - [ ] Step 2: Connect Jira (optional badge)
  - [ ] Step 3: Connect Slack (optional badge)
  - [ ] Progress indicator
  - [ ] Link buttons to integration pages
  - [ ] Style with DaisyUI steps component

### 1.4 Template: Data User State

- [ ] Create `templates/web/components/quick_stats.html`
  - [ ] 4 stat cards in grid
  - [ ] PRs merged with change indicator
  - [ ] Cycle time with change indicator
  - [ ] AI-assisted % with change indicator
  - [ ] Quality rating with change indicator
  - [ ] Use DaisyUI stat component

- [ ] Create `templates/web/components/recent_activity.html`
  - [ ] List of recent events
  - [ ] PR merged events
  - [ ] Survey response events
  - [ ] Limit to 5 items

- [ ] Create `templates/web/components/setup_prompt.html`
  - [ ] Warning/info banner for missing integrations
  - [ ] Link to connect missing service
  - [ ] Dismissible (optional)

### 1.5 Template: App Home Rewrite

- [ ] Rewrite `templates/web/app_home.html`
  - [ ] Conditional rendering based on integration status
  - [ ] Include setup_wizard for new users
  - [ ] Include quick_stats for data users
  - [ ] Include recent_activity for data users
  - [ ] Include setup_prompt for partial setup
  - [ ] Quick action buttons (View Analytics, Leaderboard)
  - [ ] Responsive design

---

## Phase 2: Dashboard Layout Fix

### 2.1 Layout Changes

- [ ] Update `templates/metrics/team_dashboard.html`
  - [ ] Change grid from `lg:grid-cols-2` to single column
  - [ ] Stack all widgets vertically
  - [ ] Add key metrics cards at top (like CTO overview)
  - [ ] Ensure proper spacing (gap-6)

### 2.2 Add Key Metrics Cards

- [ ] Add stats cards container to team_dashboard
  - [ ] Use HTMX to load `metrics:cards_metrics`
  - [ ] Same pattern as CTO overview
  - [ ] Show loading skeleton

---

## Phase 3: Additional Charts

### 3.1 PR Throughput Chart

- [ ] Create view `apps/metrics/views/chart_views.py::pr_throughput_chart()`
  - [ ] Query PRs grouped by date
  - [ ] Calculate daily/weekly counts
  - [ ] Return chart data JSON
  - [ ] Write tests

- [ ] Add URL pattern `charts/pr-throughput/`

- [ ] Create `templates/metrics/partials/pr_throughput.html`
  - [ ] Canvas element with ID
  - [ ] Chart.js bar chart config
  - [ ] Responsive sizing

### 3.2 Review Distribution Chart

- [ ] Create view `apps/metrics/views/chart_views.py::review_distribution_chart()`
  - [ ] Query reviews grouped by reviewer
  - [ ] Calculate counts per person
  - [ ] Return chart data JSON
  - [ ] Write tests

- [ ] Add URL pattern `charts/review-distribution/`

- [ ] Create `templates/metrics/partials/review_distribution.html`
  - [ ] Canvas element with ID
  - [ ] Chart.js pie/doughnut chart config
  - [ ] Legend with names

### 3.3 Recent PRs Table

- [ ] Create view `apps/metrics/views/chart_views.py::recent_prs_table()`
  - [ ] Query last 10 merged PRs
  - [ ] Include author, cycle time, quality, AI status
  - [ ] Support pagination via HTMX
  - [ ] Write tests

- [ ] Add URL pattern `tables/recent-prs/`

- [ ] Create `templates/metrics/partials/recent_prs.html`
  - [ ] DaisyUI table component
  - [ ] PR title linked to GitHub
  - [ ] Author with avatar
  - [ ] Cycle time in hours
  - [ ] Quality badge
  - [ ] AI status badge

### 3.4 Update Team Dashboard Template

- [ ] Add PR Throughput section to team_dashboard.html
- [ ] Add Review Distribution section
- [ ] Add Recent PRs section
- [ ] Order: Stats → Throughput → Cycle Time → Distribution → Leaderboard → Recent PRs

---

## Phase 4: Polish & Testing

### 4.1 Empty States

- [ ] Design empty state for charts with no data
  - [ ] Helpful message explaining why empty
  - [ ] Link to relevant action (e.g., connect GitHub)
  - [ ] Consistent visual style

- [ ] Implement empty states in:
  - [ ] PR Throughput chart
  - [ ] Cycle Time chart
  - [ ] Review Distribution chart
  - [ ] Recent PRs table
  - [ ] AI Detective Leaderboard

### 4.2 Loading States

- [ ] Verify all HTMX containers have loading indicators
- [ ] Use consistent spinner style (DaisyUI loading)
- [ ] Skeleton loaders for tables

### 4.3 Responsive Design

- [ ] Test home page on mobile
- [ ] Test dashboard on mobile
- [ ] Test tablet breakpoints
- [ ] Adjust grid/flex as needed

### 4.4 E2E Tests

- [ ] Add E2E test for new user home page
  - [ ] Verify setup wizard displays
  - [ ] Verify links work

- [ ] Add E2E test for data user home page
  - [ ] Verify stats display
  - [ ] Verify recent activity

- [ ] Add E2E test for team dashboard
  - [ ] Verify all charts load
  - [ ] Verify filter changes update charts

### 4.5 Unit Tests

- [ ] Integration status service tests
- [ ] Quick stats service tests
- [ ] Chart view tests
- [ ] Table view tests

---

## Verification Checklist

After implementation, verify:

- [ ] New user sees setup wizard on `/app/`
- [ ] User with data sees stats on `/app/`
- [ ] Setup prompt shows for missing integrations
- [ ] Team dashboard has stacked layout
- [ ] Team dashboard shows key metrics cards
- [ ] All charts load without errors
- [ ] Filters update all charts
- [ ] Mobile layout is usable
- [ ] All tests pass
- [ ] No console errors

---

## Notes

- Use test accounts: `user@example.com` / `user123` for member view
- Reference `templates/metrics/cto_overview.html` for chart patterns
- Follow HTMX lazy loading pattern from existing charts
- Use DaisyUI components consistently
