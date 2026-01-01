# Jira-PR Correlation Enhancements - Implementation Plan

**Last Updated**: 2026-01-01
**Status**: Ready for Implementation
**Related**: Previous analysis at `.claude/plans/lexical-hatching-thompson.md`
**Approach**: Strict TDD (Red-Green-Refactor)

---

## Executive Summary

Enhance the PR-Jira correlation system to:
1. Capture additional Jira data (description, labels, priority, parent_issue_key) for future LLM analysis
2. Add dashboard visualizations (linkage donut, velocity chart, story point correlation)
3. Prepare infrastructure for LLM-enhanced insights

**Goal**: Enable CTOs to visualize how well PRs connect to Jira work items and whether story point estimates correlate with actual delivery time.

---

## Current State Analysis

### What Works
- PRs link to Jira via `jira_key` string matching (regex extraction from PR title/branch)
- `get_jira_sprint_metrics()` returns issues_resolved, story_points_completed, avg_cycle_time
- `get_pr_jira_correlation()` returns linkage_rate, linked/unlinked counts, cycle time comparison
- LLM insight prompt has Jira section showing these metrics

### What's Missing
1. **Data Gaps**: JiraIssue lacks description, labels, priority, parent_issue_key
2. **No Visualizations**: Metrics exist but no charts on dashboard
3. **No SP Correlation**: Can't compare estimated story points vs actual PR delivery time
4. **No Velocity Trend**: Single period only, no sprint-over-sprint view

---

## Proposed Future State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DASHBOARD ENHANCEMENTS                                 │
└─────────────────────────────────────────────────────────────────────────────┘

CTO Overview Page:
┌─────────────────────────────────────────────────────────────────────────────┐
│  PR-Jira Linkage        │  Story Point Accuracy                             │
│  ┌──────────┐           │  ┌─────────────────────────────────────┐          │
│  │ ████ 70% │ Linked    │  │ SP │ Est   │ Actual                │          │
│  │ ░░░░ 30% │ Unlinked  │  │ 1-2│ 3h    │ ▓▓▓▓ 4.2h             │          │
│  └──────────┘           │  │ 3-5│ 8h    │ ▓▓▓▓▓▓▓ 9.1h          │          │
│  ↑ 5% from last month   │  │ 5-8│ 13h   │ ▓▓▓▓▓▓▓▓▓▓ 14.8h      │          │
│                         │  └─────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘

Team Analytics Page:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Velocity Trend (6 months)                                                   │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ 50 ─────────────────────────────────────────────────────── │            │
│  │ 40 ─────────────●─────────────●─────────────●───────────── │ Story Pts  │
│  │ 30 ────●────────────────●─────────────●───────────●─────── │            │
│  │    Sep    Oct    Nov    Dec    Jan    Feb                   │            │
│  └─────────────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **New JiraIssue Fields** | description, labels, priority, parent_issue_key | Cover future LLM needs without over-fetching |
| **OAuth Scope** | No changes needed | Current `read:jira-work` includes all fields |
| **Chart Library** | Chart.js (existing) | Consistent with other charts |
| **Correlation Calculation** | Bucket-based grouping | More actionable than scatter plot |
| **LLM Integration** | Deferred | Need real data to tune prompts |

---

## Implementation Phases

### Phase 1: Data Foundation (TDD) - Effort: M

**Goal**: Capture additional Jira data for future LLM analysis

| Task | Effort | Description | Acceptance Criteria |
|------|--------|-------------|---------------------|
| 1.1 | S | RED: Write failing tests for new JiraIssue fields | Tests exist, import JiraIssue with new fields fails |
| 1.2 | S | GREEN: Add 4 new fields to JiraIssue model | Tests pass, migration created |
| 1.3 | S | RED: Write failing tests for jira_client field extraction | Tests check description, labels, priority, parent in response |
| 1.4 | M | GREEN: Update `get_project_issues()` fields parameter | Tests pass, new fields in API response |
| 1.5 | S | RED: Write failing tests for jira_sync field mapping | Tests verify new fields saved to JiraIssue |
| 1.6 | M | GREEN: Update `_convert_jira_issue_to_dict()` and sync | Tests pass, new fields saved |
| 1.7 | S | REFACTOR: Update JiraIssueFactory with new fields | Factory supports all new fields |
| 1.8 | S | Create and run migration | Migration applies cleanly |

**Files to Modify**:
- `apps/metrics/models/jira.py` (add fields)
- `apps/integrations/services/jira_client.py` (request fields)
- `apps/integrations/services/jira_sync.py` (map fields)
- `apps/metrics/factories.py` (update factory)

---

### Phase 2A: Linkage Donut Widget (TDD) - Effort: M

**Goal**: Show PR-Jira linkage rate on CTO Overview

| Task | Effort | Description | Acceptance Criteria |
|------|--------|-------------|---------------------|
| 2A.1 | S | RED: Write failing tests for linkage chart view | View returns 404 initially |
| 2A.2 | M | GREEN: Create `jira_linkage_chart()` view | Returns chart data JSON |
| 2A.3 | S | RED: Write failing tests for linkage trend calculation | `get_linkage_trend()` not found |
| 2A.4 | M | GREEN: Add `get_linkage_trend()` to dashboard_service | Returns last 4 weeks of linkage rates |
| 2A.5 | S | Create template partial for donut chart | Chart renders with ChartManager |
| 2A.6 | S | Add URL pattern for linkage chart endpoint | HTMX can fetch chart |
| 2A.7 | M | Integrate into CTO Overview template | Widget visible on dashboard |
| 2A.8 | S | REFACTOR: Extract common chart patterns if needed | Clean, DRY code |

