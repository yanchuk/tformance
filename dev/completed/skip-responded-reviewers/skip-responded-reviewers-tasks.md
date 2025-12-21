# Skip Responded Reviewers - Task Checklist

**Last Updated:** 2025-12-21

## Overview

Prevent duplicate survey notifications by checking if reviewer/author has already responded via another channel.

## ✅ FEATURE ALREADY IMPLEMENTED

**Verified 2025-12-21**: This feature was already fully implemented with tests.

### Implementation Location
- `apps/integrations/tasks.py:send_pr_surveys_task()` (lines 426-470)

### Tests (5 tests, all passing)
- `apps/integrations/tests/test_tasks.py::TestSkipRespondedReviewers`

## Phase 1: Core Implementation ✅ COMPLETE

### 1.1 Add Reviewer Skip Check ✅

- [x] **RED**: Write failing test `test_skip_reviewer_already_responded_via_github`
- [x] **GREEN**: Add check using batch query for `responded_reviewer_ids`
- [x] **REFACTOR**: Added `reviewers_skipped` counter in return dict

### 1.2 Add Author Skip Check ✅

- [x] **RED**: Write failing test `test_skip_author_already_responded_via_github`
- [x] **GREEN**: Add check using `survey.has_author_responded()`
- [x] **REFACTOR**: Added `author_skipped` to return dict

### 1.3 Verify Positive Cases Still Work ✅

- [x] **TEST**: `test_sends_dm_when_reviewer_has_not_responded`
- [x] **TEST**: `test_sends_dm_when_prsurveyreview_exists_but_not_responded`
- [x] **TEST**: `test_task_returns_correct_counts`

## Phase 2: Enhanced Observability (Optional)

### 2.1 Structured Logging

- [ ] Add structured log fields for monitoring
  - `survey_id`, `pr_id`, `reviewer_id`, `skip_reason`

- [ ] Add Sentry breadcrumbs
  - Before each DM attempt, add breadcrumb with reviewer info

### 2.2 Metrics Collection

- [ ] Track skip rate over time
  - Could use existing metrics patterns or simple logging

## Verification Checklist

After implementation:

- [ ] Run full test suite: `make test`
- [ ] Run specific tests: `make test ARGS='apps.integrations.tests.test_tasks'`
- [ ] Manual test:
  1. Create PR with reviewer
  2. Post GitHub comment (via task or manually)
  3. Respond via GitHub web form
  4. Trigger Slack task
  5. Verify NO Slack DM received

## Files Changed

| File | Change |
|------|--------|
| `apps/integrations/tasks.py` | Add skip checks in `send_pr_surveys_task` |
| `apps/integrations/tests/test_tasks.py` | Add 5+ new tests |

## Definition of Done

- [ ] All new tests pass
- [ ] All existing tests pass
- [ ] Reviewer who responded via GitHub does NOT get Slack DM
- [ ] Author who responded via GitHub does NOT get Slack DM
- [ ] Task returns skip counts for observability
- [ ] Skip events are logged at INFO level
- [ ] Code reviewed and committed
