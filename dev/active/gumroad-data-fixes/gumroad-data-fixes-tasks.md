# Gumroad Data Fixes - Task Checklist

**Last Updated:** 2025-12-23
**Status:** COMPLETED

## Phase 1: Date Range Fix (High Priority)

- [x] Create management command `fix_gumroad_dates.py`
  - [x] Shift all PR `merged_at` dates forward by ~68 days
  - [x] Shift `pr_created_at` dates proportionally
  - [x] Shift `first_review_at` dates proportionally
  - [x] Update related review `submitted_at` timestamps
  - [x] Update related commit `committed_at` timestamps
  - [x] Update `WeeklyMetrics` `week_start` dates
  - [x] Update `AIUsageDaily` `date` field
- [x] Run command: `python manage.py fix_gumroad_dates --team Gumroad`
- [x] Verify: `/app/` shows non-zero PRs Merged on 7-day view

## Phase 2: Copilot Display Limit (High Priority)

- [x] Update `get_copilot_by_member()` in `dashboard_service.py`
  - [x] Add `limit: int = 5` parameter
  - [x] Apply limit after ordering by suggestions
- [x] Verify: Copilot Usage by Member shows only top 5 users

## Phase 3: Devin Bot Detection (Medium Priority)

- [x] Update `ai_patterns.py`:
  - [x] Add Devin bot usernames to `AI_REVIEWER_BOTS`
  - [x] Add Devin signature patterns to `AI_SIGNATURE_PATTERNS`
  - [x] Add Devin co-author pattern to `AI_CO_AUTHOR_PATTERNS`
  - [x] Add autofix-ci[bot] patterns
  - [x] Increment `PATTERNS_VERSION` to "1.1.0"

## Phase 4: AI Co-Author Parsing (Medium Priority)

- [x] Create management command `parse_ai_coauthors.py`
  - [x] Iterate all commits with empty `ai_co_authors`
  - [x] Re-run `parse_co_authors()` on commit messages
  - [x] Update `is_ai_assisted` and `ai_co_authors` fields
  - [x] Log statistics of detected co-authors
- [x] Run command: `python manage.py parse_ai_coauthors --team Gumroad`
- [x] Result: Found 1 commit with autofix-ci[bot] co-author

## Phase 5: Iteration Metrics Population (Medium Priority)

- [x] Create management command `calculate_iteration_metrics.py`
  - [x] For each merged PR with reviews:
    - [x] Calculate `review_rounds` (distinct author review count)
    - [x] Calculate `commits_after_first_review`
    - [x] Calculate `total_comments` from review comments
    - [x] Calculate `avg_fix_response_hours` (avg time between review and next commit)
- [x] Run command: `python manage.py calculate_iteration_metrics --team Gumroad`
- [x] Result: Updated 96 PRs with iteration metrics

## Phase 6: Verification

- [x] Dashboard `/app/` on 7-day view:
  - [x] PRs Merged shows 43 (was 0)
  - [x] Avg Cycle Time shows 70.4h
  - [x] AI-Assisted shows 69%
- [x] Dashboard `/app/metrics/overview/` on 7-day view:
  - [x] PRs Merged: 92
  - [x] Copilot Usage shows top 5 only (Trita, Brent, STEFAN, Jai, Paul)
  - [x] Iteration Metrics shows data (0.7 rounds, 16.5h fix response)
  - [x] AI Detection shows 4.4% (4 PRs detected from content)
  - [x] Team Breakdown shows 17 active members
  - [x] Reviewer Workload shows 6 reviewers
  - [x] File Category Breakdown shows distribution
  - [x] CI/CD Pass Rate shows 93.3%

## Files Created/Modified

### Created
- `apps/metrics/management/commands/fix_gumroad_dates.py`
- `apps/metrics/management/commands/parse_ai_coauthors.py`
- `apps/metrics/management/commands/calculate_iteration_metrics.py`

### Modified
- `apps/metrics/services/dashboard_service.py` - Added limit parameter to get_copilot_by_member()
- `apps/metrics/services/ai_patterns.py` - Added Devin and autofix patterns, bumped version to 1.1.0
