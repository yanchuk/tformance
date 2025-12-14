# High-Value Reports - Tasks

Last Updated: 2025-12-14

## Status: COMPLETE

All phases implemented, tested, and committed.

---

## Phase 1: Review Time Trend (Low Effort) - COMPLETE

### Service Layer
- [x] Add `get_review_time_trend()` to `dashboard_service.py`
- [x] Refactored to use shared `_get_metric_trend()` helper

### Tests (TDD)
- [x] 7 tests covering all edge cases
- [x] All tests passing

### View & Template
- [x] `review_time_chart()` view in `chart_views.py`
- [x] URL pattern: `charts/review-time/`
- [x] Template: `review_time_chart.html`

---

## Phase 2: PR Size Distribution (Low Effort) - COMPLETE

### Service Layer
- [x] Add `get_pr_size_distribution()` to `dashboard_service.py`
- [x] Refactored to use DB-level aggregation with Case/When
- [x] Added constants: `PR_SIZE_XS_MAX`, `PR_SIZE_S_MAX`, etc.

### Tests (TDD)
- [x] 13 tests covering all size categories and edge cases
- [x] All tests passing

### View & Template
- [x] `pr_size_chart()` view
- [x] URL pattern: `charts/pr-size/`
- [x] Template: `pr_size_chart.html` (color-coded bars)

---

## Phase 3: Revert/Hotfix Rate (Low Effort) - COMPLETE

### Service Layer
- [x] Add `get_revert_hotfix_stats()` to `dashboard_service.py`
- [x] Refactored to single DB query with Count+filter

### Tests (TDD)
- [x] 12 tests for counts, percentages, edge cases
- [x] All tests passing

### View & Template
- [x] `revert_rate_card()` view
- [x] URL pattern: `cards/revert-rate/`
- [x] Template: `revert_rate_card.html` (threshold badges)

---

## Phase 4: Unlinked PRs Table (Low Effort) - COMPLETE

### Service Layer
- [x] Add `get_unlinked_prs()` to `dashboard_service.py`
- [x] Extracted shared helpers: `_get_github_url()`, `_get_author_name()`

### Tests (TDD)
- [x] 13 tests for filtering, ordering, limit
- [x] All tests passing

### View & Template
- [x] `unlinked_prs_table()` view
- [x] URL pattern: `tables/unlinked-prs/`
- [x] Template: `unlinked_prs_table.html` (success state when all linked)

---

## Phase 5: Reviewer Workload (Medium Effort) - COMPLETE

### Service Layer
- [x] Add `get_reviewer_workload()` to `dashboard_service.py`
- [x] Uses `PRReview` model (GitHub reviews, NOT PRSurveyReview)
- [x] Percentile calculation with `statistics.quantiles()`

### Tests (TDD)
- [x] 12 tests for workload classification, filtering
- [x] All tests passing

### View & Template
- [x] `reviewer_workload_table()` view
- [x] URL pattern: `tables/reviewer-workload/`
- [x] Template: `reviewer_workload_table.html` (low/normal/high badges)

---

## Phase 6: Dashboard Integration - COMPLETE

- [x] Row 1: Cycle Time Trend + Review Time Trend
- [x] Row 2: PR Size Distribution + Quality Indicators
- [x] Row 3: Review Distribution + AI Detective Leaderboard
- [x] Row 4: Reviewer Workload (full width)
- [x] Row 5: Recent PRs + PRs Missing Jira Links
- [x] All sections use HTMX lazy loading

---

## Phase 7: E2E Tests - COMPLETE

- [x] `test('review time trend section displays')`
- [x] `test('PR size distribution section displays')`
- [x] `test('quality indicators section displays')`
- [x] `test('reviewer workload section displays')`
- [x] `test('unlinked PRs section displays')`
- [x] Fixed existing test selector for strict mode
- [x] All 25 dashboard E2E tests passing

---

## Commits - COMPLETE

- [x] `013a083` Add high-value report service functions with tests
- [x] `e0bc7fe` Add views and templates for high-value reports
- [x] `fe9a266` Integrate high-value reports into team dashboard
- [x] `3a37306` Add E2E tests for high-value dashboard reports

---

## Test Results

```bash
# Unit tests
make test ARGS='apps.metrics.tests.test_dashboard_service --keepdb'
# Result: 94 tests passing

# E2E tests
npx playwright test dashboard.spec.ts
# Result: 25 tests passing
```
