# LLM Feedback System - Context

**Last Updated:** 2026-01-02

---

## Key Files

### Existing Models (Reference)

| File | Purpose |
|------|---------|
| `apps/feedback/models.py` | Existing `AIFeedback` model for code issues |
| `apps/metrics/models/surveys.py` | `PRSurvey` and `PRSurveyReview` models |
| `apps/metrics/models/github.py` | `PullRequest.llm_summary` JSON field |
| `apps/metrics/models/insights.py` | `DailyInsight` model |

### Templates to Modify

| File | LLM Content Type | Notes |
|------|------------------|-------|
| `templates/metrics/partials/engineering_insights.html` | Engineering Insight | Main dashboard insight card |
| `templates/metrics/pull_requests/partials/expanded_row.html` | PR Summary | Expandable row with LLM analysis |
| `templates/insights/partials/answer_response.html` | Q&A Answer | Response from ask endpoint |
| `templates/insights/partials/ai_summary.html` | AI Summary | Daily summary card |
| `templates/web/app/app_base.html` | N/A | Add floating feedback button |

### Analytics Infrastructure

| File | Purpose |
|------|---------|
| `apps/utils/analytics.py` | `track_event()`, `identify_user()` helpers |
| `templates/web/components/posthog_init.html` | PostHog JS SDK init |

### Services (for context snapshots)

| File | Purpose |
|------|---------|
| `apps/metrics/services/insight_llm.py` | Generates engineering insights |
| `apps/metrics/services/llm_prompts.py` | PR summary prompt builder, `PROMPT_VERSION` |
| `apps/integrations/services/groq_batch.py` | LLM batch processing |

---

## Key Decisions

### 1. Storage Strategy
**Decision:** Store in Django model (`LLMFeedback`) + fire PostHog event
**Rationale:**
- DB storage enables export for prompt tuning
- PostHog events enable real-time dashboards
- Dual approach gives flexibility

### 2. Content Snapshot Scope
**Decision:** Store full LLM output + relevant input context
**Rationale:**
- Essential for prompt engineering iteration
- Enables "replay" of failed cases
- Worth the storage cost for prompt quality

### 3. UI Component Approach
**Decision:** Reusable template partial with Alpine.js + HTMX
**Rationale:**
- Consistent UX across all LLM content
- No page reload on rating
- Easy to maintain single component

### 4. General Feedback
**Decision:** PostHog Surveys (built-in widget)
**Rationale:**
- Zero custom UI needed
- Built-in survey analytics
- Professional widget appearance

### 5. TDD Approach
**Decision:** Strict Red-Green-Refactor for all phases
**Rationale:**
- Ensures test coverage
- Prevents regressions
- Documents expected behavior

---

## HTMX/Alpine.js Integration Patterns

### CRITICAL: Avoid Template-in-Template Issues

When thumbs rating is included in partials that are loaded via HTMX, ensure:

1. **Alpine.js components must re-initialize** after HTMX swap:
```javascript
// In htmx.js
htmx.on('htmx:afterSwap', (evt) => {
    if (window.Alpine) {
        Alpine.initTree(evt.detail.target);
    }
});
```

2. **Use `hx-swap-oob` for updating rating state** without full partial reload:
```html
<!-- Rating button sends OOB update to just the button state -->
<button id="thumbs-up-{{ content_id }}" hx-swap-oob="true">...</button>
```

3. **Test HTMX partials in isolation**:
- Create dedicated E2E test for each partial
- Verify component works when loaded via HTMX (not just initial page load)
- Test rating persistence after page navigation

### HTMX Partial Loading Pattern

```html
<!-- Parent template -->
<div id="insight-container"
     hx-get="{% url 'insights:summary' %}"
     hx-trigger="load"
     hx-swap="innerHTML">
  <!-- Loading state -->
</div>

<!-- Partial (includes thumbs rating) -->
<div class="insight-content">
  {{ insight.headline }}
  {% include "feedback/partials/thumbs_rating.html" with content_type="engineering_insight" content_id=insight.id %}
</div>
```

### Alpine.js State Management

```javascript
// Use Alpine store for feedback state that persists across HTMX swaps
Alpine.store('feedback', {
    ratings: {},  // { 'pr_123': 'up', 'insight_456': 'down' }
    setRating(key, value) {
        this.ratings[key] = value;
    },
    getRating(key) {
        return this.ratings[key] || null;
    }
});
```

---

## E2E Testing Strategy

### Priority: Test UI BEFORE Backend Changes

1. **Baseline E2E tests** - Capture current behavior before changes
2. **Feature E2E tests** - Test new thumbs rating functionality
3. **Regression E2E tests** - Ensure existing flows still work

### Test Scenarios

