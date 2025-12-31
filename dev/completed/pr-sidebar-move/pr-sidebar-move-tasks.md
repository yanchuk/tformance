# Pull Request Sidebar Move - Task Checklist

**Last Updated: 2025-12-30**

## Pre-Implementation Setup

- [ ] **Create git worktree** (S)
  ```bash
  git worktree add ../tformance-pr-sidebar -b feature/pr-sidebar-move
  cd ../tformance-pr-sidebar
  ```

- [ ] **Verify dev environment works in worktree** (S)
  ```bash
  make test ARGS='-k "test_pr_list" --maxfail=3'
  ```

---

## Phase 1: TDD Red - Write Failing Tests

### 1.1 Unit Tests for URL Changes
- [ ] **Test new PR list URL accessible** (S)
  - File: `apps/metrics/tests/test_pr_sidebar_move.py`
  - Test: `test_pr_list_accessible_at_new_url`
  - Expected: GET `/a/<team>/pull-requests/` returns 200

- [ ] **Test old URL redirects to new URL** (S)
  - Test: `test_old_pr_list_url_redirects`
  - Expected: GET `/a/<team>/metrics/pull-requests/` returns 301 → new URL

- [ ] **Test redirect preserves query params** (S)
  - Test: `test_redirect_preserves_query_params`
  - Expected: `?ai=yes&days=30` preserved through redirect

### 1.2 Unit Tests for Navigation
- [ ] **Test sidebar contains PR link** (M)
  - Test: `test_sidebar_contains_pr_link`
  - Expected: `team_nav.html` renders link to PR list

- [ ] **Test PR link appears after Analytics** (S)
  - Test: `test_pr_link_position_after_analytics`
  - Expected: PR link is second item in sidebar

- [ ] **Test active_tab highlighting** (S)
  - Test: `test_pr_page_highlights_sidebar`
  - Expected: PR link has `menu-active` class when on PR page

### 1.3 Unit Tests for Analytics Hub
- [ ] **Test Analytics has 6 tabs (no PR)** (S)
  - Test: `test_analytics_has_six_tabs`
  - Expected: Overview, AI Adoption, Delivery, Quality, Team, Trends

- [ ] **Test Analytics tabs don't include PR** (S)
  - Test: `test_analytics_tabs_exclude_pr`
  - Expected: No "Pull Requests" in tab list

### 1.4 Unit Tests for Crosslinks
- [ ] **Test overview crosslinks work** (M)
  - Test: `test_overview_pr_crosslinks`
  - Expected: Links point to new PR URL

- [ ] **Test ai_adoption crosslinks work** (M)
  - Test: `test_ai_adoption_pr_crosslinks`
  - Expected: 3 links with correct filters

- [ ] **Test delivery crosslinks work** (M)
  - Test: `test_delivery_pr_crosslinks`
  - Expected: 3 links with correct filters

- [ ] **Test quality crosslinks work** (S)
  - Test: `test_quality_pr_crosslinks`

- [ ] **Test team crosslinks work** (S)
  - Test: `test_team_pr_crosslinks`

- [ ] **Test author filter crosslink works** (M)
  - Test: `test_team_breakdown_author_crosslink`
  - Expected: `?author=<id>` filter works

- [ ] **Test size chart crosslink works** (S)
  - Test: `test_pr_size_chart_crosslink`
  - Expected: `?size=<category>` filter works

### 1.5 Unit Tests for Standalone Page
- [ ] **Test PR page has date picker** (M)
  - Test: `test_standalone_pr_page_has_date_picker`
  - Expected: Date range picker renders on PR page

- [ ] **Test PR page doesn't extend analytics base** (S)
  - Test: `test_pr_page_standalone_template`
  - Expected: Uses `app_base.html`, not `base_analytics.html`

**Verify Red Phase:**
```bash
pytest apps/metrics/tests/test_pr_sidebar_move.py -v
# All tests should FAIL
```

---

## Phase 2: TDD Green - URL & Navigation Implementation

### 2.1 URL Pattern Changes
- [ ] **Add new URL pattern for PR list** (S)
  - File: `apps/metrics/urls.py` (or create new `apps/pullrequests/urls.py`)
  - Pattern: `path("pull-requests/", ...)`
  - Deps: None

- [ ] **Add new URL pattern for PR table partial** (S)
  - Pattern: `path("pull-requests/table/", ...)`

- [ ] **Add new URL pattern for PR export** (S)
  - Pattern: `path("pull-requests/export/", ...)`

- [ ] **Add redirect from old URL** (S)
  - File: `apps/metrics/urls.py`
  - Use `RedirectView` with `permanent=True`

### 2.2 Sidebar Navigation
- [ ] **Add PR entry to team_nav.html** (S)
  - File: `templates/web/components/team_nav.html`
  - Position: After Analytics (line 9), before Integrations
  - Icon: `fa-code-pull-request` or `fa-git-pull-request`

- [ ] **Add active_tab check for PR** (S)
  - Add `{% if active_tab == 'pull_requests' %}class="menu-active"{% endif %}`

### 2.3 View Updates
- [ ] **Update pr_list view active_tab** (S)
  - File: `apps/metrics/views/pr_list_views.py`
  - Add: `context["active_tab"] = "pull_requests"`

**Verify Green Phase (partial):**
```bash
pytest apps/metrics/tests/test_pr_sidebar_move.py::TestUrlChanges -v
pytest apps/metrics/tests/test_pr_sidebar_move.py::TestNavigation -v
```

---

## Phase 3: TDD Green - Template Implementation

