# Skip Responded Reviewers - Task Checklist

**Last Updated:** 2025-12-13

## Overview

Prevent duplicate survey notifications by checking if reviewer/author has already responded via another channel.

## Phase 1: Core Implementation

### 1.1 Add Reviewer Skip Check

- [ ] **RED**: Write failing test `test_skip_reviewer_already_responded_via_github`
  - Create PRSurveyReview with `responded_at` set
  - Call task, assert `send_dm` NOT called for that reviewer
  - Assert logs contain "already responded"

- [ ] **GREEN**: Add check in `send_pr_surveys_task`
  - Location: `apps/integrations/tasks.py:350` (before `create_reviewer_survey`)
  - Query: `PRSurveyReview.objects.filter(survey=survey, reviewer=reviewer, responded_at__isnull=False).exists()`
  - If exists: log skip, continue to next reviewer

- [ ] **REFACTOR**: Add `reviewers_skipped` counter
  - Initialize `reviewers_skipped = 0` at top of function
  - Increment on each skip
  - Include in return dict

### 1.2 Add Author Skip Check

- [ ] **RED**: Write failing test `test_skip_author_already_responded_via_github`
  - Set `survey.author_ai_assisted = True` (or False)
  - Call task, assert `send_dm` NOT called for author
  - Assert logs contain "already responded"

- [ ] **GREEN**: Add check before author DM
  - Location: `apps/integrations/tasks.py:325` (before author DM block)
  - Check: `survey.author_ai_assisted is not None`
  - If True: log skip, set `author_skipped = True`

- [ ] **REFACTOR**: Add `author_skipped` to return dict
  - Initialize `author_skipped = False`
  - Set True when skipped
  - Include in return dict

### 1.3 Verify Positive Cases Still Work

- [ ] **TEST**: `test_sends_dm_when_reviewer_has_not_responded`
  - No PRSurveyReview exists yet
  - Task creates PRSurveyReview AND sends DM

- [ ] **TEST**: `test_sends_dm_when_prsurveyreview_exists_but_not_responded`
  - PRSurveyReview exists with `responded_at=None`
  - Task should STILL send DM (they created entry via Slack but didn't respond)

- [ ] **TEST**: `test_task_returns_correct_counts`
  - 3 reviewers: 1 responded, 1 not responded, 1 no slack_user_id
  - Assert: `reviewers_sent=1, reviewers_skipped=1`

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
