# Analytics Restructure - Tasks

**Last Updated:** 2025-12-23 (Session 2)
**Status:** Phase 1 Complete ✅

---

## Phase 1: Pull Requests Page (Foundation) ✅ COMPLETE
**Effort:** M | **Priority:** P0 | **Dependencies:** None
**Completed:** 2025-12-23

### 1.1 Backend - PR List Service ✅
- [x] Create `apps/metrics/services/pr_list_service.py`
- [x] Implement `get_prs_queryset(team, filters)` with all filter options
- [x] Implement `get_pr_stats(queryset)` for aggregate row
- [x] Implement `get_filter_options(team)` for dropdown values (repos, authors, reviewers)
- [x] Add PR size bucket calculation utility
- [x] Write unit tests for filter combinations (36 tests)

**Acceptance Criteria:** ✅
- Filters: repo, author, reviewer, ai, ai_tool, size, state, has_jira, date range
- Returns efficiently with 10,000+ PRs (uses select_related, annotate)
- All filters combinable

### 1.2 Backend - PR List Views ✅
- [x] Create `apps/metrics/views/pr_list_views.py`
- [x] Implement `pr_list(request)` - main page view
- [x] Implement `pr_list_table(request)` - HTMX partial for table
- [x] Implement `pr_list_export(request)` - CSV export (StreamingHttpResponse)
- [x] Add URL patterns to `apps/metrics/urls.py`
- [x] Write view tests (19 tests)

**Acceptance Criteria:** ✅
- `@login_and_team_required` decorator on all views
- HTMX request returns partial, normal request returns full page
- CSV export includes all visible columns

### 1.3 Frontend - PR List Templates ✅
- [x] Create `templates/metrics/pull_requests/list.html` - main page
- [x] Create `templates/metrics/pull_requests/partials/table.html` - sortable table with pagination
- [x] Style with DaisyUI components

**Notes:**
- Filters panel integrated into list.html (not separate file)
- Stats row integrated into list.html (not separate file)
- Pagination integrated into table.html (not separate file)

**Acceptance Criteria:** ✅
- Responsive layout (table scrollable on mobile)
- Filters update URL and table via HTMX
- PR title links to GitHub (via github_url property)

### 1.4 Refactoring Complete ✅
- [x] Extracted `_get_pr_list_context()` helper to eliminate view duplication
- [x] Simplified filter extraction with dict comprehension
- [x] Created `apps/metrics/templatetags/pr_list_tags.py` for pagination URLs

---

## Phase 2: Overview (Health Check) Page
**Effort:** M | **Priority:** P0 | **Dependencies:** Phase 1
**Status:** Not Started

### 2.1 Backend - Analytics Views Base
- [ ] Create `apps/metrics/views/analytics_views.py`
- [ ] Create `analytics_overview(request)` view
- [ ] Add URL patterns for all analytics pages (can stub others)
- [ ] Create helper `_get_analytics_context()` for shared context

**Acceptance Criteria:**
- `@team_admin_required` decorator
- Returns proper context with `active_page` for nav

### 2.2 Frontend - Base Analytics Template
- [ ] Create `templates/metrics/analytics/base_analytics.html`
- [ ] Add tab navigation component
- [ ] Add date range filter component
- [ ] Style consistent with existing dashboard

**Acceptance Criteria:**
- Tab highlighting works correctly
- Filter applies to HTMX endpoints
- Extends `web/app/app_base.html`

### 2.3 Frontend - Overview Page
- [ ] Create `templates/metrics/analytics/overview.html`
- [ ] Add Key Metrics Cards (reuse existing partial)
- [ ] Add Insights Panel (reuse existing partial)
- [ ] Add PR Velocity Trend (weekly bar chart)
- [ ] Add Active Blockers section (PRs needing attention)
- [ ] Add Quick Links to other analytics pages

**Acceptance Criteria:**
- Max 5-6 widgets on page
- All show week-over-week comparison
- Links to PR list work with pre-applied filters

### 2.4 Testing
- [ ] Verify all HTMX endpoints work
- [ ] Test date range filter
- [ ] Verify navigation to other pages

---