**Files to Modify**:
- `apps/metrics/views/chart_views.py` (add view)
- `apps/metrics/services/dashboard_service.py` (add trend function)
- `apps/metrics/urls.py` (add URL)
- `templates/metrics/cto_overview.html` (add widget)
- `templates/metrics/partials/jira_linkage_chart.html` (new)

---

### Phase 2B: Story Point Correlation Chart (TDD) - Effort: L

**Goal**: Compare estimated story points vs actual PR delivery time

| Task | Effort | Description | Acceptance Criteria |
|------|--------|-------------|---------------------|
| 2B.1 | S | RED: Write failing tests for `get_story_point_correlation()` | Function not found |
| 2B.2 | M | GREEN: Implement `get_story_point_correlation()` | Returns buckets with avg_hours, pr_count |
| 2B.3 | S | RED: Write failing tests for SP correlation chart view | View returns 404 |
| 2B.4 | M | GREEN: Create `sp_correlation_chart()` view | Returns grouped bar chart data |
| 2B.5 | S | Create template partial for grouped bar chart | Chart renders correctly |
| 2B.6 | S | Add URL pattern | Endpoint accessible |
| 2B.7 | M | Integrate into dashboard (CTO Overview or Team Analytics) | Widget visible |
| 2B.8 | S | REFACTOR: Optimize query for large datasets | Efficient aggregation |

**Files to Modify**:
- `apps/metrics/services/dashboard_service.py` (add correlation function)
- `apps/metrics/views/chart_views.py` (add view)
- `apps/metrics/urls.py` (add URL)
- `templates/metrics/partials/sp_correlation_chart.html` (new)
- Target template (TBD - CTO Overview or Team Analytics)

---

### Phase 2C: Velocity Trend Chart (TDD) - Effort: M

**Goal**: Show story points completed over time (6 months)

| Task | Effort | Description | Acceptance Criteria |
|------|--------|-------------|---------------------|
| 2C.1 | S | RED: Write failing tests for `get_velocity_trend()` | Function not found |
| 2C.2 | M | GREEN: Implement `get_velocity_trend()` | Returns 6 months of weekly/sprint data |
| 2C.3 | S | RED: Write failing tests for velocity chart view | View returns 404 |
| 2C.4 | M | GREEN: Create `velocity_trend_chart()` view | Returns line chart data |
| 2C.5 | S | Create template partial for velocity line chart | Chart renders correctly |
| 2C.6 | S | Add URL pattern | Endpoint accessible |
| 2C.7 | M | Integrate into Team Analytics page | Widget visible |
| 2C.8 | S | REFACTOR: Handle teams without sprint data (use weeks) | Graceful fallback |

**Files to Modify**:
- `apps/metrics/services/dashboard_service.py` (add velocity function)
- `apps/metrics/views/chart_views.py` (add view)
- `apps/metrics/urls.py` (add URL)
- `templates/metrics/partials/velocity_trend_chart.html` (new)
- `templates/metrics/analytics/team/index.html` (add widget)

---

### Phase 3: LLM Infrastructure Preparation - Effort: S

**Goal**: Prepare data for future LLM-enhanced insights

| Task | Effort | Description | Acceptance Criteria |
|------|--------|-------------|---------------------|
| 3.1 | S | Add linkage trend to `gather_insight_data()` | Trend data in insight context |
| 3.2 | S | Add velocity trend to `gather_insight_data()` | Velocity data in insight context |
| 3.3 | S | Document new fields for future prompt engineering | README updated |

**Note**: Actual LLM prompt changes deferred until real data available for testing.

**Files to Modify**:
- `apps/metrics/services/insight_llm.py` (add trend data)
- `dev/active/jira-pr-correlation/` (documentation)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Jira API rate limits | Low | Medium | Batch requests, respect limits |
| Large teams slow queries | Medium | Medium | Use indexes, optimize aggregations |
| Story point field varies by team | Medium | Low | Already use `customfield_10016` |
| Chart rendering issues | Low | Low | Use proven ChartManager pattern |
| Migration on production data | Low | Medium | Test migration on staging first |

---

## Success Metrics

**Phase 1 (Data)**:
- [ ] JiraIssue has description, labels, priority, parent_issue_key fields
- [ ] New issues synced with all fields populated
- [ ] All tests pass, migration applied

**Phase 2 (Dashboard)**:
- [ ] Linkage donut visible on CTO Overview with trend indicator
- [ ] SP correlation chart shows bucket comparisons
- [ ] Velocity chart shows 6 months of story points
- [ ] All charts responsive with date range selector
- [ ] All E2E tests pass

**Phase 3 (LLM Ready)**:
- [ ] Linkage trend included in insight data
- [ ] Velocity trend included in insight data
- [ ] Documentation complete for future prompt work

---

## Dependencies

- **Existing**: `get_pr_jira_correlation()`, `get_jira_sprint_metrics()` (Phase 2A/2B use these)
- **Migration**: Must run migration before syncing new fields
- **ChartManager**: Use existing pattern from `assets/javascript/charts/`
- **Factory**: Update `JiraIssueFactory` for test data

---

## Test Strategy

All phases follow strict TDD:

1. **RED**: Write failing test that describes expected behavior
2. **GREEN**: Write minimum code to pass test
3. **REFACTOR**: Clean up while keeping tests green

Test files:
- `apps/metrics/tests/models/test_jira_model.py` (Phase 1)
- `apps/metrics/tests/services/test_jira_metrics.py` (extend existing)
- `apps/metrics/tests/views/test_chart_views.py` (Phase 2)
- `tests/e2e/jira-charts.spec.ts` (E2E for Phase 2)