| Scenario | File | Priority |
|----------|------|----------|
| Thumbs rating appears on Engineering Insights | `llm-feedback.spec.ts` | P0 |
| Thumbs rating appears in PR expanded row | `llm-feedback.spec.ts` | P0 |
| Rating click sends request and updates UI | `llm-feedback.spec.ts` | P0 |
| Rating persists after page reload | `llm-feedback.spec.ts` | P0 |
| Comment modal opens after rating | `llm-feedback.spec.ts` | P1 |
| PostHog survey button visible | `llm-feedback.spec.ts` | P1 |
| Rating works in HTMX-loaded partial | `llm-feedback.spec.ts` | P0 |

### E2E Test Template

```typescript
// tests/e2e/llm-feedback.spec.ts
import { test, expect } from '@playwright/test';
import { login, navigateToDashboard } from './helpers';

test.describe('LLM Feedback System', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
        await navigateToDashboard(page);
    });

    test('thumbs rating appears on engineering insights', async ({ page }) => {
        // Wait for HTMX-loaded insight
        await page.waitForSelector('[data-testid="engineering-insight"]');

        // Verify thumbs buttons exist
        await expect(page.locator('[data-testid="thumbs-up"]')).toBeVisible();
        await expect(page.locator('[data-testid="thumbs-down"]')).toBeVisible();
    });

    test('rating click updates UI and persists', async ({ page }) => {
        const thumbsUp = page.locator('[data-testid="thumbs-up"]').first();

        await thumbsUp.click();

        // Wait for HTMX response
        await page.waitForResponse(resp => resp.url().includes('/feedback/submit'));

        // Verify visual state change
        await expect(thumbsUp).toHaveClass(/text-success/);

        // Reload and verify persistence
        await page.reload();
        await page.waitForSelector('[data-testid="thumbs-up"]');
        await expect(thumbsUp).toHaveClass(/text-success/);
    });
});
```

---

## Data Flow

### Feedback Submission Flow

```
User clicks thumbs up
    ↓
Alpine.js updates local state (instant feedback)
    ↓
HTMX sends POST to /feedback/submit_llm/
    ↓
View validates and creates LLMFeedback record
    ↓
View fires PostHog event (async)
    ↓
View returns success response
    ↓
HTMX updates button state (confirm)
```

### Content Snapshot Capture

```
PR Expanded Row loads
    ↓
Template includes thumbs_rating partial
    ↓
Partial receives pr.llm_summary as context
    ↓
On rating click, snapshot is sent:
    {
        content_snapshot: pr.llm_summary,
        input_context: { pr_id, title, body },
        prompt_version: pr.llm_summary_version
    }
```

---

## PostHog Survey Configuration

### Survey Setup (in PostHog Dashboard)

1. **Create Survey**: "General Product Feedback"
2. **Questions**:
   - Type: Multiple choice (Bug / Missing Feature / Suggestion / Other)
   - Description: Open text
3. **Targeting**: All authenticated users
4. **Display**: Popup (triggered by button click)

### Button Placement

```html
<!-- In app_base.html -->
<button id="posthog-feedback-btn"
        class="fixed bottom-4 right-4 btn btn-primary btn-circle shadow-lg z-50"
        onclick="posthog.renderSurvey('survey-id')">
    <svg><!-- Feedback icon --></svg>
</button>
```

---

## Migration Strategy

### Add to Existing Feedback App

Since `apps/feedback/` already exists with `AIFeedback` model, we add `LLMFeedback` to the same app:

```python
# apps/feedback/models.py
class AIFeedback(BaseTeamModel):
    # Existing model for AI code issues
    ...

class LLMFeedback(BaseTeamModel):
    # New model for LLM content feedback
    ...
```

### Migration Command

```bash
python manage.py makemigrations feedback --name add_llm_feedback_model
python manage.py migrate
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/a/<team_slug>/feedback/llm/submit/` | Submit thumbs rating |
| GET | `/a/<team_slug>/feedback/llm/<content_type>/<content_id>/` | Get existing rating |
| POST | `/a/<team_slug>/feedback/llm/<pk>/comment/` | Add/update comment |

### Request/Response

```python
# POST /feedback/llm/submit/
{
    "content_type": "pr_summary",
    "content_id": 123,
    "rating": true,
    "content_snapshot": {...},
    "input_context": {...},
    "prompt_version": "5.0.0"
}

# Response
{
    "id": 456,
    "rating": true,
    "created_at": "2026-01-02T10:30:00Z"
}
```

---

## Related Documentation

- `prd/PROMPT-ENGINEERING.md` - LLM prompt best practices
- `prd/AI-DETECTION-TESTING.md` - AI detection patterns
- `dev/active/posthog-analytics-enhancement/` - PostHog integration plan
- `CLAUDE.md` - Coding guidelines
