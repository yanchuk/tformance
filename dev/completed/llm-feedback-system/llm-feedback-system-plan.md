# LLM Feedback System - Implementation Plan

**Last Updated:** 2026-01-02

---

## Executive Summary

Implement a comprehensive feedback system for AI-generated content in Tformance. This enables:
1. **Thumbs up/down rating** for all LLM-generated content (insights, PR summaries, Q&A)
2. **Full snapshot storage** for prompt engineering iteration
3. **PostHog Survey integration** for general product feedback
4. **Analytics events** alongside database storage

**Approach:** Strict TDD (Red-Green-Refactor) for all implementation phases.

---

## Current State Analysis

### Existing Infrastructure

| Component | Status | Location |
|-----------|--------|----------|
| `AIFeedback` model | Exists | `apps/feedback/models.py` - for AI code issues |
| `PRSurvey` model | Exists | `apps/metrics/models/surveys.py` - author AI disclosure |
| PostHog SDK | Configured | Python + JS, `apps/utils/analytics.py` |
| Engineering Insights | Exists | `templates/metrics/partials/engineering_insights.html` |
| PR LLM Summary | Exists | `templates/metrics/pull_requests/partials/expanded_row.html` |
| Q&A System | Exists | `templates/insights/partials/answer_response.html` |

### LLM Content Types Requiring Feedback

| Content Type | Template Location | Data Source |
|--------------|-------------------|-------------|
| Engineering Insights | `engineering_insights.html` | `insight_llm.py` |
| AI Summary Card | `insights/partials/ai_summary.html` | `insights:summary` view |
| Q&A Answers | `insights/partials/answer_response.html` | `insights:ask` view |
| PR Summary | `expanded_row.html` | `PullRequest.llm_summary` JSON |

---

## Proposed Future State

### New Model: `LLMFeedback`

```python
class LLMFeedback(BaseTeamModel):
    """Feedback on LLM-generated content for prompt engineering."""

    CONTENT_TYPE_CHOICES = [
        ("engineering_insight", "Engineering Insight"),
        ("pr_summary", "PR Summary"),
        ("qa_answer", "Q&A Answer"),
        ("ai_detection", "AI Detection"),
    ]

    content_type = models.CharField(max_length=30, choices=CONTENT_TYPE_CHOICES)
    rating = models.BooleanField(help_text="True=thumbs up, False=thumbs down")
    comment = models.TextField(blank=True)

    # Snapshots for prompt engineering
    content_snapshot = models.JSONField(help_text="LLM output at feedback time")
    input_context = models.JSONField(null=True, blank=True)
    prompt_version = models.CharField(max_length=20, blank=True)

    # Relations
    pull_request = models.ForeignKey("metrics.PullRequest", null=True, blank=True, on_delete=SET_NULL)
    daily_insight = models.ForeignKey("metrics.DailyInsight", null=True, blank=True, on_delete=SET_NULL)

    # Who submitted
    submitted_by = models.ForeignKey("metrics.TeamMember", null=True, on_delete=SET_NULL)
    user = models.ForeignKey("users.CustomUser", on_delete=CASCADE)
```

### UI Component: Reusable Thumbs Rating

A reusable template partial that can be included anywhere LLM content appears:

```html
{% include "feedback/partials/thumbs_rating.html" with content_type="pr_summary" content_id=pr.id %}
```

### PostHog Survey: General Feedback

Floating button on all authenticated pages triggering PostHog's built-in survey widget.

---

## Implementation Phases (TDD)

### Phase 1: Data Layer (Est. 4 hours)

**Goal:** Create `LLMFeedback` model with full test coverage.

| Task | Effort | TDD Phase |
|------|--------|-----------|
| 1.1 Write model tests | S | RED |
| 1.2 Create LLMFeedback model | S | GREEN |
| 1.3 Write migration | S | GREEN |
| 1.4 Add Django admin | S | GREEN |
| 1.5 Write factory | S | GREEN |
| 1.6 Write export command tests | M | RED |
| 1.7 Create export command | M | GREEN |
| 1.8 Refactor/cleanup | S | REFACTOR |

### Phase 2: API Layer (Est. 3 hours)

**Goal:** Create views for submitting and retrieving feedback.

| Task | Effort | TDD Phase |
|------|--------|-----------|
| 2.1 Write view tests | M | RED |
| 2.2 Create submit_feedback view | M | GREEN |
| 2.3 Create get_feedback view | S | GREEN |
| 2.4 Add URL patterns | S | GREEN |
| 2.5 Write serializers (optional DRF) | S | GREEN |
| 2.6 Refactor/cleanup | S | REFACTOR |

### Phase 3: UI Components (Est. 4 hours)

**Goal:** Create reusable thumbs rating component and integrate.

