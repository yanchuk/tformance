# CTO Dashboard Metrics - Tasks

Last Updated: 2025-12-14

## Status: COMPLETE

All high-value reports added to CTO Dashboard.

---

## Phase 1: Template Update (Effort: S) - COMPLETE

### 1.1 Restructure Cycle Time Section
- [x] Wrap Cycle Time Trend in a 2-column grid
- [x] Move to match Team Dashboard pattern

### 1.2 Add Review Time Trend
- [x] Add Review Time Trend card next to Cycle Time
- [x] Use HTMX endpoint: `{% url 'metrics:chart_review_time' %}?days={{ days }}`
- [x] Include icon, title, description, loading spinner

### 1.3 Add PR Size + Quality Indicators Row
- [x] Create new 2-column grid row
- [x] Add PR Size Distribution card
  - [x] Use endpoint: `{% url 'metrics:chart_pr_size' %}?days={{ days }}`
- [x] Add Quality Indicators card
  - [x] Use endpoint: `{% url 'metrics:cards_revert_rate' %}?days={{ days }}`

### 1.4 Add Reviewer Workload Section
- [x] Add full-width card after Team Breakdown
- [x] Use endpoint: `{% url 'metrics:table_reviewer_workload' %}?days={{ days }}`
- [x] Include icon, title, description

### 1.5 Add PRs Missing Jira Links Section
- [x] Add card after Reviewer Workload
- [x] Use endpoint: `{% url 'metrics:table_unlinked_prs' %}?days={{ days }}`
- [x] Include icon, title, description

---

## Phase 2: E2E Tests (Effort: S) - COMPLETE

### 2.1 Add CTO Dashboard Tests
- [x] Test: 'review time trend section displays on CTO dashboard'
- [x] Test: 'PR size distribution section displays on CTO dashboard'
- [x] Test: 'quality indicators section displays on CTO dashboard'
- [x] Test: 'reviewer workload section displays on CTO dashboard'
- [x] Test: 'unlinked PRs section displays on CTO dashboard'

---

## Phase 3: Verification - COMPLETE

- [x] Run E2E tests: `npx playwright test dashboard.spec.ts`
- [x] Visual verification: All 30 tests passing
- [x] Commit changes

---

## Test Results

```bash
# E2E tests
npx playwright test dashboard.spec.ts
# Result: 30 tests passing (was 25, added 5 new)
```
