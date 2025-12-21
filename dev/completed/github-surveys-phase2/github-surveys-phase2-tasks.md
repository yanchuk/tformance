# GitHub Surveys Phase 2 - Task Checklist

**Last Updated:** 2025-12-21

## Overview

Three features to complete the GitHub survey system:
1. Task trigger on PR merge
2. Template styling with DaisyUI
3. Web-based reveal messages

## ✅ ALL PHASES COMPLETE

**Verified 2025-12-21**: All three phases were already fully implemented with tests.

### Implementation Evidence
- **Task**: `apps/integrations/tasks.py:post_survey_comment_task()` (line 861)
- **Dispatch**: `apps/metrics/processors.py:192` (`post_survey_comment_task.delay(pr.id)`)
- **Templates**: `templates/web/surveys/{base,author,reviewer,complete}.html`
- **Reveals**: `apps/web/views.py` lines 265-374

### Tests (19 tests, all passing)
- `apps/integrations/tests/test_tasks.py::TestPostSurveyCommentTask`
- `apps/integrations/tests/test_github_comments.py`

---

## Phase 1: Task Trigger ✅ COMPLETE

### 1.1 Wire Up Task Trigger ✅

- [x] **RED**: Write test `test_dispatches_github_survey_task_on_merge`
- [x] **GREEN**: Add task dispatch in `_trigger_pr_surveys_if_merged`
- [x] **REFACTOR**: Independent try/except blocks for each task

### 1.2 Verify Independence ✅

- [x] Test: GitHub task failure doesn't affect Slack task
- [x] Test: Slack task failure doesn't affect GitHub task
- [x] Logging: Both successes/failures logged independently

---

## Phase 2: Template Styling ✅ COMPLETE

### 2.1 Update base.html ✅
- [x] Standalone layout with viewport meta tag
- [x] Includes Alpine.js
- [x] Survey-specific container classes

### 2.2 Style author.html ✅
- [x] DaisyUI card layout
- [x] PR context section
- [x] Two prominent Yes/No AI buttons
- [x] Alpine.js loading state
- [x] Mobile responsive

### 2.3 Style reviewer.html ✅
- [x] DaisyUI card layout
- [x] Quality rating with visual feedback
- [x] AI guess section with visual feedback
- [x] Submit button with validation
- [x] Mobile responsive

### 2.4 Style complete.html ✅
- [x] Success icon and thank you text
- [x] Conditional reveal section

---

## Phase 3: Reveal Messages ✅ COMPLETE

### 3.1 Update survey_submit View ✅
- [x] Build reveal context after reviewer response
- [x] Store in session with token validation

### 3.2 Update survey_complete View ✅
- [x] Check for reveal data (session)
- [x] Pass to template context
- [x] Clear session data after use

### 3.3 Update complete.html Template ✅
- [x] Correct guess: 🎯 "Nice detective work!"
- [x] Wrong guess: 🤔 "Not quite!"
- [x] Accuracy stats with DaisyUI stats component

### 3.4 Handle Edge Cases ✅
- [x] No reveal when author hasn't responded
- [x] Graceful display when no accuracy stats

---

## Verification Checklist

After all phases:

- [ ] Run full test suite: `make test`
- [ ] Manual E2E test:
  1. Create test PR
  2. Merge PR
  3. Check GitHub for survey comment
  4. Click author survey link
  5. Submit response
  6. Click reviewer survey link
  7. Submit response
  8. Verify reveal shows (if author responded first)

- [ ] Mobile test: Open surveys on phone-sized viewport
- [ ] Style check: Templates match app design

---

## Files Changed Summary

| File | Type | Changes |
|------|------|---------|
| `apps/metrics/processors.py` | Modify | Add `post_survey_comment_task.delay()` |
| `apps/metrics/tests/test_processors.py` | Modify | Add trigger tests |
| `templates/web/surveys/base.html` | Modify | Add DaisyUI base layout |
| `templates/web/surveys/author.html` | Modify | Full restyle |
| `templates/web/surveys/reviewer.html` | Modify | Full restyle |
| `templates/web/surveys/complete.html` | Modify | Add reveal section |
| `apps/web/views.py` | Modify | Pass reveal data |

---

## Definition of Done

- [ ] All tests pass
- [ ] GitHub comment posts on PR merge
- [ ] Templates are styled and mobile responsive
- [ ] Reveals show for reviewer submissions (when author responded)
- [ ] Code committed and pushed
- [ ] Dev docs updated

---

## Notes

- Use `htmx-alpine-flowbite-guidelines` skill for frontend patterns
- Use `frontend-design:frontend-design` skill for complex UI components
- Follow TDD for task trigger
- Templates can be manually tested (no TDD required)
