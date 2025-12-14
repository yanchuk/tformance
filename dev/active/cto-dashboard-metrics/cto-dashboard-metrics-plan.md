# CTO Dashboard Metrics - Implementation Plan

Last Updated: 2025-12-14

## Executive Summary

Add the 5 high-value reports from the Team Dashboard to the CTO Dashboard, providing CTOs with comprehensive visibility into team performance, code quality, and process compliance.

## Current State

### CTO Dashboard (cto_overview.html)
| Section | Purpose |
|---------|---------|
| Key Metrics Cards | PRs merged, cycle time, AI %, quality |
| AI Adoption Trend | Weekly AI usage percentage chart |
| Quality by AI Status | AI vs non-AI quality comparison |
| Cycle Time Trend | Weekly cycle time chart |
| Team Breakdown | Per-member metrics table |

### Missing (Available in Team Dashboard)
| Section | Purpose | Views/Templates Already Exist |
|---------|---------|------------------------------|
| Review Time Trend | Time to first code review | Yes |
| PR Size Distribution | PRs by size category | Yes |
| Quality Indicators | Revert/hotfix rates | Yes |
| Reviewer Workload | Review bottlenecks | Yes |
| PRs Missing Jira Links | Process compliance | Yes |

## Proposed Future State

The CTO Dashboard will include all high-value reports with a layout optimized for executive-level insights:

```
Row 1: Key Metrics Cards (unchanged)
Row 2: AI Adoption Trend | Quality by AI Status (unchanged)
Row 3: Cycle Time Trend | Review Time Trend (NEW)
Row 4: PR Size Distribution | Quality Indicators (NEW)
Row 5: Team Breakdown (unchanged)
Row 6: Reviewer Workload (NEW - full width)
Row 7: PRs Missing Jira Links (NEW - actionable list)
```

## Implementation Strategy

**Good News:** All service functions and views already exist. We only need to:
1. Update the CTO dashboard template to add new sections
2. Add E2E tests for the new sections

**No backend changes required.**

## Phase 1: Template Update (Effort: S)

### Tasks

1.1 **Add Review Time Trend section**
- Add card after Cycle Time Trend in same row
- Reuse existing URL: `metrics:chart_review_time`

1.2 **Add PR Size Distribution section**
- Create new row below trends
- Reuse existing URL: `metrics:chart_pr_size`

1.3 **Add Quality Indicators section**
- Same row as PR Size Distribution
- Reuse existing URL: `metrics:cards_revert_rate`

1.4 **Add Reviewer Workload section**
- Full-width row after Team Breakdown
- Reuse existing URL: `metrics:table_reviewer_workload`

1.5 **Add PRs Missing Jira Links section**
- After Reviewer Workload
- Reuse existing URL: `metrics:table_unlinked_prs`

## Phase 2: E2E Testing (Effort: S)

### Tasks

2.1 **Add E2E tests for new CTO dashboard sections**
- Test Review Time Trend visibility
- Test PR Size Distribution visibility
- Test Quality Indicators visibility
- Test Reviewer Workload visibility
- Test PRs Missing Jira Links visibility

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template layout issues | Low | Low | Copy-paste from Team Dashboard |
| Performance impact | Low | Medium | HTMX lazy loading already implemented |
| Test failures | Low | Low | Existing patterns to follow |

## Success Metrics

- [ ] All 5 new sections visible on CTO Dashboard
- [ ] All E2E tests passing
- [ ] No performance regression (page still loads in < 2s)

## Required Resources

- **Code Changes:** 1 template file
- **Tests:** 5 new E2E test cases
- **Effort:** ~30 minutes total

## Dependencies

- Existing service functions (already implemented)
- Existing view functions (already implemented)
- Existing partial templates (already implemented)
