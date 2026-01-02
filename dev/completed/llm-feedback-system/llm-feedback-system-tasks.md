# LLM Feedback System - Tasks

**Last Updated:** 2026-01-02

---

## TDD Workflow Reminder

For each feature:
1. **RED** - Write failing test first
2. **GREEN** - Write minimum code to pass
3. **REFACTOR** - Improve code while keeping tests green

For UI changes:
1. **E2E FIRST** - Write Playwright test for expected behavior
2. **Verify current state** - Run test to confirm it fails
3. **Implement** - Build the feature
4. **Verify** - Run test to confirm it passes

---

## Phase 0: Baseline E2E Tests [S] - Est. 30 min

**Goal:** Capture current behavior before changes to prevent regressions.

- [ ] **0.1 Create E2E test file** [S]
  - File: `tests/e2e/llm-feedback.spec.ts`
  - Add: Test imports and helpers
  - Acceptance: File exists, can run empty test

- [ ] **0.2 Baseline test: Engineering Insights loads** [S]
  - Test: Navigate to dashboard, wait for insights partial to load via HTMX
  - Assert: Insight content is visible
  - Acceptance: Test passes with current code

- [ ] **0.3 Baseline test: PR expanded row loads** [S]
  - Test: Navigate to PR list, expand a row
  - Assert: LLM summary section is visible
  - Acceptance: Test passes with current code

- [ ] **0.4 Baseline test: Q&A response loads** [S]
  - Test: Ask a question, wait for response
  - Assert: Answer content is visible
  - Acceptance: Test passes with current code

---

## Phase 1: Data Layer (TDD) [M] - Est. 4 hours

**Goal:** Create `LLMFeedback` model with full test coverage.

### 1.1 Model Tests (RED)

