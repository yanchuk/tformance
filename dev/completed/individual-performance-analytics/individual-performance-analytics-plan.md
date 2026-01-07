# Individual Performance Analytics - Implementation Plan

**Last Updated**: 2026-01-05

## Executive Summary

Enhance the existing Team Performance page (`/app/metrics/analytics/team/`) with a comprehensive individual comparison table. The enhanced table will include additional metrics (PR size, reviews given, review response time), use `effective_is_ai_assisted` for AI detection (instead of survey-based), add team averages for comparison, and display visual deviation indicators.

## Current State Analysis

### Existing Implementation

**Page**: `/app/metrics/analytics/team/` (Team Performance analytics page)

**Current Table Columns** (in `team_breakdown_table.html`):
1. Team Member (avatar + name, link to PRs)
2. PRs Merged (count)
3. Avg Cycle Time (hours)
4. AI-Assisted % (survey-based - often empty)

**Current Service** (`get_team_breakdown()` in `team_metrics.py`):
- Returns: `member_id`, `member_name`, `avatar_url`, `initials`, `prs_merged`, `avg_cycle_time`, `ai_pct`
- AI % is calculated from `PRSurvey.author_ai_assisted` (survey-based)
- Sorting on: `prs_merged`, `cycle_time`, `ai_pct`, `name`

**Current View** (`team_breakdown_table` in `chart_views.py`):
- Validates sort fields and order
- Passes repo filter
- Returns template response with rows, sort, order, days, selected_repo

### Limitations

1. **AI Detection**: Survey-based AI % is often empty (no surveys active)
2. **Missing Metrics**: No reviews given, PR size, review response time
3. **No Comparison**: No team average row for benchmarking
4. **No Visual Indicators**: No highlighting for above/below average performance
5. **No Trends**: No trend arrows showing improvement/decline

## Proposed Future State

### Enhanced Table Structure

| Column | Description | Sortable | Data Source |
|--------|-------------|----------|-------------|
| Employee | Avatar + name (link to PRs) | Name | TeamMember |
| PRs | Count merged | ✓ | PullRequest.state='merged' |
| Cycle Time | Avg hours to merge | ✓ | PullRequest.cycle_time_hours |
| PR Size | Avg lines changed | ✓ | PullRequest (additions + deletions) |
| Reviews | Count given | ✓ | PRReview (by reviewer) |
| Response | Avg hours to first review | ✓ | Calculated from PRReview |
| AI % | % AI-assisted PRs | ✓ | PullRequest.effective_is_ai_assisted |

**Footer Row**: Team averages (highlighted background)

### Visual Indicators

- **Green background**: >20% better than team average
- **Red background**: >20% worse than team average
- **Trend arrows** (Phase 2): ↑ improving, ↓ declining vs previous period

## Implementation Phases

### Phase 1: Service Layer Enhancement (TDD)

**Goal**: Extend `get_team_breakdown()` to return additional metrics

**Tasks**:
1. Write failing tests for new metrics
2. Add PRReview aggregation for reviews_given
3. Add PR size calculation (avg additions + deletions)
4. Add review response time calculation
5. Switch AI % from survey to `effective_is_ai_assisted`
6. Add `get_team_averages()` function
7. Add comparison flags (better/worse/normal vs avg)

### Phase 2: View Layer Updates

**Goal**: Pass team averages and new sort options to template

**Tasks**:
1. Update allowed sort fields
2. Add team averages to context
3. Pass comparison thresholds

### Phase 3: Template Enhancement

**Goal**: Display new columns with responsive design

**Tasks**:
1. Add new column headers with sort functionality
2. Add new data cells with formatting
3. Add Team Average footer row
4. Add conditional CSS classes for highlighting
5. Mobile-responsive column hiding

### Phase 4: Testing & Polish

**Goal**: Ensure quality and responsiveness

**Tasks**:
1. Unit tests for all new service functions
2. Integration tests for view
3. Manual visual verification
4. Mobile responsiveness check

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| N+1 query performance | High | Use batch queries with aggregation |
| Breaking existing functionality | High | TDD approach, comprehensive tests |
| Template complexity | Medium | Keep changes minimal, reuse patterns |
| Empty data scenarios | Medium | Handle nulls gracefully in template |

## Success Metrics

1. Page load time < 500ms with 50 team members
2. All existing tests pass
3. New columns display correctly on desktop and mobile
4. Team averages calculated correctly
5. Color highlighting works for deviation threshold

## Required Resources

### Files to Modify

| File | Changes |
|------|---------|
| `apps/metrics/services/dashboard/team_metrics.py` | Enhance `get_team_breakdown()`, add `get_team_averages()` |
| `apps/metrics/views/chart_views.py` | Update `team_breakdown_table()` view |
| `templates/metrics/partials/team_breakdown_table.html` | Add columns, footer, highlighting |
| `apps/metrics/tests/test_chart_views.py` | Add tests for new functionality |

### Dependencies

- `PullRequest` model with `effective_is_ai_assisted` property
- `PRReview` model for reviewer aggregation
- Existing `_get_merged_prs_in_range()` helper
- DaisyUI table patterns

### Patterns to Reuse

- `apps/metrics/services/dashboard/trend_metrics.py` - For trend calculations
- `apps/metrics/services/dashboard/review_metrics.py` - For review aggregation patterns
- `templates/metrics/partials/reviewer_workload_table.html` - For table styling patterns
