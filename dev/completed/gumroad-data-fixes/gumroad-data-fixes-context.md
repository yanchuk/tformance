# Gumroad Data Fixes - Context

**Last Updated:** 2025-12-23
**Status:** COMPLETED

## Overview

Fixed Gumroad seeded data to properly display on dashboards. Data was seeded from GitHub but needed adjustments for demo purposes.

## Implementation State

### COMPLETED - All fixes implemented and verified

1. **Date Range Fix** - Shifted all dates forward 68 days
2. **Copilot Limit** - Limited to top 5 users
3. **Devin Detection** - Added patterns for Devin AI and autofix-ci[bot]
4. **AI Co-Author Parsing** - Management command created and run
5. **Iteration Metrics** - Management command created and run

## Key Files Modified

### Created
| File | Purpose |
|------|---------|
| `apps/metrics/management/commands/fix_gumroad_dates.py` | Shifts demo data dates forward by N days |
| `apps/metrics/management/commands/parse_ai_coauthors.py` | Re-parses commit messages for AI co-authors |
| `apps/metrics/management/commands/calculate_iteration_metrics.py` | Calculates review_rounds, fix_response, etc. |

### Modified
| File | Change |
|------|--------|
| `apps/metrics/services/dashboard_service.py:865` | Added `limit: int = 5` parameter to `get_copilot_by_member()` |
| `apps/metrics/services/ai_patterns.py` | Added Devin + autofix patterns, bumped `PATTERNS_VERSION` to "1.1.0" |

## Key Decisions Made

1. **Date Shift vs Reseed**: Chose to shift existing data forward (68 days) rather than re-fetching from GitHub. Faster and preserves existing survey/review data.

2. **Copilot Limit Location**: Added limit parameter to service function `get_copilot_by_member()` rather than template filter. More reusable and testable.

3. **AI Pattern Updates**: Added Devin bot patterns and autofix-ci[bot] to handle automated commits. Incremented PATTERNS_VERSION to enable future reprocessing.

4. **Iteration Metrics Calculation**: Calculated from existing review/commit data rather than re-fetching:
   - `review_rounds` = distinct reviewer count
   - `commits_after_first_review` = commits with timestamp > first review
   - `total_comments` = reviews with non-empty body
   - `avg_fix_response_hours` = avg time between review and next commit

## Commands Run (All Successful)

```bash
# Shift dates forward 68 days
python manage.py fix_gumroad_dates --team Gumroad
# Result: 224 PRs, 911 commits, 161 reviews, 843 AI usage records shifted

# Parse AI co-authors from commit messages
python manage.py parse_ai_coauthors --team Gumroad
# Result: Found 1 commit with autofix-ci[bot] co-author

# Calculate iteration metrics for merged PRs
python manage.py calculate_iteration_metrics --team Gumroad
# Result: Updated 96 PRs with iteration metrics
```

## Verification Results

| Dashboard | Metric | Before | After |
|-----------|--------|--------|-------|
| `/app/` | PRs Merged (7d) | 0 | 43 |
| `/app/` | Avg Cycle Time | — | 70.4h |
| `/app/` | AI-Assisted | — | 69% |
| `/app/metrics/overview/` | PRs Merged (7d) | 0 | 92 |
| `/app/metrics/overview/` | Copilot Users | 13 | 5 (top) |
| `/app/metrics/overview/` | Iteration Metrics | Empty | 0.7 rounds, 16.5h response |
| `/app/metrics/overview/` | Team Breakdown | Empty | 17 members |
| `/app/metrics/overview/` | Reviewer Workload | 1 | 6 reviewers |

## Database State After Fixes

```
Gumroad Team:
- Total PRs: 224 (96 merged)
- Date Range: Now Nov 3 - Dec 23, 2025 (shifted +68 days)
- Iteration Metrics: 96 PRs populated
- AI Co-Authors: 1 commit with autofix detected
- Copilot Users: 13 total, showing top 5
```

## No Migrations Needed

All fixes use existing model fields. No schema changes required.

## Testing

Commands are idempotent and safe to re-run. All include `--dry-run` option for preview.

## Files to Review Before Commit

```bash
git status
# Modified:
#   apps/metrics/services/dashboard_service.py
#   apps/metrics/services/ai_patterns.py
# New:
#   apps/metrics/management/commands/fix_gumroad_dates.py
#   apps/metrics/management/commands/parse_ai_coauthors.py
#   apps/metrics/management/commands/calculate_iteration_metrics.py
```