| Task | Effort | TDD Phase |
|------|--------|-----------|
| 3.1 Write E2E tests for component | M | RED |
| 3.2 Create thumbs_rating partial | M | GREEN |
| 3.3 Add Alpine.js interactivity | M | GREEN |
| 3.4 Integrate into Engineering Insights | S | GREEN |
| 3.5 Integrate into PR expanded row | S | GREEN |
| 3.6 Integrate into Q&A response | S | GREEN |
| 3.7 Style with Easy Eyes theme | S | REFACTOR |

### Phase 4: PostHog Survey (Est. 2 hours)

**Goal:** Add floating feedback button with PostHog survey.

| Task | Effort | TDD Phase |
|------|--------|-----------|
| 4.1 Configure survey in PostHog dashboard | S | N/A |
| 4.2 Write E2E test for button | S | RED |
| 4.3 Add floating button to base template | S | GREEN |
| 4.4 Style button with Easy Eyes theme | S | GREEN |
| 4.5 Test survey flow manually | S | VERIFY |

### Phase 5: Analytics Events (Est. 1 hour)

**Goal:** Fire PostHog events alongside DB writes.

| Task | Effort | TDD Phase |
|------|--------|-----------|
| 5.1 Write analytics tests | S | RED |
| 5.2 Add llm_feedback_submitted event | S | GREEN |
| 5.3 Add properties: content_type, rating, has_comment | S | GREEN |
| 5.4 Verify in PostHog dashboard | S | VERIFY |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PostHog survey not loading | Low | Medium | Fallback to custom modal |
| Large JSON snapshots | Medium | Low | Limit snapshot size, compress |
| Users don't provide feedback | Medium | Medium | Make it frictionless, 1-click |
| Breaking existing templates | Low | High | E2E tests before/after |

---

## Success Metrics

| Metric | Target (Week 1) | Target (Month 1) |
|--------|-----------------|------------------|
| Feedback submissions/day | 10+ | 50+ |
| Negative feedback rate | <30% | <20% (after prompt improvements) |
| PostHog survey responses | 5+ | 20+ |
| Export command usage | 1+ | Weekly usage |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| PostHog API key | Ready | In .env |
| PostHog survey feature | Requires setup | Configure in PostHog dashboard |
| HTMX | Ready | Already in base template |
| Alpine.js | Ready | Already in base template |

---

## Testing Strategy

### Unit Tests (pytest)
- Model validation (required fields, choices)
- Factory correctness
- View permissions (team isolation)
- Export command output format

### Integration Tests (pytest-django)
- Feedback submission with valid/invalid data
- Team scoping (user can only see own team's feedback)
- Analytics event firing

### E2E Tests (Playwright)
- Thumbs rating click and persistence
- Comment modal flow
- PostHog survey button visibility
- Rating state on page reload

---

## Files to Create

| File | Purpose |
|------|---------|
| `apps/feedback/models.py` | Add LLMFeedback model |
| `apps/feedback/factories.py` | Add LLMFeedbackFactory |
| `apps/feedback/tests/test_llm_feedback.py` | Model and view tests |
| `apps/feedback/views.py` | Add submit/get feedback views |
| `apps/feedback/urls.py` | Add URL patterns |
| `templates/feedback/partials/thumbs_rating.html` | Reusable component |
| `templates/feedback/partials/feedback_modal.html` | Comment modal |
| `apps/feedback/management/commands/export_llm_feedback.py` | Export command |
| `tests/e2e/llm-feedback.spec.ts` | E2E tests |

---

## Files to Modify

| File | Changes |
|------|---------|
| `templates/metrics/partials/engineering_insights.html` | Add thumbs rating |
| `templates/metrics/pull_requests/partials/expanded_row.html` | Add thumbs rating |
| `templates/insights/partials/answer_response.html` | Add thumbs rating |
| `templates/web/app/app_base.html` | Add PostHog survey button |
| `apps/utils/analytics.py` | Add track_llm_feedback helper |

---

## Technical Notes

### HTMX Pattern for Thumbs Rating

```html
<div x-data="{ rated: null, showComment: false }">
  <button
    hx-post="{% url 'feedback:submit_llm' %}"
    hx-vals='{"content_type": "pr_summary", "content_id": "{{ pr.id }}", "rating": "true"}'
    hx-swap="none"
    @htmx:after-request="rated = 'up'"
    :class="{ 'text-success': rated === 'up' }">
    👍
  </button>
  ...
</div>
```

### Content Snapshot Format

```json
{
  "content_type": "pr_summary",
  "snapshot": {
    "summary": { "title": "...", "description": "..." },
    "health": { "scope": "medium", "risk": "low" },
    "ai": { "is_assisted": true, "tools": ["claude_code"] }
  },
  "input": {
    "pr_id": 123,
    "title": "...",
    "body": "...",
    "files_changed": 5
  },
  "prompt_version": "5.0.0"
}
```

### Export Command Usage

```bash
# Export all negative PR summary feedback
python manage.py export_llm_feedback --type=pr_summary --rating=negative --format=json

# Export for promptfoo evaluation
python manage.py export_llm_feedback --type=engineering_insight --format=promptfoo
```
