# Team Tab Copilot Integration - Tasks

**Last Updated:** 2026-01-11 (Session Start)

## Progress Overview

| Phase | Status | Tasks |
|-------|--------|-------|
| Issue 7: Copilot Column | NOT STARTED | 0/5 |
| Issue 8: Champion Badges | NOT STARTED | 0/4 |

**Estimated Total Effort:** 3-4.5h with TDD

---

## Issue 7: Copilot Acceptance Column (2-3h)

### 7.1 TDD RED - Write Failing Tests (Effort: S)

- [ ] **7.1.1** Write test `test_get_team_breakdown_includes_copilot_acceptance` in `test_team_metrics.py`
- [ ] **7.1.2** Write test `test_get_team_breakdown_copilot_empty_for_no_data` (edge case)
- [ ] **7.1.3** Write test `test_table_breakdown_sort_by_copilot_pct` in `test_chart_views.py`

### 7.2 TDD GREEN - Implement Service (Effort: M)

- [ ] **7.2.1** Add `copilot_pct` aggregation to `get_team_breakdown()` in `team_metrics.py`
- [ ] **7.2.2** Add `copilot_pct` to `SORT_FIELDS` constant
- [ ] **7.2.3** Add sorting case for `copilot_pct`

### 7.3 TDD GREEN - Update Template (Effort: S)

- [ ] **7.3.1** Add "Copilot %" column header with sorting + tooltip
- [ ] **7.3.2** Add data cell with badge/"-" display
- [ ] **7.3.3** Add team average in footer

### 7.4 TDD REFACTOR (Effort: S)

- [ ] **7.4.1** Add tooltip to existing "AI %" column for clarity
- [ ] **7.4.2** Verify tests pass

---

## Issue 8: Champion Badges (1-1.5h)

### 8.1 TDD RED - Write Failing Tests (Effort: S)

- [ ] **8.1.1** Write test `test_table_breakdown_includes_champion_ids` in `test_chart_views.py`
- [ ] **8.1.2** Write test `test_table_breakdown_champion_ids_empty_when_no_champions`

### 8.2 TDD GREEN - Implement View (Effort: S)

- [ ] **8.2.1** Import `get_copilot_champions` in `chart_views.py`
- [ ] **8.2.2** Call function with same date range as breakdown
- [ ] **8.2.3** Create set: `champion_ids = {c["member_id"] for c in champions}`
- [ ] **8.2.4** Add `champion_ids` to template context

### 8.3 TDD GREEN - Update Template (Effort: S)

- [ ] **8.3.1** Add 🏆 badge next to member name if `row.member_id in champion_ids`
- [ ] **8.3.2** Add tooltip: "Copilot Champion - High acceptance + fast delivery"

### 8.4 TDD REFACTOR (Effort: S)

- [ ] **8.4.1** Verify badge matches AI Adoption tab Champions list
- [ ] **8.4.2** All tests pass

---

## Verification Checklist

- [ ] `make test` passes
- [ ] Navigate to Team tab:
  - [ ] Copilot % column visible
  - [ ] Column is sortable
  - [ ] Members without data show "-"
  - [ ] 🏆 badge appears for champions
  - [ ] Tooltips explain metrics
- [ ] Champions match AI Adoption tab list

---

## Files to Create/Modify

### Services
- `apps/metrics/services/dashboard/team_metrics.py` - Add Copilot aggregation

### Views
- `apps/metrics/views/chart_views.py` - Add champion_ids to context

### Templates
- `templates/metrics/partials/team_breakdown_table.html` - Add column + badge

### Tests
- `apps/metrics/tests/dashboard/test_team_metrics.py` - Copilot aggregation tests
- `apps/metrics/tests/test_chart_views.py` - View context tests

---

## Key Code Locations

### Existing get_team_breakdown()
File: `apps/metrics/services/dashboard/team_metrics.py`
Find: `def get_team_breakdown(`

### Existing table_breakdown view
File: `apps/metrics/views/chart_views.py`
Find: `def table_breakdown(`

### Existing get_copilot_champions()
File: `apps/metrics/services/dashboard/ai_metrics.py`
Find: `def get_copilot_champions(`

### AIUsageDaily model
File: `apps/metrics/models/aggregations.py:12`
Has: `member`, `acceptance_rate`, `source`