- [ ] **1.1.1 Write model field tests** [S]
  - File: `apps/feedback/tests/test_llm_feedback.py` (new)
  - Tests:
    - `test_llm_feedback_requires_rating`
    - `test_llm_feedback_requires_content_type`
    - `test_llm_feedback_requires_user`
    - `test_llm_feedback_content_type_choices_valid`
  - Acceptance: Tests fail (model doesn't exist yet)

- [ ] **1.1.2 Write model relationship tests** [S]
  - Tests:
    - `test_llm_feedback_can_link_to_pull_request`
    - `test_llm_feedback_can_link_to_daily_insight`
    - `test_llm_feedback_belongs_to_team`
  - Acceptance: Tests fail

- [ ] **1.1.3 Write snapshot storage tests** [S]
  - Tests:
    - `test_llm_feedback_stores_json_snapshot`
    - `test_llm_feedback_stores_input_context`
    - `test_llm_feedback_stores_prompt_version`
  - Acceptance: Tests fail

### 1.2 Model Implementation (GREEN)

- [ ] **1.2.1 Create LLMFeedback model** [M]
  - File: `apps/feedback/models.py`
  - Add: `LLMFeedback` class with all fields
  - Acceptance: All model tests pass

- [ ] **1.2.2 Create migration** [S]
  - Command: `python manage.py makemigrations feedback --name add_llm_feedback_model`
  - Acceptance: Migration file created, applies cleanly

- [ ] **1.2.3 Create factory** [S]
  - File: `apps/feedback/factories.py`
  - Add: `LLMFeedbackFactory`
  - Acceptance: Factory can create valid instances

### 1.3 Admin & Export (TDD)

- [ ] **1.3.1 Add Django admin** [S]
  - File: `apps/feedback/admin.py`
  - Add: `LLMFeedbackAdmin` with list_display, list_filter, search
  - Acceptance: Model visible in admin

- [ ] **1.3.2 Write export command tests** [M] (RED)
  - File: `apps/feedback/tests/test_export_command.py` (new)
  - Tests:
    - `test_export_all_feedback`
    - `test_export_filtered_by_type`
    - `test_export_filtered_by_rating`
    - `test_export_json_format`
    - `test_export_csv_format`
  - Acceptance: Tests fail

- [ ] **1.3.3 Create export command** [M] (GREEN)
  - File: `apps/feedback/management/commands/export_llm_feedback.py`
  - Args: `--type`, `--rating`, `--format`, `--output`
  - Acceptance: All export tests pass

### 1.4 Refactor

- [ ] **1.4.1 Add indexes for common queries** [S]
  - Index on: `(content_type, rating)`, `(team, created_at)`
  - Acceptance: Migration applies, queries use indexes

---

## Phase 2: API Layer (TDD) [M] - Est. 3 hours

**Goal:** Create views for submitting and retrieving feedback.

### 2.1 View Tests (RED)

- [ ] **2.1.1 Write submit feedback view tests** [M]
  - File: `apps/feedback/tests/test_views.py` (extend existing)
  - Tests:
    - `test_submit_llm_feedback_creates_record`
    - `test_submit_llm_feedback_requires_auth`
    - `test_submit_llm_feedback_team_scoped`
    - `test_submit_llm_feedback_fires_posthog_event`
    - `test_submit_llm_feedback_htmx_response`
  - Acceptance: Tests fail

- [ ] **2.1.2 Write get feedback view tests** [S]
  - Tests:
    - `test_get_llm_feedback_returns_existing`
    - `test_get_llm_feedback_returns_null_if_none`
    - `test_get_llm_feedback_team_scoped`
  - Acceptance: Tests fail

- [ ] **2.1.3 Write update rating tests** [S]
  - Tests:
    - `test_resubmit_updates_existing_rating`
    - `test_resubmit_clears_old_comment`
  - Acceptance: Tests fail

### 2.2 View Implementation (GREEN)

- [ ] **2.2.1 Create submit_llm_feedback view** [M]
  - File: `apps/feedback/views.py`
  - Method: POST
  - Logic: Create or update LLMFeedback, fire PostHog event
  - Acceptance: Submit tests pass

- [ ] **2.2.2 Create get_llm_feedback view** [S]
  - Method: GET
  - Returns: JSON with rating if exists, null if not
  - Acceptance: Get tests pass

- [ ] **2.2.3 Add URL patterns** [S]
  - File: `apps/feedback/urls.py`
  - Add to `team_urlpatterns`:
    - `llm/submit/`
    - `llm/<content_type>/<content_id>/`
  - Acceptance: URLs resolve correctly

### 2.3 Analytics Integration

- [ ] **2.3.1 Add track_llm_feedback helper** [S]
  - File: `apps/utils/analytics.py`
  - Event: `llm_feedback_submitted`
  - Properties: content_type, rating, has_comment, team_slug
  - Acceptance: Helper function works with tests

---

## Phase 3: UI Components (E2E First) [L] - Est. 5 hours

**Goal:** Create reusable thumbs rating component with HTMX/Alpine.js.

### 3.1 E2E Tests (RED) - Run First!

- [ ] **3.1.1 Write E2E: thumbs buttons appear** [M]
  - Test: After page load, thumbs up/down buttons visible on insights
  - File: `tests/e2e/llm-feedback.spec.ts`
  - Acceptance: Test fails (buttons don't exist yet)

- [ ] **3.1.2 Write E2E: rating click updates UI** [M]
  - Test: Click thumbs up, button shows selected state
  - Assert: Class changes to indicate selection
  - Acceptance: Test fails

- [ ] **3.1.3 Write E2E: rating persists on reload** [M]
  - Test: Rate, reload page, rating still shown
  - Assert: Button still has selected state
  - Acceptance: Test fails

- [ ] **3.1.4 Write E2E: rating works in HTMX partial** [M]
  - Test: Navigate away, come back, load HTMX partial, click rating
  - Assert: Rating works after HTMX swap
  - Acceptance: Test fails

- [ ] **3.1.5 Write E2E: comment modal flow** [M]
  - Test: Rate, comment button appears, click opens modal, submit saves
  - Acceptance: Test fails

### 3.2 Component Implementation (GREEN)

- [ ] **3.2.1 Create thumbs_rating.html partial** [M]
  - File: `templates/feedback/partials/thumbs_rating.html`
  - Context: `content_type`, `content_id`, `snapshot_json`
  - Features: Alpine.js state, HTMX submit, visual feedback
  - Acceptance: Partial renders without errors

- [ ] **3.2.2 Add data-testid attributes** [S]
  - Add: `data-testid="thumbs-up"`, `data-testid="thumbs-down"`
  - Acceptance: E2E tests can locate elements

- [ ] **3.2.3 Add Alpine.js store for feedback state** [M]
  - File: `assets/javascript/alpine.js`
  - Add: `Alpine.store('feedback', {...})` for state persistence
  - Acceptance: State persists across HTMX swaps

- [ ] **3.2.4 Create feedback_modal.html partial** [S]
  - File: `templates/feedback/partials/feedback_modal.html`
  - Features: Comment textarea, submit button
  - Acceptance: Modal opens/closes correctly

### 3.3 Template Integrations (GREEN)

- [ ] **3.3.1 Integrate into Engineering Insights** [S]
  - File: `templates/metrics/partials/engineering_insights.html`
  - Add: `{% include "feedback/partials/thumbs_rating.html" %}`
  - Pass: content_type="engineering_insight", content_id, snapshot
  - Acceptance: E2E test 3.1.1 passes

- [ ] **3.3.2 Integrate into PR Expanded Row** [S]
  - File: `templates/metrics/pull_requests/partials/expanded_row.html`
  - Add: Include in LLM summary section
  - Pass: content_type="pr_summary", pr.id, pr.llm_summary
  - Acceptance: Thumbs visible in expanded row

- [ ] **3.3.3 Integrate into Q&A Response** [S]
  - File: `templates/insights/partials/answer_response.html`
  - Add: Include after answer text
  - Pass: content_type="qa_answer", unique ID
  - Acceptance: Thumbs visible after answers

### 3.4 Styling (REFACTOR)

- [ ] **3.4.1 Style with Easy Eyes theme** [S]
  - Use: `text-success` for thumbs up active
  - Use: `text-error` for thumbs down active
  - Use: `text-base-content/50` for inactive
  - Acceptance: Matches design system

- [ ] **3.4.2 Add hover/focus states** [S]
  - Add: Hover transitions, focus ring
  - Acceptance: Accessible, looks polished

- [ ] **3.4.3 Verify all E2E tests pass** [M]
  - Run: `npx playwright test tests/e2e/llm-feedback.spec.ts`
  - Acceptance: All tests pass

---

## Phase 4: PostHog Survey Button [S] - Est. 2 hours

### 4.1 E2E Test (RED)

- [ ] **4.1.1 Write E2E: feedback button visible** [S]
  - Test: On any authenticated page, floating button visible
  - Assert: Button in bottom-right corner
  - Acceptance: Test fails (button doesn't exist)

### 4.2 Implementation (GREEN)

- [ ] **4.2.1 Configure survey in PostHog** [S]
  - Go to: PostHog Dashboard > Surveys
  - Create: "General Product Feedback" survey
  - Type: Popup with multiple choice + open text
  - Note: Record survey ID for next step

- [ ] **4.2.2 Add floating button to base template** [S]
  - File: `templates/web/app/app_base.html`
  - Add: Fixed position button, bottom-right
  - OnClick: `posthog.renderSurvey('{{ survey_id }}')`
  - Acceptance: Button visible on all pages

- [ ] **4.2.3 Style button** [S]
  - Use: `btn-primary btn-circle shadow-lg`
  - Add: Feedback icon (message or chat bubble)
  - Acceptance: Matches Easy Eyes theme

- [ ] **4.2.4 Verify E2E test passes** [S]
  - Run: E2E test for button visibility
  - Acceptance: Test passes

---

## Phase 5: Analytics Events [S] - Est. 1 hour

### 5.1 Tests (RED)

- [ ] **5.1.1 Write analytics event tests** [S]
  - File: `apps/utils/tests/test_analytics.py` (extend)
  - Tests:
    - `test_track_llm_feedback_event`
    - `test_llm_feedback_event_properties`
  - Acceptance: Tests fail

### 5.2 Implementation (GREEN)

- [ ] **5.2.1 Add event in submit view** [S]
  - File: `apps/feedback/views.py`
  - Call: `track_event(user, "llm_feedback_submitted", {...})`
  - Properties: content_type, rating, has_comment, team_slug
  - Acceptance: Tests pass

- [ ] **5.2.2 Verify in PostHog** [S]
  - Action: Submit feedback, check PostHog Live events
  - Acceptance: Event appears with correct properties

---

## Phase 6: Documentation & Cleanup [S] - Est. 1 hour

- [ ] **6.1 Update CLAUDE.md** [S]
  - Add: Section on LLM feedback system
  - Document: Model, views, component usage

- [ ] **6.2 Add component usage examples** [S]
  - Add: Comment in thumbs_rating.html with usage example
  - Document: Required context variables

- [ ] **6.3 Run full test suite** [M]
  - Command: `make test`
  - Acceptance: All tests pass, no regressions

- [ ] **6.4 Run E2E smoke tests** [S]
  - Command: `make e2e-smoke`
  - Acceptance: All smoke tests pass

- [ ] **6.5 Clean up any debug code** [S]
  - Remove: console.logs, test events
  - Acceptance: No debug code in production

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 0: Baseline E2E | 4 | 0 | Deferred |
| Phase 1: Data Layer | 10 | 10 | ✅ Complete |
| Phase 2: API Layer | 7 | 7 | ✅ Complete |
| Phase 3: UI Components | 14 | 0 | Deferred |
| Phase 4: PostHog Survey | 4 | 4 | ✅ Complete |
| Phase 5: Analytics | 3 | 3 | ✅ Complete |
| Phase 6: Documentation | 5 | 3 | 🔄 In Progress |
| **Total** | **47** | **27** | **~60%** |

**Note:** Phases 0 & 3 (E2E tests, UI components) are deferred - core backend is complete.

---

## Execution Order

**CRITICAL: Follow this order for TDD compliance**

1. Phase 0 (Baseline E2E) - Must pass before any changes
2. Phase 1.1 (Model tests) - RED
3. Phase 1.2 (Model implementation) - GREEN
4. Phase 1.3 (Admin/Export) - RED then GREEN
5. Phase 2.1 (View tests) - RED
6. Phase 2.2 (View implementation) - GREEN
7. Phase 3.1 (E2E tests) - RED - **Run and verify they fail!**
8. Phase 3.2-3.4 (UI implementation) - GREEN
9. Phase 4.1 (Survey E2E) - RED
10. Phase 4.2 (Survey implementation) - GREEN
11. Phase 5 (Analytics)
12. Phase 6 (Cleanup)

---

## Quick Commands

```bash
# Run model tests only
pytest apps/feedback/tests/test_llm_feedback.py -v

# Run view tests only
pytest apps/feedback/tests/test_views.py -v

# Run E2E feedback tests
npx playwright test tests/e2e/llm-feedback.spec.ts --reporter=list

# Run all E2E tests
make e2e

# Export feedback for prompt tuning
python manage.py export_llm_feedback --type=pr_summary --rating=negative
```
