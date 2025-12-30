# Pull Request Sidebar Migration Plan

**Last Updated: 2025-12-30**

## Executive Summary

Move the Pull Requests tab from being a sub-tab under Analytics to a top-level sidebar menu item. The new "Pull Requests" entry will appear after Analytics in the left sidebar navigation. This change improves discoverability and establishes PR exploration as a primary navigation destination.

**Key Requirements:**
1. Add "Pull Requests" as a new top-level sidebar item after Analytics
2. Remove the PR tab from the Analytics tabbed interface
3. Preserve all crosslink functionality from Analytics pages to PR list with filters
4. Maintain URL backward compatibility for existing bookmarks/links
5. Follow strict TDD methodology
6. Work in a separate git worktree

---

## Current State Analysis

### Navigation Structure (Current)

```
Left Sidebar (team_nav.html):
├── Analytics → /a/<team>/dashboard/ (redirects based on role)
├── Integrations → /a/<team>/integrations/
├── Team Settings → /a/<team>/team/ (admin only)
└── Billing → /a/<team>/subscription/ (admin only)

Analytics Hub (base_analytics.html) - 7 tabs:
├── Overview
├── AI Adoption
├── Delivery
├── Quality
├── Team
├── Trends
└── Pull Requests ← TO BE REMOVED FROM HERE
```

### Key Files Involved

| File | Purpose |
|------|---------|
| `templates/web/components/team_nav.html` | Main sidebar navigation |
| `templates/metrics/analytics/base_analytics.html` | Analytics tab container |
| `templates/metrics/analytics/pull_requests.html` | PR list page (extends base_analytics) |
| `apps/metrics/urls.py` | URL patterns for metrics app |
| `apps/metrics/views/pr_list_views.py` | PR list view functions |

### Existing Crosslinks (Must Preserve)

These Analytics pages link to PR list with pre-applied filters:

| Source Page | Link Pattern | Purpose |
|-------------|--------------|---------|
| `overview.html` | `?days={{ days }}` | View all PRs |
| `overview.html` | `?ai=yes&days={{ days }}` | View AI-assisted PRs |
| `ai_adoption.html` | `?ai=yes&days={{ days }}` | AI-assisted PRs |
| `ai_adoption.html` | `?ai=no&days={{ days }}` | Non-AI PRs |
| `delivery.html` | `?days={{ days }}` | All PRs in date range |
| `delivery.html` | `?state=merged&days={{ days }}` | Merged PRs |
| `delivery.html` | `?size=L&days={{ days }}` | Large PRs |
| `quality.html` | `?days={{ days }}` | All PRs |
| `team.html` | `?days={{ days }}` | All PRs |
| `partials/team_breakdown_table.html` | `?author={{ member_id }}` | PRs by author |
| `partials/pr_size_chart.html` | `?size={{ category }}` | PRs by size |

---

## Proposed Future State

### Navigation Structure (Target)

```
Left Sidebar (team_nav.html):
├── Analytics → /a/<team>/dashboard/
├── Pull Requests → /a/<team>/pull-requests/  ← NEW
├── Integrations → /a/<team>/integrations/
├── Team Settings → /a/<team>/team/ (admin only)
└── Billing → /a/<team>/subscription/ (admin only)

Analytics Hub (base_analytics.html) - 6 tabs:
├── Overview
├── AI Adoption
├── Delivery
├── Quality
├── Team
└── Trends
(Pull Requests tab REMOVED)
```

### URL Structure

| Old URL | New URL | Notes |
|---------|---------|-------|
| `/a/<team>/metrics/pull-requests/` | `/a/<team>/pull-requests/` | Primary URL change |
| Same path preserved | Same path preserved | Optional: Keep old URL as redirect |

### Template Changes

1. **PR List Page**: Create `templates/metrics/pull_requests/list_standalone.html`
   - Standalone page (extends `app_base.html`, not `base_analytics.html`)
   - Contains its own date range picker
   - Maintains all filter functionality

2. **Sidebar**: Add PR entry to `team_nav.html`

3. **Analytics Base**: Remove PR tab from `base_analytics.html`

---

## Implementation Phases

### Phase 1: Setup & Test Infrastructure (TDD Red)

**Objective**: Create failing tests that define expected behavior