## Phase 3: AI Adoption Page
**Effort:** M | **Priority:** P0 | **Dependencies:** Phase 2
**Status:** Not Started

### 3.1 Backend - AI Comparison Service
- [ ] Add `get_ai_vs_non_ai_comparison(team, start, end)` to dashboard_service
- [ ] Return comparison dict with all key metrics
- [ ] Calculate statistical significance if sample size allows

**Acceptance Criteria:**
- Returns cycle time, review time, PR size, review rounds, quality rating
- Calculates percentage difference

### 3.2 Frontend - AI Adoption Page
- [ ] Create `templates/metrics/analytics/ai_adoption.html`
- [ ] Add AI Adoption Trend (reuse existing chart)
- [ ] Add AI vs Non-AI Comparison Table (NEW widget)
- [ ] Add Copilot Metrics section (reuse existing partials)
- [ ] Add AI Tools Breakdown (reuse existing chart)
- [ ] Add AI Modification Effort (from surveys)
- [ ] Add "View AI-assisted PRs" link to PR list

**Acceptance Criteria:**
- Comparison table is the hero widget
- Clear visual indicators for better/worse metrics
- Link to filtered PR list works

### 3.3 Testing
- [ ] Verify comparison calculations are correct
- [ ] Test with teams that have/don't have Copilot data
- [ ] Test link to PR list preserves AI filter

---

## Phase 4: Delivery & Quality Pages
**Effort:** L | **Priority:** P1 | **Dependencies:** Phase 3
**Status:** Not Started

### 4.1 Backend - Time Allocation Service
- [ ] Add `get_time_allocation(team, start, end)` to dashboard_service
- [ ] Categorize Jira issues: Epic work, Non-Epic work, Bug fixing
- [ ] Return weekly stacked data

**Acceptance Criteria:**
- Uses Jira issue_type field
- Falls back gracefully if no Jira connection

### 4.2 Frontend - Delivery Page
- [ ] Create `templates/metrics/analytics/delivery.html`
- [ ] Add PR Throughput Trend (weekly bar)
- [ ] Add Cycle Time Trend (reuse existing)
- [ ] Add Velocity Trend (Jira story points)
- [ ] Add PR Size Distribution (reuse existing)
- [ ] Add Time Allocation (stacked bar - NEW)
- [ ] Add Deployment Frequency (reuse existing)

**Acceptance Criteria:**
- All charts show weekly data by default
- Time Allocation styled like reference image

### 4.3 Frontend - Quality Page
- [ ] Create `templates/metrics/analytics/quality.html`
- [ ] Add Quality Indicators Cards (reuse existing)
- [ ] Add Review Time Trend (reuse existing)
- [ ] Add Reviewer Workload Table with color coding
- [ ] Add Iteration Metrics (reuse existing)
- [ ] Add CI/CD Pass Rate (reuse existing)
- [ ] Add Reviewer Correlations (admin only, reuse existing)

**Acceptance Criteria:**
- Workload table has green/yellow/red color coding
- Reviewer correlations only visible to admins

### 4.4 Color Coding Implementation
- [ ] Add CSS classes to `design-system.css`
- [ ] Update Reviewer Workload template with conditional coloring
- [ ] Add helper function for percentile calculation

**Acceptance Criteria:**
- `.app-performance-top` (green), `.app-performance-mid` (yellow), `.app-performance-low` (red)
- Applied based on percentile within team

### 4.5 Testing
- [ ] Verify all widgets render correctly
- [ ] Test color coding thresholds
- [ ] Test with varying data sizes

---

## Phase 5: Team Performance Page
**Effort:** M | **Priority:** P1 | **Dependencies:** Phase 4
**Status:** Not Started

### 5.1 Backend - Team Comparison Service
- [ ] Add `get_team_member_comparison(team, start, end)` to dashboard_service
- [ ] Calculate percentiles for each metric
- [ ] Add `get_member_trend(member, start, end)` for individual view

**Acceptance Criteria:**
- Returns all members with metrics and percentile rankings
- Individual trend returns weekly data for selected member

