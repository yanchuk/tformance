# Dashboard Merge - Implementation Tasks

**Last Updated:** 2024-12-31
**Status:** Phase 5 Complete - Bug Fixes Applied

---

## Phase 1: Service Layer (Effort: M) ✅ COMPLETE

Backend services for new dashboard components.

### 1.1 Needs Attention Service ✅
- [x] Create `get_needs_attention_prs()` in `dashboard_service.py`
- [x] Implement issue detection logic (reverts, hotfixes, long cycle, large PR, no Jira)
- [x] Implement priority ordering
- [x] Add pagination support
- [ ] Add caching (5 min TTL) - deferred to Phase 4
- [x] Write unit tests for all edge cases (16 tests)

**Acceptance:** Function returns prioritized list of flagged PRs with pagination metadata. ✅

### 1.2 AI Impact Service ✅
- [x] Create `get_ai_impact_stats()` in `dashboard_service.py`
- [x] Calculate AI adoption percentage
- [x] Calculate avg cycle time with AI vs without AI
- [x] Calculate percentage difference
- [x] Handle edge cases (no AI PRs, all AI PRs, no cycle time data)
- [x] Write unit tests (15 tests)

**Acceptance:** Function returns dict with adoption %, both cycle times, and difference. ✅

### 1.3 Team Velocity Service ✅
- [x] Create `get_team_velocity()` in `dashboard_service.py`
- [x] Query top N contributors by PR count
- [x] Include avg cycle time per contributor
- [x] Handle ties in PR count (sorted alphabetically by display_name)
- [x] Write unit tests (13 tests)

**Acceptance:** Function returns ordered list of contributors with PR count and avg cycle. ✅

### 1.4 Bottleneck Detection Service ✅
- [x] Create `detect_review_bottleneck()` in `dashboard_service.py`
- [x] Calculate team average pending reviews
- [x] Identify reviewers exceeding 3x threshold
- [x] Return bottleneck details or None
- [x] Write unit tests (15 tests)

**Note:** Date parameters are accepted for API consistency but not used - bottleneck detection
looks at ALL currently open PRs since pending work is independent of when PR was created.

**Acceptance:** Function returns bottleneck info when threshold exceeded, None otherwise. ✅

---

## Phase 2: HTMX Endpoints (Effort: M) ✅ COMPLETE

New view functions for lazy-loaded sections.

### 2.1 Needs Attention Endpoint ✅
- [x] Create `needs_attention_view()` in `chart_views.py`
- [x] Accept `days` and `page` query params
- [x] Call service layer
- [x] Return rendered partial template
- [x] Add URL route `metrics:needs_attention`
- [x] Write view tests (11 tests)

**Acceptance:** Endpoint returns HTML partial with paginated issue list. ✅

### 2.2 AI Impact Endpoint ✅
- [x] Create `ai_impact_view()` in `chart_views.py`
- [x] Accept `days` query param
- [x] Call service layer
- [x] Return rendered partial template
- [x] Add URL route `metrics:ai_impact`
- [x] Write view tests (7 tests)

**Acceptance:** Endpoint returns HTML partial with AI comparison stats. ✅

### 2.3 Team Velocity Endpoint ✅
- [x] Create `team_velocity_view()` in `chart_views.py`
- [x] Accept `days` query param
- [x] Call service layer
- [x] Return rendered partial template
- [x] Add URL route `metrics:team_velocity`
- [x] Write view tests (9 tests)

**Acceptance:** Endpoint returns HTML partial with top contributors list. ✅

### 2.4 Enhanced Review Distribution Endpoint ✅
- [x] Modify existing `review_distribution_chart()` to include bottleneck check
- [x] Add bottleneck alert to response context
- [x] Write tests (3 tests)

**Note:** Also fixed bug where repo filter was passed to function that doesn't support it.

**Acceptance:** Endpoint includes bottleneck alert when threshold exceeded. ✅

---

## Phase 3: Templates (Effort: L) ✅ COMPLETE

