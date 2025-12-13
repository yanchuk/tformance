# GitHub Surveys Phase 2 - Task Checklist

**Last Updated:** 2025-12-13

## Overview

Three features to complete the GitHub survey system:
1. Task trigger on PR merge
2. Template styling with DaisyUI
3. Web-based reveal messages

---

## Phase 1: Task Trigger (Effort: S)

### 1.1 Wire Up Task Trigger

- [ ] **RED**: Write test `test_dispatches_github_survey_task_on_merge`
  - Location: `apps/metrics/tests/test_processors.py`
  - Mock `post_survey_comment_task.delay`
  - Assert called with PR id when `action="closed"` and `is_merged=True`

- [ ] **GREEN**: Add task dispatch in `_trigger_pr_surveys_if_merged`
  - Location: `apps/metrics/processors.py:168-186`
  - Import `post_survey_comment_task`
  - Call `.delay(pr.id)` after Slack task dispatch
  - Independent try/except block

- [ ] **REFACTOR**: Consider extracting task dispatch helper
  - Only if code gets repetitive

### 1.2 Verify Independence

- [ ] Test: GitHub task failure doesn't affect Slack task
- [ ] Test: Slack task failure doesn't affect GitHub task
- [ ] Logging: Both successes/failures logged independently

---

## Phase 2: Template Styling (Effort: M)

### 2.1 Update base.html

- [ ] Extend from appropriate app base or create standalone
- [ ] Add viewport meta tag for mobile
- [ ] Include Alpine.js (if not in parent)
- [ ] Add survey-specific container classes

### 2.2 Style author.html

- [ ] DaisyUI card layout
- [ ] PR context section (repo name, PR title)
- [ ] Clear question text
- [ ] Two prominent buttons (Yes AI / No AI)
- [ ] Alpine.js loading state on submit
- [ ] Mobile responsive (test on 375px width)

### 2.3 Style reviewer.html

- [ ] DaisyUI card layout
- [ ] PR context section (repo, title, author)
- [ ] Quality rating section
  - [ ] Three styled options (Could be better / OK / Super)
  - [ ] Visual feedback on selection (Alpine.js)
- [ ] AI guess section
  - [ ] Two styled options (Yes / No)
  - [ ] Visual feedback on selection
- [ ] Submit button
  - [ ] Disabled until both selections made
  - [ ] Loading state on submit
- [ ] Mobile responsive

### 2.4 Style complete.html

- [ ] Success message with icon
- [ ] Thank you text
- [ ] Conditional reveal section (if reveal data present)
- [ ] Optional: Link to dashboard

---

## Phase 3: Reveal Messages (Effort: M)

### 3.1 Update survey_submit View

- [ ] After `record_reviewer_response()`:
  - [ ] Check if `survey.author_ai_assisted is not None`
  - [ ] If yes, calculate `guess_correct`
  - [ ] Build reveal context dict
  - [ ] Store in session or pass via query param

- [ ] Reveal context structure:
  ```python
  reveal = {
      'guess_correct': True/False,
      'was_ai': True/False,
      'accuracy': {
          'correct': int,
          'total': int,
          'percentage': float
      }
  }
  ```

### 3.2 Update survey_complete View

- [ ] Check for reveal data (session or query param)
- [ ] Pass to template context
- [ ] Clear session data after use (if using session)

### 3.3 Update complete.html Template

- [ ] Add `{% if reveal %}` conditional section
- [ ] Correct guess display:
  - [ ] 🎯 icon
  - [ ] "Nice detective work!" message
  - [ ] "You guessed correctly" text
- [ ] Wrong guess display:
  - [ ] 🤔 icon
  - [ ] "Not quite!" message
  - [ ] Actual AI status text
- [ ] Accuracy stats display:
  - [ ] DaisyUI stats component
  - [ ] Percentage, correct/total

### 3.4 Handle Edge Cases

- [ ] No reveal when author hasn't responded
- [ ] Graceful display when no accuracy stats (first response)
- [ ] Test: Author responds after reviewer (no web reveal, OK)

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