### 5.2 Frontend - Team Performance Page
- [ ] Create `templates/metrics/analytics/team.html`
- [ ] Add Team Breakdown Table with color coding (enhanced version)
- [ ] Add Jira Performance Table (if Jira connected)
- [ ] Add Individual Trend section (member selector dropdown)
- [ ] Add Comparison View (select 2-3 members)

**Acceptance Criteria:**
- Tables have full color coding
- Member selector updates trend chart via HTMX
- Comparison view shows side-by-side metrics

### 5.3 Individual Trend Component
- [ ] Create `templates/metrics/analytics/partials/member_trend.html`
- [ ] Add HTMX endpoint for member-specific data
- [ ] Show PRs merged, cycle time, reviews given over time

**Acceptance Criteria:**
- Dropdown selection triggers HTMX update
- Chart shows 8+ weeks of data

### 5.4 Testing
- [ ] Test with teams of various sizes
- [ ] Verify percentile calculations
- [ ] Test member selector with all team members

---

## Phase 6: Legacy Cleanup & Polish
**Effort:** S | **Priority:** P2 | **Dependencies:** Phase 5
**Status:** Not Started

### 6.1 Navigation Updates
- [ ] Update sidebar to show Analytics submenu
- [ ] Add redirect from old `/metrics/cto-overview/` to new `/analytics/`
- [ ] Update any hardcoded links in templates

**Acceptance Criteria:**
- Old URLs redirect to new structure
- No broken links

### 6.2 Feature Flag Implementation
- [ ] Add `ANALYTICS_V2_ENABLED` to settings
- [ ] Add template conditional for old vs new navigation
- [ ] Test both modes

**Acceptance Criteria:**
- Flag off: old behavior
- Flag on: new analytics pages

### 6.3 Documentation
- [ ] Update `prd/DASHBOARDS.md` with new structure
- [ ] Add user guide for new analytics pages
- [ ] Update README if needed

### 6.4 Final Testing
- [ ] Full regression test
- [ ] Performance test with production-like data
- [ ] Cross-browser testing
- [ ] Mobile responsiveness check

### 6.5 Cleanup (after confirmed working)
- [ ] Remove old `cto_overview.html` template
- [ ] Remove feature flag (make v2 default)
- [ ] Clean up any deprecated endpoints

---

## Backlog / Future Enhancements

### B1: Export & Sharing
- [ ] Add "Share" button that copies filtered URL
- [ ] Add PDF export for analytics pages
- [ ] Add scheduled email reports

### B2: Custom Dashboards
- [ ] Allow users to create custom dashboard layouts
- [ ] Save widget preferences
- [ ] Pin favorite metrics

### B3: Alerts & Notifications
- [ ] Configure thresholds for metrics
- [ ] Slack notifications when thresholds exceeded
- [ ] Email digest of weekly changes

### B4: Drill-Down Enhancements
- [ ] Click on chart data point to filter PR list
- [ ] Hover tooltips with more detail
- [ ] Trend sparklines in tables

---

## Progress Summary

| Phase | Status | Started | Completed |
|-------|--------|---------|-----------|
| Phase 1: PR List | ✅ Complete | 2025-12-23 | 2025-12-23 |
| Phase 2: Overview | Not Started | - | - |
| Phase 3: AI Adoption | Not Started | - | - |
| Phase 4: Delivery/Quality | Not Started | - | - |
| Phase 5: Team Performance | Not Started | - | - |
| Phase 6: Cleanup | Not Started | - | - |

---

## Notes

- Follow TDD workflow: write test first, then implementation
- Reuse existing service functions wherever possible
- Test with demo data: `python manage.py seed_demo_data`
- Check mobile layout at each phase
- Get design review after Phase 2 (base template set)

## Session 2 TDD Summary

| Cycle | Phase | Tests | Status |
|-------|-------|-------|--------|
| 1 | RED | 36 service tests | ✅ |
| 1 | GREEN | Implementation | ✅ |
| 1 | REFACTOR | F() expressions | ✅ |
| 2 | RED | 19 view tests | ✅ |
| 2 | GREEN | Implementation | ✅ |
| 2 | REFACTOR | DRY views | ✅ |
