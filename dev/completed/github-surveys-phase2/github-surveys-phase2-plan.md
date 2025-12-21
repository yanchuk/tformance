# GitHub Surveys Phase 2 - Implementation Plan

**Last Updated:** 2025-12-13

## Executive Summary

Complete the GitHub survey system with three remaining features:
1. **Trigger Integration** - Wire `post_survey_comment_task` to GitHub webhook on PR merge
2. **Template Styling** - Apply DaisyUI/Tailwind styling to minimal survey templates
3. **Reveal Messages** - Show reviewers if their AI guess was correct (web-based alternative to Slack reveals)

## Current State Analysis

### What's Already Implemented

| Component | Status | Location |
|-----------|--------|----------|
| Token system | Complete | `apps/metrics/services/survey_tokens.py` |
| Survey views | Complete | `apps/web/views.py` |
| GitHub comment service | Complete | `apps/integrations/services/github_comments.py` |
| `post_survey_comment_task` | Complete | `apps/integrations/tasks.py` |
| Skip responded reviewers | Complete | `apps/integrations/tasks.py` |

### What's Missing

1. **Task Trigger**: `post_survey_comment_task` exists but is never called
   - Current: `send_pr_surveys_task` is called on PR merge (Slack surveys)
   - Need: Also call `post_survey_comment_task` on PR merge

2. **Templates**: Minimal HTML without styling
   - `templates/web/surveys/base.html` - empty base
   - `templates/web/surveys/author.html` - unstyled form
   - `templates/web/surveys/reviewer.html` - unstyled form
   - `templates/web/surveys/complete.html` - basic thank you

3. **Reveal Messages**: Only Slack reveals exist
   - `send_reveal_task` sends Slack DMs
   - No web-based reveal for GitHub survey responders

## Proposed Future State

### Task Trigger Flow

```
PR Merged (GitHub webhook)
    │
    ├─► send_pr_surveys_task (existing - Slack DMs)
    │
    └─► post_survey_comment_task (NEW trigger)
            └─► Posts comment with survey links
```

### Template Design

Survey pages with:
- DaisyUI card layout
- Clear PR context (title, author, repo)
- Accessible form controls
- Mobile-responsive design
- Consistent with app branding

### Reveal Flow

```
Author submits response
    │
    └─► For each reviewer who responded:
        ├─► If has slack_user_id: send_reveal_task (Slack DM)
        └─► Update PRSurveyReview.guess_correct in DB

Reviewer views survey_complete page
    │
    └─► If guess_correct is set: Show reveal message
        └─► Display accuracy stats
```

## Implementation Phases

### Phase 1: Task Trigger (Effort: S)

Wire up `post_survey_comment_task` to be called when a PR is merged.

**Location**: `apps/metrics/processors.py:168-186`

**Change**: Add `post_survey_comment_task.delay(pr.id)` alongside `send_pr_surveys_task.delay(pr.id)`

### Phase 2: Template Styling (Effort: M)

Apply DaisyUI/Tailwind styling following `htmx-alpine-flowbite-guidelines` skill.

**Templates to update:**
- `base.html` - Extend app base, add survey-specific styles
- `author.html` - Card with PR info + Yes/No buttons
- `reviewer.html` - Card with quality rating + AI guess
- `complete.html` - Success message with optional reveal

### Phase 3: Reveal Messages (Effort: M)

Show web-based reveal after reviewer submits if author has already responded.

**Changes:**
- Update `complete.html` to conditionally show reveal
- Pass reveal data from `survey_submit` view to template
- Display accuracy stats

## Detailed Tasks

### Phase 1: Task Trigger

#### Task 1.1: Add GitHub Survey Trigger (TDD)
- **Location**: `apps/metrics/processors.py`
- **Change**: Import and call `post_survey_comment_task.delay(pr.id)`
- **Test**: `apps/metrics/tests/test_processors.py`
- **Acceptance Criteria**:
  - When PR is merged, both tasks are dispatched
  - GitHub task is independent of Slack integration
  - Failure of one doesn't affect the other

#### Task 1.2: Add Team Setting for Survey Channel (Optional)
- **Location**: `apps/teams/models.py` or `apps/integrations/models.py`
- **Field**: `survey_channel = CharField(choices=["github", "slack", "both"], default="both")`
- **Acceptance Criteria**:
  - Can configure which channel(s) to use
  - Default is "both" for backward compatibility

### Phase 2: Template Styling

#### Task 2.1: Update base.html
- Extend `web/base.html` or create standalone
- Add survey-specific container styling
- Include HTMX/Alpine if needed

#### Task 2.2: Style author.html
- DaisyUI card with PR context
- Two prominent buttons (Yes/No)
- Loading state on submit
- Mobile responsive

#### Task 2.3: Style reviewer.html
- DaisyUI card with PR context
- Quality rating (3 options with icons)
- AI guess (Yes/No)
- Form validation
- Mobile responsive

#### Task 2.4: Style complete.html
- Success message with checkmark
- Optional reveal section
- Link back to dashboard (if logged in)

### Phase 3: Reveal Messages

#### Task 3.1: Update survey_submit View
- After recording reviewer response, check if author responded
- If yes, calculate `guess_correct`
- Pass reveal data to redirect/session

#### Task 3.2: Update complete.html for Reveals
- Check if reveal data available
- Show "You guessed correctly!" or "Not quite!"
- Display accuracy stats
- Match Slack reveal message tone

#### Task 3.3: Handle Author-First vs Reviewer-First
- If author hasn't responded yet, no reveal shown
- When author responds later, update all `PRSurveyReview.guess_correct`
- Consider: async notification? (out of scope for now)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template doesn't match app style | Medium | Low | Follow existing patterns in `templates/web/` |
| Reveal timing confusion | Medium | Medium | Clear messaging about when reveals appear |
| Two tasks both fail | Low | Medium | Independent error handling, logging |

## Success Metrics

1. **Task trigger works** - GitHub comment appears on merged PRs
2. **Templates are styled** - Match app design, mobile responsive
3. **Reveals work** - Reviewers see result after submitting

## Dependencies

- DaisyUI/Tailwind (already in project)
- HTMX/Alpine.js (already in project)
- `htmx-alpine-flowbite-guidelines` skill for patterns

## Frontend Guidelines Reference

From `htmx-alpine-flowbite-guidelines` skill:

### Form Pattern
```html
<form x-data="{ submitting: false }"
      @submit="submitting = true"
      hx-post="/submit">
  <button type="submit"
          :disabled="submitting"
          :class="{ 'loading': submitting }">
    <span x-show="!submitting">Submit</span>
    <span x-show="submitting">Saving...</span>
  </button>
</form>
```

### Card Pattern
```html
<div class="card bg-base-100 shadow-xl">
  <div class="card-body">
    <h2 class="card-title">Title</h2>
    <p>Content</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Action</button>
    </div>
  </div>
</div>
```

### Button Styles
- Primary action: `btn btn-primary`
- Secondary: `btn btn-secondary`
- Success: `btn btn-success`
- Loading: `btn loading`
