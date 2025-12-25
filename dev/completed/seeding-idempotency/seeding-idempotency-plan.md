# Seeding Idempotency Plan

**Last Updated: 2025-12-25**

## Executive Summary

Make all seeding simulators and factories idempotent for re-runs by implementing the `update_or_create` pattern consistently across the real project seeder. This ensures that running `./scripts/seed_all_oss.sh` multiple times on the same teams won't cause duplicate key constraint violations.

## Current State Analysis

### Already Fixed (update_or_create pattern)
- `JiraIssue` in `jira_simulator.py` (line 279)
- `PRSurvey` in `survey_ai_simulator.py` (line 199)
- `PRSurveyReview` in `survey_ai_simulator.py` (line 256)
- `AIUsageDaily` in `survey_ai_simulator.py` (line 363)

### Have Existence Checks (skip if exists)
- `Team` in `real_project_seeder.py` (lines 233-239)
- `TeamMember` in `real_project_seeder.py` (lines 322-330)
- `PullRequest` in `real_project_seeder.py` (lines 462-469)
- `Commit` in `real_project_seeder.py` (lines 609-611)
- `PRCheckRun` in `real_project_seeder.py` (lines 676-678)
- `WeeklyMetrics` in `real_project_seeder.py` (lines 875-890)

### Missing Idempotency (NEEDS FIX)
- `PRReview` in `real_project_seeder.py` (line 581) - No existence check
- `PRFile` in `real_project_seeder.py` (line 651) - No existence check

## Proposed Future State

All factory calls in the seeding pipeline will either:
1. Use `update_or_create()` pattern (for simulated data that should update on re-runs)
2. Have existence checks before creation (for GitHub-sourced data that shouldn't change)

## Implementation Phases

### Phase 1: Fix PRReview Idempotency (TDD)
- Add existence check before `PRReviewFactory` call
- Use unique constraint: `(team, pull_request, github_review_id)`

### Phase 2: Fix PRFile Idempotency (TDD)
- Add existence check before `PRFileFactory` call
- Use unique constraint: `(pull_request, filename)`

### Phase 3: Verification
- Run full seeding script on existing teams
- Verify no duplicate key errors
- Confirm data counts are correct on re-runs

## Risk Assessment

### Low Risk
- Changes are additive (adding checks before factory calls)
- Existing data is preserved (skip pattern vs update pattern)
- Tests already exist for related functionality

### Mitigation
- Write TDD tests before implementation
- Run full test suite after changes
- Test with actual seeding script on sample project

## Success Metrics

1. `./scripts/seed_all_oss.sh` runs without errors on existing teams
2. Second run shows 0 new records for PRs, reviews, commits, files (cache hit)
3. Simulated data (Jira, surveys, AI usage) updates correctly on re-runs
4. All existing tests continue to pass
