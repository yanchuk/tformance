# Dashboard Merge - Implementation Tasks

**Last Updated:** 2024-12-30
**Status:** Phase 2 Complete ✅

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

## Phase 3: Templates (Effort: L)

New and modified templates for the unified dashboard.

### 3.1 Needs Attention Component
- [ ] Create `templates/web/components/needs_attention.html`
- [ ] Implement prioritized list with icons (🔴🟡⚪)
- [ ] Add pagination controls
- [ ] Implement "All Clear" empty state
- [ ] Add loading skeleton
- [ ] Style with DaisyUI/Tailwind

**Acceptance:** Component displays issues correctly with pagination and empty state.

### 3.2 AI Impact Component
- [ ] Create `templates/web/components/ai_impact.html`
- [ ] Show adoption percentage with change indicator
- [ ] Show cycle time comparison
- [ ] Show percentage difference highlight
- [ ] Implement empty state (no AI data)
- [ ] Add "View AI Analytics" link

**Acceptance:** Component displays AI metrics with proper empty state handling.

### 3.3 Team Velocity Component
- [ ] Create `templates/web/components/team_velocity.html`
- [ ] Show ranked list of contributors
- [ ] Include avatar, name, PR count, avg cycle
- [ ] Implement empty state
- [ ] Add "View All Members" link

**Acceptance:** Component displays top contributors with proper formatting.

### 3.4 Bottleneck Alert Component
- [ ] Create `templates/web/components/bottleneck_alert.html`
- [ ] Warning style alert with reviewer name
- [ ] Show pending count vs team average
- [ ] Conditionally rendered (only when bottleneck exists)

**Acceptance:** Alert appears when bottleneck detected, hidden otherwise.

### 3.5 Integration Health Component
- [ ] Create `templates/web/components/integration_health.html`
- [ ] Show alerts for integration issues only
- [ ] Hidden when all integrations healthy
- [ ] Different messages for different issues (rate limit, auth expired, etc.)

**Acceptance:** Component shows relevant alerts, hidden when healthy.

### 3.6 Unified Dashboard Layout
- [ ] Rewrite `templates/web/app_home.html`
- [ ] Header with time range selector
- [ ] Key metrics row (reuse existing cards)
- [ ] Two-column grid: Needs Attention + AI Impact
- [ ] Two-column grid: Review Distribution + Team Velocity
- [ ] Conditional Integration Health
- [ ] Footer links to detailed views
- [ ] Responsive layout (mobile single column)

**Acceptance:** New layout matches wireframe with all sections loading correctly.

### 3.7 Modify Review Distribution Template
- [ ] Update `templates/metrics/partials/review_distribution_chart.html`
- [ ] Add bottleneck alert section above chart
- [ ] Add pagination for large teams
- [ ] Fixed height container

**Acceptance:** Chart includes bottleneck alert and pagination.

---

## Phase 4: Integration & Polish (Effort: M)

Wire everything together and polish UX.

### 4.1 Time Range Selector
- [ ] Add 7d/30d/90d buttons to header
- [ ] Wire to Alpine.js store
- [ ] Trigger HTMX refresh on all sections when changed
- [ ] Persist selection (localStorage or URL param)

**Acceptance:** Changing time range updates all dashboard sections.

### 4.2 Loading States
- [ ] Add skeleton loaders to all HTMX containers
- [ ] Ensure consistent loading animation
- [ ] Test with slow network (throttle)

**Acceptance:** Smooth loading experience with visible progress.

### 4.3 Error Handling
- [ ] Add error states to HTMX requests
- [ ] Show user-friendly error messages
- [ ] Implement retry mechanism

**Acceptance:** Errors display friendly message with retry option.

### 4.4 Empty States
- [ ] Implement all empty states per PRD
- [ ] Test each empty state scenario
- [ ] Ensure positive messaging

**Acceptance:** All empty states render correctly with appropriate messaging.

---

## Phase 5: Migration & Cleanup (Effort: S)

Redirect old routes and remove deprecated code.

### 5.1 Add Redirect
- [ ] Modify `team_dashboard()` to redirect to `/app/`
- [ ] Preserve `days` query parameter in redirect
- [ ] Add deprecation notice message

**Acceptance:** Old URL redirects with message.

### 5.2 Update Navigation
- [ ] Remove "View Analytics" button from new dashboard
- [ ] Update sidebar links if needed
- [ ] Ensure all internal links point to correct destinations

**Acceptance:** No broken links, navigation makes sense.

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

## Notes

- Start with Phase 1 service layer - this unblocks everything else
- Templates (Phase 3) is the largest effort, can be parallelized
- Keep existing dashboard working until Phase 5 redirect
- Feature flag optional but recommended for safe rollout
