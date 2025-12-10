# Core Data Models Implementation Tasks

**Last Updated:** 2025-12-10

## Overview

Track progress on Phase 1: Core Data Models implementation. Follow TDD workflow for each model.

**STATUS: ✅ COMPLETE - All 9 models implemented with 166 tests**

---

## Phase 1.1: App Setup & TeamMember Model ✅ COMPLETE

### Setup
- [x] Create `apps/metrics/` app with `make uv run 'pegasus startapp metrics'`
- [x] Add `"apps.metrics.apps.MetricsConfig"` to `PROJECT_APPS` in settings.py
- [x] Verify app loads with `make test`

### TeamMember Model (TDD)
- [x] **RED**: Write test for TeamMember model creation
- [x] **GREEN**: Create TeamMember model with basic fields
- [x] **REFACTOR**: Ensure model follows project conventions

- [x] **RED**: Write test for TeamMember unique constraints (github_id, email per team)
- [x] **GREEN**: Add UniqueConstraint with conditions
- [x] **REFACTOR**: Add validation and __str__ method

- [x] **RED**: Write test for TeamMember.for_team manager filtering
- [x] **GREEN**: Verify BaseTeamModel inheritance works
- [x] **REFACTOR**: Add indexes, verbose_names, help_text

### Admin
- [x] Create TeamMemberAdmin with list_display, search_fields
- [x] Verify admin loads at /admin/metrics/teammember/

### Migration
- [x] Run `make migrations` and verify migration file
- [x] Run `make migrate` to apply

**Tests:** 21 tests passing

---

## Phase 1.2: GitHub Models (PullRequest, PRReview, Commit) ✅ COMPLETE

### PullRequest Model (TDD)
- [x] **RED**: Write test for PullRequest creation
- [x] **GREEN**: Create PullRequest model with all fields
- [x] **REFACTOR**: Add Meta options, indexes

- [x] **RED**: Write test for unique constraint (team, github_pr_id, github_repo)
- [x] **GREEN**: Add UniqueConstraint
- [x] **REFACTOR**: Add __str__, verbose_name

- [x] **RED**: Write test for PullRequest.author ForeignKey to TeamMember
- [x] **GREEN**: Add ForeignKey with SET_NULL
- [x] **REFACTOR**: Add related_name

### PRReview Model (TDD)
- [x] **RED**: Write test for PRReview creation linked to PullRequest
- [x] **GREEN**: Create PRReview model
- [x] **REFACTOR**: Add choices for state field

- [x] **RED**: Write test for PRReview.reviewer ForeignKey
- [x] **GREEN**: Add reviewer ForeignKey to TeamMember
- [x] **REFACTOR**: Add related_names

### Commit Model (TDD)
- [x] **RED**: Write test for Commit creation
- [x] **GREEN**: Create Commit model
- [x] **REFACTOR**: Add unique constraint on github_sha

- [x] **RED**: Write test for Commit.pull_request optional ForeignKey
- [x] **GREEN**: Add nullable ForeignKey to PullRequest
- [x] **REFACTOR**: Add related_name 'commits'

### Admin
- [x] Create PullRequestAdmin with list_display, list_filter, inlines
- [x] Create PRReviewAdmin
- [x] Create CommitAdmin

### Migration
- [x] Run `make migrations`
- [x] Run `make migrate`

**Tests:** 50 tests passing (21 + 20 + 15 + 15 - 21 = 50 new)

---

## Phase 1.3: Jira Models ✅ COMPLETE

### JiraIssue Model (TDD)
- [x] **RED**: Write test for JiraIssue creation
- [x] **GREEN**: Create JiraIssue model with all fields
- [x] **REFACTOR**: Add Meta options

- [x] **RED**: Write test for unique constraint (team, jira_id)
- [x] **GREEN**: Add UniqueConstraint
- [x] **REFACTOR**: Add __str__ with jira_key

- [x] **RED**: Write test for JiraIssue.assignee ForeignKey
- [x] **GREEN**: Add ForeignKey to TeamMember
- [x] **REFACTOR**: Add related_name 'jira_issues', indexes

### Admin
- [x] Create JiraIssueAdmin with list_display, search_fields

### Migration
- [x] Run `make migrations`
- [x] Run `make migrate`

**Tests:** 23 tests passing

---

## Phase 1.4: AI Usage & Survey Models ✅ COMPLETE

### AIUsageDaily Model (TDD)
- [x] **RED**: Write test for AIUsageDaily creation
- [x] **GREEN**: Create AIUsageDaily model
- [x] **REFACTOR**: Add source choices

