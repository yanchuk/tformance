# Team Analytics Fixes - Tasks

**Last Updated:** 2025-12-24

## Phase 1: Debug & Fix Avatar Display [S] - COMPLETE

- [x] Check `get_team_breakdown()` returns correct `avatar_url` for Polar members
- [x] Verify template renders `<img>` tag correctly
- [x] Test GitHub avatar URL format works (`https://avatars.githubusercontent.com/u/{id}?s=80`)
- [x] ~~Check for CSS issues hiding avatars~~ (Not needed - avatars were working)

## Phase 2: Add Table Sorting [M] - COMPLETE

### 2.1 Update Service Layer (TDD)
- [x] Write failing tests for `get_team_breakdown()` with sort params
- [x] Add `sort_by` and `order` parameters to function signature
- [x] Implement sorting logic with field mapping
- [x] Default sort: `prs_merged` descending (most active first)

### 2.2 Update View
- [x] Write failing tests for view with sort query params
- [x] Parse `sort` and `order` from `request.GET`
- [x] Validate sort field against allowed list
- [x] Pass sort params to service and context

### 2.3 Update Template
- [x] Add `{% load pr_list_tags %}` for `sort_url`
- [x] Add `hx-get` and `hx-target` to column headers
- [x] Add sort indicator (▲/▼) based on current sort
- [x] Add `cursor-pointer hover:bg-base-300` styling

## Phase 3: Add User Links to PR List [S] - COMPLETE

### 3.1 Update Service
- [x] Add `member_id` to returned dicts in `get_team_breakdown()`

### 3.2 Update Template
- [x] Wrap member name in `<a>` tag
- [x] Build URL: `{% url 'metrics:pr_list' %}?author={{ row.member_id }}`
- [x] Add `target="_blank" rel="noopener"` for new tab
- [x] Style as link: `class="link link-hover text-primary"`

## Phase 4: Fix Review Distribution Empty State [S] - N/A

- [x] ~~Check if `PRSurveyReview` exists for Polar team~~ (No surveys for Polar)
- [x] Empty state already shows "No review data for this period" with helpful message

## Verification - COMPLETE

- [x] Test on Polar team page with 30-day filter
- [x] Verify avatars display for all team members
- [x] Verify sorting works on all columns
- [x] Verify clicking name opens PR list filtered by author in new tab
- [x] Verify Review Distribution shows proper empty state

## Test Results

- Service tests: 13 passed (5 new + 8 existing)
- View tests: 97 passed (6 new + 91 existing)
- Total: 110 tests passing

## Files Modified

1. `apps/metrics/services/dashboard_service.py` - Added sorting and member_id
2. `apps/metrics/views/chart_views.py` - Added sort param handling
3. `templates/metrics/partials/team_breakdown_table.html` - Sortable headers + user links
4. `apps/metrics/tests/dashboard/test_team_breakdown.py` - 5 new tests
5. `apps/metrics/tests/test_chart_views.py` - 6 new tests
