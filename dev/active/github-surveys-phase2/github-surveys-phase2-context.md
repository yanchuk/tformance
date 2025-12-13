# GitHub Surveys Phase 2 - Context Document

**Last Updated:** 2025-12-13

## Key Files

### Files to Modify

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/metrics/processors.py:168-186` | PR webhook processing | Add `post_survey_comment_task.delay()` |
| `templates/web/surveys/base.html` | Survey base template | Add DaisyUI layout |
| `templates/web/surveys/author.html` | Author survey form | Style with cards, buttons |
| `templates/web/surveys/reviewer.html` | Reviewer survey form | Style with cards, rating UI |
| `templates/web/surveys/complete.html` | Completion page | Add reveal section |
| `apps/web/views.py:277-296` | Survey submit view | Pass reveal data |

### Reference Files (Read Only)

| File | Purpose | Useful Patterns |
|------|---------|-----------------|
| `apps/integrations/services/slack_surveys.py:205-280` | Reveal message text | Copy message wording |
| `apps/integrations/tasks.py:400-475` | `send_reveal_task` | Reveal logic pattern |
| `.claude/skills/htmx-alpine-flowbite-guidelines/SKILL.md` | Frontend patterns | DaisyUI/HTMX examples |
| `templates/web/pages/dashboard.html` | Existing styled page | Design reference |

## Current Templates (Minimal)

### author.html
```html
{% extends "web/surveys/base.html" %}
{% block title %}Author Survey{% endblock %}
{% block content %}
  <h1>Author Survey</h1>
  <p>Did you use AI assistance for this pull request?</p>
  <form method="post" action="{% url 'web:survey_submit' token=token %}">
    {% csrf_token %}
    <button type="submit" name="ai_assisted" value="true">Yes</button>
    <button type="submit" name="ai_assisted" value="false">No</button>
  </form>
{% endblock %}
```

### reviewer.html
```html
{% extends "web/surveys/base.html" %}
{% block title %}Reviewer Survey{% endblock %}
{% block content %}
  <h1>Reviewer Survey</h1>
  <form method="post" action="{% url 'web:survey_submit' token=token %}">
    {% csrf_token %}
    <input type="hidden" name="reviewer_id" value="{{ reviewer.id }}">
    <!-- Quality rating -->
    <p>How would you rate the code quality?</p>
    <button type="submit" name="quality_rating" value="1">Could be better</button>
    <button type="submit" name="quality_rating" value="2">OK</button>
    <button type="submit" name="quality_rating" value="3">Super</button>
    <!-- AI guess -->
    <p>Was this PR AI-assisted?</p>
    <button type="submit" name="ai_guess" value="true">Yes</button>
    <button type="submit" name="ai_guess" value="false">No</button>
  </form>
{% endblock %}
```

## Target Template Designs

### Author Survey (Styled)

```html
{% extends "web/surveys/base.html" %}
{% block content %}
<div class="min-h-screen flex items-center justify-center bg-base-200 p-4">
  <div class="card bg-base-100 shadow-xl max-w-lg w-full">
    <div class="card-body">
      <!-- PR Context -->
      <div class="text-sm text-base-content/70 mb-2">
        {{ survey.pull_request.repository.full_name }}
      </div>
      <h2 class="card-title text-xl">{{ survey.pull_request.title }}</h2>

      <!-- Question -->
      <p class="text-lg mt-4">Did you use AI assistance for this PR?</p>

      <!-- Form -->
      <form method="post"
            action="{% url 'web:survey_submit' token=token %}"
            x-data="{ submitting: false }"
            @submit="submitting = true">
        {% csrf_token %}
        <div class="card-actions justify-center gap-4 mt-6">
          <button type="submit"
                  name="ai_assisted"
                  value="true"
                  :disabled="submitting"
                  class="btn btn-primary btn-lg">
            Yes, I used AI
          </button>
          <button type="submit"
                  name="ai_assisted"
                  value="false"
                  :disabled="submitting"
                  class="btn btn-outline btn-lg">
            No AI assistance
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
```

### Reviewer Survey (Styled)

```html
{% extends "web/surveys/base.html" %}
{% block content %}
<div class="min-h-screen flex items-center justify-center bg-base-200 p-4">
  <div class="card bg-base-100 shadow-xl max-w-lg w-full">
    <div class="card-body">
      <!-- PR Context -->
      <div class="text-sm text-base-content/70 mb-2">
        {{ survey.pull_request.repository.full_name }}
      </div>
      <h2 class="card-title text-xl">{{ survey.pull_request.title }}</h2>
      <p class="text-sm">by {{ survey.pull_request.author.display_name }}</p>

      <!-- Form -->
      <form method="post"
            action="{% url 'web:survey_submit' token=token %}"
            x-data="{ quality: null, aiGuess: null, submitting: false }"
            @submit="submitting = true">
        {% csrf_token %}
        <input type="hidden" name="reviewer_id" value="{{ reviewer.id }}">

        <!-- Quality Rating -->
        <div class="mt-6">
          <p class="font-semibold mb-3">How would you rate the code quality?</p>
          <div class="flex gap-2 flex-wrap">
            <label class="btn" :class="{ 'btn-warning': quality === '1' }">
              <input type="radio" name="quality_rating" value="1" x-model="quality" class="hidden">
              Could be better
            </label>
            <label class="btn" :class="{ 'btn-info': quality === '2' }">
              <input type="radio" name="quality_rating" value="2" x-model="quality" class="hidden">
              OK
            </label>
            <label class="btn" :class="{ 'btn-success': quality === '3' }">
              <input type="radio" name="quality_rating" value="3" x-model="quality" class="hidden">
              Super
            </label>
          </div>
        </div>

        <!-- AI Guess -->
        <div class="mt-6">
          <p class="font-semibold mb-3">Was this PR AI-assisted?</p>
          <div class="flex gap-2">
            <label class="btn flex-1" :class="{ 'btn-primary': aiGuess === 'true' }">
              <input type="radio" name="ai_guess" value="true" x-model="aiGuess" class="hidden">
              Yes, I think so
            </label>
            <label class="btn flex-1" :class="{ 'btn-secondary': aiGuess === 'false' }">
              <input type="radio" name="ai_guess" value="false" x-model="aiGuess" class="hidden">
              No, I don't think so
            </label>
          </div>
        </div>

        <!-- Submit -->
        <div class="card-actions justify-center mt-8">
          <button type="submit"
                  :disabled="!quality || !aiGuess || submitting"
                  :class="{ 'loading': submitting }"
                  class="btn btn-primary btn-lg">
            Submit
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
```

### Complete Page with Reveal

```html
{% extends "web/surveys/base.html" %}
{% block content %}
<div class="min-h-screen flex items-center justify-center bg-base-200 p-4">
  <div class="card bg-base-100 shadow-xl max-w-lg w-full">
    <div class="card-body text-center">
      <!-- Success Icon -->
      <div class="text-6xl mb-4">✓</div>
      <h2 class="card-title justify-center text-2xl">Thanks!</h2>
      <p class="text-base-content/70">Your response has been recorded.</p>

      {% if reveal %}
      <!-- Reveal Section -->
      <div class="divider"></div>
      <div class="mt-4">
        {% if reveal.guess_correct %}
        <div class="text-4xl mb-2">🎯</div>
        <p class="text-lg font-semibold text-success">Nice detective work!</p>
        <p>You guessed correctly - this PR <strong>{{ reveal.was_ai|yesno:"was,wasn't" }}</strong> AI-assisted.</p>
        {% else %}
        <div class="text-4xl mb-2">🤔</div>
        <p class="text-lg font-semibold text-warning">Not quite!</p>
        <p>This PR <strong>{{ reveal.was_ai|yesno:"was,wasn't" }}</strong> AI-assisted.</p>
        {% endif %}

        <!-- Accuracy Stats -->
        <div class="stats shadow mt-4">
          <div class="stat">
            <div class="stat-title">Your Accuracy</div>
            <div class="stat-value">{{ reveal.accuracy.percentage|floatformat:0 }}%</div>
            <div class="stat-desc">{{ reveal.accuracy.correct }}/{{ reveal.accuracy.total }} correct</div>
          </div>
        </div>
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
```

## Reveal Message Content (from Slack)

### Correct Guess
```
🎯 Nice detective work, {reviewer_name}!

