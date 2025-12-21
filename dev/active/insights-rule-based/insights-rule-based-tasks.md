# Phase 1: Rule-Based Insights - Tasks

**Last Updated:** 2025-12-21

## Task Checklist

### 1. Data Model [S]
- [ ] Add `DailyInsight` model to `apps/metrics/models.py`
- [ ] Create migration
- [ ] Add `DailyInsightFactory` to `apps/metrics/factories.py`
- [ ] Write model tests

**Acceptance:** Model created, migration applied, factory works

---

### 2. Insight Engine Core [M]
- [ ] Create `apps/metrics/services/insight_engine.py`
- [ ] Implement `InsightRule` base class (ABC)
- [ ] Create `InsightResult` dataclass
- [ ] Implement rule registry
- [ ] Create `compute_insights(team, date)` main function
- [ ] Write engine tests

**Acceptance:** Engine can run registered rules and return results

---

### 3. Trend Rules [M]
- [ ] AI adoption trend rule (4-week change > 10%)
- [ ] Cycle time trend rule (4-week change > 20%)
- [ ] Review time trend rule (4-week change > 20%)
- [ ] Write tests for each rule

**Acceptance:** Each rule detects significant trends

---

### 4. Anomaly Rules [M]
- [ ] Hotfix spike rule (3x above average)
- [ ] Revert spike rule (any reverts = alert)
- [ ] CI/CD failure rate rule (> 20%)
- [ ] Low activity rule (developer 50% below avg)
- [ ] Write tests for each rule

**Acceptance:** Each rule detects anomalies correctly

---

### 5. Comparison Rules [S]
- [ ] AI vs non-AI quality comparison rule
- [ ] Top performer rule (highest PRs merged)
- [ ] Write tests for each rule

**Acceptance:** Comparison insights generated correctly

---

### 6. Action Rules [S]
- [ ] Redundant reviewer rule (use existing correlation data)
- [ ] Unlinked PRs rule (PRs missing Jira keys)
- [ ] Low Copilot acceptance rule (< 20%)
- [ ] Write tests for each rule

**Acceptance:** Actionable recommendations generated

---

### 7. Celery Integration [S]
- [ ] Create `compute_daily_insights` task in `apps/metrics/tasks.py`
- [ ] Add to beat schedule (run after sync)
- [ ] Handle errors gracefully
- [ ] Write task tests

**Acceptance:** Task runs daily after sync, insights stored in DB

---

### 8. Dashboard Integration [M]
- [ ] Create `templates/metrics/partials/insights_panel.html`
- [ ] Add insights to CTO dashboard context
- [ ] Style with DaisyUI (card component)
- [ ] Add category icons/colors
- [ ] Implement dismiss functionality (HTMX)
- [ ] Write view tests

**Acceptance:** Top 5 insights shown on dashboard, dismissible

---

## Progress Summary

| Task | Status | Effort |
|------|--------|--------|
| 1. Data Model | ⬜ Not Started | S |
| 2. Engine Core | ⬜ Not Started | M |
| 3. Trend Rules | ⬜ Not Started | M |
| 4. Anomaly Rules | ⬜ Not Started | M |
| 5. Comparison Rules | ⬜ Not Started | S |
| 6. Action Rules | ⬜ Not Started | S |
| 7. Celery Integration | ⬜ Not Started | S |
| 8. Dashboard Integration | ⬜ Not Started | M |

**Total Effort:** ~3-4 days

## Dependencies

```
1. Data Model
    ↓
2. Engine Core
    ↓
3-6. Rules (parallel)
    ↓
7. Celery Integration
    ↓
8. Dashboard Integration
```
