# PR List Page Improvements - Task Checklist

**Last Updated:** 2026-01-03

## Overview
- **Total Tasks:** 17
- **Completed:** 17
- **In Progress:** 0
- **Remaining:** 0

---

## Phase 1: TDD Test Setup (RED Phase)

Write failing E2E tests before implementation.

- [x] **1.1** Create `tests/e2e/pr-list-accordion.spec.ts` file
  - **Effort:** S
  - **File:** `tests/e2e/pr-list-accordion.spec.ts`

- [x] **1.2** Write test: No console errors on PR list page
  - **Effort:** S
  - **Acceptance:** Test checks for Alpine expression errors; should FAIL initially

- [x] **1.3** Write test: Accordion behavior (only one PR expanded)
  - **Effort:** M
  - **Acceptance:** Test verifies first PR collapses when second expands; should FAIL initially

- [x] **1.4** Write test: Visual indicators on expanded row
  - **Effort:** S
  - **Acceptance:** Test checks for `border-l-primary` class; should FAIL initially

- [x] **1.5** Run tests and confirm they FAIL
  - **Effort:** S
  - **Command:** `make e2e ARGS='tests/e2e/pr-list-accordion.spec.ts'`

---

## Phase 2: Alpine.js Fix (GREEN Phase - Task 1)

Fix the console error by restructuring Alpine code.

- [x] **2.1** Add `cleanRequestParams()` method to x-data in `list_standalone.html`
  - **Effort:** S
  - **File:** `templates/metrics/pull_requests/list_standalone.html:26-84`
  - **Code:**
    ```javascript
    cleanRequestParams($event) {
      if ($event.detail.elt?.closest?.('[x-data]') === this.$el) {
        Object.keys($event.detail.parameters).forEach(key => {
          if ($event.detail.parameters[key] === '' || $event.detail.parameters[key] === null) {
            delete $event.detail.parameters[key];
          }
        });
      }
    }
    ```

- [x] **2.2** Replace inline handler with method call
  - **Effort:** S
  - **Before:** Multi-line `if` statement
  - **After:** `@htmx:config-request.window="cleanRequestParams($event)"`

- [x] **2.3** Verify console error test passes
  - **Effort:** S
  - **Command:** `make e2e ARGS='tests/e2e/pr-list-accordion.spec.ts -g "console errors"'`

---

## Phase 3: CSS Spacing Adjustments (GREEN Phase - Task 2)

Reduce margins and padding for more content width.

- [x] **3.1** Update `.section` margin in `app-components.css`
  - **Effort:** S
  - **File:** `assets/styles/app/tailwind/app-components.css:1-3`
  - **Before:** `@apply m-4;`
  - **After:** `@apply m-2;`

- [x] **3.2** Update `.app-card` padding in `app-components.css`
  - **Effort:** S
  - **File:** `assets/styles/app/tailwind/app-components.css:10-12`
  - **Before:** `@apply lg:shadow-md p-4 mb-2 mt-2 lg:mt-0 lg:p-8;`
  - **After:** `@apply lg:shadow-md p-3 mb-2 mt-2 lg:mt-0 lg:p-5;`

- [x] **3.3** Add gap between sidebar and content in `app_base.html`
  - **Effort:** S
  - **File:** `templates/web/app/app_base.html:12`
  - **Before:** `<div class="container flex flex-row">`
  - **After:** `<div class="container flex flex-row gap-2 lg:gap-3">`

---

## Phase 4: Accordion Mode Implementation (GREEN Phase - Task 3)

Implement single-expand behavior with visual improvements.

- [x] **4.1** Wrap table in container with shared state
  - **Effort:** M
  - **File:** `templates/metrics/pull_requests/partials/table.html:4`
  - **Add:** `<div x-data="{ expandedPrId: null }">` around table
  - **Note:** Keep `inlineOpen` per-row for notes feature

- [x] **4.2** Update row click handler to use shared state
  - **Effort:** M
  - **File:** `templates/metrics/pull_requests/partials/table.html:59`
  - **Before:** `@click="expanded = !expanded"`
  - **After:** `@click="expandedPrId = (expandedPrId === {{ pr.id }}) ? null : {{ pr.id }}"`

- [x] **4.3** Update row `:class` binding for visual highlight
  - **Effort:** S
  - **Before:** `:class="{ 'border-b-0': expanded }"`
  - **After:** `:class="{ 'border-b-0': expandedPrId === {{ pr.id }}, 'border-l-4 border-l-primary bg-base-200/50': expandedPrId === {{ pr.id }} }"`

- [x] **4.4** Update chevron button to use shared state
  - **Effort:** S
  - **File:** `templates/metrics/pull_requests/partials/table.html:66-73`
  - **Update:** `@click.stop` handler and `:class` binding

- [x] **4.5** Update expanded content row `x-show`
  - **Effort:** S
  - **File:** `templates/metrics/pull_requests/partials/table.html:210`
  - **Before:** `x-show="expanded"`
  - **After:** `x-show="expandedPrId === {{ pr.id }}"`

- [x] **4.6** Add visual styling to expanded content row
  - **Effort:** S
  - **Update:** `class="bg-base-200/50 border-l-4 border-l-primary"`

- [x] **4.7** Remove per-row `expanded` state (keep `inlineOpen`)
  - **Effort:** S
  - **Before:** `x-data="{ expanded: false, inlineOpen: false }"`
  - **After:** `x-data="{ inlineOpen: false }"`

---

## Phase 5: Verification (REFACTOR Phase)

- [x] **5.1** Run all E2E tests for PR list accordion
  - **Effort:** S
  - **Command:** `make e2e ARGS='tests/e2e/pr-list-accordion.spec.ts'`
  - **Acceptance:** All tests pass (GREEN)

- [x] **5.2** Run full E2E smoke test suite
  - **Effort:** S
  - **Command:** `make e2e-smoke`
  - **Acceptance:** No regressions

- [x] **5.3** Visual verification with Playwright screenshot
  - **Effort:** S
  - **Check:** PR list page renders correctly with new spacing

---

## Completion Criteria

All items checked = Task complete

**Definition of Done:**
- [x] All E2E tests pass
- [x] No console errors on PR list page
- [x] Only one PR can be expanded at a time
- [x] Expanded PR has visible orange left border
- [x] Spacing changes give more horizontal room
- [x] Works in both light and dark themes
