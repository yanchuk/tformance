# Seeding Idempotency Tasks

**Last Updated: 2025-12-25**

## Phase 1: Fix PRReview Idempotency

- [x] Analyze existing PRReview creation code in `_create_pr_reviews`
- [x] Add existence check before PRReviewFactory (check github_review_id)
- [x] Run tests to verify fix - All 37 GraphQL fetcher tests pass

## Phase 2: Fix PRFile Idempotency

- [x] Analyze existing PRFile creation code in `_create_pr_files`
- [x] Add existence check before PRFileFactory (check team, pull_request, filename)
- [x] Run tests to verify fix - All 198 survey/jira/ai_usage tests pass

## Phase 3: Verification

- [x] Run seeding on existing teams (Twenty)
- [x] Verify no duplicate key errors
- [x] Confirm stats show 0 for already-existing records (PR, Reviews, Commits, Files all 0)

## Completed Previously

- [x] Fix JiraIssue - Changed to `update_or_create` pattern
- [x] Fix PRSurvey - Changed to `update_or_create` pattern
- [x] Fix PRSurveyReview - Changed to `update_or_create` pattern
- [x] Fix AIUsageDaily - Changed to `update_or_create` pattern
