# Analytics UI Fixes - Tasks

**Last Updated:** 2025-12-24
**Status:** PHASES 1-3 COMPLETE
**Branch:** github-graphql-api (with analytics fixes)

---

## Phase 1: Fix Double Rendering (Priority: Critical) ✅

- [x] **1.1** Update `list.html` form HTMX attributes
  - Created new template `templates/metrics/analytics/pull_requests.html`
  - Uses `hx-target="#page-content"` with `hx-swap="outerHTML"`
  - Properly extends `base_analytics.html`

- [x] **1.2** Test filter interactions in browser
  - Verified with Playwright MCP - filters work correctly
  - URL push works correctly with filter params

- [x] **1.3** Test pagination interactions
  - Pagination links present and functional
  - URL updates with page parameter

---

## Phase 2: Add Tabs to PR List Page (Priority: High) ✅

- [x] **2.1** Create new PR list template extending analytics base
  - Created `templates/metrics/analytics/pull_requests.html`
  - Extends `base_analytics.html`
  - PR list content in `{% block analytics_content %}`

- [x] **2.2** Update PR list view to use new template
  - Modified `apps/metrics/views/pr_list_views.py`
  - Set `active_page = 'pull_requests'` for tab highlighting
  - Added `days = 30` for date filter consistency

- [x] **2.3** URL routing unchanged
  - Kept existing URL `/app/metrics/pull-requests/`
  - No redirects needed

- [x] **2.4** Verify tab navigation works
  - All 6 tabs visible: Overview, AI Adoption, Delivery, Quality, Team, Pull Requests
  - Pull Requests tab highlighted when active

---

## Phase 3: Fix Tab Contrast (Priority: Medium) ✅

- [x] **3.1** Identified contrast issue
  - Inactive tabs had low contrast on `bg-base-200`

- [x] **3.2** Add CSS override for inactive tabs
  - Added to `assets/styles/app/tailwind/design-system.css`
  - `.tabs-boxed .tab:not(.tab-active)` uses `text-base-content/80`
  - Hover state uses `text-base-content bg-base-100/50`

- [x] **3.3** Rebuilt frontend assets
  - `npm run build` completed successfully

---

## Phase 4: E2E Tests (Priority: High) - PENDING

- [ ] **4.1** Add PR list page E2E tests
  - Test page loads with tabs visible
  - Test filter application
  - Test pagination
  - Test CSV export button exists

- [ ] **4.2** Add tab navigation E2E tests
  - Test clicking each tab navigates correctly
  - Test correct tab is active on each page
  - Test back button navigation

- [ ] **4.3** Add accessibility E2E tests
  - Add axe-core accessibility checks
  - Verify tab contrast passes WCAG AA

---

## Verification Checklist

- [x] No double rendering on PR list page
- [x] Tabs visible on PR list page
- [x] Tab navigation works between all analytics pages
- [x] Inactive tab contrast improved (text-base-content/80)
- [ ] All existing E2E tests pass
- [ ] New E2E tests pass
- [x] Unit tests pass (1176 tests in 21s)

---

## Notes

- Keep old `list.html` as fallback initially, remove after verification
- Run `make e2e` after each phase to catch regressions
- Test in both light and dark themes