- [x] **RED**: Write test for unique constraint (team, member, date, source)
- [x] **GREEN**: Add UniqueConstraint
- [x] **REFACTOR**: Add Meta ordering by date desc, indexes

### PRSurvey Model (TDD)
- [x] **RED**: Write test for PRSurvey creation
- [x] **GREEN**: Create PRSurvey model with OneToOne to PullRequest
- [x] **REFACTOR**: Add null handling for author_ai_assisted

- [x] **RED**: Write test for PRSurvey OneToOne relationship
- [x] **GREEN**: Verify OneToOneField works correctly
- [x] **REFACTOR**: Add related_name 'survey', indexes

### PRSurveyReview Model (TDD)
- [x] **RED**: Write test for PRSurveyReview creation
- [x] **GREEN**: Create PRSurveyReview model
- [x] **REFACTOR**: Add quality_rating choices

- [x] **RED**: Write test for unique constraint (survey, reviewer)
- [x] **GREEN**: Add UniqueConstraint
- [x] **REFACTOR**: Add indexes

### Admin
- [x] Create AIUsageDailyAdmin with date_hierarchy
- [x] Create PRSurveyAdmin with inline PRSurveyReview
- [x] Create PRSurveyReviewAdmin

### Migration
- [x] Run `make migrations`
- [x] Run `make migrate`

**Tests:** 55 tests passing (23 + 13 + 19)

---

## Phase 1.5: Weekly Metrics Model ✅ COMPLETE

### WeeklyMetrics Model (TDD)
- [x] **RED**: Write test for WeeklyMetrics creation
- [x] **GREEN**: Create WeeklyMetrics model with all fields
- [x] **REFACTOR**: Add default values

- [x] **RED**: Write test for unique constraint (team, member, week_start)
- [x] **GREEN**: Add UniqueConstraint
- [x] **REFACTOR**: Add indexes for common queries

- [x] **RED**: Write test for WeeklyMetrics null vs 0 handling
- [x] **GREEN**: Verify null averages, 0 counts behavior
- [x] **REFACTOR**: Add verbose_names, help_text for admin clarity

### Admin
- [x] Create WeeklyMetricsAdmin with fieldsets, date_hierarchy

### Migration
- [x] Run `make migrations`
- [x] Run `make migrate`

**Tests:** 27 tests passing

---

## Integration & Polish ✅ COMPLETE

### Cross-Model Tests
- [x] Test creating full data flow: TeamMember → PullRequest → PRReview → PRSurvey
- [x] Test team isolation (data from team A not visible to team B)
- [x] Test cascade deletes work correctly
- [x] Test for_team manager filters correctly for all models

### Documentation
- [x] Update core-models-context.md with final state
- [x] Mark all tasks complete in this file

---

## Testing Summary ✅ ALL COMPLETE

### Unit Tests (per model)
- [x] `test_models.py::TestTeamMemberModel` - 21 tests
- [x] `test_models.py::TestPullRequestModel` - 20 tests
- [x] `test_models.py::TestPRReviewModel` - 15 tests
- [x] `test_models.py::TestCommitModel` - 15 tests
- [x] `test_models.py::TestJiraIssueModel` - 23 tests
- [x] `test_models.py::TestAIUsageDailyModel` - 23 tests
- [x] `test_models.py::TestPRSurveyModel` - 13 tests
- [x] `test_models.py::TestPRSurveyReviewModel` - 19 tests
- [x] `test_models.py::TestWeeklyMetricsModel` - 27 tests

**Total: 166 metrics model tests**

### Test Command
```bash
make test ARGS='apps.metrics.tests'  # Run all metrics tests
make test                             # Run all project tests (254)
```

---

## Blockers & Notes

- No blockers encountered
- All TDD cycles completed successfully with subagent delegation
- Comprehensive indexes added for query performance
- Admin inlines provide good UX for related data

---

## Completion Checklist ✅ ALL COMPLETE

Before marking Phase 1 as complete:

- [x] All 9 models created and migrated
- [x] All tests passing (`make test ARGS='apps.metrics.tests'`) - 166 tests
- [x] Code formatted and linted (`make ruff`)
- [x] Admin interface functional for all models
- [x] Team isolation verified (for_team manager tests)
- [x] No migration conflicts
- [x] Context and tasks docs updated

---

## Summary

**Phase 1: Core Data Models is COMPLETE**

| Metric | Value |
|--------|-------|
| Models Created | 9 |
| Model Tests | 166 |
| Total Project Tests | 254 |
| Migrations | 9 |
| Admin Classes | 9 |
| Admin Inlines | 3 |

Next: Phase 2 (GitHub Integration) or Phase 3 (Jira Integration)
