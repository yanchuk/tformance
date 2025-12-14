# High-Value Reports Implementation Plan

Last Updated: 2025-12-14

## Executive Summary

Add 5 high-value reports to the Team Dashboard leveraging existing data in the `PullRequest`, `PRReview`, and `PRSurveyReview` models. These reports directly address CTO pain points identified in community research (#2: code review processes, quality visibility, bottleneck identification).

## Current State Analysis

### Existing Dashboard Components
- Key Metrics Cards (PRs merged, cycle time, quality rating, AI-assisted %)
- Cycle Time Trend (line chart)
- Review Distribution (bar chart - who reviews most)
- AI Detective Leaderboard (table)
- Recent Pull Requests (table with AI status)

### Available Data (Not Yet Surfaced)
| Field | Model | Description |
|-------|-------|-------------|
| `review_time_hours` | PullRequest | Time to first review |
| `additions`, `deletions` | PullRequest | Lines changed |
| `is_revert`, `is_hotfix` | PullRequest | Quality flags |
| `jira_key` | PullRequest | Jira link status |
| `submitted_at`, `reviewer` | PRReview | GitHub review data |

## Proposed Future State

### New Reports
| Report | CTO Pain Point | Data Source | Difficulty |
|--------|----------------|-------------|------------|
| Review Time Trend | #2 - Code review bottlenecks | `review_time_hours` | Low |
| PR Size Distribution | Quality visibility | `additions + deletions` | Low |
| Revert/Hotfix Rate | Quality tracking | `is_revert`, `is_hotfix` | Low |
| Unlinked PRs Table | Process compliance | `jira_key` empty | Low |
| Reviewer Workload | Bottleneck identification | `PRReview` count | Medium |

### Dashboard Layout Updates
Team Dashboard will gain:
1. Two-column row: Review Time Trend + PR Size Distribution
2. Two-column row: Revert/Hotfix Rate + Unlinked PRs
3. Reviewer Workload (full width, after Review Distribution)

## Implementation Phases

### Phase 1: Review Time Trend (Low - 1 PR)
Service function + view + template. Nearly identical to existing `get_cycle_time_trend()`.

### Phase 2: PR Size Distribution (Low - 1 PR)
Categorize PRs by size (XS/S/M/L/XL), return counts for bar chart.

### Phase 3: Revert/Hotfix Rate (Low - 1 PR)
Count and percentage of reverts/hotfixes over time trend.

### Phase 4: Unlinked PRs Table (Low - 1 PR)
Table of PRs missing `jira_key`, similar to Recent PRs table.

### Phase 5: Reviewer Workload (Medium - 1 PR)
Reviews per team member with workload indicator (low/normal/high).

### Phase 6: Dashboard Integration (1 PR)
Add all components to team_dashboard.html with HTMX lazy loading.

### Phase 7: E2E Tests (1 PR)
Add Playwright tests for new dashboard sections.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Empty data states | High | Low | Design empty state UI for each component |
| Performance with large datasets | Medium | Medium | Use DB aggregation, limit results |
| Layout crowding | Low | Medium | Use collapsible sections, clean spacing |

## Success Metrics

- All 5 new reports visible on Team Dashboard
- E2E tests pass for each new section
- Page load time under 2s with lazy loading
- Empty states display meaningful messages

## Technical Notes

### Service Function Pattern
```python
def get_review_time_trend(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get review time trend by week."""
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    weekly_data = (
        prs.annotate(week=TruncWeek("merged_at"))
        .values("week")
        .annotate(avg_review_time=Avg("review_time_hours"))
        .order_by("week")
    )
    return [{"week": e["week"], "value": e["avg_review_time"] or 0.0} for e in weekly_data]
```

### PR Size Categories
| Category | Lines Changed |
|----------|---------------|
| XS | 1-10 |
| S | 11-50 |
| M | 51-200 |
| L | 201-500 |
| XL | 500+ |

### View Pattern
```python
@login_and_team_required
def review_time_chart(request: HttpRequest) -> HttpResponse:
    start_date, end_date = get_date_range_from_request(request)
    data = dashboard_service.get_review_time_trend(request.team, start_date, end_date)
    chart_data = chart_formatters.format_time_series(data)
    return TemplateResponse(request, "metrics/partials/review_time_chart.html", {"chart_data": chart_data})
```

## Dependencies

- No new Python packages required
- No database migrations needed
- All data already available in existing models