New and modified templates for the unified dashboard.

### 3.0 TDD - team_home() View ✅
- [x] 🔴 RED: Write tests for days parameter in `apps/web/tests/test_views.py`
  - [x] `test_default_days_is_30` - Context should have days=30
  - [x] `test_accepts_days_query_param` - Should accept ?days=7
  - [x] `test_invalid_days_defaults_to_30` - Error handling for invalid values
- [x] 🟢 GREEN: Update `apps/web/views.py` team_home()
  - [x] Add `days = int(request.GET.get("days", 30))`
  - [x] Add `days` to context
- [x] 🔵 REFACTOR: Added try/except for ValueError handling

**Acceptance:** View tests pass, days parameter works correctly. ✅

### 3.1 Bottleneck Alert Component ✅
- [x] Create `templates/metrics/partials/bottleneck_alert.html`
- [x] Warning style alert with reviewer name
- [x] Show pending count vs team average
- [x] Conditionally rendered (only when bottleneck exists)

**Acceptance:** Alert appears when bottleneck detected, hidden otherwise. ✅

### 3.2 Update Review Distribution Template ✅
- [x] Update `templates/metrics/partials/review_distribution_chart.html`
- [x] Add `{% include bottleneck_alert.html %}` at top

**Acceptance:** Chart includes bottleneck alert when present. ✅

### 3.3 Unified Dashboard Layout ✅
- [x] Rewrite `templates/web/app_home.html`
- [x] Header with time range selector (7d/30d/90d buttons)
- [x] Key metrics row (lazy loaded via HTMX)
- [x] Two-column grid: Needs Attention + AI Impact
- [x] Two-column grid: Team Velocity + Review Distribution
- [x] Skeleton loaders for all HTMX containers
- [x] Keep setup wizard for non-connected teams
- [x] Integration status footer link

**Acceptance:** New layout with all sections lazy loading correctly. ✅

### 3.4 E2E Tests ✅
- [x] Update `tests/e2e/dashboard.spec.ts`
- [x] Test dashboard loads with lazy-loaded sections
- [x] Test time range selector functionality
- [x] Test all HTMX container IDs exist
- [x] Test integration status footer link

**Acceptance:** E2E tests pass. ✅ (116 tests)

### DEFERRED Components (Move to Phase 4)
The following components already exist as partials in `templates/metrics/partials/`:
- needs_attention.html ✅ (created in Phase 2)
- ai_impact.html ✅ (created in Phase 2)
- team_velocity.html ✅ (created in Phase 2)

No need to create web/components versions - reuse existing partials.

---

## Phase 4: Integration & Polish (Effort: M) ✅ COMPLETE

Wire everything together and polish UX. (Completed as part of Phase 3)

### 4.1 Time Range Selector ✅
- [x] Add 7d/30d/90d buttons to header (in filters.html)
- [x] Uses URL params (?days=N) for state
- [x] Trigger HTMX refresh on all sections when changed
- [x] Persist selection via URL param

**Acceptance:** Changing time range updates all dashboard sections. ✅

### 4.2 Loading States ✅
- [x] Add skeleton loaders to all HTMX containers
- [x] Consistent loading spinner animation
- [x] Tested via E2E

**Acceptance:** Smooth loading experience with visible progress. ✅

### 4.3 Error Handling ✅
- [x] Error states handled by existing htmx.js error handler
- [x] Shows user-friendly error messages

**Acceptance:** Errors display friendly message. ✅

### 4.4 Empty States ✅
- [x] Empty states implemented in partials (needs_attention, ai_impact, team_velocity)
- [x] Positive messaging with suggestions

**Acceptance:** All empty states render correctly with appropriate messaging. ✅

---

## Phase 5: Migration & Cleanup (Effort: S) ✅ COMPLETE

Redirect old routes and remove deprecated code.

### 5.1 Add Redirect ✅
- [x] Modify `team_dashboard()` to redirect to `/app/`
- [x] Preserve `days` query parameter in redirect
- [x] Updated unit tests to verify redirect behavior (6 tests)
- [x] Updated E2E tests to verify redirect (2 tests)