### 3.1 Create Standalone Template
- [ ] **Create list_standalone.html** (L)
  - File: `templates/metrics/pull_requests/list_standalone.html`
  - Extends: `web/app/app_base.html`
  - Include: Date range picker
  - Include: All filter functionality from `pull_requests.html`
  - Deps: Phase 2 complete

- [ ] **Add date range picker to standalone template** (M)
  - Include `date_range_picker.html` partial
  - Initialize Alpine store from URL params

- [ ] **Add page JS for Alpine store init** (M)
  - Initialize `$store.dateRange` from URL params
  - Handle date range changes

### 3.2 Update View to Use New Template
- [ ] **Update pr_list view template path** (S)
  - File: `apps/metrics/views/pr_list_views.py`
  - Change: `"metrics/analytics/pull_requests.html"` → `"metrics/pull_requests/list_standalone.html"`

### 3.3 Remove PR Tab from Analytics
- [ ] **Remove PR tab from base_analytics.html** (S)
  - File: `templates/metrics/analytics/base_analytics.html`
  - Remove: Lines 82-86 (PR tab link)
  - Update: Date picker visibility logic (remove PR check)

**Verify Green Phase (more tests):**
```bash
pytest apps/metrics/tests/test_pr_sidebar_move.py::TestAnalyticsHub -v
pytest apps/metrics/tests/test_pr_sidebar_move.py::TestStandalonePage -v
```

---

## Phase 4: TDD Green - Crosslink Updates

### 4.1 Update Analytics Page Crosslinks
- [ ] **Update overview.html crosslinks** (S)
  - File: `templates/metrics/analytics/overview.html`
  - Lines: 108, 114
  - Change: URL to new pattern

- [ ] **Update ai_adoption.html crosslinks** (S)
  - File: `templates/metrics/analytics/ai_adoption.html`
  - Lines: 122, 128, 134

- [ ] **Update delivery.html crosslinks** (S)
  - File: `templates/metrics/analytics/delivery.html`
  - Lines: 111, 117, 123

- [ ] **Update quality.html crosslinks** (S)
  - File: `templates/metrics/analytics/quality.html`
  - Line: 141

- [ ] **Update team.html crosslinks** (S)
  - File: `templates/metrics/analytics/team.html`
  - Line: 116

### 4.2 Update Partial Crosslinks
- [ ] **Update team_breakdown_table.html crosslink** (S)
  - File: `templates/metrics/partials/team_breakdown_table.html`
  - Line: 53

- [ ] **Update pr_size_chart.html crosslink** (S)
  - File: `templates/metrics/partials/pr_size_chart.html`
  - Line: 6

**Verify Green Phase (crosslinks):**
```bash
pytest apps/metrics/tests/test_pr_sidebar_move.py::TestCrosslinks -v
```

---

## Phase 5: TDD Refactor - Polish & Cleanup

### 5.1 Code Cleanup
- [ ] **Remove old pull_requests.html template** (S)
  - File: `templates/metrics/analytics/pull_requests.html`
  - Note: Keep until fully verified

- [ ] **Update URL name references if changed** (M)
  - Search codebase for `metrics:pr_list`
  - Update to new URL name if different

- [ ] **Remove date picker hide logic from base_analytics.html** (S)
  - Lines 91-96 no longer needed

### 5.2 E2E Test Updates
- [ ] **Update dashboard.spec.ts** (M)
  - Add: Test for sidebar navigation to PR
  - Update: Any existing PR navigation tests

- [ ] **Update smoke.spec.ts** (S)
  - Add: PR page to smoke tests if not present

- [ ] **Create pr-list.spec.ts** (M)
  - New E2E tests for standalone PR page
  - Test: Filters, pagination, sorting
  - Test: Date range picker

### 5.3 Documentation
- [ ] **Update relevant PRD docs** (S)
  - Check `prd/DASHBOARDS.md` for navigation references

- [ ] **Clean up task files** (S)
  - Move to `dev/completed/pr-sidebar-move/`

**Final Verification:**
```bash
# All unit tests
make test

# All E2E tests
make e2e

# Manual verification
make dev
# Navigate to /a/<team>/pull-requests/
# Check all crosslinks
# Test all filters
```

---

## Effort Legend

| Size | Description |
|------|-------------|
| S | Small - < 30 min, single file change |
| M | Medium - 30-60 min, multiple files or logic |
| L | Large - 1-2 hours, significant new code |
| XL | Extra Large - 2+ hours, complex implementation |

---

## Progress Summary

| Phase | Total Tasks | Completed | Status |
|-------|-------------|-----------|--------|
| Setup | 2 | 0 | Not Started |
| Phase 1 (Red) | 14 | 0 | Not Started |
| Phase 2 (Green - URL) | 7 | 0 | Not Started |
| Phase 3 (Green - Template) | 6 | 0 | Not Started |
| Phase 4 (Green - Crosslinks) | 7 | 0 | Not Started |
| Phase 5 (Refactor) | 7 | 0 | Not Started |
| **Total** | **43** | **0** | **Not Started** |

---

## Quick Reference Commands

```bash
# Create worktree
git worktree add ../tformance-pr-sidebar -b feature/pr-sidebar-move

# Run specific test file
pytest apps/metrics/tests/test_pr_sidebar_move.py -v

# Run with coverage
pytest apps/metrics/tests/test_pr_sidebar_move.py --cov=apps/metrics/views/pr_list_views

# Run E2E for PR page
npx playwright test tests/e2e/pr-list.spec.ts

# Check for broken links (after changes)
grep -r "metrics:pr_list" templates/

# Verify redirect works
curl -I "http://localhost:8000/a/test-team/metrics/pull-requests/"
```
