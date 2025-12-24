# Team Analytics Page Fixes

**Last Updated:** 2025-12-24

## Executive Summary

Fix three issues on the Team Analytics page (`/app/metrics/analytics/team/`):
1. **Missing GitHub avatars** - Avatar URLs are generated but may not be displaying properly
2. **No table sorting** - Add sortable columns like the PR list table
3. **Missing user links** - Clicking team member names should open PR list filtered by that author
4. **Empty Review Distribution** - Investigate why this block shows no data for Polar

## Current State Analysis

### Architecture
- **Page:** `templates/metrics/analytics/team.html`
- **Team Breakdown HTMX:** `{% url 'metrics:table_breakdown' %}` → `views.team_breakdown_table`
- **Data Service:** `dashboard_service.get_team_breakdown()`
- **Template Partial:** `templates/metrics/partials/team_breakdown_table.html`

### Current Data Flow
1. Team Analytics page loads with HTMX container for team breakdown
2. Container triggers `hx-get` to `/tables/breakdown/?days=X`
3. View calls `get_team_breakdown()` which returns list of dicts:
   - `member_name`, `avatar_url`, `initials`, `prs_merged`, `avg_cycle_time`, `ai_pct`
4. Avatar URL is computed as: `https://avatars.githubusercontent.com/u/{github_id}?s=80`

### Current Issues

#### 1. Avatar URLs
- Service correctly generates avatar URLs from `github_id`
- Template has proper img tag with conditional placeholder
- **Need to verify:** actual HTML output and whether images load

#### 2. No Sorting
- PR list table has sorting via `sort_url` template tag and HTMX
- Team breakdown table has no sorting - just static table
- Default order is `order_by("author__display_name")` - alphabetical

#### 3. No User Links
- Member names are plain text, not links
- PR list page supports `author` filter parameter
- Need to add links that open PR list filtered by author

#### 4. Empty Review Distribution
- Chart endpoint: `{% url 'metrics:chart_review_distribution' %}`
- Service: `dashboard_service.get_review_distribution()`
- **Possible cause:** No `PRSurveyReview` data for Polar (surveys may not be enabled)

## Proposed Changes

### Phase 1: Fix Avatar Display (S)
- Verify avatar URLs are being passed to template
- Check if any CSS issues prevent display
- Test with Polar team data

### Phase 2: Add Sorting (M)
- Add `sort` and `order` query params to `team_breakdown_table` view
- Update `get_team_breakdown()` to accept sort parameters:
  - `prs_merged` (default, desc) - Most active first
  - `avg_cycle_time` (asc/desc)
  - `ai_pct` (asc/desc)
  - `member_name` (asc)
- Add sortable column headers with HTMX in template
- Reuse `sort_url` pattern from PR list

### Phase 3: Add User Links (S)
- Wrap member name in anchor tag
- Link to PR list with `?author=<member_id>` filter
- Add `target="_blank"` for new tab
- Need to include `member_id` in data returned by service

### Phase 4: Investigate Review Distribution (S)
- Check if `PRSurveyReview` data exists for Polar team
- If no data, show appropriate empty state message
- Review distribution requires survey responses which may not exist

## Implementation Tasks

### Task 1: Debug Avatar Display
- [ ] Add debug logging to view to confirm avatar_url values
- [ ] Check browser network tab for image loading failures
- [ ] Verify github_id values in database for Polar members

### Task 2: Add Sorting to Service
- [ ] Update `get_team_breakdown()` signature: add `sort_by`, `order` params
- [ ] Map sort fields to ORM fields
- [ ] Default: `sort_by='prs_merged'`, `order='desc'`

### Task 3: Add Sorting to View
- [ ] Parse `sort` and `order` from request.GET
- [ ] Validate allowed sort fields
- [ ] Pass to service and return in context

### Task 4: Update Template with Sortable Headers
- [ ] Add HTMX attributes to `<th>` elements
- [ ] Show sort indicator (▲/▼) for current sort
- [ ] Use existing `sort_url` template tag

### Task 5: Add Member ID to Service Response
- [ ] Include `member_id` in returned dicts
- [ ] Add `github_username` for URL construction

### Task 6: Add Links to Template
- [ ] Wrap member name in `<a>` tag
- [ ] Build URL: `{% url 'metrics:pr_list' %}?author={{ row.member_id }}`
- [ ] Add `target="_blank" rel="noopener"`

### Task 7: Fix Review Distribution Empty State
- [ ] Check if PRSurveyReview data exists for team
- [ ] If no surveys, show informative empty state
- [ ] Don't show "loading" skeleton indefinitely

## Technical Details

### Sort Field Mapping
```python
SORT_FIELDS = {
    'prs_merged': 'prs_merged',
    'cycle_time': 'avg_cycle_time',
    'ai_pct': 'ai_pct',
    'name': 'author__display_name',
}
```

### PR List Author Filter
The PR list view already supports `author` filter:
```python
if author := request.GET.get("author"):
    filters["author"] = int(author)
```

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing dashboard | Medium | TDD with existing tests |
| N+1 queries from new joins | Low | Already optimized with aggregation |
| Sort performance on large teams | Low | Data is aggregated, not raw PRs |

## Success Metrics

- [ ] All team members show GitHub avatars (if they have github_id)
- [ ] Table is sortable by all 4 columns
- [ ] Default sort is PRs Merged descending (most active first)
- [ ] Clicking member name opens PR list filtered to that author
- [ ] Review Distribution shows meaningful empty state if no data