You guessed correctly - this PR *was/wasn't* AI-assisted.

Your accuracy: {correct}/{total} ({percentage}%)
```

### Wrong Guess
```
🤔 Not quite, {reviewer_name}!

This PR *was/wasn't* AI-assisted.

Your accuracy: {correct}/{total} ({percentage}%)
```

## Key Code Patterns

### Current PR Merge Trigger (processors.py)

```python
def _trigger_pr_surveys_if_merged(pr: PullRequest, action: str, is_merged: bool) -> None:
    """Trigger PR survey task if the PR was just merged."""
    if action == "closed" and is_merged:
        try:
            from apps.integrations.tasks import send_pr_surveys_task
            send_pr_surveys_task.delay(pr.id)
            logger.debug(f"Dispatched send_pr_surveys_task for PR {pr.id}")
        except Exception as e:
            logger.error(f"Failed to dispatch send_pr_surveys_task for PR {pr.id}: {e}")
```

### Target Pattern (Add GitHub Task)

```python
def _trigger_pr_surveys_if_merged(pr: PullRequest, action: str, is_merged: bool) -> None:
    """Trigger PR survey tasks if the PR was just merged."""
    if action == "closed" and is_merged:
        # Trigger Slack surveys
        try:
            from apps.integrations.tasks import send_pr_surveys_task
            send_pr_surveys_task.delay(pr.id)
            logger.debug(f"Dispatched send_pr_surveys_task for PR {pr.id}")
        except Exception as e:
            logger.error(f"Failed to dispatch send_pr_surveys_task: {e}")

        # Trigger GitHub comment survey
        try:
            from apps.integrations.tasks import post_survey_comment_task
            post_survey_comment_task.delay(pr.id)
            logger.debug(f"Dispatched post_survey_comment_task for PR {pr.id}")
        except Exception as e:
            logger.error(f"Failed to dispatch post_survey_comment_task: {e}")
```

## Edge Cases

1. **Author responds before reviewer submits** - Reveal shown on complete page
2. **Reviewer submits before author** - No reveal shown (guess_correct is None)
3. **Both GitHub and Slack responses** - Skip logic already handles this
4. **Token expired** - 410 Gone response (already implemented)
5. **User not authorized** - 403 Forbidden (already implemented)

## Testing Considerations

### Task Trigger Tests
- Test both tasks dispatched on PR merge
- Test independence (one fails, other still runs)
- Mock both task.delay() calls

### Template Tests (Manual)
- Mobile responsive check
- Form validation works
- Loading states display
- Reveal section shows/hides correctly
