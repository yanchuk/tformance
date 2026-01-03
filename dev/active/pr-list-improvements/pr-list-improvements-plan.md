# PR List Page Improvements - Implementation Plan

**Last Updated:** 2026-01-03

## Executive Summary

This plan addresses three issues on the PR List page (`/app/pull-requests/`):
1. **Alpine.js Console Error** - Multi-line `if` statement in event handler causing syntax errors
2. **Layout Width Constraints** - Excessive padding/margins limiting content area width
3. **PR Expansion UX** - Unclear visual feedback when PRs are expanded, confusing multi-expand behavior

All changes are frontend-only (templates + CSS). No backend changes required.

---

## Current State Analysis

### Issue 1: Alpine.js Expression Error
- **Location:** `templates/metrics/pull_requests/list_standalone.html:86-95`
- **Root Cause:** Alpine.js event handlers only accept expressions, not multi-line statements with `if` blocks
- **Impact:** Console errors on every page load; potential JS execution issues

### Issue 2: Layout Width
- **Current spacing:**
  - `.section` class: `m-4` (16px margin all sides)
  - `.app-card` class: `p-4/p-8` (16px mobile, 32px desktop padding)
  - Sidebar: `w-64` (256px fixed) - to be kept unchanged
- **Impact:** PR table feels cramped; repository names truncated; less data visible

### Issue 3: PR Expansion UX
- **Current behavior:** Each PR row has independent `expanded` state, allowing multiple open
- **Visual feedback:** Only faint `bg-base-200/30` and small chevron rotation
- **Impact:** Users confused about which PRs are expanded and how to collapse them

---

## Proposed Future State

1. **No console errors** - Alpine expression properly structured as method call
2. **More content width** - Reduced margins/padding give ~50px more horizontal space
3. **Clear accordion UX** - Only one PR expanded at a time with prominent visual highlighting

---

## Implementation Phases

### Phase 1: TDD Test Setup (E2E Tests)
Write failing E2E tests that validate the expected behavior before implementation.

### Phase 2: Alpine.js Fix
Move inline logic to x-data method to fix console error.

### Phase 3: CSS Spacing Adjustments
Reduce margins and padding in CSS and layout template.

### Phase 4: Accordion Mode Implementation
Refactor PR table to use shared state for single-expand behavior with visual improvements.

### Phase 5: Visual Verification
Verify all changes via Playwright and manual testing.

---

## Detailed Tasks

### Phase 1: TDD Test Setup

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 1.1 | Create E2E test for no console errors on PR list page | S | Test fails initially (error exists) |
| 1.2 | Create E2E test for accordion behavior | M | Test fails (multiple PRs can expand) |
| 1.3 | Create E2E test for expanded row visual indicators | S | Test fails (no border-l-primary class) |

### Phase 2: Alpine.js Fix

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 2.1 | Add `cleanRequestParams()` method to x-data | S | Method defined in x-data object |
| 2.2 | Replace inline handler with method call | S | `@htmx:config-request.window="cleanRequestParams($event)"` |
| 2.3 | Verify E2E test 1.1 passes | S | No Alpine expression errors in console |

### Phase 3: CSS Spacing Adjustments

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 3.1 | Reduce `.section` margin from `m-4` to `m-2` | S | CSS updated |
| 3.2 | Reduce `.app-card` padding from `p-4/p-8` to `p-3/p-5` | S | CSS updated |
| 3.3 | Add explicit gap to flex container in `app_base.html` | S | `gap-2 lg:gap-3` added |
| 3.4 | Visual verification of layout changes | S | More horizontal space for table |

### Phase 4: Accordion Mode Implementation

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 4.1 | Wrap table in container with shared `expandedPrId` state | M | `x-data="{ expandedPrId: null }"` on wrapper |
| 4.2 | Update row click handlers to use shared state | M | `expandedPrId === {{ pr.id }}` checks |
| 4.3 | Update chevron button to use shared state | S | Chevron triggers shared state toggle |
| 4.4 | Add visual highlight classes to expanded row | S | `border-l-4 border-l-primary bg-base-200/50` |
| 4.5 | Update expanded content row to use shared state | S | `x-show="expandedPrId === {{ pr.id }}"` |
| 4.6 | Add primary color to chevron when expanded | S | `:class="{ 'text-primary': expandedPrId === {{ pr.id }} }"` |
| 4.7 | Verify E2E tests 1.2 and 1.3 pass | S | All accordion tests green |

### Phase 5: Visual Verification

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 5.1 | Run full E2E test suite | S | All tests pass |
| 5.2 | Visual verification with Playwright screenshot | S | UI renders correctly |
| 5.3 | Test on staging (dev.ianchuk.com) | S | No regressions |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CSS changes affect other pages | Medium | Medium | Test other pages using `.section` and `.app-card` |
| Alpine state not shared properly between rows | Low | High | Each tbody still needs its own x-data for inline notes |
| Inline notes feature broken by accordion change | Medium | Medium | Preserve `inlineOpen` state per-row separately |

---

## Success Metrics

1. **Zero console errors** on PR list page load
2. **Only one PR expanded** at a time (accordion behavior)
3. **Clear visual indicator** (orange left border) on expanded row
4. **~50px more horizontal space** for content area
5. **All E2E tests passing**

---

## Dependencies

- No backend changes required
- No new packages needed
- Tailwind CSS already supports all required classes
- Alpine.js 3.x already in use

---

## Files to Modify

| File | Purpose |
|------|---------|
| `templates/metrics/pull_requests/list_standalone.html` | Fix Alpine expression |
| `assets/styles/app/tailwind/app-components.css` | Reduce margins/padding |
| `templates/web/app/app_base.html` | Add gap to layout |
| `templates/metrics/pull_requests/partials/table.html` | Accordion mode + visuals |
| `tests/e2e/pr-list-accordion.spec.ts` | New E2E tests |
