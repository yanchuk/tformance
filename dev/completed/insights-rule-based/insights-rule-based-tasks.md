# Phase 1: Rule-Based Insights - Tasks

**Last Updated:** 2025-12-21
**Status:** ✅ COMPLETE

## Task Checklist

### 1. Data Model [S] ✅ COMPLETE
- [x] Add `DailyInsight` model to `apps/metrics/models.py`
- [x] Create migration (`0011_add_daily_insight.py`)
- [x] Add `DailyInsightFactory` to `apps/metrics/factories.py`
- [x] Write model tests (22 tests in `test_daily_insight.py`)

**Acceptance:** ✅ Model created, migration applied, factory works

---

### 2. Insight Engine Core [M] ✅ COMPLETE
- [x] Create `apps/metrics/insights/engine.py`
- [x] Implement `InsightRule` base class (ABC)
- [x] Create `InsightResult` dataclass
- [x] Implement rule registry (`register_rule`, `get_all_rules`, `clear_rules`)
- [x] Create `compute_insights(team, date)` main function
- [x] Write engine tests (17 tests in `test_insight_engine.py`)

**Acceptance:** ✅ Engine can run registered rules and return results

---

### 3. Trend Rules [M] ✅ COMPLETE
- [x] AI adoption trend rule (4-week change > 10%)
- [x] Cycle time trend rule (4-week change > 20%)
- [x] BaseTrendRule abstract class with Template Method pattern
- [x] Write tests for each rule (11 tests)

**Note:** Review time trend rule deferred - not critical for MVP

**Acceptance:** ✅ Each rule detects significant trends

---

### 4. Anomaly Rules [M] ✅ COMPLETE
- [x] Hotfix spike rule (3x above average)
- [x] Revert spike rule (any reverts = alert)
- [x] CI/CD failure rate rule (> 20%)
- [x] Write tests for each rule (12 tests)

**Note:** Low activity rule deferred - not critical for MVP

**Acceptance:** ✅ Each rule detects anomalies correctly

---

### 5. Comparison Rules [S] - DEFERRED
- [ ] AI vs non-AI quality comparison rule
- [ ] Top performer rule (highest PRs merged)

**Note:** Deferred to Phase 2 - focus on core rules first

---

### 6. Action Rules [S] ✅ COMPLETE
- [x] Redundant reviewer rule (use existing correlation data)
- [x] Unlinked PRs rule (PRs missing Jira keys, threshold: 5+)
- [x] Write tests for each rule (12 tests)

**Note:** Low Copilot acceptance rule deferred

**Acceptance:** ✅ Actionable recommendations generated

---

### 7. Celery Integration [S] ✅ COMPLETE
- [x] Create `compute_team_insights` task in `apps/metrics/tasks.py`
- [x] Create `compute_all_team_insights` task
- [x] Register all 7 rules on module import
- [x] Handle errors gracefully (continues on failure)
- [x] Write task tests (11 tests in `test_insight_tasks.py`)
- [x] Add to beat schedule (6 AM UTC daily)

**Acceptance:** ✅ Tasks work and scheduled in Celery beat

---

### 8. Dashboard Integration [M] ✅ COMPLETE
- [x] Create `templates/metrics/partials/insights_panel.html`
- [x] Add insights to CTO dashboard context
- [x] Add `get_recent_insights(team, limit=5)` service function
- [x] Style with DaisyUI (alert component)
- [x] Add category badges
- [x] Implement dismiss functionality (HTMX)
- [x] Write view tests (11 tests in `test_insight_dashboard.py`)

**Acceptance:** ✅ Top 5 insights shown on dashboard, dismissible

---

## Progress Summary

| Task | Status | Effort |
|------|--------|--------|
| 1. Data Model | ✅ Complete | S |
| 2. Engine Core | ✅ Complete | M |
| 3. Trend Rules | ✅ Complete | M |
| 4. Anomaly Rules | ✅ Complete | M |
| 5. Comparison Rules | ⏸️ Deferred | S |
| 6. Action Rules | ✅ Complete | S |
| 7. Celery Integration | ✅ Complete | S |
| 8. Dashboard Integration | ✅ Complete | M |

**Completed:** 7/8 tasks (100% of planned MVP)
**Deferred:** Comparison rules (Phase 2)

## Test Coverage

```
test_daily_insight.py      - 22 tests ✅
test_insight_engine.py     - 17 tests ✅
test_insight_rules.py      - 35 tests ✅
test_insight_tasks.py      - 11 tests ✅
test_insight_dashboard.py  - 11 tests ✅
─────────────────────────────────────────
Total new tests:             96 tests
```

All tests passing: `make test ARGS='apps.metrics.tests.test_daily_insight apps.metrics.tests.test_insight_engine apps.metrics.tests.test_insight_rules apps.metrics.tests.test_insight_tasks apps.metrics.tests.test_insight_dashboard --keepdb'`

## Commit

Committed: `db55990` - Add rule-based insights system with 7 rules and dashboard integration