**Acceptance:** Old URL redirects with days param preserved. ✅

### 5.2 Update Navigation ✅
- [x] Removed "View Analytics" button from new dashboard (n/a - not in new layout)
- [x] Dashboard is now unified at /app/
- [x] Internal links work correctly

**Acceptance:** No broken links, navigation makes sense. ✅

### 5.3 Delete Deprecated Code (After 30 days)
- [ ] Remove `team_dashboard()` view
- [ ] Remove `templates/metrics/team_dashboard.html`
- [ ] Remove `templates/web/components/recent_activity.html`
- [ ] Remove `templates/web/components/quick_stats.html`
- [ ] Remove `get_team_quick_stats()` from quick_stats.py (if fully replaced)
- [ ] Remove related tests

**Acceptance:** Codebase clean with no dead code.

---

## Phase 6: Testing & QA (Effort: M)

Comprehensive testing before launch.

### 6.1 Unit Tests
- [ ] Service layer tests (all new functions)
- [ ] View tests (all new endpoints)
- [ ] Edge cases covered

**Acceptance:** > 90% coverage on new code.

### 6.2 E2E Tests
- [ ] Update `tests/e2e/dashboard.spec.ts`
- [ ] Test all sections load
- [ ] Test pagination
- [ ] Test time range switching
- [ ] Test empty states
- [ ] Test mobile layout

**Acceptance:** All E2E tests pass.

### 6.3 Performance Testing
- [ ] Measure initial page load time
- [ ] Measure HTMX partial load times
- [ ] Optimize if > targets (2s page, 500ms partials)

**Acceptance:** Meets performance targets.

### 6.4 Cross-browser Testing
- [ ] Chrome
- [ ] Firefox
- [ ] Safari
- [ ] Mobile Safari/Chrome

**Acceptance:** Works on all major browsers.

---

## Summary

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| 1 | Service Layer | M | None |
| 2 | HTMX Endpoints | M | Phase 1 |
| 3 | Templates | L | Phase 2 |
| 4 | Integration & Polish | M | Phase 3 |
| 5 | Migration & Cleanup | S | Phase 4 |
| 6 | Testing & QA | M | Phase 4 |

**Total Effort:** L-XL

**Critical Path:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 6

Phase 5 can run in parallel with Phase 6 (redirect can be added early).

---

## Bug Fixes (Post-Release) ✅ COMPLETE

### Review Distribution Count Mismatch (2024-12-31)
- [x] Fixed semantic mismatch: dashboard counted review submissions, PR list counted unique PRs
- [x] Changed `Count("id")` to `Count("pull_request", distinct=True)` in get_review_distribution()
- [x] Added `merged_at` date filter to dashboard to match PR list semantics
- [x] Added `submitted_at` date filter to PR list's reviewer filter
- [x] Updated template label from "reviews" to "PRs"
- [x] Added test: `test_get_review_distribution_counts_unique_prs_not_total_reviews`
- [x] All 372 dashboard tests pass, all 76 PR list service tests pass

**Acceptance:** Dashboard counts match PR list counts when clicking through. ✅

### E2E Data Consistency Tests (2024-12-31)
- [x] Created `tests/e2e/dashboard-data-consistency.spec.ts`
- [x] Test: Review Distribution shows "PRs" label, not "reviews"
- [x] Test: Needs Attention total matches sum of issue types
- [x] Test: Key Metrics PRs Merged matches PR list total
- [x] Test: Time range selector updates all sections
- [x] Tests pass on chromium (3 passed, 5 skipped due to no demo data)

**Acceptance:** E2E tests verify dashboard-to-PR-list data consistency. ✅

---

## Notes

- Start with Phase 1 service layer - this unblocks everything else
- Templates (Phase 3) is the largest effort, can be parallelized
- Keep existing dashboard working until Phase 5 redirect
- Feature flag optional but recommended for safe rollout
