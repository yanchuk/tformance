# Skip Responded Reviewers - Implementation Plan

**Last Updated:** 2025-12-13

## Executive Summary

Prevent duplicate survey requests when both GitHub and Slack survey channels are active. When a reviewer has already responded via one channel (GitHub web survey), skip sending them a Slack DM, and vice versa.

## Problem Statement

Currently, the GitHub survey system (`post_survey_comment_task`) and Slack survey system (`send_pr_surveys_task`) operate independently:

1. **GitHub**: Posts PR comment with @mentions linking to web survey forms
2. **Slack**: Sends DMs to reviewers with inline survey buttons

When both are enabled, a reviewer may receive **both** notifications and be asked to respond twice. This is:
- Annoying for users
- Potentially confusing (which response counts?)
- Wasteful of notification channels

## Current State Analysis

### Survey Flow Today

```
PR Merged
    │
    ├─► post_survey_comment_task (GitHub)
    │   └─► Creates PRSurvey → Posts comment → @mentions all reviewers
    │
    └─► send_pr_surveys_task (Slack)
        └─► Gets same PRSurvey → Creates PRSurveyReview → Sends DM to all reviewers
```

### Key Observations

1. **PRSurvey** is shared between channels (OneToOne with PullRequest)
2. **PRSurveyReview** tracks each reviewer's response with `responded_at` timestamp
3. GitHub task posts comment BEFORE any response
4. Slack task sends DMs without checking existing responses
5. Both tasks run independently on PR merge

### Relevant Code Locations

| File | Function | Current Behavior |
|------|----------|------------------|
| `apps/integrations/tasks.py:350-367` | `send_pr_surveys_task` | Sends DM to ALL reviewers with `slack_user_id` |
| `apps/web/views.py:235-276` | `_handle_reviewer_submission` | Records response, sets `responded_at` |
| `apps/metrics/models.py:716-720` | `PRSurveyReview.responded_at` | Timestamp when reviewer submitted |

## Proposed Solution

### Option A: Skip Reviewers Who Already Responded (RECOMMENDED)

Add a check in `send_pr_surveys_task` before sending each DM:

```python
# In send_pr_surveys_task, before sending DM:
existing_response = PRSurveyReview.objects.filter(
    survey=survey,
    reviewer=reviewer,
    responded_at__isnull=False
).exists()

if existing_response:
    logger.info(f"Skipping {reviewer.display_name} - already responded via GitHub")
    continue
```

**Pros:**
- Minimal code change (~5 lines)
- Respects first response regardless of channel
- No UI changes needed
- Backward compatible

**Cons:**
- Doesn't prevent initial notification from both channels
- Only helps when Slack task runs AFTER GitHub response

### Enhancement: Also Skip Author

Apply same logic to author DM:

```python
if survey.author_ai_assisted is not None:
    logger.info(f"Skipping author - already responded via GitHub")
else:
    # Send author DM
```

## Implementation Phases

### Phase 1: Core Implementation (Effort: S)

1. Add response check for reviewers in `send_pr_surveys_task`
2. Add response check for author in `send_pr_surveys_task`
3. Add logging for skipped notifications
4. Write tests

### Phase 2: Metrics & Observability (Effort: S)

1. Track skip counts in task return value
2. Add Sentry breadcrumbs for debugging
3. Log channel preference per user (which they respond to first)

## Detailed Tasks

### Task 1.1: Add Reviewer Skip Check
- **Location:** `apps/integrations/tasks.py:350`
- **Change:** Check `PRSurveyReview.responded_at` before creating/sending
- **Acceptance Criteria:**
  - Reviewer who responded via GitHub does NOT get Slack DM
  - Logged with reason "already responded"
  - Task return includes `reviewers_skipped` count

### Task 1.2: Add Author Skip Check
- **Location:** `apps/integrations/tasks.py:325`
- **Change:** Check `survey.author_ai_assisted` before sending author DM
- **Acceptance Criteria:**
  - Author who responded via GitHub does NOT get Slack DM
  - Logged with reason "already responded"
  - Task return includes `author_skipped` boolean

### Task 1.3: Write Tests
- **Location:** `apps/integrations/tests/test_tasks.py`
- **Tests:**
  - `test_skip_reviewer_who_already_responded_via_github`
  - `test_skip_author_who_already_responded_via_github`
  - `test_send_dm_to_reviewer_who_has_not_responded`
  - `test_task_returns_skipped_counts`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Race condition: both tasks run simultaneously | Medium | Low | Check is idempotent, worst case: duplicate notification |
| Survey not found in skip check | Low | Low | Use `.filter().exists()` not `.get()` |
| Breaking existing Slack flow | Low | High | TDD approach, thorough testing |

## Success Metrics

1. **Reduction in duplicate notifications** - Reviewers only get surveyed once
2. **Response rate maintained** - Skip logic doesn't reduce survey responses
3. **No regressions** - All existing survey tests pass

## Dependencies

- PRSurveyReview model (exists)
- `responded_at` field (exists, indexed)
- GitHub survey system (implemented in prior phases)

## Future Considerations

1. **User preference setting**: Let users choose preferred channel
2. **Team-level setting**: Configure `survey_channel` as "github", "slack", or "both"
3. **Rate limiting between channels**: Delay Slack task to give GitHub responses time