1. Create git worktree for isolated development
2. Write failing tests for:
   - New sidebar navigation item exists
   - PR list accessible at new URL
   - Old URL redirects to new URL (backward compatibility)
   - Crosslinks work correctly
   - Analytics tabs don't include PR tab

**Acceptance Criteria:**
- [ ] Worktree created at `../tformance-pr-sidebar`
- [ ] Test file `tests/test_pr_sidebar_move.py` created
- [ ] All tests fail (Red phase)

### Phase 2: URL & View Updates (TDD Green)

**Objective**: Minimal implementation to pass tests

1. Add new URL pattern for standalone PR page
2. Create redirect from old URL to new URL
3. Update `pr_list` view to work standalone
4. Update sidebar template

**Acceptance Criteria:**
- [ ] New URL `/a/<team>/pull-requests/` works
- [ ] Old URL redirects with 301
- [ ] Sidebar shows "Pull Requests" after Analytics
- [ ] All Phase 1 tests pass

### Phase 3: Template Separation (TDD Green cont.)

**Objective**: Create standalone PR page template

1. Create `list_standalone.html` template
2. Add date range picker to PR page (since it won't inherit from analytics)
3. Remove PR tab from `base_analytics.html`
4. Update view to use new template

**Acceptance Criteria:**
- [ ] PR page renders correctly standalone
- [ ] Date range picker functional on PR page
- [ ] Analytics hub has 6 tabs (no PR)
- [ ] All crosslinks still work

### Phase 4: Crosslink Verification (TDD Green cont.)

**Objective**: Ensure all Analytics→PR crosslinks work

1. Update all crosslink URLs to use new URL pattern
2. Test each crosslink path
3. Verify filter parameters pass correctly

**Acceptance Criteria:**
- [ ] All 11+ crosslink patterns tested
- [ ] Filters apply correctly from crosslinks
- [ ] No broken links in Analytics pages

### Phase 5: Refactor & Polish (TDD Refactor)

**Objective**: Clean up implementation while keeping tests green

1. Remove duplicate code
2. Optimize template structure
3. Update E2E tests
4. Documentation updates

**Acceptance Criteria:**
- [ ] Code follows DRY principles
- [ ] E2E tests updated and passing
- [ ] All unit tests passing
- [ ] Code review ready

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Broken crosslinks | Medium | High | Comprehensive crosslink tests |
| URL bookmark breakage | Low | Medium | Permanent redirect from old URL |
| Template inheritance issues | Medium | Medium | Thorough template testing |
| Date range state loss | Medium | Medium | Verify Alpine store works on standalone page |
| E2E test failures | High | Medium | Update E2E tests early |

---

## Success Metrics

1. **Functional**
   - [ ] PR page accessible from sidebar
   - [ ] All crosslinks from Analytics work
   - [ ] Date range filtering works
   - [ ] All existing PR filters work
   - [ ] Export CSV works
   - [ ] HTMX table interactions work

2. **Quality**
   - [ ] All unit tests pass
   - [ ] All E2E tests pass
   - [ ] No console errors
   - [ ] No visual regressions

3. **User Experience**
   - [ ] One-click access to PR list from sidebar
   - [ ] Intuitive navigation flow
   - [ ] Consistent with existing design patterns

---

## Technical Notes

### Alpine.js Store Consideration

The current PR list relies on Analytics' Alpine store for date range state. When making PR list standalone:

**Option A**: Include the Alpine store on the standalone page (preferred)
```html
<!-- In standalone template -->
<div x-data x-init="$store.dateRange.days = {{ days|default:30 }}">
```

**Option B**: PR page manages its own state without global store
- Pass date params via URL
- Initialize from URL params on page load

### HTMX Considerations

The PR list table uses HTMX for:
- Filter form submission
- Pagination
- Column sorting

All these should continue to work as they target `#page-content` and `#pr-table-container` which will exist in the standalone template.

### CSS/Styling

The standalone template should use:
- `app-card` container class
- Same filter panel styling as current
- Same table styling
- Consistent with Analytics page visual weight

---

## Dependencies

- **No external dependencies** - All changes are internal
- **Blocked by**: None
- **Blocks**: None (isolated change)

---

## Rollback Plan

If issues arise post-deployment:

1. Revert sidebar changes in `team_nav.html`
2. Re-add PR tab to `base_analytics.html`
3. Revert URL pattern changes
4. Remove redirect

All changes are template/URL level - no database migrations required.
