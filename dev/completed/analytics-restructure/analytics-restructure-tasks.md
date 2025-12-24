# Analytics Restructure - Tasks

**Last Updated:** 2025-12-23 (Session 4)
**Status:** Phase 4 Complete ✅

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

## Phase 2: Overview (Health Check) Page ✅ COMPLETE
**Effort:** M | **Priority:** P0 | **Dependencies:** Phase 1
**Completed:** 2025-12-23

### 2.1 Backend - Analytics Views Base ✅
- [x] Create `apps/metrics/views/analytics_views.py`
- [x] Create `analytics_overview(request)` view
- [x] Add URL patterns for all analytics pages (can stub others)
- [x] Create helper `_get_analytics_context()` for shared context

**Acceptance Criteria:** ✅
- `@team_admin_required` decorator
- Returns proper context with `active_page` for nav

### 2.2 Frontend - Base Analytics Template ✅
- [x] Create `templates/metrics/analytics/base_analytics.html`
- [x] Add tab navigation component
- [x] Add date range filter component
- [x] Style consistent with existing dashboard

**Acceptance Criteria:** ✅
- Tab highlighting works correctly
- Filter applies to HTMX endpoints
- Extends `web/app/app_base.html`

### 2.3 Frontend - Overview Page ✅
- [x] Create `templates/metrics/analytics/overview.html`
- [x] Add Key Metrics Cards (reuse existing partial)
- [x] Add Insights Panel (reuse existing partial)
- [x] Add AI Adoption Trend chart (reuse existing chart)
- [x] Add Cycle Time Trend chart
- [x] Add Quality by AI Status chart
- [x] Add PR Size Distribution chart
- [x] Add Quick Links to other analytics pages

**Acceptance Criteria:** ✅
- Max 5-6 widgets on page
- Links to PR list work with pre-applied filters

### 2.4 Testing ✅
- [x] 14 tests in `test_analytics_views.py`
- [x] Verify all HTMX endpoints work
- [x] Test date range filter
- [x] Verify navigation to other pages

---

## Phase 3: AI Adoption Page ✅ COMPLETE
**Effort:** M | **Priority:** P0 | **Dependencies:** Phase 2
**Completed:** 2025-12-23

### 3.1 Backend - AI Adoption View ✅
- [x] Add `analytics_ai_adoption()` view to `analytics_views.py`
- [x] Reuse existing `get_ai_quality_comparison()` service function
- [x] Add URL pattern `/analytics/ai-adoption/`
- [x] Export view in `views/__init__.py`

**Acceptance Criteria:** ✅
- `@team_admin_required` decorator
- Returns comparison data in context
- HTMX partial support

### 3.2 Frontend - AI Adoption Page ✅
- [x] Create `templates/metrics/analytics/ai_adoption.html`
- [x] Add AI Adoption Trend (reuse existing chart)
- [x] Add AI vs Non-AI Quality Comparison (reuse existing chart partial)
- [x] Add Copilot Metrics section (reuse existing partial)
- [x] Add AI Tools Breakdown (reuse existing chart)
- [x] Add AI Bot Reviews card (reuse existing partial)
- [x] Add "View AI-assisted PRs" link to PR list
- [x] Update tabs in `base_analytics.html`

**Acceptance Criteria:** ✅
- Comparison chart is a hero widget
- All existing partials reused - no duplication
- Link to filtered PR list works with `?ai=yes`

### 3.3 Testing ✅
- [x] 11 tests for AI Adoption view
- [x] Test requires login
- [x] Test requires admin
- [x] Test active_page context
- [x] Test days parameter
- [x] Test HTMX partial
- [x] Test comparison data in context
- [x] Test link to filtered PR list

---

## Phase 4: Delivery & Quality Pages ✅ COMPLETE
**Effort:** L | **Priority:** P1 | **Dependencies:** Phase 3
**Completed:** 2025-12-23

### 4.1 Backend - Delivery & Quality Views ✅
- [x] Add `analytics_delivery()` view to `analytics_views.py`
- [x] Add `analytics_quality()` view to `analytics_views.py`
- [x] Add URL patterns `/analytics/delivery/`, `/analytics/quality/`
- [x] Export views in `views/__init__.py`

**Acceptance Criteria:** ✅
- `@team_admin_required` decorator on both views
- HTMX partial support for tab switching

### 4.2 Frontend - Delivery Page ✅
- [x] Create `templates/metrics/analytics/delivery.html`
- [x] Add Key Metrics Cards (reuse existing)
- [x] Add Cycle Time Trend (reuse existing)
- [x] Add PR Size Distribution (reuse existing)
- [x] Add Deployment Metrics (reuse existing)
- [x] Add File Categories (reuse existing)
- [x] Add Quick Links (All PRs, Merged PRs, Large PRs)

**Acceptance Criteria:** ✅
- All existing partials reused - no duplication
- Quick links with pre-applied filters

### 4.3 Frontend - Quality Page ✅
- [x] Create `templates/metrics/analytics/quality.html`
- [x] Add Review Time Trend (reuse existing)
- [x] Add Review Distribution (reuse existing)
- [x] Add Reviewer Workload Table (reuse existing)
- [x] Add CI/CD Pass Rate (reuse existing)
- [x] Add Iteration Metrics (reuse existing)
- [x] Add Revert Rate (reuse existing)
- [x] Add Quick Links (All PRs, Team Breakdown, Full Dashboard)

**Acceptance Criteria:** ✅
- All existing partials reused - no duplication
- Quick links to related pages

### 4.4 Tab Navigation Update ✅
- [x] Added "Delivery" and "Quality" tabs to `base_analytics.html`
- [x] Tab order: Overview → AI Adoption → Delivery → Quality → Pull Requests

### 4.5 Testing ✅
- [x] 9 tests for Delivery view
- [x] 9 tests for Quality view
- [x] All 1160 metrics tests passing

**Note:** Color coding for performance indicators deferred to Phase 5 (Team Performance)

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
| Phase 2: Overview | ✅ Complete | 2025-12-23 | 2025-12-23 |
| Phase 3: AI Adoption | ✅ Complete | 2025-12-23 | 2025-12-23 |
| Phase 4: Delivery/Quality | ✅ Complete | 2025-12-23 | 2025-12-23 |
| Phase 5: Team Performance | Not Started | - | - |
| Phase 6: Cleanup | Not Started | - | - |

---

## Notes

- Follow TDD workflow: write test first, then implementation
- Reuse existing service functions wherever possible
- Test with demo data: `python manage.py seed_demo_data`
- Check mobile layout at each phase
- Get design review after Phase 2 (base template set)

## Session 2 TDD Summary (Phase 1)

| Cycle | Phase | Tests | Status |
|-------|-------|-------|--------|
| 1 | RED | 36 service tests | ✅ |
| 1 | GREEN | Implementation | ✅ |
| 1 | REFACTOR | F() expressions | ✅ |
| 2 | RED | 19 view tests | ✅ |
| 2 | GREEN | Implementation | ✅ |
| 2 | REFACTOR | DRY views | ✅ |

## Session 4 TDD Summary (Phase 3 & 4)

| Cycle | Phase | Tests | Status |
|-------|-------|-------|--------|
| 1 | RED | 11 AI Adoption view tests | ✅ |
| 1 | GREEN | View, URL, template | ✅ |
| 1 | REFACTOR | Reused existing partials | ✅ |
| 2 | RED | 18 Delivery + Quality tests | ✅ |
| 2 | GREEN | Views, URLs, templates | ✅ |
| 2 | REFACTOR | Reused all existing partials | ✅ |
