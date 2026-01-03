# Integration Feature Flags - Tasks

**Last Updated:** 2026-01-03
**Status:** In Progress

---

## Phase 1: Flag Infrastructure (S - 1hr)

### TDD: Write Failing Tests First
- [ ] Create `apps/integrations/tests/test_integration_flags.py`
- [ ] Write `test_integration_disabled_by_default`
- [ ] Write `test_integration_enabled_when_flag_active`
- [ ] Write `test_google_workspace_always_coming_soon`
- [ ] Write `test_get_enabled_onboarding_steps_none`
- [ ] Write `test_get_enabled_onboarding_steps_both`
- [ ] Verify all tests FAIL (RED phase)

### Implementation
- [ ] Create `apps/teams/migrations/0008_add_integration_flags.py`
- [ ] Create `apps/integrations/services/integration_flags.py`
- [ ] Implement `is_integration_enabled(request, integration_name)`
- [ ] Implement `get_all_integration_statuses(request)`
- [ ] Implement `IntegrationStatus` dataclass
- [ ] Run migration: `make migrate`
- [ ] Verify all tests PASS (GREEN phase)

### Refactor
- [ ] Review code for improvements
- [ ] Ensure tests still pass

---

## Phase 2: Integration Page UI (M - 2hr)

### TDD: Write Failing Tests First
- [ ] Write test for integration page passing flag context
- [ ] Write test for Coming Soon badge display
- [ ] Write test for "I'm Interested" button visibility
- [ ] Verify tests FAIL (RED phase)

### Implementation
- [ ] Update `integrations_home` view to pass `integration_statuses` context
- [ ] Create `apps/integrations/templates/integrations/components/integration_card.html`
- [ ] Update `home.html` to use card component
- [ ] Add Google Workspace card (always Coming Soon)
- [ ] Style Coming Soon state with badge
- [ ] Verify tests PASS (GREEN phase)

### Refactor
- [ ] Extract common card styles
- [ ] Ensure templates are DRY

---

## Phase 3: Interest Tracking (S - 1hr)

### TDD: Write Failing Tests First
- [ ] Write `test_track_interest_success`
- [ ] Write `test_track_interest_invalid_integration`
- [ ] Write `test_track_interest_htmx_returns_partial`
- [ ] Verify tests FAIL (RED phase)

### Implementation
- [ ] Add `track_integration_interest` view to `status.py`
- [ ] Add URL route `interest/` to `urls.py`
- [ ] Create `interest_confirmed.html` partial
- [ ] Integrate PostHog `track_event`
- [ ] Verify tests PASS (GREEN phase)

### Refactor
- [ ] Review HTMX flow
- [ ] Ensure error handling is robust

---

## Phase 4: Onboarding Flow (M - 2hr)

### TDD: Write Failing Tests First
- [ ] Create `apps/onboarding/tests/test_flag_skip.py`
- [ ] Write `test_jira_step_skipped_when_disabled`
- [ ] Write `test_jira_step_shown_when_enabled`
- [ ] Write `test_slack_step_skipped_when_disabled`
- [ ] Write `test_onboarding_completes_with_no_optional_steps`
- [ ] Verify tests FAIL (RED phase)

### Implementation
- [ ] Add `_get_next_onboarding_step()` helper to `views.py`
- [ ] Update `sync_progress` view to use helper for redirect
- [ ] Update `connect_jira` view with flag check (redirect if disabled)
- [ ] Update `connect_slack` view with flag check (redirect if disabled)
- [ ] Verify tests PASS (GREEN phase)

### Refactor
- [ ] Consider edge cases
- [ ] Ensure redirect logic is clear

---

## Phase 5: E2E Testing & Polish (S - 1hr)

### Playwright Tests
- [ ] Create `tests/e2e/integration-flags.spec.ts`
- [ ] Test: Integration page shows Coming Soon badges when flags off
- [ ] Test: "I'm Interested" button shows and works
- [ ] Test: Button changes to "Thanks!" after click
- [ ] Test: Google Workspace always shows Coming Soon
- [ ] Run tests: `make e2e`

### Manual Verification
- [ ] Start dev server: `make dev`
- [ ] Navigate to integration page
- [ ] Verify all integrations show Coming Soon (flags off by default)
- [ ] Click "I'm Interested" - verify button changes
- [ ] Check PostHog for events

### Final Checks
- [ ] All unit tests pass: `make test`
- [ ] All E2E tests pass: `make e2e`
- [ ] No lint errors: `make ruff`
- [ ] Ready for commit

---

## Completion Checklist

- [ ] Phase 1 complete (Flag Infrastructure)
- [ ] Phase 2 complete (Integration Page UI)
- [ ] Phase 3 complete (Interest Tracking)
- [ ] Phase 4 complete (Onboarding Flow)
- [ ] Phase 5 complete (E2E Testing)
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Ready for PR
